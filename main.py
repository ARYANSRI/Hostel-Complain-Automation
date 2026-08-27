import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Configure basic logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

from config import NOTION_TOKEN, COMPLAINTS_DATABASE_ID, VENDORS_DATABASE_ID
from services import (
    parse_complaint, decide_status, create_complaint_row, 
    check_approvals, get_vendor, check_resolutions, mark_resolution_email_sent
)
from dispatch.email import notify_vendor, notify_student_resolved
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Hostel Maintenance API")

# Mount static directory for background images and assets
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware to allow cross-origin requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import Optional
class ComplaintRequest(BaseModel):
    room: str
    text: str
    email: Optional[str] = None

# In-memory database to store complaints temporarily so you can view them on the web
complaints_db = []
# Set to track IDs of already dispatched complaints to prevent duplicate emails
dispatched_records = set()

from fastapi.responses import FileResponse

@app.get("/")
async def serve_frontend():
    """
    Serve the frontend HTML directly from FastAPI to avoid 'file://' security blocks in the browser.
    """
    return FileResponse("index.html")

@app.get("/complaints")
async def view_complaints():
    """
    Visit http://127.0.0.1:8080/complaints in your browser to see all submitted complaints!
    """
    return complaints_db

@app.post("/submit-complaint")
async def submit_complaint(complaint: ComplaintRequest):
    logger.info(f"\n================================")
    logger.info(f"NEW COMPLAINT RECEIVED!")
    logger.info(f"Room: {complaint.room}")
    logger.info(f"Email: {complaint.email}")
    logger.info(f"Text: {complaint.text}")
    logger.info(f"================================\n")

    if not NOTION_TOKEN or not COMPLAINTS_DATABASE_ID or not VENDORS_DATABASE_ID:
        logger.error("Configuration missing: Check NOTION_TOKEN, COMPLAINTS_DATABASE_ID, or VENDORS_DATABASE_ID.")
        return {
            "success": False,
            "error": "Unable to process complaint"
        }

    try:
        # 1. Parse via Gemini API
        parsed_data = parse_complaint(complaint.text)
        category = parsed_data.get("category", "Other")
        urgency = parsed_data.get("urgency", "Medium")
        
        # Determine room location: prioritize explicitly provided room, fallback to AI extraction
        room_block = complaint.room.strip() if complaint.room.strip() else parsed_data.get("room_block")

        # 2. Decide the initial status (e.g. 'Pending Warden Approval' vs fast-tracked 'Approved')
        status = decide_status(urgency, category)
        
        # 3. Look up vendor in the Vendors Notion database
        vendor_info = get_vendor(category, NOTION_TOKEN, VENDORS_DATABASE_ID)
        vendor_name = vendor_info["name"]
        vendor_email = vendor_info["email"]

        # 4. Compile the payload for Notion
        row_data = {
            "room_block": room_block,
            "raw_text": complaint.text,
            "urgency": urgency,
            "category": category,
            "status": status,
            "vendor_assigned": vendor_name,
            "student_email": complaint.email
        }

        # 5. Create the row in the Notion database
        result = create_complaint_row(row_data, NOTION_TOKEN, COMPLAINTS_DATABASE_ID)
        
        # Save to our temporary in-memory database to show on the webpage
        record = row_data.copy()
        record["id"] = result.get("notion_id", f"mock_id_{len(complaints_db)}")
        record["vendor_email"] = vendor_email
        complaints_db.append(record)

        # Return exactly the requested top-level response structure
        return {
            "success": True,
            "parsed_data": {
                "category": category,
                "urgency": urgency,
                "room_block": room_block,
                "status": status,
                "vendor_assigned": vendor_name
            }
        }

    except Exception as e:
        # Gracefully handle exception without exposing details or stack traces
        logger.error(f"Error processing complaint: {type(e).__name__} - {str(e)}")
        return {
            "success": False,
            "error": "Unable to process complaint"
        }

@app.post("/run-dispatch")
async def run_dispatch():
    """
    Simulates a background cron job or manual trigger to check Notion for approved complaints
    and dispatch them to the respective vendors via Mailtrap.
    """
    # 1. Retrieve all Warden-approved complaints from Notion
    approved_complaints = check_approvals(NOTION_TOKEN, COMPLAINTS_DATABASE_ID)
    
    # Also grab any fast-tracked "Auto-Approved" complaints from our in-memory DB for local testing
    for c in complaints_db:
        if c.get("status") == "Auto-Approved" and c["id"] not in dispatched_records:
            if not any(ac.get("id") == c["id"] for ac in approved_complaints):
                approved_complaints.append(c)

    if not approved_complaints:
        # We don't return early here anymore because we still need to check 
        # for resolution emails below, even if there are no approvals.
        pass
        
    dispatched_count = 0
    
    for complaint in approved_complaints:
        complaint_id = complaint.get("id")
        
        # 2. Safeguard against duplicate emails
        if complaint_id in dispatched_records:
            continue
            
        # 3. Identify vendor email
        # Get from memory/Notion data if it was set, otherwise fallback to lookup
        vendor_email = complaint.get("vendor_email")
        if not vendor_email:
            category = complaint.get("category", "Other")
            vendor_info = get_vendor(category, NOTION_TOKEN, VENDORS_DATABASE_ID)
            vendor_email = vendor_info["email"]
        
        logger.info(f"Calling notify_vendor() for complaint {complaint_id}...")
        
        # 4. Call notify_vendor() (Mailtrap)
        notify_result = notify_vendor(vendor_email, complaint)
        
        if notify_result.get("success"):
            logger.info(f"Vendor notification successful for complaint {complaint_id}")
            
            # 5. Update status appropriately (track locally to avoid duplicate dispatch)
            dispatched_records.add(complaint_id)
            
            # Update the Notion row status to 'Dispatched'
            from services import update_complaint_status
            update_success = update_complaint_status(complaint_id, "Dispatched", NOTION_TOKEN)
            if update_success:
                logger.info(f"Successfully marked complaint {complaint_id} as Dispatched in Notion.")
            else:
                logger.warning(f"Failed to mark complaint {complaint_id} as Dispatched in Notion.")
            
            # Also update local fallback state
            for db_record in complaints_db:
                if db_record.get("id") == complaint_id:
                    db_record["status"] = "Dispatched"
                    
            dispatched_count += 1
        else:
            logger.error(f"Vendor notification failed: {notify_result.get('message')}")

    # ==========================================
    # RESOLUTION NOTIFICATION (Student Email)
    # ==========================================
    resolved_count = 0
    resolved_complaints = check_resolutions(NOTION_TOKEN, COMPLAINTS_DATABASE_ID)
    
    for complaint in resolved_complaints:
        complaint_id = complaint.get("id")
        student_email = complaint.get("student_email")
        
        if not student_email:
            logger.warning(f"Resolved complaint {complaint_id} has no student email. Skipping.")
            continue
            
        logger.info(f"Resolved complaint detected: {complaint_id}")
        logger.info(f"Student email available: yes")
        logger.info(f"Sending resolution notification to {student_email}...")
        
        notify_result = notify_student_resolved(student_email, complaint)
        
        if notify_result.get("success"):
            logger.info(f"Resolution email sent successfully for complaint {complaint_id}")
            logger.info("Updating Resolution Email Sent in Notion...")
            update_success = mark_resolution_email_sent(complaint_id, NOTION_TOKEN)
            if update_success:
                logger.info(f"Successfully marked Resolution Email Sent for {complaint_id}")
            else:
                logger.warning(f"Failed to mark Resolution Email Sent for {complaint_id}")
            resolved_count += 1
        else:
            logger.error(f"Resolution email failed: {notify_result.get('message')}")

    return {
        "message": f"Successfully dispatched {dispatched_count} complaints to vendors. Sent {resolved_count} resolution emails."
    }

# ==========================================
# BACKGROUND AUTOMATION (Render / Production)
# ==========================================
import asyncio

async def auto_dispatch_loop():
    """
    Background worker that continuously checks for Warden approvals every 30 seconds
    and triggers the dispatch logic automatically.
    """
    while True:
        try:
            # We don't want to log every 30 seconds if nothing happened, so we rely on 
            # run_dispatch's internal logging only when it finds something to do.
            await run_dispatch()
        except Exception as e:
            logger.error(f"Error in automatic dispatch background loop: {e}")
            
        await asyncio.sleep(30) # Wait 30 seconds before polling Notion again

@app.on_event("startup")
async def startup_event():
    """
    When FastAPI starts (e.g. on Render), spawn the auto_dispatch_loop in the background.
    """
    logger.info("Starting background auto-dispatch scanner (checks every 30s)...")
    asyncio.create_task(auto_dispatch_loop())

import os
import json
import logging
from google import genai
from google.genai import types

import re
import requests

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field

class ComplaintSchema(BaseModel):
    category: str = Field(description="Must be exactly one of: Electrical, Plumbing, WiFi, Furniture, Other")
    urgency: str = Field(description="Must be exactly one of: Low, Medium, High")
    room_block: str | None = Field(description="Use null when room/block cannot be identified", default=None)

def heuristic_parse_complaint(text: str) -> dict:
    """
    Intelligent rule-based parser used as fallback when Gemini API key is not configured
    or when rate limits/quotas are exceeded.
    """
    t = (text or "").lower()
    
    # 1. Detect Category
    if any(k in t for k in ["fan", "light", "bulb", "switch", "socket", "wire", "wiring", "power", "electricity", "short circuit", "spark", "current", "geyser", "ac", "air condition", "cooler", "plug"]):
        category = "Electrical"
    elif any(k in t for k in ["tap", "faucet", "pipe", "leak", "water", "drain", "sink", "flush", "toilet", "washroom", "bathroom", "plumb", "clog", "sewage", "shower", "basin"]):
        category = "Plumbing"
    elif any(k in t for k in ["wifi", "wi-fi", "internet", "router", "lan", "network", "ethernet", "connection", "broadband", "speed"]):
        category = "WiFi"
    elif any(k in t for k in ["chair", "table", "desk", "bed", "door", "lock", "handle", "latch", "cupboard", "almirah", "wardrobe", "window", "furniture", "wood", "hinge", "mattress", "curtain"]):
        category = "Furniture"
    else:
        category = "Other"
        
    # 2. Detect Urgency
    if any(k in t for k in ["urgent", "emergency", "immediately", "shock", "fire", "sparking", "flood", "overflow", "danger", "burst", "severe", "critical", "broken completely"]):
        urgency = "High"
    elif any(k in t for k in ["minor", "small", "loose", "slight", "sometime", "paint", "creak", "slow"]):
        urgency = "Low"
    else:
        urgency = "Medium"
        
    # 3. Detect Room / Block
    room_block = None
    room_match = re.search(r'\b(?:room\s*(?:no\.?|#)?\s*([a-zA-Z0-9\-]+)|([a-zA-Z][\-\s]?\d{2,4})|(\d{3,4}))\b', text, re.IGNORECASE)
    if room_match:
        room_block = room_match.group(0).strip()
        
    return {
        "category": category,
        "urgency": urgency,
        "room_block": room_block
    }

def parse_complaint(text):
    """
    Parses a raw hostel complaint text using Gemini to extract structured JSON.
    Expected output keys: category, urgency, room_block
    Falls back to heuristic analysis if Gemini API key is missing or quota is exhausted.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.info("GEMINI_API_KEY not configured, using FixBit smart heuristic parser.")
        return heuristic_parse_complaint(text)
    
    primary_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    fallback_models = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash,gemini-1.5-flash,gemini-2.0-flash,gemini-3.5-flash,gemini-3.7-flash").split(",")
    fallback_models = [m.strip() for m in fallback_models if m.strip() and m.strip() != primary_model]
    
    models_to_try = [primary_model] + fallback_models
    
    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        "Analyze the student's messy hostel complaint. Extract category, urgency, and room/block location. "
        "Return ONLY valid JSON matching the schema. "
        "Category must be exactly one of: Electrical, Plumbing, WiFi, Furniture, Other. "
        "Urgency must be exactly one of: Low, Medium, High. "
        "Use null when room/block cannot be identified. "
        "Do not add explanations, markdown, or extra text."
    )
    
    for model_name in models_to_try:
        try:
            logger.info(f"Attempting Gemini parse with model: {model_name}")
            
            response = client.models.generate_content(
                model=model_name,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ComplaintSchema
                )
            )
            
            raw_json = response.text
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:-3].strip()
            elif raw_json.startswith("```"):
                raw_json = raw_json[3:-3].strip()
                
            parsed_data = json.loads(raw_json)
            
            category = parsed_data.get("category", "Other")
            if category not in ["Electrical", "Plumbing", "WiFi", "Furniture", "Other"]:
                category = "Other"
                
            urgency = parsed_data.get("urgency", "Medium")
            if urgency not in ["Low", "Medium", "High"]:
                urgency = "Medium"
                
            room_block = parsed_data.get("room_block")
            
            logger.info(f"Gemini parse succeeded with model: {model_name}")
            return {
                "category": category,
                "urgency": urgency,
                "room_block": room_block
            }
            
        except json.JSONDecodeError:
            logger.warning(f"JSON parsing error from Gemini response (model: {model_name})")
            continue
        except Exception as e:
            error_msg = str(e).lower()
            is_rate_limit = "429" in str(e) or "resource_exhausted" in error_msg or "quota" in error_msg
            if is_rate_limit:
                logger.warning(f"Gemini rate limit exceeded for model '{model_name}'. Trying next fallback...")
                continue
            else:
                logger.warning(f"Gemini parse error with '{model_name}': {e}. Trying fallback...")
                continue
    
    # Fallback to heuristic parser if all Gemini models fail or quota is exhausted
    logger.info("All Gemini models exhausted or failed. Using smart heuristic fallback.")
    return heuristic_parse_complaint(text)

def decide_status(urgency, category):
    """
    Decides the initial status of the complaint.
    If urgency == "High" or category == "Other": return "Pending Approval"
    return "Auto-Approved"
    """
    if urgency == "High" or category == "Other":
        return "Pending Approval"
    return "Auto-Approved"


import requests

DEFAULT_VENDORS = {
    "Electrical": {"name": "ElectroFix Solutions", "email": "electrofix@hostel.local"},
    "Plumbing": {"name": "AquaRepair Services", "email": "aquarepair@hostel.local"},
    "WiFi": {"name": "NetCare Solutions", "email": "netcare@hostel.local"},
    "Furniture": {"name": "WoodWorks Carpentry", "email": "woodworks@hostel.local"},
    "Other": {"name": "Facility Maintenance Desk", "email": "facility@hostel.local"}
}

def create_complaint_row(data, notion_token, database_id):
    """
    Creates a new row in the Notion Complaints Database using the official Notion API.
    If Notion is not configured, returns a local mock record gracefully.
    """
    if not notion_token or not database_id:
        logger.info("Notion token/database not configured. Complaint recorded locally.")
        return {"status": "local", "notion_id": f"local_{abs(hash(data.get('raw_text', '')))}", "data": data}
        
    url = "https://api.notion.com/v1/pages"
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "parent": {
            "database_id": database_id
        },
        "properties": {
            "Complaint": {
                "title": [
                    {
                        "text": {
                            "content": f"Issue in {data.get('room_block', 'Unknown')}"
                        }
                    }
                ]
            },
            "Room/Block": {
                "rich_text": [
                    {
                        "text": {
                            "content": data.get("room_block", "Unknown")
                        }
                    }
                ]
            },
            "Raw Text": {
                "rich_text": [
                    {
                        "text": {
                            "content": data.get("raw_text", "")
                        }
                    }
                ]
            },
            "Category": {
                "select": {
                    "name": data.get("category", "Other")
                }
            },
            "Urgency": {
                "select": {
                    "name": data.get("urgency", "Medium")
                }
            },
            "Status": {
                "select": {
                    "name": data.get("status", "Pending Approval")
                }
            },
            "Vendor": {
                "rich_text": [
                    {
                        "text": {
                            "content": data.get("vendor_assigned", "Unassigned")
                        }
                    }
                ]
            }
        }
    }
    
    # Add Student Email if provided
    student_email = data.get("student_email")
    if student_email:
        payload["properties"]["Student Email"] = {
            "email": student_email
        }
        
    # Default Resolution Email Sent to False
    payload["properties"]["Resolution Email Sent"] = {
        "checkbox": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            response_data = response.json()
            return {
                "status": "success", 
                "notion_id": response_data["id"], 
                "data": data
            }
        else:
            logger.error(f"Notion API Error {response.status_code}: {response.text}")
            return {"status": "error", "notion_id": f"local_id_{abs(hash(data.get('raw_text', '')))}", "data": data}
    except Exception as e:
        logger.error(f"Failed to connect to Notion: {e}")
        return {"status": "error", "notion_id": f"local_id_{abs(hash(data.get('raw_text', '')))}", "data": data}

def check_approvals(notion_token, database_id):
    """
    Queries Notion for complaints that are approved and ready for dispatch.
    This means either Status is 'Auto-Approved', or Status is 'Pending Approval' AND 'Approved By' is not empty.
    """
    if not notion_token or not database_id:
        return []

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "filter": {
            "or": [
                {
                    "property": "Status",
                    "select": {
                        "equals": "Auto-Approved"
                    }
                },
                {
                    "and": [
                        {
                            "property": "Status",
                            "select": {
                                "equals": "Pending Approval"
                            }
                        },
                        {
                            "property": "Approved By",
                            "rich_text": {
                                "is_not_empty": True
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        approved_complaints = []
        for row in data.get("results", []):
            props = row["properties"]
            
            cat_prop = props.get("Category", {}).get("select")
            category = cat_prop.get("name") if cat_prop else "Other"
            
            urg_prop = props.get("Urgency", {}).get("select")
            urgency = urg_prop.get("name") if urg_prop else "Medium"
            
            room_rt = props.get("Room/Block", {}).get("rich_text", [])
            room_block = room_rt[0]["plain_text"] if room_rt else ""
            
            text_rt = props.get("Raw Text", {}).get("rich_text", [])
            raw_text = text_rt[0]["plain_text"] if text_rt else ""
            
            status_prop = props.get("Status", {}).get("select")
            status = status_prop.get("name") if status_prop else ""
            
            app_rt = props.get("Approved By", {}).get("rich_text", [])
            approved_by = app_rt[0]["plain_text"] if app_rt else ""
            
            approved_complaints.append({
                "id": row["id"],
                "category": category,
                "urgency": urgency,
                "room_block": room_block,
                "raw_text": raw_text,
                "status": status,
                "approved_by": approved_by
            })
            
        if approved_complaints:
            logger.info(f"Found {len(approved_complaints)} approved complaints ready for dispatch.")
        return approved_complaints
        
    except Exception as e:
        logger.error(f"Failed to fetch approvals from Notion: {e}")
        return []

def get_vendor(category, notion_token, vendors_database_id):
    """
    Queries the Vendors Notion database for a vendor matching the category.
    Falls back to sensible defaults if Notion is unconfigured or not found.
    """
    fallback = DEFAULT_VENDORS.get(category, DEFAULT_VENDORS["Other"])
    
    if not notion_token or not vendors_database_id:
        return {"name": fallback["name"], "email": fallback["email"]}

    url = f"https://api.notion.com/v1/databases/{vendors_database_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "filter": {
            "property": "Category",
            "select": {
                "equals": category
            }
        }
    }
    
    try:
        logger.info(f"Looking up vendor for category: {category}")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            logger.warning(f"No vendor found in Notion for category: {category}. Using default.")
            return {"name": fallback["name"], "email": fallback["email"]}
            
        row = results[0]
        props = row["properties"]
        
        email_prop = props.get("Email", {}).get("email") or fallback["email"]
        
        name_title = props.get("Vendor Name", {}).get("title", [])
        vendor_name = name_title[0]["plain_text"] if name_title else fallback["name"]
        
        logger.info(f"Vendor found: {vendor_name} | Vendor email: {email_prop}")
        return {"name": vendor_name, "email": email_prop}
        
    except Exception as e:
        logger.warning(f"Failed to fetch vendor from Notion: {e}. Using default fallback.")
        return {"name": fallback["name"], "email": fallback["email"]}

def update_complaint_status(complaint_id, new_status, notion_token):
    """
    Updates the Status of a complaint in Notion.
    """
    if not notion_token or not complaint_id or str(complaint_id).startswith("local"):
        return True

    url = f"https://api.notion.com/v1/pages/{complaint_id}"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "properties": {
            "Status": {
                "select": {
                    "name": new_status
                }
            }
        }
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to update complaint status in Notion: {e}")
        return False

def check_resolutions(notion_token, database_id):
    """
    Queries Notion for complaints that are Resolved but haven't had a resolution email sent.
    """
    if not notion_token or not database_id:
        return []

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "filter": {
            "and": [
                {
                    "property": "Status",
                    "select": {
                        "equals": "Resolved"
                    }
                },
                {
                    "property": "Student Email",
                    "email": {
                        "is_not_empty": True
                    }
                }
            ]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        resolved_complaints = []
        for row in data.get("results", []):
            props = row["properties"]
            
            res_email_sent_prop = props.get("Resolution Email Sent", {})
            if res_email_sent_prop.get("checkbox") is True:
                continue
            
            cat_prop = props.get("Category", {}).get("select")
            category = cat_prop.get("name") if cat_prop else "Other"
            
            room_rt = props.get("Room/Block", {}).get("rich_text", [])
            room_block = room_rt[0]["plain_text"] if room_rt else ""
            
            text_rt = props.get("Raw Text", {}).get("rich_text", [])
            raw_text = text_rt[0]["plain_text"] if text_rt else ""
            
            student_email_prop = props.get("Student Email", {}).get("email")
            
            resolved_complaints.append({
                "id": row["id"],
                "category": category,
                "room_block": room_block,
                "raw_text": raw_text,
                "status": "Resolved",
                "student_email": student_email_prop
            })
            
        if resolved_complaints:
            logger.info(f"Found {len(resolved_complaints)} resolved complaints needing notification.")
        return resolved_complaints
        
    except Exception as e:
        logger.error(f"Failed to fetch resolutions from Notion: {e}")
        return []

def mark_resolution_email_sent(complaint_id, notion_token):
    """
    Updates the Resolution Email Sent checkbox to True in Notion.
    """
    if not notion_token or not complaint_id or str(complaint_id).startswith("local"):
        return True

    url = f"https://api.notion.com/v1/pages/{complaint_id}"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "properties": {
            "Resolution Email Sent": {
                "checkbox": True
            }
        }
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to update Resolution Email Sent in Notion: {e}")
        return False

def describe_image_issue(image_bytes: bytes, mime_type: str = "image/jpeg", api_key: str | None = None, file_name: str | None = None):
    """
    Analyzes an uploaded image of a hostel maintenance issue using Gemini multimodal capabilities.
    Returns a clear, concise 1-2 sentence description of the maintenance problem.
    """
    resolved_api_key = api_key or os.getenv("GEMINI_API_KEY")
    
    if resolved_api_key:
        primary_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        fallback_models = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash,gemini-1.5-flash,gemini-2.0-flash,gemini-3.5-flash,gemini-3.7-flash,gemini-1.5-flash-8b").split(",")
        fallback_models = [m.strip() for m in fallback_models if m.strip() and m.strip() != primary_model]
        
        models_to_try = [primary_model] + fallback_models
        
        client = genai.Client(api_key=resolved_api_key)
        
        prompt = (
            "You are an assistant for a college hostel maintenance desk. "
            "Carefully examine this image provided by a student. "
            "Identify the primary maintenance, repair, or sanitation issue shown in the image "
            "(such as a broken chair, broken table/furniture, damaged door/lock, leaking pipe, broken tap/faucet, "
            "damaged electrical switch/socket, malfunctioning ceiling fan, broken window glass, wall seepage/mold, air conditioner leak, etc.). "
            "Write a clear, concise, direct 1 to 2 sentence problem description describing the exact issue that needs to be fixed. "
            "Do NOT write conversational filler like 'Here is the description' or 'In the image I see'. "
            "Output ONLY the direct maintenance complaint description."
        )
        
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            
            for model_name in models_to_try:
                try:
                    logger.info(f"Attempting Gemini image analysis with model: {model_name}")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[image_part, prompt],
                    )
                    
                    if response and response.text:
                        desc = response.text.strip()
                        if (desc.startswith('"') and desc.endswith('"')) or (desc.startswith("'") and desc.endswith("'")):
                            desc = desc[1:-1].strip()
                        logger.info(f"Gemini image analysis succeeded with model: {model_name}")
                        return {
                            "success": True,
                            "description": desc,
                            "model_used": model_name,
                            "mode": "live_gemini"
                        }
                except Exception as e:
                    error_msg = str(e).lower()
                    is_rate_limit = "429" in str(e) or "resource_exhausted" in error_msg or "quota" in error_msg
                    if is_rate_limit:
                        logger.warning(f"Gemini rate limit exceeded for model '{model_name}'. Trying next fallback model...")
                        continue
                    else:
                        logger.warning(f"Gemini image analysis error with model '{model_name}': {e}. Trying fallback...")
                        continue
        except Exception as e:
            logger.error(f"Failed to create Part from image bytes: {e}")

    # Fallback Generator when API key is missing or quota exhausted
    logger.info("Generating intelligent issue description from image context...")
    desc = generate_contextual_issue_description(file_name, len(image_bytes))
    return {
        "success": True,
        "description": desc,
        "mode": "demo_fallback",
        "notice": "Generated via FixBit Vision fallback (Configure GEMINI_API_KEY for live Gemini API)"
    }

def generate_contextual_issue_description(file_name: str | None, size_bytes: int) -> str:
    """
    Intelligent context-based maintenance issue generator used when live Gemini quota is exhausted or unconfigured.
    """
    fn = (file_name or "").lower()
    if "chair" in fn:
        return "Hostel room chair is broken and damaged with weak support structure, requiring immediate repair or replacement."
    elif "fan" in fn:
        return "Ceiling fan is not functioning properly and making abnormal grinding noises."
    elif "tap" in fn or "faucet" in fn or "water" in fn or "leak" in fn or "pipe" in fn:
        return "Water pipe / faucet is leaking water continuously causing dampness and water wastage."
    elif "light" in fn or "bulb" in fn or "switch" in fn or "socket" in fn:
        return "Room electrical switch / lighting fixture is malfunctioning and not working."
    elif "door" in fn or "lock" in fn or "handle" in fn:
        return "Door lock and latch mechanism is damaged and not locking securely."
    elif "window" in fn or "glass" in fn:
        return "Window pane / latch is damaged and needs maintenance attention."
    elif "bed" in fn or "table" in fn or "desk" in fn:
        return "Hostel room furniture is damaged and requires carpenter repair."
    else:
        return "Maintenance issue identified in the room requiring inspection and vendor repair."



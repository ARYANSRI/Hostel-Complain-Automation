import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field

class ComplaintSchema(BaseModel):
    category: str = Field(description="Must be exactly one of: Electrical, Plumbing, WiFi, Furniture, Other")
    urgency: str = Field(description="Must be exactly one of: Low, Medium, High")
    room_block: str | None = Field(description="Use null when room/block cannot be identified", default=None)

def parse_complaint(text):
    """
    Parses a raw hostel complaint text using Gemini to extract structured JSON.
    Expected output keys: category, urgency, room_block
    
    On a 429 rate-limit error, tries fallback models (each has a separate free-tier quota).
    Does NOT retry on auth errors, model-not-found, or other failures.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return {"category": "Other", "urgency": "Medium", "room_block": None}
    
    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    # Fallback models with separate free-tier quotas (tried only on 429)
    # All confirmed working via probe: gemini-3.5-flash, gemini-3.7-flash, gemini-3.1-flash-lite
    fallback_models = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash,gemini-3.7-flash").split(",")
    # Remove primary from fallbacks to avoid double-trying
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
    
    last_error = None
    
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
            logger.error(f"JSON parsing error from Gemini response (model: {model_name})")
            return {"category": "Other", "urgency": "Medium", "room_block": None}
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            is_rate_limit = "429" in str(e) or "resource_exhausted" in error_msg or "quota" in error_msg
            
            if is_rate_limit:
                logger.warning(
                    f"Gemini rate limit/quota exceeded for model '{model_name}'. "
                    "Trying next fallback model if available..."
                )
                continue  # Try the next model in the fallback chain
            elif "404" in str(e) or "not_found" in error_msg:
                logger.error(f"Gemini model '{model_name}' not found or unavailable. Check GEMINI_MODEL in .env")
                return {"category": "Other", "urgency": "Medium", "room_block": None}
            elif "403" in str(e) or "permission" in error_msg:
                logger.error("Gemini API authentication/permission error. Check GEMINI_API_KEY in .env")
                return {"category": "Other", "urgency": "Medium", "room_block": None}
            else:
                logger.error(f"Gemini API error ({type(e).__name__})")
                return {"category": "Other", "urgency": "Medium", "room_block": None}
    
    # All models exhausted their quotas
    logger.error(
        "All Gemini models quota-exhausted. "
        "Wait for quota reset or check https://ai.google.dev/gemini-api/docs/rate-limits"
    )
    return {"category": "Other", "urgency": "Medium", "room_block": None}

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

def create_complaint_row(data, notion_token, database_id):
    """
    Creates a new row in the Notion Complaints Database using the official Notion API.
    """
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
            return {"status": "error", "notion_id": f"mock_id_{hash(data.get('raw_text'))}", "data": data}
    except Exception as e:
        logger.error(f"Failed to connect to Notion: {e}")
        # Fallback to mock behavior so it doesn't crash if network fails
        return {"status": "error", "notion_id": f"mock_id_{hash(data.get('raw_text'))}", "data": data}

def check_approvals(notion_token, database_id):
    """
    Queries Notion for complaints that are approved and ready for dispatch.
    This means either Status is 'Auto-Approved', or Status is 'Pending Approval' AND 'Approved By' is not empty.
    """
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # We query for anything that is NOT Dispatched and NOT Resolved, then filter in code for simplicity,
    # or use a Notion compound filter. Let's use a compound filter for efficiency.
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
            
            # Extract fields safely matching the Notion schema exactly
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
    """
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
            logger.warning(f"No vendor found for category: {category}")
            return {"name": "Unknown Vendor", "email": None}
            
        row = results[0]
        props = row["properties"]
        
        email_prop = props.get("Email", {}).get("email")
        
        name_title = props.get("Vendor Name", {}).get("title", [])
        vendor_name = name_title[0]["plain_text"] if name_title else "Unknown Vendor"
        
        logger.info(f"Vendor found: {vendor_name} | Vendor email available: {'yes' if email_prop else 'no'}")
        return {"name": vendor_name, "email": email_prop}
        
    except Exception as e:
        logger.error(f"Failed to fetch vendor from Notion: {e}")
        return {"name": "Unknown Vendor", "email": None}

def update_complaint_status(complaint_id, new_status, notion_token):
    """
    Updates the Status of a complaint in Notion.
    """
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

# The notify_vendor function was removed from here because it was successfully 
# integrated into dispatch/email.py as per the user's previous instructions.

def check_resolutions(notion_token, database_id):
    """
    Queries Notion for complaints that are Resolved but haven't had a resolution email sent.
    """
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
            
            # NOTION API QUIRK: Newly created Checkbox columns often evaluate as 'null' internally
            # instead of False, which breaks the API filter. So we filter locally in Python.
            res_email_sent_prop = props.get("Resolution Email Sent", {})
            # If it explicitly equals True, skip it
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

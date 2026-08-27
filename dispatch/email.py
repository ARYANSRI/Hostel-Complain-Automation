import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import logging

# Ensure environment variables are loaded
load_dotenv()

# Configure logger (inherits configuration from the main app)
logger = logging.getLogger(__name__)

def get_smtp_connection() -> smtplib.SMTP:
    """
    Establishes and returns an authenticated SMTP connection using Mailtrap configuration.
    Raises ValueError for missing config, or smtplib exceptions on failure.
    """
    host = os.getenv("MAILTRAP_HOST")
    port = os.getenv("MAILTRAP_PORT")
    username = os.getenv("MAILTRAP_USERNAME")
    password = os.getenv("MAILTRAP_PASSWORD")

    if not all([host, port, username, password]):
        logger.error("Missing Mailtrap SMTP configuration in environment variables.")
        raise ValueError("Missing Mailtrap SMTP environment variables (HOST, PORT, USERNAME, or PASSWORD).")

    try:
        port_num = int(port)
        server = smtplib.SMTP(host, port_num, timeout=10)
        server.ehlo()
        
        if server.has_extn('STARTTLS'):
            server.starttls()
            server.ehlo()
            
        server.login(username, password)
        return server
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP Authentication failed. Please verify your MAILTRAP_USERNAME and password.")
        raise Exception("SMTP Authentication failed. Verify credentials in .env")
        
    except Exception as e:
        logger.error(f"Failed to establish SMTP connection: {type(e).__name__}")
        raise

def send_email(to_email: str, subject: str, content: str) -> bool:
    """
    Reusable helper to send an email using the established SMTP configuration.
    """
    mail_from = os.getenv("MAIL_FROM")
    if not mail_from:
        logger.error("Missing MAIL_FROM environment variable.")
        raise ValueError("Missing MAIL_FROM environment variable.")

    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = subject
    # Construct professional sender identity
    msg["From"] = f"Hostel Maintenance System <{mail_from}>"
    msg["To"] = to_email

    try:
        with get_smtp_connection() as server:
            server.send_message(msg)
            logger.info(f"Successfully dispatched email to {to_email}")
            return True
    except Exception as e:
        logger.error(f"Failed to dispatch email to {to_email}. Error: {type(e).__name__}")
        raise

def notify_vendor(vendor_email: str, complaint_details: dict) -> dict:
    """
    Dispatches a formatted email notification to a vendor.
    
    Args:
        vendor_email (str): The email address of the assigned vendor.
        complaint_details (dict): Dictionary with keys: category, urgency, room_block, raw_text
        
    Returns:
        dict: A result dictionary indicating success or failure.
    """
    # Extract details, defaulting to 'Unknown' if missing
    category = complaint_details.get("category", "Unknown").capitalize()
    urgency = complaint_details.get("urgency", "Unknown").capitalize()
    room_block = complaint_details.get("room_block", "Unknown")
    raw_text = complaint_details.get("raw_text", "No text provided")

    subject = f"Hostel Maintenance Complaint — {urgency} Urgency — {category}"
    
    body = (
        f"Hello,\n\n"
        f"A new hostel maintenance complaint has been assigned to your department.\n\n"
        f"Complaint Details\n"
        f"-----------------\n"
        f"Category: {category}\n"
        f"Urgency: {urgency}\n"
        f"Location: {room_block}\n\n"
        f"Student Complaint:\n"
        f"\"{raw_text}\"\n\n"
        f"Please review and attend to the complaint.\n\n"
        f"Regards,\n"
        f"Hostel Maintenance System"
    )

    try:
        success = send_email(to_email=vendor_email, subject=subject, content=body)
        if success:
            return {"success": True, "message": f"Successfully notified vendor at {vendor_email}"}
        else:
            return {"success": False, "message": "Failed to send email to vendor silently."}
    except Exception as e:
        # Gracefully handle the error, ensuring the main application flow is not crashed
        logger.error(f"Failed to notify vendor {vendor_email}: {type(e).__name__}")
        return {"success": False, "message": f"SMTP sending failed: {type(e).__name__}"}

def notify_student_resolved(student_email: str, complaint_details: dict) -> dict:
    """
    Sends a professional email notification to the student confirming that their
    hostel maintenance complaint has been resolved.
    """
    if not student_email or '@' not in str(student_email):
        return {"success": False, "message": "Invalid or missing student email"}

    category = complaint_details.get("category", "General")
    room_block = complaint_details.get("room_block", "Unknown Room")
    raw_text = complaint_details.get("raw_text", "No description provided")
    
    subject = f"Maintenance Complaint Resolved — {room_block}"
    
    body = (
        f"Hello,\n\n"
        f"Your hostel maintenance complaint has been marked as resolved.\n\n"
        f"Complaint Details\n"
        f"-----------------\n"
        f"Location: {room_block}\n"
        f"Category: {category}\n"
        f"Issue: {raw_text}\n\n"
        f"Status: Resolved\n\n"
        f"The maintenance team has completed the required action for this request.\n\n"
        f"If you believe the issue is still unresolved, please contact the hostel administration or submit a follow-up complaint.\n\n"
        f"Regards,\n"
        f"Hostel Maintenance System"
    )

    try:
        success = send_email(to_email=student_email, subject=subject, content=body)
        if success:
            logger.info(f"Resolution email sent successfully to {student_email}")
            return {"success": True, "message": f"Successfully notified student at {student_email}"}
        else:
            return {"success": False, "message": "Failed to send resolution email silently."}
    except Exception as e:
        logger.error(f"Failed to notify student {student_email}: {type(e).__name__}")
        return {"success": False, "message": f"SMTP sending failed: {type(e).__name__}"}

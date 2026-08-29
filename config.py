import os
import logging
from dotenv import load_dotenv

# Load environment variables with override to ensure latest values are picked up
load_dotenv(override=True)

# Logger for config
logger = logging.getLogger(__name__)

# Notion Configuration
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")
VENDORS_DATABASE_ID = os.getenv("VENDORS_DATABASE_ID")

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Mailtrap SMTP Configuration
MAILTRAP_HOST = os.getenv("MAILTRAP_HOST")
MAILTRAP_PORT = os.getenv("MAILTRAP_PORT")
MAILTRAP_USERNAME = os.getenv("MAILTRAP_USERNAME")
MAILTRAP_PASSWORD = os.getenv("MAILTRAP_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM", "noreply@fixbit.local")

# Informative startup status check
if NOTION_TOKEN and COMPLAINTS_DATABASE_ID and VENDORS_DATABASE_ID:
    logger.info("Notion Database: Configured (Live Sync Enabled)")
else:
    logger.info("Notion Database: Not configured (Running in local memory demo mode)")

if GEMINI_API_KEY:
    logger.info(f"Gemini AI Engine: Configured (Model: {GEMINI_MODEL})")
else:
    logger.info("Gemini AI Engine: No API key found (Smart heuristic fallback enabled; add key in UI settings)")

if all([MAILTRAP_HOST, MAILTRAP_PORT, MAILTRAP_USERNAME, MAILTRAP_PASSWORD]):
    logger.info("Email Dispatch: Configured (Mailtrap/SMTP active)")
else:
    logger.info("Email Dispatch: Demo Mode (Simulating notifications)")


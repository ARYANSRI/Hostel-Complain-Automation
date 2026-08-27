import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger for config
logger = logging.getLogger(__name__)

# Notion Configuration
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")
VENDORS_DATABASE_ID = os.getenv("VENDORS_DATABASE_ID")

# Validate Notion Configuration
if not NOTION_TOKEN:
    logger.warning("NOTION_TOKEN is not configured")
if not COMPLAINTS_DATABASE_ID:
    logger.warning("COMPLAINTS_DATABASE_ID is not configured")
if not VENDORS_DATABASE_ID:
    logger.warning("VENDORS_DATABASE_ID is not configured")

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not configured")

# Mailtrap SMTP Configuration
MAILTRAP_HOST = os.getenv("MAILTRAP_HOST")
MAILTRAP_PORT = os.getenv("MAILTRAP_PORT")
MAILTRAP_USERNAME = os.getenv("MAILTRAP_USERNAME")
MAILTRAP_PASSWORD = os.getenv("MAILTRAP_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")

if not all([MAILTRAP_HOST, MAILTRAP_PORT, MAILTRAP_USERNAME, MAILTRAP_PASSWORD, MAIL_FROM]):
    logger.warning("MAILTRAP configuration is not configured (missing one or more required fields)")

import os
from dotenv import load_dotenv
from services import check_resolutions
import logging

logging.basicConfig(level=logging.DEBUG)

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")

res = check_resolutions(NOTION_TOKEN, COMPLAINTS_DATABASE_ID)
print("FINAL RESULT:", res)

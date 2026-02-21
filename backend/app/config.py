import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
META_WHATSAPP_TOKEN: str = os.getenv("META_WHATSAPP_TOKEN", "")
WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "my-verify-token")
WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR.parent / "data" / "demo.db"))
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

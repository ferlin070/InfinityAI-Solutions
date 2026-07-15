import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ai_command_center")

# API Configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")
GAS_URL = os.getenv("GAS_WEB_APP_URL")
LOG_FILE = "daily_log.json"

# Google Drive folder mappings for agents
FOLDER_IDS = {
    "ZARA": os.getenv("ZARA_DRIVE_FOLDER_ID"),
    "DANISH": os.getenv("DANISH_DRIVE_FOLDER_ID"),
    "MAYA": os.getenv("MAYA_DRIVE_FOLDER_ID"),
    "AMELIA": os.getenv("AMELIA_DRIVE_FOLDER_ID"),
    "AIMAN": os.getenv("AIMAN_DRIVE_FOLDER_ID"),
    "ADILA": os.getenv("ADILA_DRIVE_FOLDER_ID"),
    "HAKIM": os.getenv("HAKIM_DRIVE_FOLDER_ID")
}

# Startup verification
def verify_environment():
    if not NVIDIA_API_KEY:
        logger.warning("NVIDIA_NIM_API_KEY tidak dikonfigurasikan dalam fail .env! Panggilan API ke model NVIDIA akan gagal.")
    if not GAS_URL:
        logger.warning("GAS_WEB_APP_URL tidak dikonfigurasikan dalam fail .env! Sistem tidak dapat memuat naik hasil kerja ke Google Drive.")

    for agent_name, folder_id in FOLDER_IDS.items():
        if not folder_id:
            logger.warning(f"Google Drive folder ID untuk ejen '{agent_name}' tidak dijumpai dalam fail .env.")

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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GAS_URL = os.getenv("GAS_WEB_APP_URL")
LOG_FILE = "daily_log.json"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


# Environment & Admin Credentials Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Local development fallback
if ENVIRONMENT != "production":
    if not ADMIN_EMAIL:
        ADMIN_EMAIL = "bos@infinityai.com"
    if not ADMIN_PASSWORD:
        ADMIN_PASSWORD = "password123"

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

def get_frontend_dir():
    # Check current working dir
    if os.path.exists("frontend/src"):
        return os.path.abspath("frontend/src")
    if os.path.exists("../frontend/src"):
        return os.path.abspath("../frontend/src")
    
    # Check relative to this file (core/config.py)
    file_dir = os.path.dirname(os.path.abspath(__file__)) # core
    src_dir = os.path.dirname(file_dir) # src
    backend_dir = os.path.dirname(src_dir) # backend
    
    # In docker, frontend is copied directly to WORKDIR/frontend
    docker_frontend = os.path.join(backend_dir, "frontend", "src")
    if os.path.exists(docker_frontend):
        return docker_frontend
        
    # Local development where frontend is parallel to backend
    root_dir = os.path.dirname(backend_dir)
    local_frontend = os.path.join(root_dir, "frontend", "src")
    if os.path.exists(local_frontend):
        return local_frontend
        
    # Fallback
    return os.path.abspath("frontend/src")

FRONTEND_DIR = get_frontend_dir()
logger.info(f"Frontend directory resolved to: {FRONTEND_DIR}")

# Startup verification
def verify_environment():
    # Log dev mode warnings for credential fallbacks
    if ENVIRONMENT == "production":
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            raise RuntimeError(
                "ADMIN_EMAIL dan ADMIN_PASSWORD wajib diset di .env — "
                "sistem tidak akan start tanpa kelayakan admin yang sah."
            )
    else:
        if not os.getenv("ADMIN_EMAIL"):
            logger.warning("ADMIN_EMAIL tidak diset di .env. Menggunakan fallback: bos@infinityai.com")
        if not os.getenv("ADMIN_PASSWORD"):
            logger.warning("ADMIN_PASSWORD tidak diset di .env. Menggunakan fallback: password123")

    # Supabase validation (fail-open-by-design)
    if (SUPABASE_URL and not SUPABASE_SERVICE_ROLE_KEY) or (not SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        raise RuntimeError(
            "Konfigurasi Supabase tidak lengkap! Kedua-dua SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY "
            "mesti diset bersama-sama di .env, atau kedua-duanya dikosongkan."
        )
    elif not SUPABASE_URL and not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase tidak dikonfigurasikan (SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY kosong). Aplikasi berjalan tanpa integrasi pangkalan data (fail-open).")
    else:
        logger.info("Supabase dikonfigurasikan: SUPABASE_URL diset, SUPABASE_SERVICE_ROLE_KEY diset.")

    if not NVIDIA_API_KEY:
        logger.warning("NVIDIA_NIM_API_KEY tidak dikonfigurasikan dalam fail .env! Panggilan API ke model NVIDIA akan gagal.")
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY tidak dikonfigurasikan dalam fail .env! Panggilan AI execution layer (CrewAI) akan gagal.")
    if not GAS_URL:
        logger.warning("GAS_WEB_APP_URL tidak dikonfigurasikan dalam fail .env! Sistem tidak dapat memuat naik hasil kerja ke Google Drive.")

    for agent_name, folder_id in FOLDER_IDS.items():
        if not folder_id:
            logger.warning(f"Google Drive folder ID untuk ejen '{agent_name}' tidak dijumpai dalam fail .env.")


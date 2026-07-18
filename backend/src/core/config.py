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
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_BASE_URL = os.getenv("AZURE_OPENAI_BASE_URL")
GAS_URL = os.getenv("GAS_WEB_APP_URL")
LOG_FILE = "daily_log.json"

# Browser / Playwright (optional)
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true")
BROWSER_LAUNCH_ARGS = os.getenv("BROWSER_LAUNCH_ARGS", "")
BROWSER_IDLE_TTL_SECONDS = os.getenv("BROWSER_IDLE_TTL_SECONDS", "300")
BROWSER_DEFAULT_TIMEOUT_MS = os.getenv("BROWSER_DEFAULT_TIMEOUT_MS", "15000")
BROWSER_SCREENSHOT_DIR = os.getenv("BROWSER_SCREENSHOT_DIR", "/tmp/infinityai_screenshots")
BROWSER_SESSION_ID = os.getenv("BROWSER_SESSION_ID", "")

# MCP (optional, JSON-encoded list of server configs in MCP_SERVERS env var)
MCP_SERVERS = os.getenv("MCP_SERVERS", "")

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

    if not os.getenv("SESSION_SECRET_KEY"):
        logger.warning(
            "SESSION_SECRET_KEY tidak diset di .env — session token ditandatangan "
            "guna kunci terbitan dari ADMIN_PASSWORD sebagai fallback. Set "
            "SESSION_SECRET_KEY khusus (rawak, panjang) di production supaya "
            "session tidak bergantung pada ADMIN_PASSWORD."
        )

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

    # Optional AI provider bridges — only warn if the agent tries to use them
    # (we don't want to spam warnings for keys the operator never asked for).
    if not ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY tidak diset — bridge ke Claude tidak aktif.")
    if not GEMINI_API_KEY and not GOOGLE_API_KEY:
        logger.info("GEMINI_API_KEY / GOOGLE_API_KEY tidak diset — bridge ke Gemini tidak aktif.")
    if not OPENROUTER_API_KEY:
        logger.info("OPENROUTER_API_KEY tidak diset — bridge ke OpenRouter tidak aktif.")
    if not AZURE_OPENAI_API_KEY:
        logger.info("AZURE_OPENAI_API_KEY tidak diset — bridge ke Azure OpenAI tidak aktif.")

    # Optional Playwright / browser tools
    try:
        import playwright  # noqa: F401
        logger.info("Playwright tersedia — browser tools diaktifkan untuk agen terpilih.")
    except ImportError:
        logger.info(
            "Playwright tidak dipasang — browser tools dinyah-aktifkan. "
            "Untuk aktifkan: `pip install playwright && playwright install chromium`."
        )

    # Optional MCP
    if MCP_SERVERS:
        try:
            import mcp  # noqa: F401
            logger.info("MCP_SERVERS dikonfigurasikan dan SDK mcp tersedia — alat MCP akan dimuatkan.")
        except ImportError:
            logger.warning(
                "MCP_SERVERS dikonfigurasikan tetapi SDK `mcp` tidak dipasang. "
                "Untuk aktifkan: `pip install mcp`."
            )

    for agent_name, folder_id in FOLDER_IDS.items():
        if not folder_id:
            logger.warning(f"Google Drive folder ID untuk ejen '{agent_name}' tidak dijumpai dalam fail .env.")


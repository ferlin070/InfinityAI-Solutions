import os
import sys
from fastapi import FastAPI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import verify_environment, logger, FRONTEND_DIR
from src.core.middleware import setup_cors, setup_security_headers
from src.api.routes import router as api_router
from src.api.webhooks import router as webhook_router
from src.api.wa_routes import router as wa_router
from fastapi.staticfiles import StaticFiles

# Initialize FastAPI app
app = FastAPI(title="AI Command Center: 8-Agent System")

# Setup middleware
setup_cors(app)
setup_security_headers(app)

# Mount static files
css_dir = os.path.join(FRONTEND_DIR, "css")
if os.path.exists(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")

js_dir = os.path.join(FRONTEND_DIR, "js")
if os.path.exists(js_dir):
    app.mount("/js", StaticFiles(directory=js_dir), name="js")

icons_dir = os.path.join(FRONTEND_DIR, "icons")
if os.path.exists(icons_dir):
    app.mount("/icons", StaticFiles(directory=icons_dir), name="icons")

assets_dir = os.path.join(FRONTEND_DIR, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


# Include routes
app.include_router(api_router)
app.include_router(webhook_router)
app.include_router(wa_router)

# Verify environment on startup
verify_environment()



if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

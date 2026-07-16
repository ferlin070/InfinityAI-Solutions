import os
import sys
from fastapi import FastAPI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import verify_environment, logger, FRONTEND_DIR
from src.core.middleware import setup_cors, setup_security_headers
from src.api.routes import router as api_router
from fastapi.staticfiles import StaticFiles

# Initialize FastAPI app
app = FastAPI(title="AI Command Center: 8-Agent System")

# Setup middleware
setup_cors(app)
setup_security_headers(app)

# Mount static files
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

# Include routes
app.include_router(api_router)

# Verify environment on startup
verify_environment()



if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

import json
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from src.core.config import LOG_FILE, FRONTEND_DIR
from src.schemas.models import UserInput, UserLogin
from src.services.orchestrator import execute_task
from src.core.sessions import verify_session, create_session, destroy_session

router = APIRouter()

# Read credentials from env (with secure fallbacks)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "bos@infinityai.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password123")


@router.get("/", response_class=HTMLResponse)
async def index(session_token: str | None = Cookie(None)):
    """Serve the main dashboard HTML if authenticated, otherwise redirect to login"""
    if not verify_session(session_token):
        return RedirectResponse(url="/login", status_code=303)
    
    with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
        return f.read()


@router.get("/login", response_class=HTMLResponse)
async def login_page(session_token: str | None = Cookie(None)):
    """Serve the login page or redirect to dashboard if already authenticated"""
    if verify_session(session_token):
        return RedirectResponse(url="/", status_code=303)
        
    with open(os.path.join(FRONTEND_DIR, "login.html"), "r", encoding="utf-8") as f:
        return f.read()


@router.post("/api/login")
async def api_login(data: UserLogin, response: Response):
    """Authenticate user and set secure httpOnly cookie"""
    if data.email == ADMIN_EMAIL and data.password == ADMIN_PASSWORD:
        token = create_session()
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=False  # Set to True if using HTTPS in prod
        )
        return {
            "status": "success",
            "user": {
                "email": data.email,
                "name": "Bos"
            }
        }
    
    raise HTTPException(
        status_code=401,
        detail="E-mel atau kata laluan salah. Sila cuba lagi."
    )


@router.post("/api/logout")
async def api_logout(response: Response, session_token: str | None = Cookie(None)):
    """Destroy session and clear cookie"""
    destroy_session(session_token)
    response.delete_cookie(key="session_token")
    return {"status": "success"}


@router.get("/api/history")
async def history(session_token: str | None = Cookie(None)):
    """Return execution history log if authenticated"""
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")
        
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/api/execute")
async def execute(data: UserInput, background_tasks: BackgroundTasks, session_token: str | None = Cookie(None)):
    """Execute a task with Claudia orchestration if authenticated"""
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")
        
    return await execute_task(data, background_tasks)


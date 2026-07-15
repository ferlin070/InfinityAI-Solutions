import json
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from src.core.config import LOG_FILE
from src.schemas.models import UserInput
from src.services.orchestrator import execute_task

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main dashboard HTML"""
    with open("frontend/src/index.html", "r", encoding="utf-8") as f:
        return f.read()


@router.get("/api/history")
async def history():
    """Return execution history log"""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/api/execute")
async def execute(data: UserInput, background_tasks: BackgroundTasks):
    """Execute a task with Claudia orchestration"""
    return await execute_task(data, background_tasks)

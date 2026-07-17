import asyncio
import json
import os
import queue
import threading
from fastapi import APIRouter, HTTPException, Cookie, Response, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from src.core.config import LOG_FILE, FRONTEND_DIR, logger
from src.core import config
from src.schemas.models import ExecuteResponse, ExecutionRequest, UserLogin
from src.ai.flows.task_execution_flow import TaskExecutionFlow
from src.core.sessions import verify_session, create_session, destroy_session
from src.services import dashboard_memory

router = APIRouter()

# Bounds how long an /api/chat/stream client waits with zero events before
# giving up — see chat_stream() below. Module-level so tests can tune it down.
CHAT_STREAM_TIMEOUT_S = 180

# Rate limiter configuration & helper functions
from datetime import datetime, timedelta
import hmac

login_attempts = {} # { ip: [timestamp1, timestamp2, ...] }

def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Extract the last element in the chain to prevent client-side header spoofing
        client_ip = forwarded_for.split(",")[-1].strip()
        from src.core.config import logger
        logger.info(f"Raw X-Forwarded-For: {forwarded_for} -> Resolved Client IP: {client_ip}")
        return client_ip
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"

def check_rate_limit(ip_address: str):
    now = datetime.now()
    attempts = login_attempts.get(ip_address, [])
    attempts = [t for t in attempts if now - t < timedelta(minutes=15)]
    login_attempts[ip_address] = attempts
    
    if len(attempts) >= 5:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak percubaan log masuk. Sila cuba lagi selepas 15 minit."
        )

def record_login_attempt(ip_address: str):
    if ip_address not in login_attempts:
        login_attempts[ip_address] = []
    login_attempts[ip_address].append(datetime.now())


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
        
    with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
        return f.read()


@router.post("/api/login")
async def api_login(data: UserLogin, response: Response, request: Request):
    """Authenticate user and set secure httpOnly cookie"""
    client_ip = get_client_ip(request)
    check_rate_limit(client_ip)
    
    # Timing-attack safe credential comparison
    if hmac.compare_digest(data.email, config.ADMIN_EMAIL) and hmac.compare_digest(data.password, config.ADMIN_PASSWORD):
        token = create_session()
        IS_PRODUCTION = config.ENVIRONMENT == "production"
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=IS_PRODUCTION
        )
        return {
            "status": "success",
            "user": {
                "email": data.email,
                "name": "Bos"
            }
        }
    
    record_login_attempt(client_ip)
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


@router.get("/api/me")
async def api_me(session_token: str | None = Cookie(None)):
    """Get currently logged-in user profile if session is valid"""
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")
    return {
        "status": "success",
        "user": {
            "email": config.ADMIN_EMAIL,
            "name": "Bos"
        }
    }



@router.get("/api/history")
async def history(session_token: str | None = Cookie(None)):
    """Return execution history log if authenticated"""
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")
        
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/api/executions", response_model=ExecuteResponse)
async def create_execution(data: ExecutionRequest, session_token: str | None = Cookie(None)):
    """Execute a task via the CrewAI-backed AI execution layer (OpenAI provider).
    Replaces /api/execute — see docs/architecture/ai-execution-crewai.md §6/§10.
    `org_id` is None until the multi-tenant auth/org layer (proposal-v2.md §2)
    exists; every execution runs against the platform-wide OpenAI key until then.
    """
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")

    flow = TaskExecutionFlow()
    return await flow.kickoff_async(
        inputs={"prompt": data.prompt, "model": data.model, "org_id": None}
    )


def _sse_frame(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _flatten_execute_response(response: ExecuteResponse) -> str:
    if response.status == "success" and response.results:
        return "\n\n".join(f"[{r.agent}]: {r.result}" for r in response.results)
    return response.message or ""


@router.post("/api/chat/stream")
async def chat_stream(data: ExecutionRequest, session_token: str | None = Cookie(None)):
    """Chat with Claudia over a live SSE stream — the memory-aware, unified-UI
    counterpart to /api/executions. Runs the (synchronous, blocking) CrewAI
    flow in a background thread, bridging its `on_event` progress callbacks
    and final result into the async response via a thread-safe queue, so the
    frontend can render live activity ("Claudia sedang fikir...", "Danish
    sedang menjana imej...") instead of waiting silently for the whole thing.
    """
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")

    event_q: "queue.Queue[tuple[str, dict] | None]" = queue.Queue()

    def emit(event_type: str, payload: dict) -> None:
        event_q.put((event_type, payload))

    def run_flow() -> None:
        try:
            history = dashboard_memory.get_recent()
            flow = TaskExecutionFlow(on_event=emit)
            response: ExecuteResponse = flow.kickoff(
                inputs={
                    "prompt": data.prompt,
                    "model": data.model,
                    "org_id": None,
                    "history": history,
                }
            )
            dashboard_memory.append_message("user", data.prompt)
            dashboard_memory.append_message("assistant", _flatten_execute_response(response))
            emit("final", response.model_dump())
        except Exception as e:
            logger.error(f"Ralat semasa chat stream: {e}", exc_info=True)
            emit("error", {"message": "Ralat dalaman semasa memproses mesej."})
        finally:
            event_q.put(None)

    threading.Thread(target=run_flow, daemon=True).start()

    async def event_gen():
        loop = asyncio.get_event_loop()
        while True:
            try:
                # A stuck OpenAI/gateway call in run_flow's background thread would
                # otherwise hang the SSE response (and the UI's spinner) forever
                # with no feedback, since that thread can't be safely cancelled
                # from here — this only bounds what the *client* waits for; the
                # background thread itself is left to finish or fail on its own.
                item = await asyncio.wait_for(
                    loop.run_in_executor(None, event_q.get), timeout=CHAT_STREAM_TIMEOUT_S
                )
            except asyncio.TimeoutError:
                logger.error("Chat stream timed out waiting for a response.")
                yield _sse_frame("error", {"message": "Masa tamat menunggu balasan. Sila cuba lagi."})
                break
            if item is None:
                break
            event_type, payload = item
            yield _sse_frame(event_type, payload)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            # Without these, some reverse proxies (Railway's edge included, per
            # observed production behavior) buffer the whole response instead of
            # forwarding chunks as they're yielded — the client then sees nothing
            # until the entire stream finishes, indistinguishable from a hang.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/api/chat/history")
async def chat_history(session_token: str | None = Cookie(None)):
    """Return the dashboard chat transcript to hydrate the UI on page load."""
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")
    return dashboard_memory.get_recent(n=40)


@router.post("/api/chat/clear")
async def chat_clear(session_token: str | None = Cookie(None)):
    """Reset the dashboard chat's conversation memory."""
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")
    dashboard_memory.clear()
    return {"status": "success"}


@router.get("/manifest.json")
async def manifest():
    """Serve manifest.json for PWA"""
    return FileResponse(
        os.path.join(FRONTEND_DIR, "manifest.json"),
        media_type="application/json"
    )


@router.get("/sw.js")
async def service_worker():
    """Serve sw.js for PWA"""
    return FileResponse(
        os.path.join(FRONTEND_DIR, "sw.js"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"}
    )



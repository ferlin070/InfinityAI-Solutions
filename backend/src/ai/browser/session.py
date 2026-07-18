"""Playwright-powered headless Chromium browser session manager.

The browser is an optional dependency (`pip install playwright && playwright install chromium`).
Tools that need it gracefully return a clear error string if Playwright is not
installed — the rest of the system keeps working.

The manager keeps one Chromium instance per `session_id`, with its own isolated
BrowserContext (separate cookies/storage per session). Idle sessions are reaped
on access. The default "default" session is shared unless an explicit session
id is passed in.
"""

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from src.core.config import logger

_SESSION_IDLE_TTL_SECONDS = int(os.getenv("BROWSER_IDLE_TTL_SECONDS", "300"))
_BROWSER_LAUNCH_TIMEOUT = int(os.getenv("BROWSER_LAUNCH_TIMEOUT_MS", "30000"))
_DEFAULT_SESSION_ID = "default"


@dataclass
class _Session:
    session_id: str
    playwright: Any | None = None
    browser: Any | None = None
    context: Any | None = None
    page: Any | None = None
    last_used: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)


class BrowserUnavailableError(RuntimeError):
    """Raised when Playwright is not installed or Chromium cannot be launched."""


class BrowserSessionManager:
    """Singleton manager. One Chromium process, many isolated contexts.

    Lazy-imports Playwright only when a session is first opened, so the cost
    is paid only by agents/tools that actually use the browser.
    """

    _instance: "BrowserSessionManager | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._sessions: dict[str, _Session] = {}
        self._manager_lock = threading.Lock()
        self._playwright_module: Any | None = None

    @classmethod
    def get(cls) -> "BrowserSessionManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = BrowserSessionManager()
            return cls._instance


def get_browser_session_manager() -> BrowserSessionManager:
    """Module-level convenience for `from src.ai.browser import get_browser_session_manager`."""
    return BrowserSessionManager.get()

    @property
    def is_available(self) -> bool:
        """True if Playwright is importable. Does not guarantee Chromium binary
        is installed — call `open()` to surface that error."""
        return self._import_playwright() is not None

    def open(self, session_id: str = _DEFAULT_SESSION_ID) -> "_Session":
        """Return an active session, launching Chromium on first use."""
        session_id = session_id or _DEFAULT_SESSION_ID
        with self._manager_lock:
            self._reap_idle_locked()
            sess = self._sessions.get(session_id)
            if sess is not None and sess.page is not None:
                sess.last_used = time.time()
                return sess
            if sess is None:
                sess = _Session(session_id=session_id)
                self._sessions[session_id] = sess

        # Launch outside manager lock — `playwright.chromium.launch()` may take
        # seconds; other sessions should not be blocked.
        with sess.lock:
            try:
                self._launch_into(sess)
            except Exception:
                # Drop the broken session so the next call retries cleanly.
                with self._manager_lock:
                    self._sessions.pop(session_id, None)
                raise
            sess.last_used = time.time()
            return sess

    def close(self, session_id: str = _DEFAULT_SESSION_ID) -> None:
        with self._manager_lock:
            sess = self._sessions.pop(session_id, None)
        if sess is None:
            return
        with sess.lock:
            try:
                if sess.context is not None:
                    sess.context.close()
            except Exception:
                pass
            try:
                if sess.browser is not None:
                    sess.browser.close()
            except Exception:
                pass
            try:
                if sess.playwright is not None:
                    sess.playwright.stop()
            except Exception:
                pass

    def close_all(self) -> None:
        with self._manager_lock:
            ids = list(self._sessions.keys())
        for sid in ids:
            self.close(sid)

    def list_sessions(self) -> list[str]:
        with self._manager_lock:
            self._reap_idle_locked()
            return list(self._sessions.keys())

    def _reap_idle_locked(self) -> None:
        now = time.time()
        stale = [
            sid for sid, s in self._sessions.items()
            if now - s.last_used > _SESSION_IDLE_TTL_SECONDS
        ]
        for sid in stale:
            old = self._sessions.pop(sid, None)
            if old is None:
                continue
            try:
                if old.context is not None:
                    old.context.close()
            except Exception:
                pass
            try:
                if old.browser is not None:
                    old.browser.close()
            except Exception:
                pass
            try:
                if old.playwright is not None:
                    old.playwright.stop()
            except Exception:
                pass

    def _import_playwright(self) -> Any | None:
        if self._playwright_module is not None:
            return self._playwright_module
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            return None
        self._playwright_module = sync_playwright
        return sync_playwright

    def _launch_into(self, sess: _Session) -> None:
        sync_playwright = self._import_playwright()
        if sync_playwright is None:
            raise BrowserUnavailableError(
                "Playwright is not installed. Run: "
                "`pip install playwright && playwright install chromium`"
            )
        headless = os.getenv("BROWSER_HEADLESS", "true").lower() != "false"
        # Allow `BROWSER_LAUNCH_ARGS` to add custom Chromium flags (e.g. proxy).
        extra_args: list[str] = []
        extra = os.getenv("BROWSER_LAUNCH_ARGS", "")
        if extra:
            extra_args = [a for a in extra.split(" ") if a]
        pw_ctx = sync_playwright().start()
        browser = pw_ctx.chromium.launch(
            headless=headless,
            args=extra_args,
            timeout=_BROWSER_LAUNCH_TIMEOUT,
        )
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        sess.playwright = pw_ctx
        sess.browser = browser
        sess.context = context
        sess.page = page
        logger.info(f"Browser session '{sess.session_id}' opened (headless={headless}).")

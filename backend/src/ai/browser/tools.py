"""Browser tools as CrewAI tools. All tools share the singleton
`BrowserSessionManager` and accept an optional `session_id` so multiple
agents/users can run in isolated browser contexts concurrently.

Tools follow the same `@tool("Name")` pattern as the rest of `src/ai/tools/`
so they plug straight into `TOOL_MAPPINGS` in `src/ai/agents/tool_mappings.py`.
"""

import os
import time
from typing import Optional

from crewai.tools import tool

from src.ai.browser.session import (
    BrowserSessionManager,
    BrowserUnavailableError,
    _DEFAULT_SESSION_ID,
)
from src.core.config import logger

_DEFAULT_TIMEOUT_MS = int(os.getenv("BROWSER_DEFAULT_TIMEOUT_MS", "15000"))
_SCREENSHOT_DIR = os.getenv("BROWSER_SCREENSHOT_DIR", "/tmp/infinityai_screenshots")


def _resolve_session(session_id: Optional[str]) -> str:
    return session_id or os.getenv("BROWSER_SESSION_ID") or _DEFAULT_SESSION_ID


def _get_page(session_id: str):
    try:
        sess = BrowserSessionManager.get().open(session_id)
    except BrowserUnavailableError as e:
        raise RuntimeError(str(e)) from e
    if sess.page is None:
        raise RuntimeError(f"Browser session '{session_id}' has no page.")
    return sess.page


def _to_result(success: bool, message: str, **extra) -> str:
    """Standard tool return shape: short text the LLM can read, with optional
    structured data serialised into the message itself."""
    if not extra:
        return message
    extras = "\n".join(f"{k}: {v}" for k, v in extra.items())
    return f"{message}\n{extras}"


@tool("Browser Navigate")
def browser_navigate_tool(url: str, session_id: Optional[str] = None) -> str:
    """Navigate a headless Chromium browser to a URL and wait for the page to
    load. Returns the final URL and page title. Use this as the first step of
    any browser automation — every other browser tool needs an open page."""
    sid = _resolve_session(session_id)
    try:
        page = _get_page(sid)
        response = page.goto(url, wait_until="domcontentloaded", timeout=_DEFAULT_TIMEOUT_MS)
        status = response.status if response else "n/a"
        return _to_result(
            True,
            f"Navigated to {page.url}",
            title=page.title(),
            status=status,
        )
    except Exception as e:
        logger.warning(f"browser_navigate_tool failed: {e}")
        return _to_result(False, f"Navigation failed: {e}")


@tool("Browser Get UI State")
def browser_get_ui_state_tool(
    selector: Optional[str] = None,
    include_hidden: bool = False,
    session_id: Optional[str] = None,
) -> str:
    """Return a compact representation of the current page state — URL, title,
    and a flat list of interactive elements (buttons, links, inputs, selects,
    textareas) with their selectors, labels, and visible text. Optionally
    scope to elements matching a CSS selector. Use this before clicking or
    typing to discover the correct selectors."""
    sid = _resolve_session(session_id)
    try:
        page = _get_page(sid)
        scope = page.locator(selector) if selector else page
        elements = scope.evaluate(
            """(args) => {
                const includeHidden = args.includeHidden;
                const out = [];
                const sel = (el) => {
                    if (el.id) return '#' + el.id;
                    if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';
                    if (el.getAttribute('data-testid')) return '[data-testid="' + el.getAttribute('data-testid') + '"]';
                    if (el.getAttribute('aria-label')) return '[aria-label="' + el.getAttribute('aria-label') + '"]';
                    return el.tagName.toLowerCase();
                };
                const tags = ['a','button','input','select','textarea'];
                const nodes = Array.from(document.querySelectorAll(tags.join(',')));
                for (const n of nodes) {
                    const rect = n.getBoundingClientRect();
                    const visible = rect.width > 0 && rect.height > 0;
                    if (!includeHidden && !visible) continue;
                    const text = (n.innerText || n.value || n.getAttribute('aria-label') || n.getAttribute('placeholder') || '').trim().slice(0, 120);
                    out.push({
                        tag: n.tagName.toLowerCase(),
                        type: n.getAttribute('type') || null,
                        selector: sel(n),
                        text: text,
                        name: n.getAttribute('name') || null,
                        placeholder: n.getAttribute('placeholder') || null,
                        value: n.value !== undefined ? n.value : null,
                        href: n.getAttribute('href') || null,
                        options: n.tagName === 'SELECT'
                            ? Array.from(n.options).map(o => ({value: o.value, label: o.text}))
                            : null,
                    });
                }
                return out.slice(0, 200);
            }""",
            {"includeHidden": include_hidden},
        )
        header = f"Page: {page.url}  Title: {page.title()}"
        body = "\n".join(
            f"- <{e['tag']}{(' type='+e['type']) if e.get('type') else ''}> "
            f"selector={e['selector']} "
            f"text={e.get('text') or ''} "
            f"placeholder={e.get('placeholder') or ''} "
            f"value={e.get('value') or ''} "
            f"href={e.get('href') or ''} "
            f"options={e.get('options') or ''}"
            for e in elements
        ) or "(no interactive elements found)"
        return f"{header}\n{body}"
    except Exception as e:
        logger.warning(f"browser_get_ui_state_tool failed: {e}")
        return f"Error reading UI state: {e}"


@tool("Browser Click")
def browser_click_tool(selector: str, session_id: Optional[str] = None) -> str:
    """Click an element on the current page identified by a CSS selector (e.g.
    '#submit', 'button.primary', '[aria-label=\"Close\"]'). Waits for the
    element to be visible and clickable, then clicks. Returns the new URL after
    the click (often a navigation). Use `Browser Get UI State` first to find
    the right selector."""
    sid = _resolve_session(session_id)
    try:
        page = _get_page(sid)
        page.locator(selector).first.wait_for(
            state="visible", timeout=_DEFAULT_TIMEOUT_MS
        )
        page.locator(selector).first.click(timeout=_DEFAULT_TIMEOUT_MS)
        # Best-effort wait for any resulting navigation/network.
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        return _to_result(True, f"Clicked {selector}", url=page.url, title=page.title())
    except Exception as e:
        logger.warning(f"browser_click_tool failed: {e}")
        return _to_result(False, f"Click failed for selector {selector!r}: {e}")


@tool("Browser Type")
def browser_type_tool(
    selector: str,
    text: str,
    press_enter: bool = False,
    clear_first: bool = True,
    session_id: Optional[str] = None,
) -> str:
    """Type text into an input/textarea identified by a CSS selector.
    By default the field is cleared first. Set `press_enter=True` to submit
    the form (e.g. for a search box). Use `Browser Get UI State` first to
    find the right selector for the input field."""
    sid = _resolve_session(session_id)
    try:
        page = _get_page(sid)
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=_DEFAULT_TIMEOUT_MS)
        if clear_first:
            loc.fill("")
        loc.fill(text)
        if press_enter:
            loc.press("Enter")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
        return _to_result(
            True, f"Typed {len(text)} chars into {selector}", url=page.url
        )
    except Exception as e:
        logger.warning(f"browser_type_tool failed: {e}")
        return _to_result(False, f"Type failed for selector {selector!r}: {e}")


@tool("Browser Select Dropdown")
def browser_select_tool(
    selector: str,
    value: Optional[str] = None,
    label: Optional[str] = None,
    index: Optional[int] = None,
    session_id: Optional[str] = None,
) -> str:
    """Select an option from a `<select>` dropdown. Match by `value`, visible
    `label`, or `index` (zero-based). Exactly one of the three match modes
    must be supplied. Use `Browser Get UI State` to see the available
    `options` for the dropdown."""
    sid = _resolve_session(session_id)
    if sum(x is not None for x in (value, label, index)) != 1:
        return "Error: provide exactly one of `value`, `label`, or `index`."
    try:
        page = _get_page(sid)
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=_DEFAULT_TIMEOUT_MS)
        kwargs = {}
        if value is not None:
            kwargs["value"] = value
        elif label is not None:
            kwargs["label"] = label
        elif index is not None:
            kwargs["index"] = index
        loc.select_option(**kwargs)
        return _to_result(
            True, f"Selected option on {selector}", value=loc.input_value()
        )
    except Exception as e:
        logger.warning(f"browser_select_tool failed: {e}")
        return _to_result(False, f"Select failed for {selector!r}: {e}")


@tool("Browser Screenshot")
def browser_screenshot_tool(
    full_page: bool = False,
    filename: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """Take a PNG screenshot of the current page and save it to the screenshot
    directory (default `/tmp/infinityai_screenshots`). Returns the absolute
    file path. Set `full_page=True` to capture the entire scrollable page.
    Use this when you need to visually confirm a page state or to attach an
    image to a customer message / report."""
    sid = _resolve_session(session_id)
    try:
        page = _get_page(sid)
        os.makedirs(_SCREENSHOT_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        fname = filename or f"{sid}-{ts}.png"
        if not fname.endswith(".png"):
            fname += ".png"
        path = os.path.join(_SCREENSHOT_DIR, fname)
        page.screenshot(path=path, full_page=full_page)
        return _to_result(True, f"Screenshot saved", path=path, full_page=full_page)
    except Exception as e:
        logger.warning(f"browser_screenshot_tool failed: {e}")
        return _to_result(False, f"Screenshot failed: {e}")


@tool("Browser Scroll")
def browser_scroll_tool(
    direction: str = "down",
    amount: int = 600,
    session_id: Optional[str] = None,
) -> str:
    """Scroll the current page in `direction` ("up"/"down"/"left"/"right") by
    `amount` pixels. Useful for revealing more of a long page or triggering
    lazy-loaded content."""
    sid = _resolve_session(session_id)
    try:
        page = _get_page(sid)
        direction = direction.lower()
        x, y = 0, 0
        if direction == "down":
            y = amount
        elif direction == "up":
            y = -amount
        elif direction == "right":
            x = amount
        elif direction == "left":
            x = -amount
        else:
            return f"Error: unknown direction {direction!r} (use up/down/left/right)"
        page.evaluate(f"window.scrollBy({x}, {y})")
        scroll_y = page.evaluate("window.scrollY")
        return _to_result(True, f"Scrolled {direction} by {amount}px", scroll_y=scroll_y)
    except Exception as e:
        logger.warning(f"browser_scroll_tool failed: {e}")
        return f"Scroll failed: {e}"


@tool("Browser Wait For")
def browser_wait_for_tool(
    selector: str,
    state: str = "visible",
    timeout_ms: int = _DEFAULT_TIMEOUT_MS,
    session_id: Optional[str] = None,
) -> str:
    """Wait until an element matching the CSS selector reaches the given
    `state` — one of "visible", "hidden", "attached", "detached". Returns
    once the condition is met or times out. Use this to synchronise with
    pages that load content asynchronously."""
    sid = _resolve_session(session_id)
    try:
        page = _get_page(sid)
        page.locator(selector).first.wait_for(state=state, timeout=timeout_ms)
        return f"Selector {selector!r} reached state {state!r}."
    except Exception as e:
        logger.warning(f"browser_wait_for_tool failed: {e}")
        return f"Wait failed for {selector!r}: {e}"


@tool("Browser Extract Text")
def browser_extract_text_tool(
    selector: str = "body",
    session_id: Optional[str] = None,
) -> str:
    """Extract the inner text of one or more elements matching a CSS selector,
    separated by newlines. Defaults to `body` for the whole page. Use this
    to read content out of a page for the LLM to reason about."""
    sid = _resolve_session(session_id)
    try:
        page = _get_page(sid)
        texts = page.locator(selector).all_inner_texts()
        return "\n\n---\n\n".join(t.strip() for t in texts if t and t.strip())
    except Exception as e:
        logger.warning(f"browser_extract_text_tool failed: {e}")
        return f"Extract failed for {selector!r}: {e}"


@tool("Browser Close Session")
def browser_close_session_tool(session_id: Optional[str] = None) -> str:
    """Close a browser session and free its Chromium context. Use when you are
    done with browser automation to avoid leaving idle browser processes open."""
    sid = _resolve_session(session_id)
    try:
        BrowserSessionManager.get().close(sid)
        return f"Closed browser session {sid!r}."
    except Exception as e:
        return f"Close failed: {e}"

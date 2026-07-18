"""Platform self-discovery: a structured catalog of every page + API
endpoint the InfinityAI dashboard exposes, with a short description and
the recommended data tool to use for each query.

The catalog is consumed by:
- `db_discover_platform_tool` — LLM-facing, returns a JSON summary the
  model can read to reason about which tool to call for a given request.
- `db_platform_status_tool` — reads multiple sources (DB if configured,
  else local log files + env) to answer "is everything OK?" / "adakah
  kita sudah bersambung dengan X?" without ever opening a browser.
- `db_get_configuration_status_tool` — tells the agent/user what is set
  up (DB, providers, browser, MCP) so they can debug "why doesn't X
  work?" without going through env files.

Design principle: every tool in this module MUST work in BOTH
`mode=live` (Supabase configured) and `mode=demo` (Supabase not set up).
In demo mode they fall back to local log files + env vars, so the agent
always has something useful to answer. This is what the user asked for
after the 'tools are too strict' incident.

`PLATFORM_ROUTES` is the single source of truth. When a new page or API
endpoint is added to the dashboard, add a row here and the LLM will
know about it on the next call to `db_discover_platform_tool`.
"""

import json
import os
from typing import Optional

from crewai.tools import tool

from src.core.config import (
    ANTHROPIC_API_KEY,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_BASE_URL,
    GEMINI_API_KEY,
    GOOGLE_API_KEY,
    LOG_FILE,
    MCP_SERVERS,
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    logger,
)
from src.db.client import db_health
from src.db.repositories.business_profile import BusinessProfileRepo
from src.db.repositories.channels import ChannelRepo
from src.db.repositories.conversations import ConversationRepo
from src.db.repositories.jobs import JobRepo
from src.db.repositories.leads import LeadRepo
from src.db.repositories.quotations import QuotationRepo

ORG_ID = "00000000-0000-0000-0000-000000000001"
_DASHBOARD_CHAT_FILE = "dashboard_chat.json"


# ─── PLATFORM_ROUTES — single source of truth ──────────────────────────────
# Each entry tells the LLM:
#   - what the page/API is,
#   - when to use it,
#   - which direct data tool to call (preferred over browser).
# `id` and `kind` ("page" vs "api") are machine-readable; the rest is for
# the LLM. Keep descriptions short and answer the question "what would I
# find here?".
PLATFORM_ROUTES: list[dict] = [
    # ─── Dashboard pages ──────────────────────────────────────────────────
    {
        "id": "dashboard",
        "kind": "page",
        "label": "Dashboard",
        "tab": "Dashboard",
        "description": (
            "Ringkasan metrik operasi: jumlah tugasan, tugasan siap, "
            "petunjuk sambungan WhatsApp, aktiviti terkini. "
            "Untuk status keseluruhan platform dalam satu panggilan, "
            "guna DB Platform Status (mode live/demo automatik)."
        ),
        "preferred_tool": "DB Platform Status",
    },
    {
        "id": "workorder",
        "kind": "page",
        "tab": "Arahan Kerja",
        "description": (
            "Hantar arahan kerja baru kepada Claudia (Chief of Staff) untuk "
            "diagihkan kepada ejen pakar. Sejarah arahan dan log komunikasi "
            "juga di sini."
        ),
        "preferred_tool": "DB Get Configuration Status (untuk semak ejen) / DB Platform Status",
    },
    {
        "id": "whatsapp-conversations",
        "kind": "page",
        "tab": "WhatsApp > Conversations",
        "description": (
            "Sembang langsung dengan pelanggan WhatsApp yang sedang "
            "berinteraksi. Tunjuk senarai perbualan terbuka dan mesej. "
            "Dalam mode demo (DB tak konfig), akan kosong dengan notis."
        ),
        "preferred_tool": "DB List Open Conversations / Conversation History",
    },
    {
        "id": "whatsapp-leads",
        "kind": "page",
        "tab": "WhatsApp > Leads",
        "description": (
            "Senarai prospek (leads) yang dijana oleh AI selepas interaksi "
            "WhatsApp. Skor (hot/warm/cold), status pipeline, ringkasan "
            "minat, sebab skor. Demo mode = kosong."
        ),
        "preferred_tool": "DB List Leads",
    },
    {
        "id": "whatsapp-quotations",
        "kind": "page",
        "tab": "WhatsApp > Quotations",
        "description": (
            "Sebut harga yang dijana oleh AI, menunggu kelulusan atau "
            "sudah dihantar. Boleh diluluskan oleh Zara atau Bos. "
            "Demo mode = kosong."
        ),
        "preferred_tool": "DB List Pending Quotations",
    },
    {
        "id": "agents",
        "kind": "page",
        "tab": "Agent Config",
        "description": (
            "Konfigurasi setiap ejen AI: provider (OpenAI / Anthropic / "
            "Gemini / OpenRouter / Ollama / Azure), model, role, goal, "
            "backstory, override per-organisasi."
        ),
        "preferred_tool": "DB Get Configuration Status (laporan provider tersedia)",
    },
    {
        "id": "business",
        "kind": "page",
        "tab": "Konfigurasi Perniagaan",
        "description": (
            "Profil syarikat (nama, industri, alamat, telefon, emel, "
            "website, logo) dan katalog produk (nama, harga, stok). "
            "Demo mode = profil kosong, produk kosong."
        ),
        "preferred_tool": "DB Get Business Profile / DB List Products",
    },
    {
        "id": "analytics",
        "kind": "page",
        "tab": "Analytics",
        "description": (
            "Analitik: bilangan mesej diproses, lead dijana, sebut harga "
            "dihantar, kadar respons, trend masa. Demo mode fallback: "
            "guna DB Get Recent Activity (dari daily_log.json)."
        ),
        "preferred_tool": "DB List Leads / DB List Quotations / DB Get Recent Activity",
    },
    {
        "id": "settings",
        "kind": "page",
        "tab": "Settings",
        "description": (
            "Sambungkan WhatsApp Business (QR scan), urus nombor, status "
            "gateway. Untuk status sambungan WhatsApp, guna DB List "
            "Channels (live) atau DB Get Configuration Status (demo)."
        ),
        "preferred_tool": "DB List Channels / DB Get Configuration Status",
    },

    # ─── API endpoints (for direct read when the LLM wants the raw JSON) ──
    {
        "id": "api-business-profile",
        "kind": "api",
        "method": "GET",
        "path": "/api/business/profile",
        "description": "Profil perniagaan syarikat (JSON).",
        "preferred_tool": "DB Get Business Profile",
    },
    {
        "id": "api-channels",
        "kind": "api",
        "method": "GET",
        "path": "/api/channels",
        "description": "Senarai WhatsApp channel + status (pending_qr / connected / disconnected).",
        "preferred_tool": "DB List Channels",
    },
    {
        "id": "api-leads",
        "kind": "api",
        "method": "GET",
        "path": "/api/leads",
        "description": "Senarai leads + skor + status + minat.",
        "preferred_tool": "DB List Leads",
    },
    {
        "id": "api-quotations",
        "kind": "api",
        "method": "GET",
        "path": "/api/quotations",
        "description": "Senarai sebut harga (filter by status).",
        "preferred_tool": "DB List Pending Quotations",
    },
    {
        "id": "api-conversations",
        "kind": "api",
        "method": "GET",
        "path": "/api/conversations",
        "description": "Senarai perbualan terbuka + contact.",
        "preferred_tool": "DB List Open Conversations",
    },
]


# ─── Helpers ───────────────────────────────────────────────────────────────

def _safe_json(obj, limit: int = 6000) -> str:
    try:
        s = json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        s = str(obj)
    if len(s) > limit:
        s = s[:limit] + "... [truncated]"
    return s


def _read_json_file(path: str, default=None, max_entries: int = 50) -> list | dict:
    """Read a local JSON file. Returns `default` if missing or unreadable.
    Used as a fallback when DB isn't configured — every platform tool
    should still be useful in demo mode."""
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data[:max_entries]
        return data
    except Exception as e:
        logger.debug(f"Could not read {path}: {e}")
        return default if default is not None else []


def _check_browser_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _check_mcp_available() -> bool:
    if not MCP_SERVERS:
        return False
    try:
        import mcp  # noqa: F401
        return True
    except ImportError:
        return False


def _provider_status() -> dict:
    """Which AI providers are wired up. Always works — reads from env."""
    return {
        "openai": {"configured": bool(OPENAI_API_KEY), "required": True,
                    "note": "Primary provider for MVP"},
        "anthropic": {"configured": bool(ANTHROPIC_API_KEY), "required": False,
                      "note": "Claude — set ANTHROPIC_API_KEY to enable"},
        "gemini": {"configured": bool(GEMINI_API_KEY or GOOGLE_API_KEY), "required": False,
                   "note": "Google Gemini — set GEMINI_API_KEY or GOOGLE_API_KEY to enable"},
        "openrouter": {"configured": bool(OPENROUTER_API_KEY), "required": False,
                       "note": "Multi-model proxy — set OPENROUTER_API_KEY to enable"},
        "ollama": {"configured": bool(OLLAMA_API_KEY), "base_url": OLLAMA_BASE_URL,
                   "required": False,
                   "note": f"Local models — set OLLAMA_BASE_URL to override {OLLAMA_BASE_URL}"},
        "azure": {"configured": bool(AZURE_OPENAI_API_KEY), "base_url": AZURE_OPENAI_BASE_URL,
                  "required": False,
                  "note": "Azure OpenAI — set AZURE_OPENAI_API_KEY + AZURE_OPENAI_BASE_URL"},
    }


# ─── Tools ─────────────────────────────────────────────────────────────────

@tool("DB Discover Platform")
def db_discover_platform_tool(topic: Optional[str] = None) -> str:
    """Senaraikan semua halaman + API endpoint yang ada di InfinityAI
    dashboard, dengan penerangan ringkas dan tool yang disyorkan untuk
    setiap satu.

    GUNA TOOL INI PERTAMA bila:
    - Bos tanya 'apa yang ada dalam sistem ni?' / 'halaman apa yang kita ada?'
    - Bos tanya sesuatu yang kabur dan anda tidak pasti data di mana
    - Bos merujuk 'website ni' / 'dashboard ni' / 'operasi' tanpa spesifik

    Selepas dapat catalog, pilih tool yang disyorkan (`preferred_tool`)
    untuk fetch data — JANGAN guna browser (browser hanya untuk UI
    testing / screenshot, BUKAN untuk baca data).

    Penapis pilihan: `topic` (contoh: 'whatsapp', 'produk', 'konfigurasi')
    untuk cari route yang berkaitan sahaja."""
    try:
        if topic:
            needle = topic.lower().strip()
            matched = [
                r for r in PLATFORM_ROUTES
                if needle in r.get("id", "").lower()
                or needle in r.get("tab", "").lower()
                or needle in r.get("description", "").lower()
                or needle in r.get("label", "").lower()
            ]
            if not matched:
                return (
                    f"Tiada route匹配 untuk '{topic}'. Cuba: 'whatsapp', 'produk', "
                    f"'profil', 'lead', 'quotation', 'konfigurasi', 'agent'."
                )
            return _safe_json({"topic": topic, "count": len(matched), "routes": matched})
        return _safe_json({
            "total": len(PLATFORM_ROUTES),
            "pages": [r for r in PLATFORM_ROUTES if r["kind"] == "page"],
            "apis": [r for r in PLATFORM_ROUTES if r["kind"] == "api"],
            "tip": (
                "Untuk data, guna `preferred_tool` dari setiap route — "
                "bukan browser. Browser (Playwright) hanya untuk UI testing. "
                "Kebanyakan tool berfungsi dalam mode live (DB) DAN demo "
                "(fallback ke fail tempatan); panggil DB Get Configuration "
                "Status untuk lihat apa yang dikonfigurasikan."
            ),
        })
    except Exception as e:
        logger.warning(f"db_discover_platform_tool failed: {e}")
        return f"Error listing platform routes: {e}"


@tool("DB Get Configuration Status")
def db_get_configuration_status_tool() -> str:
    """Laporan status konfigurasi InfinityAI platform — apa yang sudah
    DISET dan apa yang BELUM. Guna bila:
    - Bos tanya 'kenapa X tak jalan?' / 'apa yang perlu disetup?'
    - Anda perlu tahu sama ada sesuatu akan berfungsi (DB, provider, browser, MCP)
    - Nak debug sebab agent tak boleh akses data

    Sentiasa berfungsi — baca terus dari env vars, tidak bergantung DB.
    Setiap seksyen ada: `configured: bool`, `status: "ready"|"missing"|"disabled"`,
    dan `hint` untuk apa yang perlu dibuat kalau belum ready."""
    try:
        health = db_health()
        providers = _provider_status()
        browser_ok = _check_browser_available()
        mcp_ok = _check_mcp_available()

        return _safe_json({
            "database": {
                "configured": health["available"],
                "mode": health["mode"],
                "url": health["url"],
                "status": "ready" if health["available"] else "missing",
                "reason": health["reason"],
                "hint": health["hint"] if not health["available"] else "",
                "impact": (
                    "Tiada akses langsung ke contacts / leads / products / "
                    "quotations / conversations / business profile / jobs"
                    if not health["available"] else ""
                ),
            },
            "providers": {
                "ready": [k for k, v in providers.items() if v["configured"]],
                "missing": [k for k, v in providers.items() if not v["configured"]],
                "details": providers,
            },
            "browser_tools": {
                "configured": browser_ok,
                "status": "ready" if browser_ok else "missing",
                "reason": "Playwright SDK installed" if browser_ok else "playwright package missing",
                "hint": "" if browser_ok else "Install with: pip install playwright && playwright install chromium",
            },
            "mcp": {
                "configured": mcp_ok,
                "servers_configured": bool(MCP_SERVERS),
                "status": "ready" if mcp_ok else ("disabled" if not MCP_SERVERS else "missing"),
                "reason": (
                    "MCP_SERVERS set + mcp SDK installed" if mcp_ok
                    else "MCP_SERVERS not set" if not MCP_SERVERS
                    else "mcp package missing"
                ),
                "hint": "" if mcp_ok else (
                    "Set MCP_SERVERS env var (JSON) to enable. Install: pip install mcp"
                ),
            },
            "summary": {
                "fully_ready": health["available"] and providers["openai"]["configured"],
                "fallback_mode": not health["available"],
                "any_provider_configured": any(v["configured"] for v in providers.values()),
            },
        })
    except Exception as e:
        logger.warning(f"db_get_configuration_status_tool failed: {e}")
        return f"Error reading configuration status: {e}"


@tool("DB Get Recent Activity")
def db_get_recent_activity_tool(limit: int = 10) -> str:
    """Baca aktiviti terkini InfinityAI (siapa panggil ejen apa, model apa,
    berapa lama, success/error). Sentiasa berfungsi — baca dari fail
    tempatan `daily_log.json` (tidak perlukan DB). Guna sebagai fallback
    untuk 'apa yang baru berlaku?' bila DB tak konfigurasikan."""
    try:
        logs = _read_json_file(LOG_FILE, default=[], max_entries=max(1, min(limit, 100)))
        if not logs:
            return _safe_json({
                "source": LOG_FILE,
                "count": 0,
                "items": [],
                "note": "Tiada aktiviti direkodkan lagi, atau fail daily_log.json belum wujud.",
            })
        return _safe_json({
            "source": LOG_FILE,
            "count": len(logs),
            "items": logs,
        })
    except Exception as e:
        logger.warning(f"db_get_recent_activity_tool failed: {e}")
        return f"Error reading recent activity: {e}"


@tool("DB Platform Status")
def db_platform_status_tool() -> str:
    """Ringkasan status keseluruhan InfinityAI platform dalam SATU panggilan.
    Berfungsi dalam DUA mode:
    - mode=live: Supabase dikonfigurasikan — baca data langsung dari DB
    - mode=demo: Supabase tak diset — fallback ke fail tempatan + env

    Laporan merangkumi:
    - WhatsApp channels + status (connected / pending_qr / disconnected)
    - Bilangan leads (jumlah + pecahan hot/warm/cold)
    - Bilangan sebut harga menunggu kelulusan
    - Bilangan perbualan terbuka
    - Profil perniagaan (nama syarikat, industri)
    - Aktiviti terkini dari daily_log.json (sentiasa)

    GUNA TOOL INI bila Bos tanya soalan status umum seperti:
    - 'adakah kita sudah bersambung dengan WhatsApp?'
    - 'macam mana state platform sekarang?'
    - 'apa yang sedang berlaku dalam sistem?'
    - 'ringkaskan operasi hari ni'

    Tidak perlu browser — semua data dibaca terus dari pangkalan data
    atau fail tempatan. Lebih cepat dan lebih dipercayai dari browser
    scraping."""
    health = db_health()
    mode = health["mode"]

    # ─── Live mode: try the DB ────────────────────────────────────────
    wa_connected = False
    wa_pending = False
    channel_summary: list[dict] = []
    leads: list = []
    pending_quotes: list = []
    open_convs: list = []
    profile: Optional[dict] = None
    live_errors: list[str] = []

    if health["available"]:
        try:
            channels = ChannelRepo().list_by_org(ORG_ID)
            channel_summary = [
                {
                    "id": c.get("id"),
                    "phone_number": c.get("phone_number"),
                    "type": c.get("type"),
                    "status": c.get("status"),
                }
                for c in channels
            ]
            wa_connected = any(c.get("status") == "connected" for c in channels)
            wa_pending = any(c.get("status") == "pending_qr" for c in channels)
        except Exception as e:
            live_errors.append(f"channels: {e}")

        try:
            leads = LeadRepo().list_by_org(ORG_ID)
        except Exception as e:
            live_errors.append(f"leads: {e}")

        try:
            pending_quotes = QuotationRepo().list_pending_approval(ORG_ID)
        except Exception as e:
            live_errors.append(f"quotations: {e}")

        try:
            open_convs = ConversationRepo().list_open(ORG_ID)
        except Exception as e:
            live_errors.append(f"conversations: {e}")

        try:
            profile = BusinessProfileRepo().get_profile(ORG_ID)
        except Exception as e:
            live_errors.append(f"profile: {e}")

    lead_counts: dict = {"hot": 0, "warm": 0, "cold": 0, "other": 0}
    for ld in leads:
        sc = (ld.get("score") or "cold").lower()
        lead_counts[sc if sc in lead_counts else "other"] += 1

    # ─── Always-available: recent activity + chat history (local files)
    recent_activity = _read_json_file(LOG_FILE, default=[], max_entries=10)
    chat_history = _read_json_file(_DASHBOARD_CHAT_FILE, default=[], max_entries=10)

    return _safe_json({
        "mode": mode,
        "database": {
            "available": health["available"],
            "reason": health["reason"],
            "hint": health["hint"],
            "live_errors": live_errors or None,
        },
        "whatsapp": {
            "connected": wa_connected,
            "has_pending_qr": wa_pending,
            "channels": channel_summary,
            "summary": (
                "TERSAMBUNG ke WhatsApp" if wa_connected
                else "MENUNGGU QR scan" if wa_pending
                else "TIDAK DISAMBUNG — tiada channel aktif" if mode == "live"
                else "TIDAK DAPAT DISAHKAN (DB tidak dikonfigurasikan) — semak Settings > WhatsApp Connection untuk setup"
            ),
        },
        "leads": {
            "total": len(leads),
            "by_score": lead_counts,
            "note": "" if mode == "live" else "Tiada data dalam mode demo (DB tidak dikonfigurasikan).",
        },
        "quotations": {
            "pending_approval": len(pending_quotes),
            "note": "" if mode == "live" else "Tiada data dalam mode demo.",
        },
        "conversations": {
            "open": len(open_convs),
            "note": "" if mode == "live" else "Tiada data dalam mode demo.",
        },
        "business_profile": {
            "configured": bool(profile and (profile.get("company_name") or profile.get("industry"))),
            "company_name": (profile or {}).get("company_name", ""),
            "industry": (profile or {}).get("industry", ""),
            "email": (profile or {}).get("email", ""),
        },
        "recent_activity": {
            "source": LOG_FILE,
            "count": len(recent_activity),
            "items": recent_activity,
        },
        "chat_history": {
            "source": _DASHBOARD_CHAT_FILE,
            "count": len(chat_history),
            "items": chat_history[-5:] if chat_history else [],
        },
    })
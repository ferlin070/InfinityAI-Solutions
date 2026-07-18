"""Tests for the platform self-discovery tools (`db_discover_platform_tool`,
`db_platform_status_tool`, `db_get_configuration_status_tool`,
`db_get_recent_activity_tool`) + the `db_health()` helper.

These tools must work in BOTH `mode=live` (Supabase configured) and
`mode=demo` (Supabase not set up) — the whole point of the graceful
fallback rewrite was so the agent can answer even when the DB is missing.
"""

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─── db_health() ────────────────────────────────────────────────────────────

def test_db_health_in_demo_mode_when_env_missing():
    """No SUPABASE env vars -> demo mode, available=False, helpful hint."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
        from src.db.client import db_health
        h = db_health()
    assert h["available"] is False
    assert h["mode"] == "demo"
    assert h["url"] is None
    assert "SUPABASE_URL" in h["reason"]
    assert "SUPABASE_SERVICE_ROLE_KEY" in h["reason"]
    assert h["hint"]  # non-empty hint


def test_db_health_in_live_mode_when_env_set():
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
    }):
        from src.db.client import db_health
        h = db_health()
    assert h["available"] is True
    assert h["mode"] == "live"
    assert h["url"] == "https://test.supabase.co"
    assert h["reason"]


# ─── db_discover_platform_tool ──────────────────────────────────────────────

def test_discover_returns_catalog_with_pages_and_apis():
    from src.ai.tools.platform_catalog import db_discover_platform_tool
    out = json.loads(db_discover_platform_tool.run())
    assert out["total"] >= 10
    assert "pages" in out
    assert "apis" in out
    assert "tip" in out


def test_discover_filters_by_topic():
    from src.ai.tools.platform_catalog import db_discover_platform_tool
    out = json.loads(db_discover_platform_tool.run(topic="whatsapp"))
    assert out["count"] >= 1
    assert all("whatsapp" in r["id"].lower() or "whatsapp" in r.get("tab", "").lower()
               or "whatsapp" in r["description"].lower()
               for r in out["routes"])


def test_discover_unknown_topic_returns_friendly_message():
    from src.ai.tools.platform_catalog import db_discover_platform_tool
    out = db_discover_platform_tool.run(topic="nonexistent-thing")
    assert "Tiada route" in out or "tiada" in out.lower()


# ─── db_get_configuration_status_tool ───────────────────────────────────────

def test_config_status_works_without_db():
    """The whole point — config status always works because it reads env."""
    from src.ai.tools.platform_catalog import db_get_configuration_status_tool
    out = json.loads(db_get_configuration_status_tool.run())
    assert "database" in out
    assert "providers" in out
    assert "browser_tools" in out
    assert "mcp" in out
    assert "summary" in out
    # providers list has all 6
    assert set(out["providers"]["details"].keys()) == {
        "openai", "anthropic", "gemini", "openrouter", "ollama", "azure"
    }
    # DB status reflects env
    assert out["database"]["configured"] is False
    assert out["database"]["mode"] == "demo"
    # Summary reflects demo mode
    assert out["summary"]["fallback_mode"] is True


def test_config_status_reports_openai_when_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from src.ai.tools.platform_catalog import db_get_configuration_status_tool
    out = json.loads(db_get_configuration_status_tool.run())
    assert out["providers"]["ready"] == ["openai"]
    assert "openai" not in out["providers"]["missing"]


def test_config_status_reports_browser_missing(monkeypatch):
    """If playwright not installed, browser_tools.configured = False."""
    monkeypatch.setattr("src.ai.tools.platform_catalog._check_browser_available",
                        lambda: False)
    from src.ai.tools.platform_catalog import db_get_configuration_status_tool
    out = json.loads(db_get_configuration_status_tool.run())
    assert out["browser_tools"]["configured"] is False
    assert out["browser_tools"]["status"] == "missing"
    assert "pip install playwright" in out["browser_tools"]["hint"]


# ─── db_get_recent_activity_tool ────────────────────────────────────────────

def test_recent_activity_reads_local_log_file(tmp_path, monkeypatch):
    """Always works — no DB needed, reads daily_log.json."""
    log_file = tmp_path / "daily_log.json"
    log_file.write_text(json.dumps([
        {"timestamp": "2026-07-19 03:00:00", "agent": "Maya", "model": "gpt-4o-mini",
         "status": "Success", "speed": "0.5s"},
        {"timestamp": "2026-07-19 03:01:00", "agent": "Danish", "model": "gpt-4o",
         "status": "Success", "speed": "1.2s"},
    ]))
    monkeypatch.setattr("src.ai.tools.platform_catalog.LOG_FILE", str(log_file))
    from src.ai.tools.platform_catalog import db_get_recent_activity_tool
    out = json.loads(db_get_recent_activity_tool.run(limit=10))
    assert out["count"] == 2
    assert out["items"][0]["agent"] == "Maya"


def test_recent_activity_handles_missing_file_gracefully(tmp_path, monkeypatch):
    """Missing file -> count=0 + note (not an error)."""
    monkeypatch.setattr("src.ai.tools.platform_catalog.LOG_FILE",
                        str(tmp_path / "does-not-exist.json"))
    from src.ai.tools.platform_catalog import db_get_recent_activity_tool
    out = json.loads(db_get_recent_activity_tool.run())
    assert out["count"] == 0
    assert "note" in out


# ─── db_platform_status_tool (graceful in BOTH modes) ──────────────────────

def test_platform_status_works_in_demo_mode_without_db(monkeypatch):
    """THE bug fix: 'adakah kita sudah bersambung dengan WhatsApp?' should
    still get a useful answer even when Supabase isn't configured."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    from src.ai.tools.platform_catalog import db_platform_status_tool
    out = json.loads(db_platform_status_tool.run())

    assert out["mode"] == "demo"
    assert out["database"]["available"] is False
    assert out["database"]["hint"]  # helpful hint
    # WhatsApp section is present and informative (not a crash)
    assert "summary" in out["whatsapp"]
    assert "tidak dapat disahkan" in out["whatsapp"]["summary"].lower() or \
           "TIDAK DAPAT DISAHKAN" in out["whatsapp"]["summary"]
    # recent_activity section is always populated from local file
    assert "recent_activity" in out
    assert "items" in out["recent_activity"]


def test_platform_status_in_live_mode_uses_db(monkeypatch):
    """When DB is configured, the tool should attempt to read from it and
    return whatever the repos return (empty if empty)."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")

    fake_db = type("FakeDB", (), {})()
    # Make every repo return [] (no data but no crash)
    with patch("src.db.repositories.business_profile.get_supabase", return_value=fake_db), \
         patch("src.db.repositories.channels.get_supabase", return_value=fake_db), \
         patch("src.db.repositories.leads.get_supabase", return_value=fake_db), \
         patch("src.db.repositories.quotations.get_supabase", return_value=fake_db), \
         patch("src.db.repositories.conversations.get_supabase", return_value=fake_db):
        from src.ai.tools.platform_catalog import db_platform_status_tool
        out = json.loads(db_platform_status_tool.run())

    assert out["mode"] == "live"
    assert out["database"]["available"] is True
    assert out["leads"]["total"] == 0
    assert out["conversations"]["open"] == 0


# ─── Wiring: tools on HAKIM and NEXUS ──────────────────────────────────────

def test_hakim_has_all_four_platform_tools():
    from src.ai.agents.tool_mappings import get_tools
    names = {t.name for t in get_tools("HAKIM")}
    assert "DB Discover Platform" in names
    assert "DB Platform Status" in names
    assert "DB Get Configuration Status" in names
    assert "DB Get Recent Activity" in names


def test_nexus_has_all_four_platform_tools_via_union():
    from src.ai.agents.tool_mappings import get_tools
    names = {t.name for t in get_tools("NEXUS")}
    assert "DB Discover Platform" in names
    assert "DB Platform Status" in names
    assert "DB Get Configuration Status" in names
    assert "DB Get Recent Activity" in names


# ─── Backstory guidance mentions "discover first" / "tool over browser" ────

def test_hakim_backstory_mentions_platform_status_tool():
    from src.ai.prompts.loader import resolve_role_goal_backstory
    _, _, backstory = resolve_role_goal_backstory("HAKIM")
    upper = backstory.upper()
    assert "DB PLATFORM STATUS" in upper
    assert "DB DISCOVER PLATFORM" in upper
    # Key teaching point: tool first, browser last
    assert "BROWSER" in upper
    assert "JANGAN" in upper  # don't use browser for data


def test_nexus_backstory_mentions_tool_first_strategy():
    from src.ai.prompts.loader import resolve_role_goal_backstory
    _, _, backstory = resolve_role_goal_backstory("NEXUS")
    upper = backstory.upper()
    assert "DB PLATFORM STATUS" in upper
    assert "JANGAN" in upper  # don't jump to browser

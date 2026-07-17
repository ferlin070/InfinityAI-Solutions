import os
import re

from crewai.tools import tool

_DOCS_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs")
)
_README_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "README.md")
)
_DOCKER_COMPOSE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docker-compose.yml")
)

_TOPIC_MAP: list[tuple[list[str], list[str]]] = [
    (["whatsapp", "wa", "gateway", "was-", "process_inbound", "inbound"],
     ["architecture/m1-whatsapp-sales-funnel.md"]),
    (["setup", "install", "deploy", "docker", "compose", "run", "jalan", "start"],
     ["deployment.md", "architecture/proposal-v2.md"]),
    (["agent", "claudia", "maya", "zara", "crewai", "orchestrat", "task execution",
      "aiman", "danish", "amelia", "adila", "hakim", "llm", "provider"],
     ["architecture/ai-execution-crewai.md"]),
    (["dashboard", "frontend", "design", "ui", "css", "html", "tema", "theme",
      "dokumen pejabat", "office document"],
     ["frontend/dashboard-design.md", "../README.md"]),
    (["database", "supabase", "postgres", "migration", "sql", "tables", "schema",
      "rls", "row level security"],
     ["architecture/proposal-v2.md"]),
    (["architecture", "overview", "senibina", "system", "platform", "modul",
      "component", "structure"],
     ["architecture/proposal-v2.md", "architecture/sistem-semasa.md"]),
    (["business", "pricing", "harga", "produk", "product", "client", "customer",
      "value", "paket", "plan", "cost", "kos"],
     ["business/dokumentasi-perniagaan.md"]),
    (["security", "keselamatan", "audit", "xss", "csrf", "vulnerability",
      "bug", "fix"],
     ["development/audit-report-2026-07.md"]),
    (["api", "endpoint", "route", "rest", "webhook"],
     ["architecture/proposal-v2.md"]),
    (["quotation", "sebut harga", "quote", "pdf", "reportlab", "harga",
      "price", "billing"],
     ["architecture/m1-whatsapp-sales-funnel.md"]),
    (["lead", "prospek", "score", "scoring", "crm", "sales", "jualan"],
     ["architecture/m1-whatsapp-sales-funnel.md"]),
    (["daily briefing", "briefing", "laporan", "report", "scheduler",
      "schedule", "8am", "pagi"],
     ["architecture/m1-whatsapp-sales-funnel.md"]),
    (["prd", "product requirements", "requirement", "specification"],
     ["business/PRD.md"]),
    (["config", "configuration", "konfigurasi", "setting", "env",
      "environment", ".env"],
     ["deployment.md"]),
    (["tool", "function calling", "tool call", "crewai tool", "@tool",
      "product_pricing", "contact_info", "conversation_history"],
     ["architecture/ai-execution-crewai.md"]),
    (["troubleshoot", "error", "problem", "masalah", "issue", "not working",
      "fail", "gagal", "error"],
     ["deployment.md", "development/audit-report-2026-07.md"]),
]


def _find_relevant_files(query: str) -> list[str]:
    query_lower = query.lower()
    matched = set()
    for keywords, files in _TOPIC_MAP:
        if any(kw in query_lower for kw in keywords):
            for f in files:
                if f.startswith("../"):
                    path = os.path.join(os.path.dirname(_README_PATH), f[3:])
                else:
                    path = os.path.join(_DOCS_ROOT, f)
                if os.path.exists(path):
                    matched.add(path)
    if not matched:
        matched.add(os.path.join(_DOCS_ROOT, "architecture", "sistem-semasa.md"))
        readme_note = os.path.join(os.path.dirname(_README_PATH), "README.md")
        if os.path.exists(readme_note):
            matched.add(readme_note)
    return list(matched)


def _read_file(path: str, max_chars: int = 6000) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n... [truncated]"
        return content
    except Exception as e:
        return f"[Error reading {path}: {e}]"


@tool("System Documentation")
def system_documentation_tool(query: str) -> str:
    """Search the project's documentation for setup guides, architecture docs,
    deployment instructions, and feature explanations. Use this tool whenever
    someone asks how to set up, configure, deploy, or use the InfinityAI platform
    itself — never invent instructions, always look them up here."""
    files = _find_relevant_files(query)
    if not files:
        return "No relevant documentation found for your query."

    parts = [f"--- {os.path.relpath(p, _DOCS_ROOT)} ---\n{_read_file(p)}" for p in files]
    return "\n\n".join(parts)

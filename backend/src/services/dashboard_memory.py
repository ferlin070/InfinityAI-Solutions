import json
import os
from src.core.config import logger

MEMORY_FILE = "dashboard_chat.json"
MAX_TURNS = 40


def append_message(role: str, content: str) -> None:
    """Append one turn (role: 'user' or 'assistant') to the dashboard chat
    transcript, keeping only the most recent MAX_TURNS entries."""
    history = _load()
    history.append({"role": role, "content": content})
    _save(history[-MAX_TURNS:])


def get_recent(n: int = 20) -> list[dict]:
    return _load()[-n:]


def clear() -> None:
    _save([])


def _load() -> list[dict]:
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Gagal baca {MEMORY_FILE}: {str(e)}. Memulakan sejarah baru.")
        return []


def _save(history: list[dict]) -> None:
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Gagal simpan {MEMORY_FILE}: {str(e)}")

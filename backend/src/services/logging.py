import json
import os
from datetime import datetime
from src.core.config import LOG_FILE, logger


def extract_json(text: str) -> str | None:
    """
    Extract a JSON object from `text` robustly.

    Tries, in order:
      1. The whole text (in case the LLM emits pure JSON).
      2. A fenced ```json ... ``` block.
      3. A fenced ``` ... ``` block (no language tag).
      4. The first balanced `{...}` substring (with proper string escaping).
      5. A balanced `{...}` ignoring string rules (last-resort fallback).

    Returns the JSON text on success, or None if no candidate parses.
    The caller is expected to handle the None case gracefully — see
    `task_execution_flow.py`: when the LLM gives a non-empty answer
    without JSON, the flow treats it as a `chat` reply instead of an
    error, so the user still sees Claudia's response.
    """
    if not text:
        return None

    text_clean = text.strip()
    # Normalize line endings inside strings — LLMs sometimes embed
    # literal \n or unescaped newlines that break json.loads.
    # We try parsing as-is first; fall back to other strategies if it fails.

    candidates: list[str] = []

    # 1. Whole text as JSON
    candidates.append(text_clean)

    # 2 & 3. Fenced code blocks
    import re as _re
    for m in _re.finditer(r"```(?:json)?\s*\n?(.*?)\n?```", text_clean, _re.DOTALL):
        candidates.append(m.group(1).strip())

    # 4. First balanced {...} with proper string escaping
    start = text_clean.find("{")
    if start != -1:
        count = 0
        in_string = False
        escape = False
        for i in range(start, len(text_clean)):
            char = text_clean[i]
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string:
                if char == "{":
                    count += 1
                elif char == "}":
                    count -= 1
                    if count == 0:
                        candidates.append(text_clean[start:i + 1])
                        break

    # 5. Last-resort: balanced {...} ignoring string rules
    if start != -1:
        count = 0
        for i in range(start, len(text_clean)):
            if text_clean[i] == "{": count += 1
            elif text_clean[i] == "}":
                count -= 1
                if count == 0:
                    candidates.append(text_clean[start:i + 1])
                    break

    # Try every candidate, return the first one that parses.
    for c in candidates:
        try:
            json.loads(c)
            return c
        except Exception:
            continue
    return None


def add_json_log(agent: str, model: str, status: str, duration: float) -> None:
    """
    Add entry to daily JSON log file.

    Args:
        agent: Agent name
        model: Model used
        status: Status (Success, Error, etc.)
        duration: Execution duration in seconds
    """
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent": agent,
        "model": model,
        "status": status,
        "speed": f"{duration:.2f}s"
    }

    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception as e:
            logger.warning(f"Ralat membaca fail log harian: {str(e)}. Memulakan log baru.")
            logs = []

    logs.insert(0, log_entry)

    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs[:50], f, indent=4)
    except Exception as e:
        logger.error(f"Gagal menulis log ke fail {LOG_FILE}: {str(e)}")

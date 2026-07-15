import json
import os
from datetime import datetime
from src.core.config import LOG_FILE, logger


def extract_json(text: str) -> str | None:
    """
    Extract and parse JSON from text robustly.
    Handles markdown code blocks, control characters, and nested braces.

    Returns:
        JSON string if found, None otherwise
    """
    if not text:
        return None

    text_clean = text.replace("```json", "").replace("```", "").strip()

    # Find first opening brace
    start = text_clean.find('{')
    if start == -1:
        return None

    # Try to find matching braces while respecting strings
    count = 0
    in_string = False
    escape = False

    for i in range(start, len(text_clean)):
        char = text_clean[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                count += 1
            elif char == '}':
                count -= 1
                if count == 0:
                    candidate = text_clean[start:i+1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        pass

    # Fallback: simple brace counting
    count = 0
    for i in range(start, len(text_clean)):
        if text_clean[i] == '{': count += 1
        elif text_clean[i] == '}': count -= 1
        if count == 0:
            return text_clean[start:i+1]

    return text_clean[start:].strip() if start != -1 else None


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

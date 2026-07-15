import requests
from src.core.config import GAS_URL, FOLDER_IDS, logger


def upload_to_drive(filename: str, content: str, agent_name: str) -> None:
    """
    Upload task result to Google Drive via Google Apps Script.

    Args:
        filename: Name of the file to upload
        content: File content (text)
        agent_name: Agent name to determine folder
    """
    folder_id = FOLDER_IDS.get(agent_name)
    if not GAS_URL or not folder_id:
        logger.info(f"Skip Drive: GAS_URL atau Folder ID untuk {agent_name} tiada.")
        return

    try:
        payload = {"filename": filename, "content": content, "folderId": folder_id}
        resp = requests.post(GAS_URL, json=payload, timeout=30)
        resp.raise_for_status()
        logger.info(f"GAS Upload Berjaya: {filename} ({agent_name})")
    except Exception as e:
        logger.error(f"Ralat Upload Drive untuk {agent_name}: {str(e)}", exc_info=True)

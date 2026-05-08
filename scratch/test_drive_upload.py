import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = 'credentials.json'
ZARA_FOLDER_ID = os.getenv("ZARA_DRIVE_FOLDER_ID")

def test_upload():
    if not os.path.exists(CREDENTIALS_FILE):
        print("Credentials file not found.")
        return

    scopes = ['https://www.googleapis.com/auth/drive.file']
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': 'Test_Upload_System.txt',
        'parents': [ZARA_FOLDER_ID]
    }
    
    content = "Ini adalah fail ujian untuk pengesahan integrasi Google Drive."
    fh = io.BytesIO(content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)
    
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"Berjaya! Fail dimuat naik dengan ID: {file.get('id')}")
    except Exception as e:
        print(f"Gagal muat naik: {str(e)}")

if __name__ == "__main__":
    test_upload()

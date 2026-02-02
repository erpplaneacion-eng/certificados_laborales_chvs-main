from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from app.google_clients import get_drive_service
from app.config import settings

def upload_pdf(file_stream: BytesIO, filename: str):
    drive = get_drive_service()
    media = MediaIoBaseUpload(file_stream, mimetype="application/pdf")
    metadata = {"name": filename, "parents": [settings.DRIVE_FOLDER_ID]}
    file = drive.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True  # <- AÑADE ESTA LÍNEA
    ).execute()
    return file

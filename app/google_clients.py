import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread
from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents"
]

def get_credentials():
    raw = settings.GOOGLE_CREDENTIALS_JSON
    # --- INICIO DEL CÓDIGO DE DEPURACIÓN ---
    print("--- DEBUG: Verificando el contenido de GOOGLE_CREDENTIALS_JSON ---")
    print(f"El contenido recibido es: '{raw}'")
    print(f"La longitud del contenido es: {len(raw)}")
    # --- FIN DEL CÓDIGO DE DEPURACIÓN ---
    info = json.loads(raw)
    return Credentials.from_service_account_info(info, scopes=SCOPES)

def get_gspread_client():
    creds = get_credentials()
    return gspread.authorize(creds)

def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)

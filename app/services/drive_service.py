from io import BytesIO
from typing import Optional
from googleapiclient.http import MediaIoBaseUpload
from app.google_clients import get_drive_service
from app.config import settings

def get_or_create_person_folder(nombre_completo: str, cedula: str) -> str:
    """
    Busca o crea una carpeta para la persona dentro de la carpeta principal.

    Args:
        nombre_completo: Nombre completo de la persona
        cedula: Número de cédula

    Returns:
        ID de la carpeta de la persona
    """
    drive = get_drive_service()

    # Crear nombre de carpeta limpio: "Juan_Perez_12345678"
    folder_name = f"{nombre_completo.replace(' ', '_')}_{cedula}"

    # Buscar si ya existe la carpeta
    query = (
        f"name='{folder_name}' and "
        f"'{settings.DRIVE_FOLDER_ID}' in parents and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"trashed=false"
    )

    response = drive.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    folders = response.get('files', [])

    if folders:
        # La carpeta ya existe, retornar su ID
        return folders[0]['id']

    # La carpeta no existe, crearla
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [settings.DRIVE_FOLDER_ID]
    }

    folder = drive.files().create(
        body=folder_metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()

    return folder['id']

def upload_pdf(file_stream: BytesIO, filename: str, nombre_completo: Optional[str] = None, cedula: Optional[str] = None):
    """
    Sube un PDF a Google Drive.

    Args:
        file_stream: Stream del archivo PDF
        filename: Nombre del archivo
        nombre_completo: Nombre completo de la persona (opcional, para crear subcarpeta)
        cedula: Cédula de la persona (opcional, para crear subcarpeta)

    Returns:
        Información del archivo subido
    """
    drive = get_drive_service()
    media = MediaIoBaseUpload(file_stream, mimetype="application/pdf")

    # Determinar la carpeta padre
    if nombre_completo and cedula:
        # Crear/obtener carpeta de la persona
        parent_folder_id = get_or_create_person_folder(nombre_completo, cedula)
    else:
        # Usar carpeta principal directamente
        parent_folder_id = settings.DRIVE_FOLDER_ID

    metadata = {"name": filename, "parents": [parent_folder_id]}
    file = drive.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True
    ).execute()
    return file

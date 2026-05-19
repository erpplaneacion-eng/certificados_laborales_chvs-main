from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Mi App de Certificados"
    environment: str = "development"
    debug: bool = True
    GOOGLE_CREDENTIALS_JSON: str
    SHEET_ID: str
    SHEET_ID_PLANTA: Optional[str] = None  # Sheet secundaria con pestaña "Planta"
    SOLICITUDES_SHEET_ID: str  # Sheet donde llegan las solicitudes del Google Form
    DRIVE_FOLDER_ID: str
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=(".env", "certificados_laborales_chvs-docker.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

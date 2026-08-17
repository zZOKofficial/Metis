from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    '''Application settings loaded from environment variables.'''

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_delimiter=',',
    )

    # Google Cloud
    GOOGLE_CLOUD_PROJECT: str = ''
    GOOGLE_APPLICATION_CREDENTIALS: str = ''
    GEMINI_API_KEY: str = ''

    # Application
    APP_NAME: str = 'METIS'
    APP_VERSION: str = '0.4.1'
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = ['http://localhost:3000', 'http://localhost:8000']

    # Firestore
    FIRESTORE_DATABASE: str = '(default)'


settings = Settings()

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from typing import Any, Optional


def _accept_comma_separated_lists(
    source: PydanticBaseSettingsSource,
) -> PydanticBaseSettingsSource:
    '''Let list-valued settings be written as `a,b` and not only as `["a","b"]`.

    pydantic-settings decodes a `list[str]` env var as JSON, so the obvious way
    to write CORS_ORIGINS into a hosting dashboard -- comma-separated, one
    origin after another -- raises SettingsError while the module is still
    being imported, and the container dies at boot with a message naming the
    field but not the reason. A JSON array still works; this only adds the
    plainer spelling alongside it.

    The source is decorated rather than subclassed because pydantic hands us
    instances it has already configured (`env_file`, `case_sensitive`, and the
    rest, including per-call overrides like `Settings(_env_file=None)` in the
    tests). Rebuilding them here would silently drop all of that.
    '''
    original = source.prepare_field_value

    def prepare_field_value(
        field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        is_complex, _ = source._field_is_complex(field)
        if (
            (is_complex or value_is_complex)
            and isinstance(value, str)
            and not value.lstrip().startswith(('[', '{'))
        ):
            return [item.strip() for item in value.split(',') if item.strip()]
        return original(field_name, field, value, value_is_complex)

    source.prepare_field_value = prepare_field_value
    return source


class Settings(BaseSettings):
    '''Application settings loaded from environment variables.'''

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            _accept_comma_separated_lists(env_settings),
            _accept_comma_separated_lists(dotenv_settings),
            file_secret_settings,
        )

    # Google Cloud
    GOOGLE_CLOUD_PROJECT: str = ''
    GOOGLE_APPLICATION_CREDENTIALS: str = ''
    # The same service-account key, inlined. Hosts without a metadata server
    # (Hugging Face Spaces, Render, any plain container) have nowhere to put a
    # file, so the key travels as a secret and is materialised at startup --
    # see core/credentials.py.
    GOOGLE_APPLICATION_CREDENTIALS_JSON: str = ''
    GEMINI_API_KEY: str = ''

    # Application
    APP_NAME: str = 'METIS'
    APP_VERSION: str = '0.8.6'
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = ['http://localhost:3000', 'http://localhost:8000']

    # Firestore
    FIRESTORE_DATABASE: str = '(default)'

    # Local storage
    METIS_DB_PATH: str = ''  # override the SQLite path (tests / E2E use a clean copy)

    # Refuse to fall back to SQLite when Firestore was asked for and did not
    # answer. Off locally, where falling back is the point; on for any hosted
    # deployment, where the container filesystem is thrown away on restart and
    # a silent fallback means silently losing every order.
    METIS_REQUIRE_FIRESTORE: bool = False

    # Demo mode: answer agent chats deterministically without a Gemini key
    METIS_MOCK_AI: bool = False

    # Enforce business ownership on owner-facing routes. Off for local
    # development; required before hosting the API.
    METIS_AUTH_ENABLED: bool = False

    # Firebase Authentication (falls back to GOOGLE_CLOUD_PROJECT when unset)
    FIREBASE_PROJECT_ID: str = ''


settings = Settings()

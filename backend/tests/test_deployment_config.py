"""Configuration that only ever runs on a hosted deployment.

Everything here is about the gap between a laptop and a container: settings
written into a dashboard text box instead of a file, credentials that arrive
as a secret rather than a mounted key, and a Firestore fallback that is
correct locally and data-destroying in production. None of it needs a network,
a Google project or a Firebase key -- `google.cloud.firestore` is patched at
the one place `get_db()` imports it.
"""
import json
import os

import pytest

from src.core import credentials
from src.core.config import Settings, settings
from src.services import firestore as firestore_module


# --- CORS_ORIGINS ------------------------------------------------------------
# pydantic-settings decodes list-typed env vars as JSON. A hosting dashboard is
# a single text box, so the comma-separated spelling has to work too -- without
# it the failure is a SettingsError at import, i.e. a container that never boots.

@pytest.mark.parametrize('raw, expected', [
    ('["https://a.app","https://b.app"]', ['https://a.app', 'https://b.app']),
    ('https://a.app,https://b.app', ['https://a.app', 'https://b.app']),
    ('https://a.app, https://b.app', ['https://a.app', 'https://b.app']),
    ('https://solo.app', ['https://solo.app']),
])
def test_cors_origins_accepts_json_and_comma_separated(monkeypatch, raw, expected):
    monkeypatch.setenv('CORS_ORIGINS', raw)
    assert Settings(_env_file=None).CORS_ORIGINS == expected


def test_cors_origins_defaults_to_localhost(monkeypatch):
    monkeypatch.delenv('CORS_ORIGINS', raising=False)
    assert Settings(_env_file=None).CORS_ORIGINS == [
        'http://localhost:3000',
        'http://localhost:8000',
    ]


def test_env_file_override_still_honoured(monkeypatch):
    """The lenient sources must not drop the config pydantic hands them.

    `Settings(_env_file=None)` is how the tests ignore a developer's local
    backend/.env; rebuilding the sources instead of decorating them would
    silently reinstate it.
    """
    monkeypatch.delenv('APP_VERSION', raising=False)
    assert Settings(_env_file=None).APP_VERSION == Settings.model_fields['APP_VERSION'].default


# --- service-account credentials ---------------------------------------------

VALID_KEY = {
    'type': 'service_account',
    'project_id': 'metis-test',
    'client_email': 'metis@metis-test.iam.gserviceaccount.com',
    'private_key': '-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n-----END PRIVATE KEY-----\n',
}


@pytest.fixture()
def clean_credentials_env(monkeypatch):
    monkeypatch.delenv('GOOGLE_APPLICATION_CREDENTIALS', raising=False)
    monkeypatch.setattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', '')
    monkeypatch.setattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS_JSON', '')


def test_no_credentials_configured_is_a_noop(clean_credentials_env):
    """Local development and the test suite: nothing set, nothing invented."""
    assert credentials.configure_google_credentials() is None
    assert 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ


def test_inlined_key_is_written_and_exported(clean_credentials_env, monkeypatch):
    monkeypatch.setattr(
        settings, 'GOOGLE_APPLICATION_CREDENTIALS_JSON', json.dumps(VALID_KEY)
    )
    path = credentials.configure_google_credentials()
    try:
        assert os.environ['GOOGLE_APPLICATION_CREDENTIALS'] == path
        with open(path, encoding='utf-8') as f:
            assert json.load(f) == VALID_KEY
    finally:
        os.unlink(path)


def test_a_mounted_key_file_wins_over_an_inlined_one(clean_credentials_env, monkeypatch):
    """An explicit path in the real environment is the operator being specific."""
    monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', '/mounted/key.json')
    monkeypatch.setattr(
        settings, 'GOOGLE_APPLICATION_CREDENTIALS_JSON', json.dumps(VALID_KEY)
    )
    assert credentials.configure_google_credentials() == '/mounted/key.json'
    assert os.environ['GOOGLE_APPLICATION_CREDENTIALS'] == '/mounted/key.json'


def test_credentials_path_from_settings_is_exported(clean_credentials_env, monkeypatch):
    """The long-standing trap: set in .env, never reaching the SDKs.

    pydantic-settings reads .env into `settings` and never writes back to
    os.environ, where Application Default Credentials actually looks.
    """
    monkeypatch.setattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', '/from/dotenv.json')
    assert credentials.configure_google_credentials() == '/from/dotenv.json'
    assert os.environ['GOOGLE_APPLICATION_CREDENTIALS'] == '/from/dotenv.json'


@pytest.mark.parametrize('bad, reason', [
    ('{"client_email": "x@y.com"', 'truncated'),
    ('not json at all', 'not json'),
    ('["client_email"]', 'not an object'),
    ('{"project_id": "metis"}', 'no client_email'),
])
def test_unusable_inlined_key_fails_loudly(clean_credentials_env, monkeypatch, bad, reason):
    """A mangled paste must name itself, not surface later inside a Google SDK."""
    monkeypatch.setattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS_JSON', bad)
    with pytest.raises(RuntimeError):
        credentials.configure_google_credentials()


# --- the Firestore fallback --------------------------------------------------

class _ExplodingFirestore:
    """Stands in for `google.cloud.firestore` with unusable credentials."""

    @staticmethod
    def Client(*args, **kwargs):
        raise RuntimeError('could not determine credentials')


@pytest.fixture()
def firestore_unreachable(monkeypatch):
    """Make `from google.cloud import firestore` yield a client that cannot connect."""
    import google.cloud
    monkeypatch.setattr(google.cloud, 'firestore', _ExplodingFirestore, raising=False)
    monkeypatch.setitem(
        __import__('sys').modules, 'google.cloud.firestore', _ExplodingFirestore
    )
    firestore_module._db = None
    yield
    firestore_module._db = None


def test_falls_back_to_sqlite_when_firestore_fails_and_is_optional(
    firestore_unreachable, monkeypatch, tmp_path
):
    """Today's local behaviour, pinned: a laptop with no credentials still runs."""
    monkeypatch.setattr(settings, 'GOOGLE_CLOUD_PROJECT', 'metis-test')
    monkeypatch.setattr(settings, 'METIS_REQUIRE_FIRESTORE', False)
    monkeypatch.setattr(settings, 'METIS_DB_PATH', str(tmp_path / 'fallback.db'))
    assert isinstance(firestore_module.get_db(), firestore_module.SqliteDB)


def test_refuses_to_fall_back_when_firestore_is_required(
    firestore_unreachable, monkeypatch, tmp_path
):
    """The whole point: on an ephemeral container, quiet SQLite loses everything."""
    monkeypatch.setattr(settings, 'GOOGLE_CLOUD_PROJECT', 'metis-test')
    monkeypatch.setattr(settings, 'METIS_REQUIRE_FIRESTORE', True)
    monkeypatch.setattr(settings, 'METIS_DB_PATH', str(tmp_path / 'never.db'))
    with pytest.raises(RuntimeError, match='METIS_REQUIRE_FIRESTORE'):
        firestore_module.get_db()
    assert not (tmp_path / 'never.db').exists(), 'SQLite must not be touched'


def test_requiring_firestore_without_a_project_is_a_contradiction(monkeypatch):
    monkeypatch.setattr(settings, 'GOOGLE_CLOUD_PROJECT', '')
    monkeypatch.setattr(settings, 'METIS_REQUIRE_FIRESTORE', True)
    firestore_module._db = None
    try:
        with pytest.raises(RuntimeError, match='GOOGLE_CLOUD_PROJECT'):
            firestore_module.get_db()
    finally:
        firestore_module._db = None


def test_a_lazily_broken_client_is_caught_at_startup(monkeypatch, tmp_path):
    """`firestore.Client(...)` constructs fine on bad credentials and fails later.

    Without the verifying read, a deployment with an expired key reports itself
    healthy and then fails one request at a time.
    """
    class _LazyClient:
        def collection(self, name):
            raise RuntimeError('403 Missing or insufficient permissions')

    class _LazyFirestore:
        Client = staticmethod(lambda *a, **k: _LazyClient())

    monkeypatch.setitem(__import__('sys').modules, 'google.cloud.firestore', _LazyFirestore)
    import google.cloud
    monkeypatch.setattr(google.cloud, 'firestore', _LazyFirestore, raising=False)
    monkeypatch.setattr(settings, 'GOOGLE_CLOUD_PROJECT', 'metis-test')
    monkeypatch.setattr(settings, 'METIS_REQUIRE_FIRESTORE', True)
    monkeypatch.setattr(settings, 'METIS_DB_PATH', str(tmp_path / 'never.db'))
    firestore_module._db = None
    try:
        with pytest.raises(RuntimeError, match='unreachable'):
            firestore_module.get_db()
    finally:
        firestore_module._db = None


# --- /health -----------------------------------------------------------------

def test_health_reports_the_live_backend_and_auth_mode(client, monkeypatch):
    """The post-deploy smoke test: which store is really serving, is auth on."""
    body = client.get('/health').json()
    assert body['status'] == 'healthy'
    assert body['database'] == 'sqlite'
    assert body['auth_enforced'] is False


def test_health_reflects_auth_being_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, 'METIS_AUTH_ENABLED', True)
    assert client.get('/health').json()['auth_enforced'] is True

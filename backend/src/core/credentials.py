'''Make a Google service-account key visible to the Google SDKs.

Both SDKs this app uses -- `google-cloud-firestore` in
`services/firestore.py` and `firebase_admin` in `core/firebase.py` -- resolve
their credentials through Application Default Credentials, which reads the
real process environment variable `GOOGLE_APPLICATION_CREDENTIALS` and expects
it to name a key file on disk. Neither reads our `Settings` object.

That leaves two gaps this module closes, both of which fail silently:

1. `GOOGLE_APPLICATION_CREDENTIALS` set in `backend/.env` does nothing at all.
   pydantic-settings reads the file into `settings`; it never exports anything
   back into `os.environ`, so ADC keeps looking at an environment that was
   never told. The setting has existed since the first commit and has never
   had any effect.

2. A host with no metadata server and no mountable file -- Hugging Face
   Spaces, Render, any plain container -- can only inject a secret as an
   environment variable. There is nowhere to put a key file, so the key
   arrives as JSON text and has to be written to disk before the SDKs look
   for it.

Both are resolved once, at startup, so that every SDK downstream sees the
single environment variable it already knows how to find.
'''
import json
import os
import stat
import tempfile
from typing import Optional

from .config import settings

_ENV_VAR = 'GOOGLE_APPLICATION_CREDENTIALS'


def configure_google_credentials() -> Optional[str]:
    '''Point ADC at a usable key file. Returns its path, or None.

    Order of precedence, most explicit first:

    1. A real `GOOGLE_APPLICATION_CREDENTIALS` already in the environment --
       someone mounted a file and said where it is. Never overridden.
    2. `GOOGLE_APPLICATION_CREDENTIALS_JSON` -- the key inlined as a secret.
       Written to a private temp file, which the environment variable is then
       pointed at.
    3. `GOOGLE_APPLICATION_CREDENTIALS` from `.env`/settings -- exported to
       the real environment so it finally takes effect.

    A no-op when none of those is set, which is the local-development and test
    case: no credentials means `get_db()` uses SQLite and `verify_token()`
    reports Firebase as unavailable, both of which are already handled.
    '''
    if os.environ.get(_ENV_VAR):
        return os.environ[_ENV_VAR]

    inline = settings.GOOGLE_APPLICATION_CREDENTIALS_JSON.strip()
    if inline:
        return _write_key_file(inline)

    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        os.environ[_ENV_VAR] = settings.GOOGLE_APPLICATION_CREDENTIALS
        return settings.GOOGLE_APPLICATION_CREDENTIALS

    return None


def _write_key_file(inline: str) -> str:
    '''Materialise an inlined key, failing loudly if it is not usable.

    Parsed before it is written so a truncated or quote-mangled secret -- the
    usual result of pasting JSON into a dashboard text box -- is reported here,
    naming the actual problem, instead of surfacing later as an opaque refusal
    from deep inside a Google SDK.
    '''
    try:
        key = json.loads(inline)
    except ValueError as e:
        raise RuntimeError(
            f'{_ENV_VAR}_JSON is not valid JSON ({e}). Paste the whole '
            f'service-account key file, on one line.'
        ) from e

    if not isinstance(key, dict) or 'client_email' not in key:
        raise RuntimeError(
            f'{_ENV_VAR}_JSON does not look like a service-account key '
            f'(no "client_email" field).'
        )

    fd, path = tempfile.mkstemp(prefix='metis-gcp-key-', suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(inline)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    os.environ[_ENV_VAR] = path
    print(f'INFO: Google credentials for {key["client_email"]} written to {path}.')
    return path

'''Firebase Admin token verification.

Deliberately a thin seam: everything the rest of the app needs is
`verify_token(id_token) -> uid | None`. That keeps `firebase_admin` out of the
import path when auth is disabled (local development, the test suite) and gives
tests one function to patch instead of a vendor SDK.

Verification is a local JWT signature check against Google's public keys, which
the SDK fetches once and caches -- there is no network round-trip per request.
'''
import threading
from typing import Optional

from .config import settings

_app = None
_lock = threading.Lock()
_unavailable_reason: Optional[str] = None


def _get_app():
    '''Initialise the Admin SDK once, or return None if it cannot be set up.

    On Cloud Run the default service account supplies credentials implicitly;
    locally, GOOGLE_APPLICATION_CREDENTIALS points at a service-account key.
    '''
    global _app, _unavailable_reason
    if _app is not None or _unavailable_reason is not None:
        return _app

    with _lock:
        if _app is not None or _unavailable_reason is not None:
            return _app
        try:
            import firebase_admin
            from firebase_admin import credentials

            if firebase_admin._apps:
                _app = firebase_admin.get_app()
            else:
                options = {}
                project_id = settings.FIREBASE_PROJECT_ID or settings.GOOGLE_CLOUD_PROJECT
                if project_id:
                    options['projectId'] = project_id
                _app = firebase_admin.initialize_app(
                    credentials.ApplicationDefault(), options or None
                )
        except Exception as e:
            # Missing package, missing credentials, malformed key -- all mean
            # the same thing to callers: no verification is possible. Recorded
            # once so a misconfigured deployment is visible in the logs without
            # printing on every request.
            _unavailable_reason = str(e)
            print(
                f'WARNING: Firebase Admin unavailable ({e}). Bearer tokens '
                f'cannot be verified; every request will be treated as '
                f'anonymous. With METIS_AUTH_ENABLED on, owner routes will '
                f'reject all callers.'
            )
    return _app


def verify_token(id_token: str) -> Optional[str]:
    '''Return the uid for a valid Firebase ID token, or None.

    Never raises: an expired, forged, or malformed token is simply not a
    signed-in caller. The middleware relies on that to stay non-rejecting, so
    public routes keep working for clients that send no token at all.
    '''
    if not id_token:
        return None
    app = _get_app()
    if app is None:
        return None
    try:
        from firebase_admin import auth as firebase_auth
        claims = firebase_auth.verify_id_token(id_token, app=app)
    except Exception:
        return None
    return claims.get('uid') or claims.get('sub')


def reset_for_tests() -> None:
    '''Drop the cached app so a test can re-exercise initialisation.'''
    global _app, _unavailable_reason
    _app = None
    _unavailable_reason = None

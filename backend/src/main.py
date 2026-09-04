from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from .core.config import settings
from .core import firebase
from .core.credentials import configure_google_credentials
from .services.firestore import backend_name
from .api.routes import router

STATIC_DIR = Path(__file__).parent / 'static'

# Before anything touches a Google SDK: both of them read credentials from the
# real process environment, which nothing has populated yet on a host that can
# only hand us secrets as environment variables.
configure_google_credentials()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description='METIS - AI-operated business management platform',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.middleware('http')
async def resolve_caller_identity(request: Request, call_next):
    '''Attach the caller's uid to the request, when they present a valid token.

    Deliberately non-rejecting. Authorisation is decided per route by
    `require_business_access`, and the public storefront endpoints must stay
    reachable by shoppers who have no account at all -- so a missing, expired
    or forged token yields uid=None and the request proceeds. Turning
    METIS_AUTH_ENABLED on is what makes that None start being refused, and only
    on the routes that require ownership.
    '''
    uid = None
    header = request.headers.get('authorization') or ''
    scheme, _, token = header.partition(' ')
    if scheme.lower() == 'bearer' and token.strip():
        uid = firebase.verify_token(token.strip())
    request.state.uid = uid
    return await call_next(request)


app.include_router(router, prefix='/api')


@app.get('/favicon.ico', include_in_schema=False)
def favicon_ico():
    return FileResponse(STATIC_DIR / 'favicon.ico', media_type='image/x-icon')


@app.get('/icon.svg', include_in_schema=False)
def favicon_svg():
    return FileResponse(STATIC_DIR / 'icon.svg', media_type='image/svg+xml')


@app.get('/health')
def health_check():
    '''Liveness plus the two facts a deployment is most likely to get wrong.

    `database` resolves the lazy client rather than reporting what was
    configured, so a deployment that meant to use Firestore and quietly landed
    on ephemeral SQLite says so here instead of at the next restart, with the
    data already gone.
    '''
    return {
        'status': 'healthy',
        'app': settings.APP_NAME,
        'version': settings.APP_VERSION,
        'database': backend_name(),
        'auth_enforced': settings.METIS_AUTH_ENABLED,
    }


@app.get('/')
def root():
    return {
        'name': 'METIS API',
        'version': settings.APP_VERSION,
        'description': 'Think. Act. Grow.',
        'docs': '/docs',
    }

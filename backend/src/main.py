from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from .core.config import settings
from .api.routes import router

STATIC_DIR = Path(__file__).parent / 'static'

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

app.include_router(router, prefix='/api')


@app.get('/favicon.ico', include_in_schema=False)
def favicon_ico():
    return FileResponse(STATIC_DIR / 'favicon.ico', media_type='image/x-icon')


@app.get('/icon.svg', include_in_schema=False)
def favicon_svg():
    return FileResponse(STATIC_DIR / 'icon.svg', media_type='image/svg+xml')


@app.get('/health')
def health_check():
    return {
        'status': 'healthy',
        'app': settings.APP_NAME,
        'version': settings.APP_VERSION,
    }


@app.get('/')
def root():
    return {
        'name': 'METIS API',
        'version': settings.APP_VERSION,
        'description': 'Think. Act. Grow.',
        'docs': '/docs',
    }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.routes import router

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
        'description': 'Your Business. Operated by AI.',
        'docs': '/docs',
    }

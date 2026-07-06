from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router

# Import Config/DB init
from app.core.db_config import init_db

# Load Environment and Init DB
load_dotenv()
init_db()

app = FastAPI(
    title='Georgia Invoice Extractor',
    description='An AI-powered invoice extraction tool that automates invoice processing from Invoice PDF and Images.',
    version='1.0.0',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include routers
# app.include_router(api_v1_router, prefix='/api/v1')
app.include_router(api_v1_router)


@app.get('/health', tags=['Health'])
async def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'message': 'Invoice processing is running'}

from fastapi import APIRouter

from app.api.v1.endpoints import start_process, cancel_process, stream_process

router = APIRouter()

# Include specific endpoint routers
router.include_router(start_process.router, tags=['Invoice Processing'])
router.include_router(stream_process.router, tags=['Streaming Processing'])
router.include_router(cancel_process.router, tags=['Cancel Processing'])

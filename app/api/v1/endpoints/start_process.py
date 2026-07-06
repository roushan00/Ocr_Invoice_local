import os
import asyncio

from fastapi import APIRouter, HTTPException

from app.state.shared import ProcessingContext, processing_queues
from app.services.processor import LOCAL_STORAGE_PATH, process_db_task
from app.db_operations.distributor_ops import get_distributor_name_by_id
# Import Internal Modules
from app.models.input_request import ProcessRequest

router = APIRouter()


@router.post('/start-process')
async def start_process(request: ProcessRequest):
    """
    Initiates the invoice processing task in the background.
    """
    unique_id = request.unique_id
    dist_id = request.distributor_id

    # dist_name = None
    # Validate Distributor
    if dist_id:
        dist_name = await asyncio.to_thread(get_distributor_name_by_id, dist_id)
        if not dist_name:
            raise HTTPException(status_code=404, detail='Distributor not found.')

    # Validate File Existence
    target_folder = os.path.join(LOCAL_STORAGE_PATH, unique_id)
    if not os.path.exists(target_folder):
        raise HTTPException(status_code=404, detail='Folder not found')

    # Initialize Queue
    if unique_id not in processing_queues:
        processing_queues[unique_id] = ProcessingContext()
    # Fire and forget the background task
    task = asyncio.create_task(process_db_task(unique_id, dist_name))

    processing_queues[unique_id].task = task

    return {
        'message': 'Processing started.',
        # "unique_id": unique_id,
        'status': 'processing_background',
    }

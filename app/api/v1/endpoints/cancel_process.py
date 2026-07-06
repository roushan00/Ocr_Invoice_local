import asyncio

from loguru import logger
from fastapi import APIRouter

# Import Shared State
from app.state.shared import processing_queues

# Import DB Operations
from app.models.input_request import CancelRequest  # Assuming this has unique_id

router = APIRouter()

@router.post('/cancel-process')
async def cancel_process(request: CancelRequest):
    """
    Cancels a running background invoice processing task.
    """
    unique_id = request.unique_id

    # 1. Check if the process exists in our memory queue
    if unique_id not in processing_queues:
        # Check DB to see if it's already done or just missing from memory
        # Optional: You could return 404, but usually 200 with a message is safer
        return {
            "message": "Process not found in active queue (already finished or never started).",
            "status": "not_found"
        }

    ctx = processing_queues[unique_id]

    # 2. Cancel the asyncio Task
    if ctx.task and not ctx.task.done():
        logger.warning(f"[{unique_id}] 🛑 Received cancellation request. Stopping task...")
        ctx.task.cancel()

        try:
            # Wait briefly to allow the task to handle the CancelledError and clean up
            await asyncio.wait_for(ctx.task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass # Expected
        except Exception as e:
            logger.error(f"[{unique_id}] Error while cancelling: {e}")

    # 3. Remove from queue immediately
    processing_queues.pop(unique_id, None)

    return {
        "message": "Processing cancelled successfully.",
        "status": "cancelled"
    }

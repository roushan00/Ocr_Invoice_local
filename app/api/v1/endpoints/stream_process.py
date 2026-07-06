import json

from fastapi import Request, APIRouter
from fastapi.responses import StreamingResponse

from app.core.redis import redis_client
from app.core.config import settings

router = APIRouter()

@router.get("/stream-process/{unique_id}")
async def stream_process(unique_id: str, request: Request):

    async def event_generator():
        key = f"progress:{unique_id}"
        channel = f"progress-events:{unique_id}"

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        try:
            # 🔁 Always send latest snapshot first (refresh-safe)
            payload = await redis_client.hget(key, "payload")
            if payload:
                yield f"data:{payload}\n\n"

            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break

                if message["type"] != "message":
                    continue

                # 🔁 Fetch latest snapshot
                payload = await redis_client.hget(key, "payload")
                if not payload:
                    continue

                data = json.loads(payload)
                yield f"data:{payload}\n\n"

                # 🛑 Stop condition
                if (
                    data.get("status") in (settings.STATUS_COMPLETED, settings.STATUS_ERROR)
                    and data.get("percentage") == 100
                ):
                    break

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# import json
# import asyncio

# from loguru import logger
# from fastapi import APIRouter, Request
# from fastapi.responses import StreamingResponse

# from app.core.config import settings
# from app.state.shared import processing_queues, ProcessingContext
# from app.services.processor import get_completed_process_data

# router = APIRouter()


# @router.get('/stream-process/{unique_id}')
# async def stream_process(unique_id: str, request: Request):

#     async def event_generator():

#         if unique_id in processing_queues:
#             logger.info(f'[{unique_id}] Client connected to LIVE stream.')

#             ctx = processing_queues[unique_id]

#             # Safety: legacy Queue → Context
#             if isinstance(ctx, asyncio.Queue):
#                 new_ctx = ProcessingContext()
#                 new_ctx.queue = ctx
#                 processing_queues[unique_id] = new_ctx
#                 ctx = new_ctx

#             q = ctx.queue

#             # ✅ Send last known event on refresh
#             if ctx.last_update:
#                 yield f'{json.dumps(ctx.last_update)}\n\n'

#             try:
#                 while True:
#                     if await request.is_disconnected():
#                         break

#                     try:
#                         data = await asyncio.wait_for(q.get(), timeout=1.0)
#                         yield f'{json.dumps(data)}\n\n'

#                         if data.get('status') in (
#                             settings.STATUS_COMPLETED,
#                             settings.STATUS_ERROR,
#                         ) and data.get("percentage") == 100:
#                             break

#                     except asyncio.TimeoutError:
#                         continue

#             except asyncio.CancelledError:
#                 logger.info(f'[{unique_id}] Stream cancelled.')

#         else:
#             completed_data = await get_completed_process_data(unique_id)

#             if completed_data:
#                 yield f'{json.dumps(completed_data)}\n\n'
#             else:
#                 yield f'{json.dumps({
#                     "status": settings.STATUS_ERROR,
#                     "message": "Process not found or ID is invalid."
#                 })}\n\n'

#     return StreamingResponse(event_generator(), media_type='text/event-stream')

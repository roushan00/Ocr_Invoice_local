import json
import time

from app.core.redis import redis_client


async def send_progress_update(unique_id: str, data: dict):
    key = f"progress:{unique_id}"
    channel = f"progress-events:{unique_id}"

    # 1️⃣ Store latest state ONLY
    await redis_client.hset(
        key,
        mapping={
            "payload": json.dumps(data),
            "updated_at": str(time.time()),
        }
    )

    await redis_client.expire(key, 3600)

    # 2️⃣ Notify listeners (no payload here)
    await redis_client.publish(channel, "update")

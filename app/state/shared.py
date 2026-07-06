import asyncio


class ProcessingContext:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.last_update: dict | None = None
        # Add a slot to store the specific background task
        self.task: asyncio.Task | None = None

# Key: unique_id, Value: ProcessingContext object
processing_queues: dict[str, ProcessingContext] = {}

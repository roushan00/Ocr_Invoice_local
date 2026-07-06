import asyncio

from loguru import logger
from pydantic import BaseModel
from tenacity import (
    retry,
    before_sleep_log,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

from app.services.llm import extract_invoice_from_image

GPU_SEMAPHORE = asyncio.Semaphore(1)

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=10, max=60),
    retry=retry_if_exception_type((asyncio.TimeoutError, Exception)),
    before_sleep=before_sleep_log(logger, logger.level('WARNING').no),
)
async def extract_with_retry(
    img_path: str,
    selected_model: type[BaseModel],
    selected_prompt: str,
    unique_id: str,
    page_no: int,
    attempt_timeout: float = 180.0,
):
    try:
        logger.debug(
            f'[{unique_id}] 🔄 Attempting extraction for Page {page_no} (timeout: {attempt_timeout}s)'
        )
        async with GPU_SEMAPHORE:
            result = await asyncio.wait_for(
                extract_invoice_from_image(img_path, selected_model, selected_prompt),
                timeout=attempt_timeout
            )
            logger.debug(f'[{unique_id}] ✅ Page {page_no} extraction completed successfully')
            return result
    except asyncio.TimeoutError:
        logger.warning(f'[{unique_id}] ⏰ Page {page_no} extraction timed out')
        raise
    except Exception as e:
        logger.warning(f'[{unique_id}] ❌ Page {page_no} extraction failed: {e}')
        raise

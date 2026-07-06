import json
import base64
import asyncio

from typing import Any

import numpy as np

from dotenv import load_dotenv
from loguru import logger
from openai import AsyncOpenAI  # CHANGED: Use Async Client
from pydantic import BaseModel
from json_repair import repair_json

from app.core.config import settings

from .field_confidence import compute_field_confidences

load_dotenv()

MODEL_NAME = settings.MODEL_NAME

# Initialize Async Client
client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

def encode_image(image_path_or_bytes: str | bytes) -> str:
    """
    Optimized: Can now accept raw bytes directly from memory, 
    skipping the disk read entirely.
    """
    if isinstance(image_path_or_bytes, bytes):
        return base64.b64encode(image_path_or_bytes).decode('utf-8')

    # Fallback to disk read if a file path is passed
    with open(image_path_or_bytes, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


async def extract_invoice_from_image(
    image_data: str | bytes, # Changed to accept bytes or path
    model_class: type[BaseModel],
    prompt_text: str,
    retries: int = 1,
) -> tuple[BaseModel | None, dict[str, Any] | None]:
    """
    Returns a tuple: (PydanticModel, ConfidenceDict)
    """
    attempt = 0

    # 1. Encode Image (In-memory if bytes are passed, skipping disk read)
    image_base64 = await asyncio.to_thread(encode_image, image_data)

    while attempt <= retries:
        try:
            # 2. Call OpenAI-compatible endpoint (ASYNC)
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                temperature=0.0,
                max_tokens=4096,
                seed=42,
                logprobs=True,
                top_logprobs=1,
                response_format={"type": "json_object"},
                extra_body={"keep_alive": "5m"} # Keeps model in VRAM
            )

            generated_text = response.choices[0].message.content.strip()
            logger.debug(f"Raw generated text snippet: {generated_text[:100]}...")

            # Repair JSON for Pydantic
            repaired_json = repair_json(generated_text)

            # 3. Parse JSON & Validate with Pydantic
            invoice = model_class.model_validate_json(repaired_json)
            logger.success("Invoice successfully validated via Pydantic.")

            # 4. Calculate Confidence Scores
            confidence_dict = {}
            if response.choices[0].logprobs:
                logprob_contents = response.choices[0].logprobs.content
                if logprob_contents:
                    tokens = [item.token for item in logprob_contents if item.logprob is not None]
                    probs = [np.exp(item.logprob) for item in logprob_contents if item.logprob is not None]

                    try:
                        extracted_dict = json.loads(repaired_json)
                        # 🚀 CRITICAL FIX: Pass `generated_text`, NOT `repaired_json` to keep token indices aligned!
                        confidence_dict = compute_field_confidences(extracted_dict, generated_text, tokens, probs)
                    except json.JSONDecodeError:
                        logger.warning("JSON parsed by Pydantic but failed json.loads? Rare edge case.")
                        confidence_dict = {}

            return invoice, confidence_dict

        except Exception as e:
            logger.warning(f'Attempt {attempt + 1} failed: {e}')
            attempt += 1
            if attempt <= retries:
                logger.info('Retrying in 1 second...')
                await asyncio.sleep(1)
            else:
                logger.error('❌ Failed to extract data after retries.')
                return None, None


# def extract_invoice_from_image(image_path, retries=1) -> Optional[Invoice]:
#     attempt = 0
#     while attempt <= retries:
#         try:
#             response = chat(
#                 model=MODEL_NAME,
#                 messages=[{
#                     'role': 'user',
#                     'content': prompt_for_georgia,
#                     'images': [image_path],
#                 }],
#                 format=Invoice.model_json_schema(),
#                 # Options are critical for GB10/ARM setup
#                 options={
#                     'temperature': 0,      # Deterministic output
#                 },
#             )

#             # Validate JSON
#             invoice = Invoice.model_validate_json(response.message.content)
#             return invoice

#         except Exception as e:
#             logger.warning(f"Attempt {attempt+1} failed for {image_path}: {e}")
#             attempt += 1
#             if attempt <= retries:
#                 logger.info("Retrying...")
#                 # If we failed, try clearing memory before retry
#                 unload_model_memory()
#             else:
#                 logger.error(f"❌ Failed to extract {image_path} after retries.")
#                 return None


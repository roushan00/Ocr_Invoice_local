import gc
import os
import time

import ollama

from dotenv import load_dotenv
from loguru import logger

load_dotenv()
# MODEL_NAME = "my_finetuned_vision_11b_q4km:latest"
MODEL_NAME = os.getenv('MODEL_NAME')


def unload_model_memory():
    """
    Forces Ollama to release VRAM and Python to run Garbage Collection.
    Uses multiple methods to ensure the model is properly unloaded.
    """
    logger.info('♻️  Maintenance: Unloading model and clearing VRAM...')

    unload_success = False

    # Method 1: Try using generate with keep_alive=0
    try:
        ollama.generate(model=MODEL_NAME, prompt='', keep_alive=0)
        logger.debug('✓ Model unload signal sent via generate()')
        unload_success = True
    except Exception as e:
        logger.warning(f'Could not force unload model via generate: {e}')

    # Method 2: Fallback to chat method if generate failed
    if not unload_success:
        try:
            ollama.chat(model=MODEL_NAME, messages=[], keep_alive=0)
            logger.debug('✓ Model unload signal sent via chat()')
            unload_success = True
        except Exception as e:
            logger.warning(f'Could not force unload model via chat: {e}')

    # Method 3: Last resort - try to list models to wake up the service
    if not unload_success:
        try:
            ollama.list()
            logger.debug('✓ Ollama service pinged')
        except Exception as e:
            logger.error(f'Could not communicate with Ollama service: {e}')

    # Aggressive Python garbage collection (run multiple times for better cleanup)
    logger.debug('Running garbage collection...')
    for i in range(3):
        collected = gc.collect()
        if i == 0:
            logger.debug(f'✓ GC pass {i + 1}: collected {collected} objects')

    # Give GPU more time to release VRAM
    time.sleep(3)  # Increased from 2 to 3 seconds

    logger.debug('✓ Memory cleanup cycle complete')


def get_model_info():
    """
    Optional: Get information about the current model status.
    Useful for debugging memory issues.
    """
    try:
        models = ollama.list()
        logger.debug(f'Available models: {models}')
        return models
    except Exception as e:
        logger.error(f'Could not retrieve model info: {e}')
        return None

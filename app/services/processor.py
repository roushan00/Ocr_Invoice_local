import os
import glob
import time
import shutil
import asyncio
import tempfile

from datetime import datetime

from loguru import logger
from PyPDF2 import PdfReader
from sqlalchemy import text

from app.core.config import settings

# Import Shared State
from app.state.shared import ProcessingContext, processing_queues
from app.core.db_config import SessionLocal  # Import Session for reading status
from app.services.retry import extract_with_retry
from app.services.progress import send_progress_update
from app.services.convert_pdf import pdf_to_images
# from app.prompts.general_prompt import INVOICE_PROMPT
from app.prompts.georgia_prompt import INVOICE_PROMPT
#from app.prompts.general_prompt2 import INVOICE_PROMPT2
#from app.prompts.georgia_qwen_prompt import INVOICE_PROMPT3


from app.services.memoery_clean import unload_model_memory
from app.db_operations.invoice_ops import update_invoice_stats, create_invoice_record
from app.services.prompt_strategy import get_prompt_for_distributor
# Import existing operations
from app.db_operations.update_page import update_pdf_page
from app.models.universal_template import UniversalInvoice
#from app.models.georgia_inv import UniversalInvoice
from app.db_operations.distributor_ops import GENERAL_TABLE_SCHEMA, check_or_create_distributor
from app.db_operations.invoice_items_ops import create_invoice_table_data
from app.db_operations.update_invoice_status import update_invoice_status

# Config
LOCAL_STORAGE_PATH = settings.LOCAL_STORAGE_BASE_PATH


def get_invoice_status_from_db(unique_id: str):
    """Helper to synchronously check DB status."""
    db = SessionLocal()
    try:
        query = text('SELECT "Status" FROM "public"."InvoiceFiles" WHERE "Id" = :id')
        result = db.execute(query, {'id': unique_id}).fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Error checking status for {unique_id}: {e}")
        return None
    finally:
        db.close()

async def get_completed_process_data(unique_id: str):

    db_status = await asyncio.to_thread(get_invoice_status_from_db, unique_id)

    # If DB says Processing, but queue is gone, it might be a crash,
    # but strictly speaking, it's not "Completed".
    if db_status == settings.STATUS_PROCESSING:
        return None

    if db_status == settings.STATUS_ERROR:
        return {
            'status': settings.STATUS_ERROR,
            'message': 'Process failed (checked from DB).'
        }

    # 2. If DB says COMPLETED (or we continue checks), verify files
    target_folder = os.path.join(LOCAL_STORAGE_PATH, unique_id)

    if not os.path.exists(target_folder):
        return None

    search_pattern = os.path.join(target_folder, '*.pdf')
    pdf_files = glob.glob(search_pattern) or glob.glob(os.path.join(target_folder, '*.PDF'))

    if not pdf_files:
        return None

    pdf_path = pdf_files[0]
    file_name = os.path.basename(pdf_path)

    try:
        file_size_int = os.path.getsize(pdf_path)
        # Quick read for page count
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
    except Exception:
        return None

    # 3. Construct the "Done" payload
    return {
        'elapsed': 0,
        'fileName': file_name,
        'pages': total_pages,
        'percentage': 100,
        'size': file_size_int,
        'started': datetime.now().isoformat(),
        'pageProcess': {'pageNo': total_pages, 'status': settings.STATUS_COMPLETED},
        'status': settings.STATUS_COMPLETED,
    }



async def process_db_task(unique_id: str, distributor_name: str | None):
    """
    Background task to process the PDF.
    """
    start_time = time.perf_counter()
    process_start_timestamp = datetime.now().isoformat()

    selected_prompt = get_prompt_for_distributor(distributor_name)
    # Initialize Queue if missing (safety check)
    if unique_id not in processing_queues:
        processing_queues[unique_id] = ProcessingContext()

    temp_dir = tempfile.mkdtemp()

    final_status = settings.STATUS_ERROR

    try:
        #DB status PRocessing Immediately
        await asyncio.to_thread(update_invoice_status, unique_id, settings.STATUS_PROCESSING)

        target_folder = os.path.join(LOCAL_STORAGE_PATH, unique_id)

        # Find PDF
        search_pattern = os.path.join(target_folder, '*.pdf')
        pdf_files = glob.glob(search_pattern)
        if not pdf_files:
            pdf_files = glob.glob(os.path.join(target_folder, '*.PDF'))

        if not pdf_files:
            error_msg = 'No PDF found to process'
            logger.error(f'[{unique_id}] {error_msg}.')
            await asyncio.to_thread(update_invoice_status, unique_id, settings.STATUS_ERROR, error_msg)
            await send_progress_update(
                unique_id, {'status': settings.STATUS_ERROR, 'message': error_msg}
            )
            return

        pdf_path = pdf_files[0]
        file_name = os.path.basename(pdf_path)
        try:
            file_size_int = os.path.getsize(pdf_path)
        except Exception:
            file_size_int = 0

        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            await asyncio.to_thread(update_pdf_page, unique_id, total_pages)
        except Exception as e:
            error_msg = f'Could not read PDF: {e}'
            logger.error(f'[{unique_id}] {error_msg}')
            await asyncio.to_thread(update_invoice_status, unique_id, settings.STATUS_ERROR, error_msg)
            await send_progress_update(
                unique_id,
                {'status': settings.STATUS_ERROR, 'message': error_msg},
            )
            return

        # Convert PDF to Images
        image_paths = await asyncio.to_thread(pdf_to_images, pdf_path, temp_dir)

        last_invoice_number = None
        invoice_page_sequence = 0
        failed_pages = []
        # successful_pages = 0

        for i, img_path in enumerate(image_paths):

            if asyncio.current_task().cancelled():
                raise asyncio.CancelledError()

            physical_page_no = i + 1
            page_start_time = time.perf_counter()
            elapsed_now = time.perf_counter() - start_time
            current_percentage = int(((physical_page_no - 1) / total_pages) * 100)

            await send_progress_update(
                unique_id,
                {
                    'elapsed': round(elapsed_now, 4),
                    'fileName': file_name,
                    'pages': total_pages,
                    'percentage': current_percentage,
                    'size': file_size_int,
                    'started': process_start_timestamp,
                    'pageProcess': {
                        'pageNo': physical_page_no,
                        'status': settings.STATUS_PROCESSING,
                    },
                    'status': settings.STATUS_PROCESSING,
                },
            )
            await asyncio.sleep(0.2)
            extraction_successful = False
            extracted_data = None
            confidence_data = None
            page_error_msg = None

            try:
                extracted_data, confidence_data = await extract_with_retry(
                    img_path,
                    UniversalInvoice,
                    selected_prompt,
                    unique_id,
                    physical_page_no,
                    attempt_timeout=300.0,
                )

                if extracted_data is not None:
                    extraction_successful = True
                    # successful_pages += 1
                else:
                    # Case: Retries finished but returned None (soft failure in LLM)
                    page_error_msg = "Extraction returned empty (failed)"
                    failed_pages.append((physical_page_no, page_error_msg))

                logger.success(extracted_data)

                page_duration = time.perf_counter() - page_start_time
                logger.info(
                    f'[{unique_id}] ✅ Page {physical_page_no} extracted successfully in {page_duration:.2f}s'
                )

            except Exception as e:
                # Case: Hard exception (Timeout, Crash)
                page_error_msg = str(e)
                failed_pages.append((physical_page_no, page_error_msg))
                await asyncio.to_thread(unload_model_memory)

            if page_error_msg:
                # If we have an error msg, it means this page failed.
                # Send the ERROR status for this specific page immediately.
                logger.error(f"[{unique_id}] Page {physical_page_no} Failed: {page_error_msg}")

                await asyncio.to_thread(
                    update_invoice_status, unique_id, settings.STATUS_ERROR, f"Page {physical_page_no}: {page_error_msg}"
                )

                await send_progress_update(
                    unique_id,
                    {
                        'elapsed': round(time.perf_counter() - start_time, 4),
                        'fileName': file_name,
                        'pages': total_pages,
                        'percentage': current_percentage,
                        'size': file_size_int,
                        'started': process_start_timestamp,
                        'pageProcess': {
                            'pageNo': physical_page_no,
                            'status': settings.STATUS_ERROR, # <--- 3 sent here
                        },
                        'status': settings.STATUS_ERROR, # Overall doc is still processing
                    },
                )
                # await asyncio.sleep(0.2)
                try:
                    await asyncio.to_thread(unload_model_memory)
                except Exception:
                    logger.warning(f"[{unique_id}] Failed to run unload_model_memory synchronously before exit.")

                # Stop processing immediately
                return
                # continue # Skip the database insertion logic below

            if extraction_successful and extracted_data:
                llm_distributor_name = extracted_data.distributor_name
                if not llm_distributor_name or not llm_distributor_name.strip():
                    raise Exception("Distributor name missing from LLM extraction")

                llm_distributor_name = llm_distributor_name.strip()

                await asyncio.to_thread(
                    check_or_create_distributor,
                    llm_distributor_name,
                    GENERAL_TABLE_SCHEMA
                )

                # Overwrite any previous value (frontend is ignored)
                distributor_name = llm_distributor_name

                logger.info(
                    f"[{unique_id}] 🏷️ Distributor resolved from LLM: {llm_distributor_name}"
                )

                current_invoice_no = extracted_data.invoice_no
                is_new_invoice = current_invoice_no != last_invoice_number

                if is_new_invoice:
                    invoice_page_sequence = 1
                    last_invoice_number = current_invoice_no
                else:
                    invoice_page_sequence += 1

                invoice_id = await asyncio.to_thread(
                    create_invoice_record, unique_id, extracted_data, is_new_invoice
                )

                if invoice_id:
                    line_items = getattr(extracted_data, 'items', [])

                    # Extract item confidences from the dictionary
                    items_confidence_list = []
                    if confidence_data and 'items' in confidence_data and isinstance(confidence_data['items'], list):
                        items_confidence_list = confidence_data['items']

                    if line_items:
                        items_to_save = []
                        for idx, item in enumerate(line_items):
                            item_dict = item.model_dump()

                            # Retrieve confidence for this specific item index
                            # Note: The structure of confidence_data['items'] mirrors the Pydantic items list
                            item_conf_data = {}
                            if idx < len(items_confidence_list):
                                item_conf_data = items_confidence_list[idx]

                            # Calculate an average confidence for the row to store as a single value (optional)
                            row_conf_score = 0.0
                            if isinstance(item_conf_data, dict):
                                valid_scores = [v for v in item_conf_data.values() if isinstance(v, (int, float))]
                                if valid_scores:
                                    row_conf_score = sum(valid_scores) / len(valid_scores)

                            # Merge logic (Replacing wrap_line_item_with_confidence)
                            # We add a 'confidence' key with the raw breakdown and 'confidence_score' with average
                            merged_item = {
                                **item_dict,
                                "confidence_details": item_conf_data,
                                "confidence": row_conf_score # Used for single-column score
                            }

                            items_to_save.append(merged_item)

                        await asyncio.to_thread(
                            create_invoice_table_data,
                            invoice_id,
                            items_to_save,
                            invoice_page_sequence,
                            distributor_name,
                        )

                        if invoice_page_sequence > 1:
                            await asyncio.to_thread(
                                update_invoice_stats, invoice_id, extracted_data
                            )

            # Update Progress
            elapsed_now = time.perf_counter() - start_time
            current_percentage = int((physical_page_no / total_pages) * 100)

            # await asyncio.sleep(0.5)
            is_last_page = physical_page_no == total_pages
            final_page_status = (
                settings.STATUS_COMPLETED if is_last_page else settings.STATUS_PROCESSING
            )
            completion_payload = {
                'elapsed': round(elapsed_now, 4),
                'fileName': file_name,
                'pages': total_pages,
                'percentage': current_percentage,
                'size': file_size_int,
                'started': process_start_timestamp,
                'pageProcess': {
                    'pageNo': physical_page_no,
                    'status': settings.STATUS_COMPLETED,
                },
                'status': final_page_status,  # ✅ FIX
            }


            # 1. SEND STATUS FIRST TIME
            await send_progress_update(unique_id, completion_payload)

            # 2. WAIT 2 SECONDS (Allow client to receive it)
            # await asyncio.sleep(1.0)

            # 3. UPDATE TIMESTAMP & RESEND (Redundancy check)
            completion_payload['elapsed'] = round(time.perf_counter() - start_time, 4)
            await send_progress_update(unique_id, completion_payload)

            # 4. BIG DELAY BEFORE NEXT PAGE (3 Seconds)
            # This ensures the 'Completed' status stays valid for a long time
            # before the next loop iteration overwrites it with 'Processing'.
            # await asyncio.sleep(1.0)

            # ---------------------------------------------------------

            # Memory Cleanup
            if physical_page_no % 1 == 0 or physical_page_no == total_pages:
                await asyncio.to_thread(unload_model_memory)

        final_status = settings.STATUS_ERROR if failed_pages else settings.STATUS_COMPLETED


        # Build error message if there were failed pages
        final_error_message = None
        if failed_pages:
            failed_page_details = [f"Page {pg}: {err}" for pg, err in failed_pages]
            final_error_message = f"Failed pages: {'; '.join(failed_page_details)}"
            logger.warning(f"[{unique_id}] Completed with errors: {final_error_message}")

        # Update DB with final status and error message (if any)
        await asyncio.to_thread(update_invoice_status, unique_id, final_status, final_error_message)

        # await asyncio.to_thread(update_invoice_status, unique_id, settings.STATUS_COMPLETED)
        # await asyncio.sleep(0.5)

        await send_progress_update(
            unique_id,
            {
                'elapsed': round(time.perf_counter() - start_time, 4),
                'fileName': file_name,
                'pages': total_pages,
                'percentage': 100,
                'size': file_size_int,
                'started': process_start_timestamp,
                'pageProcess': {
                    'pageNo': total_pages,
                    'status': final_status, # Reflects Error or Completed
                },
                'status': final_status,
            },
        )
        # await asyncio.sleep(0.9)
    except asyncio.CancelledError:
        logger.warning(f"[{unique_id}] 🛑 Task was CANCELLED by user.")

        await send_progress_update(
            unique_id,
            {
                "status": "Cancelled",
                "message": "Process cancelled by user."
            }
        )

        # 3. Important: We do not re-raise if we want the 'finally' block to run cleanly
        # without crashing the asyncio loop, but usually re-raising CancelledError is
        # standard practice if this task was awaited. Since it's fire-and-forget, returning is fine.
        return
    except Exception as e:
        error_msg = f'Background Task Error: {str(e)}'
        logger.exception(f'[{unique_id}] {error_msg}')
        # Catastrophic failure catch-all
        await asyncio.to_thread(update_invoice_status, unique_id, settings.STATUS_ERROR, error_msg)
        await send_progress_update(unique_id, {"status": settings.STATUS_ERROR, "message": error_msg})
    finally:
        logger.info(f"[{unique_id}] 🧹 Running cleanup (Temp files & GPU Memory).")

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        await asyncio.to_thread(unload_model_memory)

        # CRITICAL: Wait a moment to ensure consumers (stream_process) get the final message
        # await asyncio.sleep(0.9)

        # CRITICAL: This is the ONLY place we delete the queue.
        # This prevents the queue from being deleted just because a frontend refreshed.
        if unique_id in processing_queues:
            logger.info(f"[{unique_id}] Cleaning up processing queue.")
            processing_queues.pop(unique_id, None)


    end_time = time.perf_counter()
    total_seconds = end_time - start_time

    logger.success(
        f'[{unique_id}] ✅ TOTAL EXECUTION TIME: '
        f'{total_seconds:.2f} seconds '
    )

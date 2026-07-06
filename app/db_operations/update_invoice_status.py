import time

from loguru import logger
from sqlalchemy import text

from app.core.db_config import SessionLocal


def update_invoice_status(file_id: str, status: int, error_message: str = None, max_retries=5):
    """
    Updates status and optional error message. Retries if ID is not found immediately (Race Condition Fix).
    """
    db = SessionLocal()
    try:
        # Build query based on whether we have an error message
        if error_message:
            query = text('UPDATE "public"."InvoiceFiles" SET "Status" = :status, "ErrorMessage" = :error_message WHERE "Id" = :id')
            params = {'status': status, 'error_message': error_message, 'id': file_id}
        else:
            # Clear error message when status is not error (e.g., processing or completed)
            query = text('UPDATE "public"."InvoiceFiles" SET "Status" = :status, "ErrorMessage" = NULL WHERE "Id" = :id')
            params = {'status': status, 'id': file_id}

        for attempt in range(1, max_retries + 1):
            result = db.execute(query, params)
            db.commit()

            if result.rowcount > 0:
                logger.info(f'✅ [{file_id}] Status updated to {status}' + (f' with error: {error_message}' if error_message else ''))
                return  # Success! Exit function.

            # If we are here, ID was not found. Wait and retry.
            logger.warning(
                f'⏳ [{file_id}] ID not found yet (Attempt {attempt}/{max_retries}). Waiting...'
            )
            time.sleep(1)  # Wait 1 second before retrying

        # If loop finishes without success:
        logger.error(
            f'❌ [{file_id}] Failed to update Status after {max_retries} attempts. ID missing.'
        )

    except Exception as e:
        logger.error(f'❌ [{file_id}] Status Update Failed: {e}')
        db.rollback()
    finally:
        db.close()

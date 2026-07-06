import time

from loguru import logger
from sqlalchemy import text

from app.core.db_config import SessionLocal


def update_pdf_page(file_id: str, total_pages: int, max_retries=5):
    """
    Updates page count. Retries if ID is not found immediately (Race Condition Fix).
    """
    db = SessionLocal()
    try:
        query = text('UPDATE "public"."InvoiceFiles" SET "Pages" = :pages WHERE "Id" = :id')

        for attempt in range(1, max_retries + 1):
            result = db.execute(query, {'pages': total_pages, 'id': file_id})
            db.commit()

            if result.rowcount > 0:
                logger.info(f'✅ [{file_id}] DB Updated. Total Pages: {total_pages}')
                return  # Success! Exit function.

            # If we are here, ID was not found. Wait and retry.
            logger.warning(
                f'⏳ [{file_id}] ID not found yet (Attempt {attempt}/{max_retries}). Waiting...'
            )
            time.sleep(1)  # Wait 1 second before retrying

        # If loop finishes without success:
        logger.error(
            f'❌ [{file_id}] Failed to update Pages after {max_retries} attempts. ID missing.'
        )

    except Exception as e:
        logger.error(f'❌ [{file_id}] DB Update Failed: {e}')
        db.rollback()
    finally:
        db.close()


# --- 1. THE DATABASE UPDATE FUNCTION ---
# def update_pdf_page(file_id: str, total_pages: int):
#     """
#     Synchronous function to update the database.
#     """
#     db = SessionLocal()
#     try:
#         # Construct query for case-sensitive PostgreSQL columns
#         query = text('UPDATE "public"."InvoiceFiles" SET "Pages" = :pages WHERE "Id" = :id')

#         result = db.execute(query, {'pages': total_pages, 'id': file_id})
#         db.commit()

#         if result.rowcount > 0:
#             logger.info(f'✅ [{file_id}] DB Updated. Total Pages: {total_pages}')
#         else:
#             logger.warning(f'⚠️ [{file_id}] ID not found in InvoicelFiles table.')

#     except Exception as e:
#         logger.error(f'❌ [{file_id}] DB Update Failed: {e}')
#         db.rollback()
#     finally:
#         db.close()

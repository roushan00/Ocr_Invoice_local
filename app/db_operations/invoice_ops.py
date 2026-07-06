import json
import uuid

from typing import Any

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import text

from app.core.db_config import SessionLocal
from app.db_operations.distributor_ops import get_distributor_id_by_name

from .utils import parse_date_safe
from .stats_calculation_for_general import (
    calculate_invoice_stats,
    calculate_invoice_stats_with_confidence,
)


def create_invoice_record(unique_id: str, invoice_data: BaseModel, is_first_page: bool = False):

    db = SessionLocal()
    try:
        inv_num = getattr(invoice_data, 'invoice_no', None)

        # --- Step 1: Check if Invoice Already Exists ---
        check_query = text("""
            SELECT "Id" FROM "public"."Invoice"
            WHERE "InvoiceNumber" = :inv_num
            AND "InvoiceFileId" = :file_id
        """)

        existing_record = db.execute(
            check_query, {'inv_num': inv_num, 'file_id': unique_id}
        ).fetchone()

        if existing_record:
            invoice_id = existing_record.Id

            if is_first_page:
                logger.warning(
                    f'🔄 Invoice {inv_num} already exists but this is page 1 of new run. '
                    f'RESETTING stats AND distributor.'
                )

                # -----------------------------
                # 1. RECALCULATE STATS (FIX)
                # -----------------------------
                has_confidence = (
                    hasattr(invoice_data, '__class__')
                    and 'Confidence' in invoice_data.__class__.__name__
                )

                if has_confidence:
                    stats_array = calculate_invoice_stats_with_confidence(invoice_data)
                else:
                    stats_array = calculate_invoice_stats(invoice_data)

                stats_json = json.dumps(stats_array)

                # -----------------------------
                # 2. RESOLVE DISTRIBUTOR FROM LLM
                # -----------------------------
                llm_distributor_name = getattr(invoice_data, 'distributor_name', None)

                if not llm_distributor_name or not llm_distributor_name.strip():
                    raise Exception("Distributor name missing while resetting invoice")

                resolved_distributor_id = get_distributor_id_by_name(
                    llm_distributor_name.strip()
                )

                if not resolved_distributor_id:
                    raise Exception(
                        f"Distributor '{llm_distributor_name}' not found while resetting invoice"
                    )

                # -----------------------------
                # 3. RESET STATS + UPDATE DISTRIBUTOR
                # -----------------------------
                reset_query = text("""
                    UPDATE "public"."Invoice"
                    SET 
                        "Stats" = :stats,
                        "DistributorId" = :dist_id
                    WHERE "Id" = :invoice_id
                """)

                db.execute(
                    reset_query,
                    {
                        'stats': stats_json,
                        'dist_id': resolved_distributor_id,
                        'invoice_id': invoice_id,
                    }
                )
                db.commit()

                logger.success(
                    f'✅ RESET Invoice {inv_num} | DistributorId → {resolved_distributor_id}'
                )

            return invoice_id
        # --- Step 2: Fetch Parent Info ---
        fetch_query = text("""
            SELECT "DistributorId", "CreatedBy", "CreatedDate"
            FROM "public"."InvoiceFiles"
            WHERE "Id" = :id
        """)

        parent_record = db.execute(fetch_query, {'id': unique_id}).fetchone()

        if not parent_record:
            logger.error(f'❌ Parent InvoiceFile not found for ID: {unique_id}')
            return False

        # --- Step 3: Prepare Data ---
        new_invoice_id = uuid.uuid4()

        raw_date = getattr(invoice_data, 'invoice_date', None)
        parsed_bill_date = parse_date_safe(raw_date)
        route_val = getattr(invoice_data, 'route_no', None)

        # --- Calculate initial stats (returns array format) ---
        logger.info(f'📊 Calculating initial stats for NEW Invoice {inv_num}...')
        has_confidence = (
            hasattr(invoice_data, '__class__') and 'Confidence' in invoice_data.__class__.__name__
        )

        if has_confidence:
            stats_array = calculate_invoice_stats_with_confidence(invoice_data)
        else:
            stats_array = calculate_invoice_stats(invoice_data)

        # Store stats as JSON array
        stats_json = json.dumps(stats_array)

        llm_distributor_name = getattr(invoice_data, 'distributor_name', None)

        if not llm_distributor_name or not llm_distributor_name.strip():
            raise Exception("Distributor name missing while creating invoice")

        resolved_distributor_id = get_distributor_id_by_name(
            llm_distributor_name.strip()
        )

        if not resolved_distributor_id:
            raise Exception(
                f"Distributor '{llm_distributor_name}' not found after creation"
            )
        # --- Step 4: Insert New Invoice (Modified fields are NULL) ---
        insert_query = text("""
            INSERT INTO "public"."Invoice" (
                "Id",
                "DistributorId",
                "InvoiceNumber",
                "Status",
                "CreatedDate",
                "CreatedBy",
                "ModifiedDate",
                "ModifiedBy",
                "BillingDate",
                "DueDate",
                "Stats",
                "InvoiceFileId",
                "Route"
            ) VALUES (
                :id,
                :dist_id,
                :inv_num,
                :status,
                :created_date,
                :created_by,
                :mod_date,
                :mod_by,
                :bill_date,
                :due_date,
                :stats,
                :file_id,
                :route
            )
        """)

        db.execute(
            insert_query,
            {
                'id': new_invoice_id,
                'dist_id': resolved_distributor_id,
                'inv_num': inv_num,
                'status': 1,
                'created_date': parent_record.CreatedDate,
                'created_by': parent_record.CreatedBy,
                'mod_date': None,  # Stays NULL
                'mod_by': None,  # Stays NULL
                'bill_date': parsed_bill_date,
                'due_date': parsed_bill_date,
                'stats': stats_json,
                'file_id': unique_id,
                'route': route_val,
            },
        )

        db.commit()

        # FIX: use short title keys matching _format_stats_array output
        discount_item = next(
            (item for item in stats_array if item['Title'] == 'Discount'), None
        )
        payable_item = next(
            (item for item in stats_array if item['Title'] == 'Payable'), None
        )
        items_item = next((item for item in stats_array if item['Title'] == 'Items'), None)

        discount_value = discount_item['Value'] if discount_item else '0.00'
        payable_value = payable_item['Value'] if payable_item else '0.00'
        items_value = items_item['Value'] if items_item else '0'

        logger.success(
            f'✅ Created NEW Invoice {inv_num} with ID: {new_invoice_id}\n'
            f'   Initial Stats - Discount: ${discount_value}, '
            f'Payable: ${payable_value}, '
            f'Items: {items_value}'
        )
        return new_invoice_id

    except Exception as e:
        logger.error(f'❌ Failed to create invoice record: {e}')
        db.rollback()
        return None
    finally:
        db.close()


def update_invoice_stats(invoice_id: str, invoice_data: BaseModel) -> bool:
    db = SessionLocal()
    try:
        logger.info(f'🔄 Updating stats for Invoice ID: {invoice_id}...')

        has_confidence = hasattr(invoice_data, '__class__') and 'Confidence' in invoice_data.__class__.__name__
        if has_confidence:
            page_stats_array = calculate_invoice_stats_with_confidence(invoice_data)
        else:
            page_stats_array = calculate_invoice_stats(invoice_data)

        page_stats = _array_to_dict(page_stats_array)

        # Fetch existing stats from previous pages
        fetch_query = text('SELECT "Stats" FROM "public"."Invoice" WHERE "Id" = :invoice_id')
        result = db.execute(fetch_query, {'invoice_id': invoice_id}).fetchone()

        if not result:
            logger.warning(f'⚠️ Invoice ID {invoice_id} not found')
            return False

        existing_stats = {}
        try:
            existing_array = json.loads(result.Stats) if isinstance(result.Stats, str) else (result.Stats or [])
            existing_stats = _array_to_dict(existing_array)
        except Exception:
            pass

        # ACCUMULATE LOGIC: We mathematically add previous pages to the current page.
        # BUT if the current page has a high "Total Payable", it means the AI found the real summary!
        updated_stats = {}
        for key in page_stats.keys():
            prev_val = float(existing_stats.get(key, 0) or 0)
            curr_val = float(page_stats.get(key, 0) or 0)

            # If it's Total Payable and the current page gives us the document summary, overwrite.
            # Otherwise, just accumulate quantities across pages.
            if key in ['Total Payable', 'Sub Total'] and curr_val > prev_val:
                updated_stats[key] = f"{curr_val:.2f}"
            elif key in ['Liters', 'Discount', 'Tax', 'Deposit']:
                updated_stats[key] = f"{(prev_val + curr_val):.2f}"
            else: # Items, Out of Stock, Cases, Units (Integers)
                updated_stats[key] = str(int(prev_val + curr_val))

        stats_json = json.dumps(_dict_to_array(updated_stats))

        update_query = text('UPDATE "public"."Invoice" SET "Stats" = :stats WHERE "Id" = :invoice_id')
        db.execute(update_query, {'stats': stats_json, 'invoice_id': invoice_id})
        db.commit()

        logger.success(f'✅ Updated multi-page accumulated stats for Invoice ID: {invoice_id}')
        return True

    except Exception as e:
        logger.error(f'❌ Failed to update invoice stats: {e}')
        db.rollback()
        return False
    finally:
        db.close()


def _array_to_dict(stats_array: list[dict[str, Any]]) -> dict[str, str]:
    """Convert array of objects format to dictionary"""
    result = {}
    for item in stats_array:
        title = item.get('Title') or item.get('title', '')
        value = item.get('Value') or item.get('value', '')
        result[title] = value
    return result


def _dict_to_array(stats_dict: dict[str, str]) -> list[dict[str, Any]]:
    """Convert dictionary to exact 10 fields format"""
    return [
        {'Index': 1, 'Title': 'Items', 'Value': stats_dict.get('Items', '0')},
        {'Index': 2, 'Title': 'Out Of Stock Items', 'Value': stats_dict.get('Out Of Stock Items', '0')},
        {'Index': 3, 'Title': 'Cases', 'Value': stats_dict.get('Cases', '0')},
        {'Index': 4, 'Title': 'Units', 'Value': stats_dict.get('Units', '0')},
        {'Index': 5, 'Title': 'Liters', 'Value': stats_dict.get('Liters', '0.00')},
        {'Index': 6, 'Title': 'Sub Total', 'Value': stats_dict.get('Sub Total', '0.00')},
        {'Index': 7, 'Title': 'Discount', 'Value': stats_dict.get('Discount', '0.00')},
        {'Index': 8, 'Title': 'Tax', 'Value': stats_dict.get('Tax', '0.00')},
        {'Index': 9, 'Title': 'Deposit', 'Value': stats_dict.get('Deposit', '0.00')},
        {'Index': 10, 'Title': 'Total Payable', 'Value': stats_dict.get('Total Payable', '0.00')},
    ]


def get_invoice_stats_formatted(invoice_id: str) -> list[dict[str, Any]] | None:
    db = SessionLocal()
    try:
        fetch_query = text("""
            SELECT "Stats" FROM "public"."Invoice"
            WHERE "Id" = :invoice_id
        """)

        result = db.execute(fetch_query, {'invoice_id': invoice_id}).fetchone()

        if not result:
            logger.warning(f'⚠️ Invoice ID {invoice_id} not found')
            return None

        # Parse stats
        if isinstance(result.Stats, str):
            stats_array = json.loads(result.Stats)
        else:
            stats_array = result.Stats

        if not stats_array or len(stats_array) == 0:
            logger.warning(f'⚠️ No stats available for Invoice ID {invoice_id}')
            return None

        # FIX: use short title key
        discount_item = next(
            (item for item in stats_array if item['Title'] == 'Discount'), None
        )
        discount_value = discount_item['Value'] if discount_item else '0.00'
        logger.info(f'📊 Retrieved stats for Invoice {invoice_id}: Discount = ${discount_value}')

        return stats_array

    except Exception as e:
        logger.error(f'❌ Failed to retrieve invoice stats: {e}')
        return None
    finally:
        db.close()

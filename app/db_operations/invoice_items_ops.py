import json
import uuid

from typing import Any

from loguru import logger
from sqlalchemy import text

from app.core.db_config import SessionLocal

# ---------------------------
# Helpers
# ---------------------------

def parse_ocr_line_no(raw_value) -> int | None:
    """
    Extract integer line number from OCR output safely.
    """
    if raw_value is None:
        return None

    if isinstance(raw_value, dict):
        raw_value = raw_value.get("value")

    try:
        line_no = int(raw_value)
        return line_no if line_no > 0 else None
    except (ValueError, TypeError):
        return None


def override_line_no_field(field_array: list[dict], line_no: int):
    """
    Force LINE_NO inside ItemData JSON.
    """
    for field in field_array:
        if field["FieldCode"] == "LINE_NO":
            field["Value"] = str(line_no)
            field["ConfidenceLevel"] = 100
            return


# ---------------------------
# Field Conversion
# ---------------------------

def convert_to_field_value_format(
    item_dict: dict,
    distributor_name: str
) -> list[dict[str, Any]]:

    field_mappings = get_field_mappings(distributor_name)
    regex_mappings = get_regex_mappings(distributor_name)

    # Confidence map injected by processor
    confidence_details = item_dict.get("confidence_details", {})

    result = []

    for field_code, source_key in field_mappings.items():
        raw_value = item_dict.get(source_key, "")

        value = ""
        confidence_level = 0

        # Legacy OCR wrapper support
        if isinstance(raw_value, dict) and "value" in raw_value:
            value = raw_value.get("value")
            legacy_conf = raw_value.get("confidence", 0)
            confidence_level = int(legacy_conf * 100) if legacy_conf < 1 else int(legacy_conf)
        else:
            value = raw_value

        # Override with new confidence map if present
        if source_key in confidence_details:
            conf_val = confidence_details.get(source_key)
            if conf_val is not None:
                confidence_level = int(float(conf_val))

        # Normalize value
        if value is None:
            value = ""
        elif not isinstance(value, str):
            value = str(value)

        field_obj = {
            "Lock": False,
            "Value": value,
            "FieldCode": field_code,
            "RegexCode": regex_mappings.get(field_code, ""),
            "ConfidenceLevel": confidence_level,
        }
        result.append(field_obj)

    return result


# ---------------------------
# Mappings
# ---------------------------

def get_regex_mappings(distributor_name: str) -> dict[str, str]:
    return {
        "LINE_NO": "",
        "ITEM_DISTRIBUTOR_CODE": "",
        "UPC": "",
        "ITEM_NAME": "",
        "SIZE": "",
        "PACK": "",
        "UNIT_IN_CASE": "",
        "CASE_QTY": "",
        "UNIT_QTY": "",
        "PRICE": "",
        "DISCOUNT": "",
        "TAX": "",
        "NET_UNIT_COST": "",
        "TOTAL_COST": "",
        "RIP": "",
        "IS_OUT_OF_STOCK": "",
        "IS_FREE": "",
    }


def get_field_mappings(distributor_name: str) -> dict[str, str]:
    return {
        "LINE_NO": "line_no",
        "ITEM_DISTRIBUTOR_CODE": "item_distributor_code",
        "UPC": "upc",
        "ITEM_NAME": "item_name",
        "SIZE": "size",
        "PACK": "pack",
        "UNIT_IN_CASE": "unit_in_case",
        "CASE_QTY": "case_qty",
        "UNIT_QTY": "unit_qty",
        "PRICE": "unit_cost",
        "DISCOUNT": "discount",
        "TAX": "tax",
        "NET_UNIT_COST": "net_unit_cost",
        "TOTAL_COST": "total_cost",
        "RIP": "rip",
        "IS_OUT_OF_STOCK": "is_out_of_stock",
        "IS_FREE": "is_free",
    }


# ---------------------------
# Main DB Logic
# ---------------------------

def create_invoice_table_data(
    invoice_id: uuid.UUID,
    line_items: list[dict],
    page_no: int,
    distributor_name: str,
):
    db = SessionLocal()

    try:
        if not line_items:
            return False

        # 🔥 PRODUCTION-GRADE FIX
        # Always delete existing items for this invoice (idempotent)
        # ✅ Delete only THIS page (not entire invoice)
        db.execute(
            text("""
                DELETE FROM "public"."InvoiceTableData"
                WHERE "InvoiceId" = :invoice_id
                AND "PageNo" = :page_no
            """),
            {
                "invoice_id": invoice_id,
                "page_no": page_no,
            },
        )
        insert_query = text("""
            INSERT INTO "public"."InvoiceTableData" (
                "Id",
                "InvoiceId",
                "ItemData",
                "PageNo"
            ) VALUES (
                :id,
                :invoice_id,
                :item_data,
                :page_no
            )
        """)

        current_line_no = 0

        for item in line_items:
            # Prefer OCR line number if present
            ocr_line_no = parse_ocr_line_no(item.get("line_no"))

            if ocr_line_no is not None:
                line_no = ocr_line_no
                current_line_no = max(current_line_no, line_no)
            else:
                current_line_no += 1
                line_no = current_line_no

            field_value_array = convert_to_field_value_format(
                item,
                distributor_name,
            )

            override_line_no_field(field_value_array, line_no)

            db.execute(
                insert_query,
                {
                    "id": uuid.uuid4(),
                    "invoice_id": invoice_id,
                    "item_data": json.dumps(field_value_array),
                    "page_no": page_no,
                },
            )

        db.commit()
        return True

    except Exception as e:
        logger.error(f"❌ Failed saving invoice table data: {e}")
        db.rollback()
        return False

    finally:
        db.close()

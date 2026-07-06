import json
import uuid
import datetime

from loguru import logger
from sqlalchemy import text

from app.core.db_config import SessionLocal

# Default Schema based on your sample data
GENERAL_TABLE_SCHEMA = json.dumps([
    {'Index': 1, 'Code': 'LINE_NO', 'Title': 'Line No'},
    {'Index': 2, 'Code': 'ITEM_DISTRIBUTOR_CODE', 'Title': 'Item Dist. Code'},
    {'Index': 3, 'Code': 'UPC', 'Title': 'UPC'},
    {'Index': 4, 'Code': 'ITEM_NAME', 'Title': 'Item Name'},
    {'Index': 5, 'Code': 'SIZE', 'Title': 'Size'},
    {'Index': 6, 'Code': 'PACK', 'Title': 'Pack'},
    {'Index': 7, 'Code': 'UNIT_IN_CASE', 'Title': 'Units in Case'},
    {'Index': 8, 'Code': 'CASE_QTY', 'Title': 'Case Qty'},
    {'Index': 9, 'Code': 'UNIT_QTY', 'Title': 'Unit Qty'},
    {'Index': 10, 'Code': 'PRICE', 'Title': 'Unit Cost'},
    {'Index': 11, 'Code': 'DISCOUNT', 'Title': 'Discount'},
    {'Index': 12, 'Code': 'TAX', 'Title': 'Tax'},
    {'Index': 13, 'Code': 'NET_UNIT_COST', 'Title': 'Net Unit Cost'},
    {'Index': 14, 'Code': 'TOTAL_COST', 'Title': 'Total Cost'},
    {'Index': 15, 'Code': 'RIP', 'Title': 'RIP'},
    {'Index': 16, 'Code': 'IS_OUT_OF_STOCK', 'Title': 'Out of Stock'},
    {'Index': 17, 'Code': 'IS_FREE', 'Title': 'Free Item'}
])

def get_distributor_id_by_name(distributor_name: str):
    db = SessionLocal()
    try:
        query = text(
            'SELECT "Id" FROM "masters"."Distributor" WHERE "Name" = :name'
        )
        result = db.execute(query, {'name': distributor_name}).fetchone()
        return result.Id if result else None
    finally:
        db.close()

def get_distributor_name_by_id(distributor_id: str) -> str:
    """
    Fetches the Distributor Name based on the provided UUID.
    Returns None if not found.
    """
    db = SessionLocal()
    try:
        # Ensure the string is a valid UUID (optional validation)
        # uuid_obj = uuid.UUID(distributor_id)

        query = text('SELECT "Name" FROM "masters"."Distributor" WHERE "Id" = :id')
        result = db.execute(query, {'id': distributor_id}).fetchone()

        if result:
            return result.Name
        else:
            logger.warning(f"⚠️ Distributor ID '{distributor_id}' not found in database.")
            return None
    except Exception as e:
        logger.error(f'❌ Error fetching distributor by ID: {e}')
        return None
    finally:
        db.close()


def check_or_create_distributor(distributor_name: str, table_schema_json: str) -> bool:
    """
    Checks if a distributor exists in the 'masters' schema.
    If NOT, creates it with default values.

    Returns:
        bool: True if it already existed, False if it was newly created.
    """
    db = SessionLocal()
    try:
        # 1. Check if exists
        check_query = text('SELECT "Id" FROM "masters"."Distributor" WHERE "Name" = :name')
        result = db.execute(check_query, {'name': distributor_name}).fetchone()

        if result:
            logger.info(f"✅ Distributor '{distributor_name}' already exists. ID: {result.Id}")
            update_query = text("""
                UPDATE "masters"."Distributor"
                SET "TableSchema" = :schema
                WHERE "Id" = :id
            """)
            db.execute(update_query, {'schema': table_schema_json, 'id': result.Id})
            db.commit()

            return True

        # 2. If not exists, Create new
        logger.info(f"🆕 Distributor '{distributor_name}' not found. Creating new record...")

        new_id = uuid.uuid4()
        current_time = datetime.datetime.now(datetime.timezone.utc)

        # Using the new ID as CreatedBy as well, mirroring your sample data pattern
        insert_query = text("""
            INSERT INTO "masters"."Distributor"
            ("Id", "Name", "CreatedDate", "CreatedBy", "TableSchema", "Address")
            VALUES (:id, :name, :created_date, :created_by, :schema, :address)
        """)

        db.execute(
            insert_query,
            {
                'id': new_id,
                'name': distributor_name,
                'created_date': current_time,
                'created_by': new_id,
                'schema': table_schema_json,
                'address': '',  # Default empty address
            },
        )
        db.commit()

        logger.success(f"✅ Created new Distributor '{distributor_name}' with ID: {new_id}")
        return False

    except Exception as e:
        logger.error(f'❌ Error checking/creating distributor: {e}')
        db.rollback()
        # In case of error, we assume it doesn't exist to avoid crashing, or re-raise
        return False
    finally:
        db.close()

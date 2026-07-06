from datetime import date, datetime

from loguru import logger


def parse_date_safe(date_val: str | datetime | date | None):
    """
    Helper to ensure we get a Python date object.
    """
    if not date_val:
        return None

    if isinstance(date_val, (datetime, date)):
        if isinstance(date_val, datetime):
            return date_val.date()
        return date_val

    date_str = str(date_val).strip()

    formats = [
        '%Y-%m-%d',  # 2026-07-24
        '%m/%d/%Y',  # 07/24/2026
        '%m/%d/%y',  # 07/24/26
        '%m-%d-%Y',  # 07-24-2026
        '%m-%d-%y',  # 07-24-26
        '%m-%y',     # 07-24 (Month/Year)
        '%m/%y',     # 07/24 (Month/Year)
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    logger.warning(f'⚠️ Could not parse date: {date_val}')
    return None

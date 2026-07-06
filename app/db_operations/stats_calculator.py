from typing import Any

from loguru import logger

from app.models.georgia_inv import Invoice


def calculate_invoice_stats(invoice_data: Invoice) -> list[dict[str, Any]]:

    try:
        stats = {
            'total_items': 0,
            'total_bottles': 0,
            'total_cases': 0,
            'total_liters': 0.0,
            'total_discount': 0.0,
            'total_payable': 0.0,
            'total_out_of_stock_items': 0,
        }

        # --- Calculate discount from line items ---
        total_discount = 0.0
        discount_breakdown = []

        if invoice_data.items and len(invoice_data.items) > 0:
            logger.info(f'💰 Calculating discount from {len(invoice_data.items)} line items...')

            for idx, item in enumerate(invoice_data.items, 1):
                line_no = getattr(item, 'line_no', idx)
                description = getattr(item, 'description', 'N/A')

                if hasattr(item, 'discount') and item.discount is not None:
                    try:
                        discount_val = float(item.discount)
                        total_discount += discount_val
                        discount_breakdown.append({
                            'line': line_no,
                            'description': description[:30],
                            'discount': discount_val,
                        })
                        logger.debug(
                            f'   Line {line_no} ({description[:30]}): Discount = ${discount_val:.2f}'
                        )
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"   Line {line_no}: Invalid discount value '{item.discount}' - {e}"
                        )
                else:
                    logger.debug(f'   Line {line_no} ({description[:30]}): No discount')

            stats['total_discount'] = round(total_discount, 2)

            logger.success(
                f'💰 Page Discount Summary: ${stats["total_discount"]:.2f} from {len(discount_breakdown)} items with discounts'
            )
            if discount_breakdown:
                logger.debug(f'   Discount breakdown: {discount_breakdown}')
        else:
            logger.warning('⚠️  No line items found for discount calculation')

        # --- Calculate other stats ONLY if summary present ---
        if invoice_data.summary_breakdown:
            if invoice_data.items and len(invoice_data.items) > 0:
                last_item = invoice_data.items[-1]
                if hasattr(last_item, 'line_no') and last_item.line_no is not None:
                    try:
                        stats['total_items'] = int(last_item.line_no)
                    except (ValueError, TypeError):
                        stats['total_items'] = 0

            total_bottles = 0
            total_cases = 0
            total_liters = 0.0

            for row in invoice_data.summary_breakdown:
                if row.bottles is not None:
                    total_bottles += row.bottles
                if row.cases is not None:
                    total_cases += row.cases
                if row.liters is not None:
                    total_liters += row.liters

            stats['total_bottles'] = total_bottles
            stats['total_cases'] = total_cases
            stats['total_liters'] = round(total_liters, 2)

            if invoice_data.total_net_amount_due is not None:
                stats['total_payable'] = round(invoice_data.total_net_amount_due, 2)

        logger.info(
            f'📊 Stats calculated: {stats["total_items"]} items, '
            f'{stats["total_bottles"]} bottles, '
            f'{stats["total_cases"]} cases, '
            f'${stats["total_payable"]} payable, '
            f'discount: ${stats["total_discount"]}'
        )

        # Convert to array of objects format with CAPITALIZED keys
        return _format_stats_array(stats)

    except Exception as e:
        logger.error(f'❌ Failed to calculate stats: {e}')
        return _format_stats_array({
            'total_items': 0,
            'total_bottles': 0,
            'total_cases': 0,
            'total_liters': 0.0,
            'total_discount': 0.0,
            'total_payable': 0.0,
            'total_out_of_stock_items': 0,
        })


def calculate_invoice_stats_with_confidence(invoice_data) -> list[dict[str, Any]]:

    try:
        stats = {
            'total_items': 0,
            'total_bottles': 0,
            'total_cases': 0,
            'total_liters': 0.0,
            'total_discount': 0.0,
            'total_payable': 0.0,
            'total_out_of_stock_items': 0,
        }

        # --- Calculate discount from line items ---
        total_discount = 0.0
        discount_breakdown = []

        if invoice_data.items and len(invoice_data.items) > 0:
            logger.info(
                f'💰 Calculating discount (with confidence) from {len(invoice_data.items)} line items...'
            )

            for idx, item in enumerate(invoice_data.items, 1):
                line_no_val = _extract_value(getattr(item, 'line_no', None)) or idx
                description_val = _extract_value(getattr(item, 'description', None)) or 'N/A'
                discount_val = _extract_value(getattr(item, 'discount', None))

                if discount_val is not None:
                    try:
                        discount_float = float(discount_val)
                        total_discount += discount_float
                        discount_breakdown.append({
                            'line': line_no_val,
                            'description': str(description_val)[:30],
                            'discount': discount_float,
                        })
                        logger.debug(
                            f'   Line {line_no_val} ({str(description_val)[:30]}): Discount = ${discount_float:.2f}'
                        )
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"   Line {line_no_val}: Invalid discount value '{discount_val}' - {e}"
                        )
                else:
                    logger.debug(
                        f'   Line {line_no_val} ({str(description_val)[:30]}): No discount'
                    )

            stats['total_discount'] = round(total_discount, 2)

            logger.success(
                f'💰 Page Discount Summary: ${stats["total_discount"]:.2f} from {len(discount_breakdown)} items with discounts'
            )
            if discount_breakdown:
                logger.debug(f'   Discount breakdown: {discount_breakdown}')
        else:
            logger.warning('⚠️  No line items found for discount calculation')

        # --- Calculate other stats ONLY if summary present ---
        if invoice_data.summary_breakdown:
            if invoice_data.items and len(invoice_data.items) > 0:
                last_item = invoice_data.items[-1]
                line_no_val = _extract_value(getattr(last_item, 'line_no', None))
                if line_no_val is not None:
                    try:
                        stats['total_items'] = int(line_no_val)
                    except (ValueError, TypeError):
                        stats['total_items'] = 0

            total_bottles = 0
            total_cases = 0
            total_liters = 0.0

            for row in invoice_data.summary_breakdown:
                bottles_val = _extract_value(row.bottles) or 0
                cases_val = _extract_value(row.cases) or 0
                liters_val = _extract_value(row.liters) or 0.0

                total_bottles += bottles_val
                total_cases += cases_val
                total_liters += liters_val

            stats['total_bottles'] = total_bottles
            stats['total_cases'] = total_cases
            stats['total_liters'] = round(total_liters, 2)

            payable = _extract_value(invoice_data.total_net_amount_due)
            if payable is not None:
                stats['total_payable'] = round(payable, 2)

        logger.info(
            f'📊 Stats calculated: {stats["total_items"]} items, '
            f'{stats["total_bottles"]} bottles, '
            f'{stats["total_cases"]} cases, '
            f'${stats["total_payable"]} payable, '
            f'discount: ${stats["total_discount"]}'
        )

        # Convert to array of objects format with CAPITALIZED keys
        return _format_stats_array(stats)

    except Exception as e:
        logger.error(f'❌ Failed to calculate stats with confidence: {e}')
        return _format_stats_array({
            'total_items': 0,
            'total_bottles': 0,
            'total_cases': 0,
            'total_liters': 0.0,
            'total_discount': 0.0,
            'total_payable': 0.0,
            'total_out_of_stock_items': 0,
        })


def _format_stats_array(stats_dict: dict) -> list[dict[str, Any]]:
    return [
        {'Index': 1, 'Title': 'Items', 'Value': str(stats_dict.get('total_items', 0))},
        {
            'Index': 2,
            'Title': 'Bottles',
            'Value': str(stats_dict.get('total_bottles', 0)),
        },
        {'Index': 3, 'Title': 'Cases', 'Value': str(stats_dict.get('total_cases', 0))},
        {
            'Index': 4,
            'Title': 'Liters',
            'Value': f'{stats_dict.get("total_liters", 0.0):.2f}',
        },
        {
            'Index': 5,
            'Title': 'Discount',
            'Value': f'{stats_dict.get("total_discount", 0.0):.2f}',
        },
        {
            'Index': 6,
            'Title': 'Payable',
            'Value': f'{stats_dict.get("total_payable", 0.0):.2f}',
        },
        {
            'Index': 7,
            'Title': 'Out of Stock Items',
            'Value': str(stats_dict.get('total_out_of_stock_items', 0)),
        },
    ]


def _extract_value(confidence_wrapped):
    """Extract 'value' from confidence-wrapped field"""
    if confidence_wrapped is None:
        return None
    if isinstance(confidence_wrapped, dict) and 'value' in confidence_wrapped:
        return confidence_wrapped['value']
    return confidence_wrapped


def _extract_all_confidences(obj) -> list[float]:
    """Recursively extract all confidence scores from nested structure"""
    confidences = []

    if isinstance(obj, dict):
        if 'confidence' in obj and isinstance(obj['confidence'], (int, float)):
            confidences.append(obj['confidence'])
        for v in obj.values():
            confidences.extend(_extract_all_confidences(v))
    elif isinstance(obj, list):
        for item in obj:
            confidences.extend(_extract_all_confidences(item))

    return confidences

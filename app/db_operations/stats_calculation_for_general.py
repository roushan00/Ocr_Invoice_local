from typing import Any

from loguru import logger

from app.models.universal_template import UniversalInvoice


def calculate_invoice_stats(invoice_data: UniversalInvoice) -> list[dict[str, Any]]:
    try:
        stats = {
            'Items': 0,
            'Out Of Stock Items': 0,
            'Cases': 0.0,
            'Units': 0.0,
            'RIP': 0.0,
            'Sub Total': 0.0,
            'Discount': 0.0,
            'Tax': 0.0,
            'Deposit': 0.0,
            'Total Payable': 0.0,
        }

        # --- PASS 1: Calculate from Line Items (Fallback) ---
        if invoice_data.items and len(invoice_data.items) > 0:
            logger.info(f'🧮 Calculating base stats from {len(invoice_data.items)} line items...')
            stats['Items'] = len(invoice_data.items)

            for item in invoice_data.items:
                # Out of stock count
                if getattr(item, 'is_out_of_stock', False) is True:
                    stats['Out Of Stock Items'] += 1

                # Quantities
                try: stats['Cases'] += float(getattr(item, 'case_qty', 0) or 0)
                except: pass
                try: stats['Units'] += float(getattr(item, 'unit_qty', 0) or 0)
                except: pass

                # Financials
                try: stats['Discount'] += float(getattr(item, 'discount', 0) or 0)
                except: pass
                try: stats['Tax'] += float(getattr(item, 'tax', 0) or 0)
                except: pass

                # Sub Total (Try total_cost first, fallback to price)
                item_cost = getattr(item, 'total_cost', None)
                if item_cost is None:
                    item_cost = getattr(item, 'unit_cost', 0)
                try: stats['Sub Total'] += float(item_cost or 0)
                except: pass

        # --- PASS 2: Override with Summary Data (Source of Truth) ---
        summary_data = getattr(invoice_data, 'summary', None)
        if summary_data:
            logger.info('📝 Summary block found, overriding line item calculations with summary totals...')

            # Ensure it's iterable
            if not isinstance(summary_data, list):
                summary_data = [summary_data]

            for row in summary_data:
                if getattr(row, 'total_items', None) is not None:
                    stats['Items'] = max(stats['Items'], int(row.total_items))
                if getattr(row, 'total_out_of_stocks', None) is not None:
                    stats['Out Of Stock Items'] = int(row.total_out_of_stocks)
                if getattr(row, 'total_case', None) is not None:
                    stats['Cases'] = float(row.total_case)
                if getattr(row, 'total_units', None) is not None:
                    stats['Units'] = float(row.total_units)

                # Liters can sometimes be "liters" or "total_liters"
                liters_val = getattr(row, 'total_rip', getattr(row, 'rip', None))
                if liters_val is not None:
                    stats['RIP'] = float(liters_val)

                if getattr(row, 'sub_total', None) is not None:
                    stats['Sub Total'] = float(row.sub_total)
                if getattr(row, 'total_discounts', None) is not None:
                    stats['Discount'] = float(row.total_discounts)
                if getattr(row, 'total_tax', None) is not None:
                    stats['Tax'] = float(row.total_tax)
                if getattr(row, 'deposit', None) is not None:
                    stats['Deposit'] = float(row.deposit)

                # Payable logic
                payable_val = getattr(row, 'total_payable', getattr(invoice_data, 'total_payable', None))
                if payable_val is not None:
                    stats['Total Payable'] = float(payable_val)

        # Fallback Calculation for Total Payable if missing
        if stats['Total Payable'] == 0.0 and stats['Sub Total'] > 0:
            stats['Total Payable'] = stats['Sub Total'] - stats['Discount'] + stats['Tax'] + stats['Deposit']

        logger.info(f'📊 Final Stats: {stats}')
        return _format_stats_array(stats)

    except Exception as e:
        logger.error(f'❌ Failed to calculate stats: {e}')
        return _format_stats_array({})


def calculate_invoice_stats_with_confidence(invoice_data) -> list[dict[str, Any]]:
    try:
        stats = {
            'Items': 0, 'Out Of Stock Items': 0, 'Cases': 0.0, 'Units': 0.0, 'RIP': 0.0,
            'Sub Total': 0.0, 'Discount': 0.0, 'Tax': 0.0, 'Deposit': 0.0, 'Total Payable': 0.0
        }

        # --- PASS 1: Calculate from Line Items ---
        if invoice_data.items and len(invoice_data.items) > 0:
            stats['Items'] = len(invoice_data.items)
            for item in invoice_data.items:
                if _extract_value(getattr(item, 'is_out_of_stock', False)) is True:
                    stats['Out Of Stock Items'] += 1

                try: stats['Cases'] += float(_extract_value(getattr(item, 'case_qty', 0)) or 0)
                except: pass
                try: stats['Units'] += float(_extract_value(getattr(item, 'unit_qty', 0)) or 0)
                except: pass
                try: stats['Discount'] += float(_extract_value(getattr(item, 'discount', 0)) or 0)
                except: pass
                try: stats['Tax'] += float(_extract_value(getattr(item, 'tax', 0)) or 0)
                except: pass

                item_cost = _extract_value(getattr(item, 'total_cost', None))
                if item_cost is None:
                    item_cost = _extract_value(getattr(item, 'unit_cost', 0))
                try: stats['Sub Total'] += float(item_cost or 0)
                except: pass

        # --- PASS 2: Override with Summary Data ---
        summary_data = getattr(invoice_data, 'summary', None)
        if summary_data:
            if not isinstance(summary_data, list):
                summary_data = [summary_data]

            for row in summary_data:
                items_val = _extract_value(getattr(row, 'total_items', None))
                if items_val is not None: stats['Items'] = max(stats['Items'], int(items_val))

                oos_val = _extract_value(getattr(row, 'total_out_of_stocks', None))
                if oos_val is not None: stats['Out Of Stock Items'] = int(oos_val)

                cases_val = _extract_value(getattr(row, 'total_case', None))
                if cases_val is not None: stats['Cases'] = float(cases_val)

                units_val = _extract_value(getattr(row, 'total_units', None))
                if units_val is not None: stats['Units'] = float(units_val)

                liters_val = _extract_value(getattr(row, 'total_rip', getattr(row, 'rip', None)))
                if liters_val is not None: stats['RIP'] = float(liters_val)

                sub_total_val = _extract_value(getattr(row, 'sub_total', None))
                if sub_total_val is not None: stats['Sub Total'] = float(sub_total_val)

                discount_val = _extract_value(getattr(row, 'total_discounts', None))
                if discount_val is not None: stats['Discount'] = float(discount_val)

                tax_val = _extract_value(getattr(row, 'total_tax', None))
                if tax_val is not None: stats['Tax'] = float(tax_val)

                deposit_val = _extract_value(getattr(row, 'deposit', None))
                if deposit_val is not None: stats['Deposit'] = float(deposit_val)

                payable_val = _extract_value(getattr(row, 'total_payable', getattr(invoice_data, 'total_payable', None)))
                if payable_val is not None: stats['Total Payable'] = float(payable_val)

        if stats['Total Payable'] == 0.0 and stats['Sub Total'] > 0:
            stats['Total Payable'] = stats['Sub Total'] - stats['Discount'] + stats['Tax'] + stats['Deposit']

        return _format_stats_array(stats)

    except Exception as e:
        logger.error(f'❌ Failed to calculate stats with confidence: {e}')
        return _format_stats_array({})


def _format_stats_array(stats_dict: dict) -> list[dict[str, Any]]:
    # Formats the exact 10 keys requested
    return [
        {'Index': 1, 'Title': 'Items', 'Value': str(int(stats_dict.get('Items', 0)))},
        {'Index': 2, 'Title': 'Out Of Stock Items', 'Value': str(int(stats_dict.get('Out Of Stock Items', 0)))},
        {'Index': 3, 'Title': 'Cases', 'Value': str(int(stats_dict.get('Cases', 0)))},
        {'Index': 4, 'Title': 'Units', 'Value': str(int(stats_dict.get('Units', 0)))},
        {'Index': 5, 'Title': 'RIP', 'Value': f"{float(stats_dict.get('RIP', 0.0)):.2f}"},
        {'Index': 6, 'Title': 'Sub Total', 'Value': f"{float(stats_dict.get('Sub Total', 0.0)):.2f}"},
        {'Index': 7, 'Title': 'Discount', 'Value': f"{float(stats_dict.get('Discount', 0.0)):.2f}"},
        {'Index': 8, 'Title': 'Tax', 'Value': f"{float(stats_dict.get('Tax', 0.0)):.2f}"},
        {'Index': 9, 'Title': 'Deposit', 'Value': f"{float(stats_dict.get('Deposit', 0.0)):.2f}"},
        {'Index': 10, 'Title': 'Total Payable', 'Value': f"{float(stats_dict.get('Total Payable', 0.0)):.2f}"},
    ]

def _extract_value(confidence_wrapped):
    if confidence_wrapped is None:
        return None
    if isinstance(confidence_wrapped, dict) and 'value' in confidence_wrapped:
        return confidence_wrapped['value']
    return confidence_wrapped

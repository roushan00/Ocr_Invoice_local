from app.models.georgia_inv import Invoice


def merge_invoices(invoices: list[Invoice]) -> Invoice:
    merged = Invoice()

    for inv in invoices:
        if not inv:
            continue  # Skip failed pages

        data = inv.model_dump()

        for field, value in data.items():
            if field in ['items', 'summary_breakdown']:
                continue
            # Merge fields if current is empty but new one has data
            if getattr(merged, field) in [None, ''] and value not in [None, '']:
                setattr(merged, field, value)

        merged.items.extend(inv.items)

        if inv.summary_breakdown:
            merged.summary_breakdown = inv.summary_breakdown

        if inv.total_net_amount_due not in [None, '']:
            merged.total_net_amount_due = inv.total_net_amount_due
        if inv.total_bottles_footer not in [None, '']:
            merged.total_bottles_footer = inv.total_bottles_footer
        if inv.total_each_footer not in [None, '']:
            merged.total_each_footer = inv.total_each_footer

    return merged

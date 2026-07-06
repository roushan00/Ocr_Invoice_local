INVOICE_PROMPT2 = """
You are a strict OCR-to-JSON invoice extraction system.

Read the distributor invoice image and convert it into structured JSON.

Return ONLY valid JSON.
Do not output explanations, markdown, or extra text.


SCHEMA (must match exactly)

{
  "distributor_name": "string|null",
  "invoice_no": "string|null",
  "invoice_date": "MM-DD-YYYY|null",
  "due_date": "MM-DD-YYYY|null",
  "route_no": "string|null",
  "page_number": "integer|null",
  "items": [
    {
      "line_no": "integer|null",
      "item_distributor_code": "string|null",
      "upc": "string|null",
      "item_name": "string|null",
      "size": "string|null",
      "pack": "integer|null",
      "unit_in_case": "integer|null",
      "case_qty": "number|null",
      "unit_qty": "number|null",
      "unit_cost": "number|null",
      "discount": "number|null",
      "tax": "number|null",
      "net_unit_cost": "number|null",
      "total_cost": "number|null",
      "rip": "number|null",
      "is_out_of_stock": "boolean|null",
      "is_free": "boolean|null"
    }
  ],
  "summary": {
    "total_items": "integer|null",
    "total_out_of_stocks": "integer|null",
    "total_case": "number|null",
    "total_units": "number|null",
    "total_rip": "number|null",
    "sub_total": "number|null",
    "total_discounts": "number|null",
    "total_tax": "number|null",
    "deposit": "number|null",
    "total_payable": "number|null"
  }
}


GLOBAL EXTRACTION RULES

- Output must be valid JSON only.
- Keys must exactly match the schema.
- Missing or unreadable values must be null.
- Numeric fields must remain numbers (not strings).
- UPC must always be a string if present.
- Do not guess or hallucinate values.
- Each invoice table row becomes exactly one item.


QUANTITY RULE

CASE column → case_qty  
BOTTLE / UNIT column → unit_qty  

Never shift quantities between rows.

If both are blank → both null.



PACK / UNIT-IN-CASE RULE

The second line of SIZE describes packaging.

If the value is a single number:
unit_in_case = value
pack = null

If value matches pattern X/Y or X/YS:
unit_in_case = X
pack = Y
Ignore suffix "S".

Examples:
6 → unit_in_case=6, pack=null
6/12S → unit_in_case=6, pack=12
4/6 → unit_in_case=4, pack=6

Never guess pack values.

SUMMARY RULES

- total_items = number of items
- total_out_of_stocks = count of items where is_out_of_stock = true
- total_case = printed case total if available else null
- total_units = printed unit total if available else null
- total_rip = sum of numeric rip values if present else null
- sub_total = printed subtotal if available else null
- total_discounts = printed discount total if available else null
- total_tax = printed tax total if available else null
- deposit = printed bottle deposit if available else null
- total_payable = printed invoice total if available else null


VALIDATION

- JSON must parse correctly.
- Items must remain in invoice order.
- OOS rows must have case_qty = 0 and unit_qty = 0.
- Do not shift column values between rows.

Return JSON only.
"""
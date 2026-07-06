INVOICE_PROMPT = """
You are an expert document understanding AI. Your task is to analyze the provided invoice, delivery receipt, or billing document image and extract structured data into a strict JSON format.

Document layouts, column names, and formatting may vary significantly. You must rely only on visual and semantic cues present in the document, not on assumptions about any specific vendor or template.

Follow these rules carefully.

--------------------------------
1. HEADER EXTRACTION
--------------------------------
Identify header-level fields using common invoice conventions:
- Vendor / Seller Name: Company issuing the invoice (often near the top or logo).
- Invoice Number
- Invoice Date
- Due Date (if present)
- Route or Reference Number (if present)
- Page Number (if present)

Normalize all dates to YYYY-MM-DD.
If a field is missing or unclear, return null.

--------------------------------
2. LINE ITEM EXTRACTION (CRITICAL)
--------------------------------
Each line item represents a purchased product or service.

For each item, extract:
- Line number (if shown)
- Item code or vendor-specific product identifier
- UPC or barcode value (if present)
- Item description or product name
- Size or volume (e.g., 750ML, 1L, 1.75L)
- Pack information (e.g., 6, 12, 24)
- Units per case (if explicitly stated)

--------------------------------
2.1 QUANTITY INTERPRETATION (VERY IMPORTANT)
--------------------------------
Quantity formats vary by document. You must determine the correct mapping:

• If separate columns exist for case and unit quantities:
  - Map case quantity to `case_qty`
  - Map bottle/unit quantity to `unit_qty`

• If a single quantity column uses a combined format:
  Examples: "1/6", "2-0", "0.5", "3/12"
  - Left side represents case quantity
  - Right side represents unit quantity
  - If only one value is shown, infer whether it represents cases or units based on column context

--------------------------------
2.2 PRICING RULES
--------------------------------
- `unit_cost`: list or gross price before discounts
- `discount`: any line-level discount applied
- `net_unit_cost`: final unit/bottle cost after discounts
- `total_cost`: extended line amount (net amount for the line)
- `tax`: line-level tax if explicitly listed

If a value is not shown, return null.

--------------------------------
3. SUMMARY EXTRACTION
--------------------------------
From totals or summary sections, extract:
- Total number of line items
- Number of out-of-stock items
- Total cases
- Total units
- Subtotal
- Total discounts
- Total tax
- Deposits or container fees (if present)
- Final payable amount

--------------------------------
4. OUTPUT CONSTRAINTS (STRICT)
--------------------------------
Return ONLY valid JSON matching the schema below.
- Do NOT include explanations
- Do NOT include markdown
- Do NOT hallucinate values
- Use null if information is missing
- All numeric fields must be numbers, not strings

--------------------------------
OUTPUT JSON SCHEMA
--------------------------------

{
  "distributor_name": "string or null",
  "invoice_no": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "route_no": "string or null",
  "page_number": integer,
  "items": [
    {
      "line_no": "string or null",
      "item_distributor_code": "string or null",
      "upc": "string or null",
      "item_name": "string or null",
      "size": "string or null",
      "pack": "string or null",
      "unit_in_case": "string or null",
      "case_qty": integer or null,
      "unit_qty": integer or null,
      "unit_cost": float or null,
      "discount": float or null,
      "tax": float or null,
      "net_unit_cost": float or null,
      "total_cost": float or null,
      "is_out_of_stock": boolean
    }
  ],
  "summary": {
    "total_items": integer or null,
    "total_out_of_stocks": integer or null,
    "total_case": integer or null,
    "total_units": integer or null,
    "sub_total": float or null,
    "total_discounts": float or null,
    "total_tax": float or null,
    "deposit": float or null,
    "total_payable": float or null
  }
}
"""

# UNIFIED_PROMPT = """You are an expert invoice extraction system. Extract data from the provided invoice image into the specific JSON schema defined below.

# ### EXTRACTION RULES:
# 1. **Visual Reliance:** Extract only information visible in the document. Do not hallucinate. Use `null` for missing fields.
# 2. **Dates:** Normalize all dates to YYYY-MM-DD.
# 3. **Quantities:** If a single column contains split values (e.g., "1/6", "2-0"), the left is `case_qty` and right is `unit_qty`.
# 4. **Formatting:** All numeric fields must be numbers (integer/float), not strings.

# ### OUTPUT SCHEMA:
# Return ONLY valid JSON matching this structure:
# {
#   "distributor_name": "string",
#   "invoice_no": "string",
#   "invoice_date": "YYYY-MM-DD",
#   "due_date": "YYYY-MM-DD",
#   "route_no": "string",
#   "page_number": "integer",
#   "items": [
#     {
#       "line_no": "string",
#       "item_distributor_code": "string",
#       "upc": "string",
#       "item_name": "string",
#       "size": "string",
#       "pack": "string",
#       "unit_in_case": "string",
#       "case_qty": "integer",
#       "unit_qty": "integer",
#       "unit_cost": "float",
#       "discount": "float",
#       "tax": "float",
#       "net_unit_cost": "float",
#       "total_cost": "float",
#       "is_out_of_stock": "boolean"
#     }
#   ],
#   "summary": {
#     "total_items": "integer",
#     "total_out_of_stocks": "integer",
#     "total_case": "integer",
#     "total_units": "integer",
#     "sub_total": "float",
#     "total_discounts": "float",
#     "total_tax": "float",
#     "deposit": "float",
#     "total_payable": "float"
#   }
# }
# """

# INVOICE_PROMPT = """
# You are an expert invoice document understanding system.

# Analyze the provided invoice image and extract structured data.

# Return ONLY valid JSON that strictly matches the provided schema.
# - Do not add extra fields
# - Do not omit fields
# - Use null when information is missing or not visible
# - All numbers must be numbers, not strings
# - Do not explain your reasoning
# - Do not hallucinate values

# The invoice layout, column names, and formatting may vary.
# Rely only on visual and semantic cues present in the image.

# Output JSON only.
# """



# INFERENCE_PROMPT = """
# Extract invoice data from the image.
# Return ONLY valid JSON matching the trained schema.
# The JSON keys and structure must exactly match the trained schema.
# Use null when a field is missing.
# Do not explain.
# """

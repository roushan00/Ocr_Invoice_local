from pydantic import BaseModel


class GeneralLineItem(BaseModel):
    description: str
    quantity: float | None = 0
    unit_price: float | None = 0
    total_amount: float | None = 0
    product_code: str | None = None


class GeneralInvoice(BaseModel):
    invoice_no: str | None = None
    invoice_date: str | None = None
    net_amount: float | None = 0
    # Vendor/Distributor name if extracted from OCR
    vendor_name: str | None = None
    line_items: list[GeneralLineItem] = []

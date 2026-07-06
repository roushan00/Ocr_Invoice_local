from pydantic import Field, BaseModel


class InvoiceLineItem(BaseModel):
    line_no: int | None = Field(None, description="Line number on invoice", examples=[1])

    item_distributor_code: str | None = Field(None, description="Internal distributor product code", examples=["12345-AB"])
    upc: str | None = Field(None, description="Universal Product Code", examples=["08500002568"])
    item_name: str | None = Field(None, description="Product description", examples=["Jack Daniels Whiskey"])

    size: str | None = Field(None, description="Bottle size, e.g. 750ML, 1.5L", examples=["750ML"])
    pack: str | None = Field(None, description="Pack size, e.g. 6, 12", examples=[12])

    unit_in_case: int | None = Field(None, description="Number of units per case configuration", examples=[12])
    case_qty: float | None = Field(None, description="Quantity of full cases ordered/shipped", examples=[2.0])
    unit_qty: float | None = Field(None, description="Quantity of individual split units ordered/shipped", examples=[5.5])

    unit_cost: float | None = Field(None, description="Unit price per item/case", examples=[25.50])
    discount: float | None = Field(None, description="Discount amount or percentage applied", examples=[5.00])
    tax: float | None = Field(None, description="Tax amount applied to this line", examples=[1.25])
    net_unit_cost: float | None = Field(None, description="Net cost per bottle after adjustments", examples=[24.00])
    total_cost: float | None = Field(None, description="Total net line amount (Qty * Net Cost)", examples=[240.00])
    rip: float | None = Field(default=None, description="Retail incentive program or rebate value if present", examples=[1.50])
    is_out_of_stock: bool | None = Field(default=None, description="True if the item was unavailable or shorted", examples=[False])
    is_free: bool | None = Field(default=None, description="True if the product is free or promotional", examples=[False])

class InvoiceSummary(BaseModel):
    total_items: int | None = Field(None, description="Total count of unique line items", examples=[10])
    total_out_of_stocks: int | None = Field(None, description="Count of items marked as out of stock", examples=[1])
    total_case: float | None = Field(None, description="Sum of all cases shipped", examples=[20.0])
    total_units: float | None = Field(None, description="Sum of all split units shipped", examples=[5.0])
    total_rip: float | None = Field(default=None,description="Total Retail Incentive Program (RIP) amount summed across all line items on the invoice",examples=[25.50])
    sub_total: float | None = Field(None, description="Sum of line items before tax/deposits", examples=[1500.50])
    total_discounts: float | None = Field(None, description="Total value of discounts applied", examples=[50.00])
    total_tax: float | None = Field(None, description="Total sales tax amount", examples=[125.00])
    deposit: float | None = Field(None, description="Bottle deposit or container fees", examples=[12.00])
    total_payable: float | None = Field(None, description="Final invoice amount due", examples=[1587.50])


class UniversalInvoice(BaseModel):
    distributor_name: str | None = Field(None, description="Name of the distributor/vendor", examples=["Southern Glazer's Wine & Spirits"])
    invoice_no: str | None = Field(None, description="Unique invoice identifier", examples=["INV-998877"])
    invoice_date: str | None = Field(default=None,description="Date of invoice issuance (MM-DD-YYYY)",examples=["10-25-2023"])
    due_date: str | None = Field(default=None,description="Payment due date (MM-DD-YYYY) or null if not available",examples=["11-25-2025", None])
    route_no: str | None = Field(None, description="Delivery route number or identifier", examples=["1145"])
    page_number: int | None = Field(None, description="Page number of the invoice if multi-page", examples=[1])
    items: list[InvoiceLineItem] = Field(default_factory=list, description="List of line items on the invoice")
    summary: InvoiceSummary | None = Field(None, description="Summary totals of the invoice")

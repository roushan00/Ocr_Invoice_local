from typing import Generic, TypeVar

from pydantic import Field, BaseModel

T = TypeVar('T')


class FieldWithConfidence(BaseModel, Generic[T]):
    value: T | None = Field(None, description='Extracted value')
    confidence: float | None = Field(None, description='Confidence score between 0.0 and 1.0')


class InvoiceLineItem(BaseModel):
    line_no: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    product_code: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    upc: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    case_quantity: FieldWithConfidence[int] = Field(default_factory=FieldWithConfidence)
    bottle_quantity: FieldWithConfidence[int] = Field(default_factory=FieldWithConfidence)
    size: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    pack: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    description: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    unit_price: FieldWithConfidence[float] = Field(default_factory=FieldWithConfidence)
    discount: FieldWithConfidence[float] = Field(default_factory=FieldWithConfidence)
    net_bottle_price: FieldWithConfidence[float] = Field(default_factory=FieldWithConfidence)
    net_amount: FieldWithConfidence[float] = Field(default_factory=FieldWithConfidence)


class SummaryCategoryRow(BaseModel):
    bottles: FieldWithConfidence[int] = Field(default_factory=FieldWithConfidence)
    cases: FieldWithConfidence[int] = Field(default_factory=FieldWithConfidence)
    liters: FieldWithConfidence[float] = Field(default_factory=FieldWithConfidence)
    category_description: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    local_tax: FieldWithConfidence[float] = Field(default_factory=FieldWithConfidence)
    net_amount: FieldWithConfidence[float] = Field(default_factory=FieldWithConfidence)


class InvoiceWithConfidence(BaseModel):
    # --- Distributor Info ---
    distributor_name: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    distributor_address: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    city: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    country: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    distributor_phone: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    distributor_state_permit_no: FieldWithConfidence[str] = Field(
        default_factory=FieldWithConfidence
    )
    distributor_support_no: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)

    # --- Customer Info ---
    sold_to_name: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    sold_to_address: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    sold_to_phone: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    customer_account_no: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)

    # --- Invoice Details ---
    invoice_no: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    invoice_date: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    page_no: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    customer_purchase_order_no: FieldWithConfidence[str] = Field(
        default_factory=FieldWithConfidence
    )
    route_no: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)

    # --- Salesman & License ---
    salesman_liquor: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    salesman_wine: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    salesman_beer: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    salesman_misc: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    license_liquor: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    license_wine: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    license_beer: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)

    # --- Main Data ---
    special_instructions: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    items: list[InvoiceLineItem] = Field(default_factory=list)
    summary_breakdown: list[SummaryCategoryRow] = Field(default_factory=list)

    # --- Totals ---
    total_bottles_footer: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    total_each_footer: FieldWithConfidence[str] = Field(default_factory=FieldWithConfidence)
    total_net_amount_due: FieldWithConfidence[float] = Field(default_factory=FieldWithConfidence)

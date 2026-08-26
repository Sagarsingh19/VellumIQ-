from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    description: Optional[str] = Field(
        None, description="Description of the product or service."
    )
    quantity: Optional[float] = Field(None, description="Quantity of items purchased.")
    unit_price: Optional[float] = Field(
        None, description="Price per unit of the product or service."
    )
    tax_percentage: Optional[float] = Field(
        None, description="Tax percentage applied to this line item."
    )
    total: Optional[float] = Field(None, description="Total amount for this line item.")


class InvoiceExtractionSchema(BaseModel):
    vendor_name: Optional[str] = Field(
        None, description="Name of the vendor or company issuing the invoice."
    )
    vendor_address: Optional[str] = Field(None, description="Physical address of the vendor.")
    vendor_tax_id: Optional[str] = Field(
        None, description="Tax ID / GSTIN / VAT number of the vendor."
    )
    invoice_number: Optional[str] = Field(None, description="Unique identifying invoice number.")
    invoice_date: Optional[date] = Field(None, description="Date when the invoice was issued.")
    due_date: Optional[date] = Field(None, description="Date when payment is due.")
    purchase_order_number: Optional[str] = Field(
        None, description="Associated Purchase Order (PO) number."
    )
    currency: Optional[str] = Field(
        None, description="Currency symbol or ISO code (e.g. USD, INR, EUR)."
    )
    subtotal: Optional[float] = Field(
        None, description="Subtotal amount before taxes and discounts."
    )
    tax_amount: Optional[float] = Field(None, description="Total tax amount applied.")
    discount_amount: Optional[float] = Field(None, description="Total discount amount applied.")
    total_amount: Optional[float] = Field(
        None, description="Grand total amount due for payment."
    )
    payment_terms: Optional[str] = Field(
        None, description="Payment terms description (e.g. Net 30, Due on Receipt)."
    )
    bank_details: Optional[str] = Field(
        None, description="Bank account numbers, routing numbers, or transfer details."
    )
    line_items: List[InvoiceLineItem] = Field(
        default=[], description="List of individual itemized charges."
    )

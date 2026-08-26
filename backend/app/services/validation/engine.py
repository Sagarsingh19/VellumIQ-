import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.invoice import InvoiceExtractionSchema

logger = logging.getLogger(__name__)


class ValidationError(BaseModel):
    rule_name: str
    message: str
    severity: str = "ERROR"  # "ERROR" or "WARNING"


class ValidationOutput(BaseModel):
    is_valid: bool
    errors: List[ValidationError] = Field(default=[])


class InvoiceValidationEngine:
    @staticmethod
    def validate(invoice: InvoiceExtractionSchema) -> ValidationOutput:
        """Executes all deterministic validation rules on an extracted invoice."""
        logger.info("Executing invoice validation rules.")
        errors: List[ValidationError] = []

        # Rule 1: Validate required fields are present
        InvoiceValidationEngine._check_required_fields(invoice, errors)

        # Rule 2: Validate Invoice and Due dates sanity
        InvoiceValidationEngine._check_dates(invoice, errors)

        # Rule 3: Validate Subtotal + Tax - Discount = Total
        InvoiceValidationEngine._check_totals_arithmetic(invoice, errors)

        # Rule 4: Validate Line Item math: quantity * unit_price = total
        InvoiceValidationEngine._check_line_items_arithmetic(invoice, errors)

        # Rule 5: Validate sum of line item totals equals subtotal
        InvoiceValidationEngine._check_line_items_sum(invoice, errors)

        # is_valid is True only if there are no errors with "ERROR" severity
        is_valid = not any(err.severity == "ERROR" for err in errors)
        
        return ValidationOutput(is_valid=is_valid, errors=errors)

    @staticmethod
    def _check_required_fields(invoice: InvoiceExtractionSchema, errors: List[ValidationError]):
        required_fields = {
            "vendor_name": "Vendor Name",
            "invoice_number": "Invoice Number",
            "invoice_date": "Invoice Date",
            "total_amount": "Total Amount",
        }
        for field, label in required_fields.items():
            value = getattr(invoice, field, None)
            if value is None or str(value).strip() == "":
                errors.append(
                    ValidationError(
                        rule_name="REQUIRED_FIELD_MISSING",
                        message=f"Required field '{label}' is missing or empty.",
                        severity="ERROR",
                    )
                )

    @staticmethod
    def _check_dates(invoice: InvoiceExtractionSchema, errors: List[ValidationError]):
        if invoice.invoice_date and invoice.due_date:
            if invoice.due_date < invoice.invoice_date:
                errors.append(
                    ValidationError(
                        rule_name="DUE_DATE_BEFORE_INVOICE_DATE",
                        message=f"Due date ({invoice.due_date}) cannot occur before invoice date ({invoice.invoice_date}).",
                        severity="ERROR",
                    )
                )

    @staticmethod
    def _check_totals_arithmetic(invoice: InvoiceExtractionSchema, errors: List[ValidationError]):
        # Calculate subtotal, tax, discount, total defaults
        subtotal = invoice.subtotal or 0.0
        tax = invoice.tax_amount or 0.0
        discount = invoice.discount_amount or 0.0
        total = invoice.total_amount or 0.0

        expected_total = round(subtotal + tax - discount, 2)
        actual_total = round(total, 2)

        # Use absolute tolerance threshold of 0.05 to account for rounding differences
        if abs(expected_total - actual_total) > 0.05:
            errors.append(
                ValidationError(
                    rule_name="ARITHMETIC_TOTAL_MISMATCH",
                    message=(
                        f"Invoice grand total mismatch: Subtotal ({subtotal}) + Tax ({tax}) "
                        f"- Discount ({discount}) = expected total {expected_total:.2f}, "
                        f"but got actual total {actual_total:.2f}."
                    ),
                    severity="ERROR",
                )
            )

    @staticmethod
    def _check_line_items_arithmetic(invoice: InvoiceExtractionSchema, errors: List[ValidationError]):
        for idx, item in enumerate(invoice.line_items):
            if item.quantity is not None and item.unit_price is not None:
                item_total = item.total or 0.0
                expected_item_total = round(item.quantity * item.unit_price, 2)
                actual_item_total = round(item_total, 2)

                if abs(expected_item_total - actual_item_total) > 0.05:
                    errors.append(
                        ValidationError(
                            rule_name="LINE_ITEM_MATH_MISMATCH",
                            message=(
                                f"Line item {idx + 1} arithmetic mismatch: Qty ({item.quantity}) "
                                f"* Unit Price ({item.unit_price}) = expected total {expected_item_total:.2f}, "
                                f"but got actual total {actual_item_total:.2f}."
                            ),
                            severity="ERROR",
                        )
                    )

    @staticmethod
    def _check_line_items_sum(invoice: InvoiceExtractionSchema, errors: List[ValidationError]):
        if invoice.line_items:
            expected_subtotal = round(sum(item.total for item in invoice.line_items if item.total is not None), 2)
            actual_subtotal = round(invoice.subtotal or 0.0, 2)

            if abs(expected_subtotal - actual_subtotal) > 0.05:
                # If there are items but they don't add up to the subtotal
                errors.append(
                    ValidationError(
                        rule_name="LINE_ITEMS_SUM_MISMATCH",
                        message=(
                            f"Sum of line items ({expected_subtotal:.2f}) does not match "
                            f"invoice subtotal ({actual_subtotal:.2f})."
                        ),
                        severity="WARNING",  # Set as WARNING since some invoices omit lines or contain rounding buffers
                    )
                )

import logging
from typing import Dict, Any, Optional
from app.services.validation.engine import ValidationOutput

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    @staticmethod
    def calculate_confidence(
        extracted_fields: Dict[str, Any],
        model_confidence_scores: Dict[str, float],
        validation_output: ValidationOutput,
        avg_ocr_confidence: Optional[float] = 1.0,
    ) -> Dict[str, Any]:
        """Calculates combined confidence scores per field and an overall document confidence rating.

        Combines model signals, OCR results, and programmatic validation checks.
        """
        logger.info("Calculating confidence scores.")
        
        # 1. Initialize per-field confidence from the model inputs (defaulting to 0.95)
        field_scores: Dict[str, float] = {}
        for key, val in extracted_fields.items():
            if val is not None:
                # Get the initial score, default to 0.95 if missing
                field_scores[key] = model_confidence_scores.get(key, 0.95)

        # 2. Scale scores based on OCR extraction quality
        ocr_factor = avg_ocr_confidence or 1.0
        if ocr_factor < 0.90:
            # Deduct confidence if OCR characters are generally fuzzy or low quality
            deduction = 0.05
            logger.warning(f"OCR average confidence is low ({ocr_factor:.2f}). Applying {deduction} deduction.")
            for key in field_scores:
                field_scores[key] = max(0.0, field_scores[key] - deduction)

        # 3. Apply deductions based on programmatic validation errors
        for error in validation_output.errors:
            rule = error.rule_name
            
            if rule == "REQUIRED_FIELD_MISSING":
                # Missing required field has 0 confidence
                pass
            
            elif rule == "DUE_DATE_BEFORE_INVOICE_DATE":
                # Deduct heavily from date fields
                for date_field in ["invoice_date", "due_date"]:
                    if date_field in field_scores:
                        field_scores[date_field] = max(0.0, field_scores[date_field] - 0.4)
            
            elif rule == "ARITHMETIC_TOTAL_MISMATCH":
                # Deduct from financial total fields
                for total_field in ["subtotal", "tax_amount", "discount_amount", "total_amount"]:
                    if total_field in field_scores:
                        field_scores[total_field] = max(0.0, field_scores[total_field] - 0.40)
            
            elif rule == "LINE_ITEM_MATH_MISMATCH":
                # Deduct from line items field
                if "line_items" in field_scores:
                    field_scores["line_items"] = max(0.0, field_scores["line_items"] - 0.30)
            
            elif rule == "LINE_ITEMS_SUM_MISMATCH":
                # Deduct slightly from subtotal and line items
                for field in ["subtotal", "line_items"]:
                    if field in field_scores:
                        field_scores[field] = max(0.0, field_scores[field] - 0.15)

        # Round all field confidence scores to two decimal places
        for key in field_scores:
            field_scores[key] = round(field_scores[key], 2)

        # 4. Calculate overall document-level confidence
        # Average of all populated fields' confidence scores
        if field_scores:
            overall_confidence = round(sum(field_scores.values()) / len(field_scores), 2)
        else:
            overall_confidence = 0.0

        return {
            "document_confidence": overall_confidence,
            "field_confidence": field_scores,
        }

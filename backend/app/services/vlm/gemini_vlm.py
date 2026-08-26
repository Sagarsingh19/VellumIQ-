import logging
import os
import re
from typing import List, Type, TypeVar
from pydantic import BaseModel

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings
from app.services.vlm.base import BaseVLMExtractor

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiVLMExtractor(BaseVLMExtractor):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.use_live = self.api_key and self.api_key != "mock_key"
        
        if self.use_live:
            self.client = genai.Client(api_key=self.api_key)
            # Default model for document analysis
            self.model_name = "gemini-2.0-flash"
        else:
            logger.info("Initializing GeminiVLMExtractor with MOCK fallback mode.")

    def extract_structured_data(
        self, image_paths: List[str], ocr_text: str, schema_class: Type[T]
    ) -> T:
        """Sends document images and OCR text to Gemini VLM and parses the structured response."""
        if not self.use_live:
            return self._generate_mock_extraction(ocr_text, schema_class)

        logger.info(f"Invoking Gemini VLM ({self.model_name}) for structured extraction.")
        contents = []
        
        # 1. Add instructions and OCR context
        prompt = (
            "Analyze the attached document page images and OCR layout text.\n"
            "Extract all available fields and items according to the requested schema.\n"
            "Ensure amounts, dates, and names are read accurately.\n\n"
            f"--- OCR TEXT REFERENCE ---\n{ocr_text}\n---------------------------"
        )
        contents.append(prompt)
        
        # 2. Add page images
        for path in image_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    img_bytes = f.read()
                contents.append(
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                )
            else:
                logger.warning(f"VLM Page image path not found: {path}")

        try:
            # 3. Call Gemini using Pydantic schema validation
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema_class,
                ),
            )
            # 4. Parse the structured JSON response into Pydantic model
            json_text = response.text
            return schema_class.model_validate_json(json_text)
            
        except APIError as e:
            logger.error(f"Gemini API Exception: {str(e)}")
            raise RuntimeError(f"Gemini VLM call failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error in Gemini VLM extraction: {str(e)}")
            raise e

    def _generate_mock_extraction(self, ocr_text: str, schema_class: Type[T]) -> T:
        """Heuristic regex parser that mocks Gemini VLM by reading fields directly from OCR text."""
        logger.info("Running Mock VLM heuristic extraction.")
        
        # Default mock fallback data
        data = {
            "vendor_name": "Acme Corp",
            "vendor_address": "123 Industrial Way, Tech City",
            "vendor_tax_id": None,
            "invoice_number": "INV-MOCK-999",
            "invoice_date": None,
            "due_date": None,
            "currency": "USD",
            "subtotal": 1500.00,
            "tax_amount": 150.00,
            "discount_amount": 0.0,
            "total_amount": 1650.00,
            "line_items": []
        }
        
        # 1. Parse Invoice Number
        inv_match = re.search(r"Invoice\s+Number:\s*(\S+)", ocr_text, re.IGNORECASE)
        if not inv_match:
            inv_match = re.search(r"INV-\d+", ocr_text)
        if inv_match:
            data["invoice_number"] = inv_match.group(1) if len(inv_match.groups()) > 0 else inv_match.group(0)

        # 2. Parse Vendor Name
        vendor_match = re.search(r"Vendor:\s*([^\n]+)", ocr_text, re.IGNORECASE)
        if vendor_match:
            data["vendor_name"] = vendor_match.group(1).strip()

        # 3. Parse Totals
        subtotal_match = re.search(r"Subtotal:\s*(\d+\.?\d*)", ocr_text, re.IGNORECASE)
        if subtotal_match:
            data["subtotal"] = float(subtotal_match.group(1))

        tax_match = re.search(r"Tax(?:\s*\(?\d*%\)?)?:\s*(\d+\.?\d*)", ocr_text, re.IGNORECASE)
        if tax_match:
            data["tax_amount"] = float(tax_match.group(1))

        total_match = re.search(r"Total\s*Due:\s*(\d+\.?\d*)", ocr_text, re.IGNORECASE)
        if not total_match:
            total_match = re.search(r"Total:\s*(\d+\.?\d*)", ocr_text, re.IGNORECASE)
        if total_match:
            data["total_amount"] = float(total_match.group(1))

        # 4. Parse Date values
        date_match = re.search(r"Invoice\s+Date:\s*(\d{4}-\d{2}-\d{2})", ocr_text, re.IGNORECASE)
        if date_match:
            data["invoice_date"] = date_match.group(1)

        due_match = re.search(r"Due\s+Date:\s*(\d{4}-\d{2}-\d{2})", ocr_text, re.IGNORECASE)
        if due_match:
            data["due_date"] = due_match.group(1)

        # Return validated Pydantic model
        return schema_class.model_validate(data)

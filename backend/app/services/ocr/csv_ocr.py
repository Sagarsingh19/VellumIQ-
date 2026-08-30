import csv
import logging
from typing import Dict, Any, List

from app.schemas.ocr import OCRResult, OCRPage, OCRWord

logger = logging.getLogger(__name__)

class CSVParserEngine:
    """Parser engine that extracts structured financial data and layout metadata from CSV files."""

    def extract_text(self, file_path: str) -> OCRResult:
        """Reads a CSV file and constructs structured fields and word coordinate data."""
        logger.info(f"Parsing CSV document from path: {file_path}")
        
        rows = []
        headers = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if idx == 0:
                    headers = [h.strip().lower() for h in row]
                else:
                    rows.append(row)

        if not headers:
            return {
                "pages": [{
                    "page_number": 1,
                    "width": 612,
                    "height": 792,
                    "text": "",
                    "words": []
                }],
                "raw_text": "",
                "extracted_fields": {}
            }

        # Build extracted fields map from headers and first data row
        extracted_fields: Dict[str, Any] = {}
        line_items: List[Dict[str, Any]] = []

        first_row = rows[0] if rows else []
        row_dict = {headers[i]: first_row[i].strip() for i in range(min(len(headers), len(first_row)))}

        def find_val(keys: List[str]) -> Any:
            # 1. Exact header name match first
            for k in keys:
                for hk, val in row_dict.items():
                    if hk == k:
                        return val
            # 2. Substring match fallback (excluding 'total' matching 'subtotal')
            for k in keys:
                for hk, val in row_dict.items():
                    if k in hk:
                        if k == "total" and "subtotal" in hk:
                            continue
                        return val
            return None

        # Vendor Name
        vendor = find_val(["vendor", "company", "supplier", "merchant", "biller"])
        if vendor:
            extracted_fields["vendor_name"] = vendor

        # Invoice Number
        inv_num = find_val(["invoice", "inv", "bill_no", "doc_num", "number"])
        if inv_num:
            extracted_fields["invoice_number"] = inv_num

        # Dates
        inv_date = find_val(["invoice_date", "date", "bill_date"])
        if inv_date:
            extracted_fields["invoice_date"] = inv_date

        due_date = find_val(["due_date", "due"])
        if due_date:
            extracted_fields["due_date"] = due_date

        # Financial Totals helper
        def parse_float(val: Any) -> float:
            if not val:
                return 0.0
            cleaned = str(val).replace("$", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        subtotal_val = find_val(["subtotal", "sub_total", "amount_before_tax"])
        tax_val = find_val(["tax", "vat", "gst", "tax_amount"])
        discount_val = find_val(["discount", "disc", "discount_amount"])
        total_val = find_val(["total", "grand_total", "amount_due", "total_amount"])

        if subtotal_val is not None:
            extracted_fields["subtotal"] = parse_float(subtotal_val)
        if tax_val is not None:
            extracted_fields["tax_amount"] = parse_float(tax_val)
        if discount_val is not None:
            extracted_fields["discount_amount"] = parse_float(discount_val)
        if total_val is not None:
            extracted_fields["total_amount"] = parse_float(total_val)

        # Parse Line Items from subsequent rows if tabular
        for r_idx, r in enumerate(rows):
            r_map = {headers[i]: r[i].strip() for i in range(min(len(headers), len(r)))}
            item_desc = None
            for k in ["item", "description", "product", "title", "name"]:
                for hk, val in r_map.items():
                    if k in hk:
                        item_desc = val
                        break

            if item_desc:
                qty = parse_float(r_map.get("quantity") or r_map.get("qty") or 1)
                unit_price = parse_float(r_map.get("unit_price") or r_map.get("price") or 0)
                total = parse_float(r_map.get("line_total") or r_map.get("amount") or r_map.get("item_total") or (qty * unit_price))
                line_items.append({
                    "description": item_desc,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_amount": total
                })

        if line_items:
            extracted_fields["line_items"] = line_items

        # Construct raw text and pseudo OCR word coordinates for UI rendering
        raw_lines = [", ".join(headers)] + [", ".join(r) for r in rows]
        full_raw_text = "\n".join(raw_lines)

        words = []
        y_offset = 50
        for line in raw_lines[:20]:  # Cap first 20 lines for preview
            line_words = line.split()
            x_offset = 50
            for w in line_words:
                words.append(OCRWord(
                    text=w,
                    bbox=[x_offset, y_offset, x_offset + (len(w) * 8), y_offset + 14],
                    confidence=1.0
                ))
                x_offset += (len(w) * 8) + 6
            y_offset += 20

        page = OCRPage(
            page_number=1,
            width=612.0,
            height=792.0,
            text=full_raw_text,
            words=words
        )
        
        return OCRResult(pages=[page], extracted_fields=extracted_fields)

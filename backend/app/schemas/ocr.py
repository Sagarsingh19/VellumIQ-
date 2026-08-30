from typing import List, Optional
from pydantic import BaseModel, Field


class OCRWord(BaseModel):
    text: str
    bbox: List[float] = Field(
        ...,
        description="Bounding box coordinates in [x0, y0, x1, y1] format, normally normalized to page width/height.",
    )
    confidence: Optional[float] = Field(
        None, description="Confidence score between 0.0 and 1.0."
    )


class OCRLine(BaseModel):
    text: str
    bbox: List[float] = Field(..., description="Line-level bounding box [x0, y0, x1, y1]")
    words: List[OCRWord] = Field(default=[], description="Words making up this line")


class OCRPage(BaseModel):
    page_number: int
    width: float = Field(..., description="Page width in points or pixels")
    height: float = Field(..., description="Page height in points or pixels")
    lines: List[OCRLine] = Field(default=[], description="Lines of text extracted from this page")
    text: str = Field(..., description="Full text content of this page")


class OCRResult(BaseModel):
    pages: List[OCRPage] = Field(..., description="List of pages processed")
    extracted_fields: Optional[dict] = Field(default=None, description="Optional extracted fields dictionary for structured formats like CSV")

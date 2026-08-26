from abc import ABC, abstractmethod
from app.schemas.ocr import OCRResult


class BaseOCREngine(ABC):
    @abstractmethod
    def extract_text(self, file_path: str) -> OCRResult:
        """Extracts structured text, bounding boxes, and coordinates from a document file."""
        pass

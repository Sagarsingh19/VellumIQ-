from abc import ABC, abstractmethod
from typing import List, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseVLMExtractor(ABC):
    @abstractmethod
    def extract_structured_data(
        self, image_paths: List[str], ocr_text: str, schema_class: Type[T]
    ) -> T:
        """Sends document images and OCR layout text to the VLM and extracts structured data matching the schema."""
        pass

from sqlalchemy import Column, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class ExtractionResult(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "extraction_results"

    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    raw_model_response = Column(JSON, nullable=True)
    extracted_fields = Column(JSON, nullable=False)  # Key-value JSON of extracted data
    field_confidence = Column(JSON, nullable=False)  # Confidence score mapping [0,1] per field

    # Relationships
    document = relationship("Document", back_populates="extraction_result")

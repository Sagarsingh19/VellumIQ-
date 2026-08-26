from sqlalchemy import Column, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class ValidationResult(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "validation_results"

    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_errors = Column(JSON, default=list, nullable=False)  # List of validation issues

    # Relationships
    document = relationship("Document", back_populates="validation_result")

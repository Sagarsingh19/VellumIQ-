from sqlalchemy import Column, ForeignKey, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class Review(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reviews"

    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    reviewed_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    original_fields = Column(JSON, nullable=False)
    corrected_fields = Column(JSON, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, COMPLETED
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    document = relationship("Document", back_populates="review")
    reviewed_by = relationship("User", back_populates="reviews")

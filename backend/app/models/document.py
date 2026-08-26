from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    page_count = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="UPLOADED", nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="documents")
    uploaded_by = relationship("User", back_populates="uploaded_documents")
    pages = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    extraction_result = relationship(
        "ExtractionResult", back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    validation_result = relationship(
        "ValidationResult", back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    review = relationship(
        "Review", back_populates="document", uselist=False, cascade="all, delete-orphan"
    )

from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class DocumentPage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_pages"

    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    page_number = Column(Integer, nullable=False)
    image_storage_path = Column(String(512), nullable=False)
    ocr_data = Column(JSON, nullable=True)  # Stores bounding boxes, raw text tokens

    # Relationships
    document = relationship("Document", back_populates="pages")

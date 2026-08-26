from sqlalchemy import Column, String, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class UsageEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "usage_events"

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type = Column(String(100), nullable=False)  # e.g., 'ocr_pages', 'vlm_tokens', 'api_calls'
    quantity = Column(Integer, default=1, nullable=False)
    estimated_cost = Column(Numeric(10, 4), default=0.0000, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="usage_events")

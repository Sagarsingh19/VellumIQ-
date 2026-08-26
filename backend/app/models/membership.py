from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class Membership(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "memberships"

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(50), default="member", nullable=False)  # owner, admin, reviewer, member

    # Relationships
    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

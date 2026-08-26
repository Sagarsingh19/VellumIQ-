from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)

    # Relationships
    memberships = relationship(
        "Membership", back_populates="organization", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="organization", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="organization", cascade="all, delete-orphan"
    )
    usage_events = relationship(
        "UsageEvent", back_populates="organization", cascade="all, delete-orphan"
    )

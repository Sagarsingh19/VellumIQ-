from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)
    plan_tier = Column(String(50), default="FREE", nullable=False)
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)
    monthly_page_limit = Column(Integer, default=100, nullable=False)
    subscription_active = Column(Boolean, default=True, nullable=False)

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
    api_keys = relationship(
        "ApiKey", back_populates="organization", cascade="all, delete-orphan"
    )

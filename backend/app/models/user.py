from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Relationships
    memberships = relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan"
    )
    uploaded_documents = relationship(
        "Document", back_populates="uploaded_by", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    reviews = relationship("Review", back_populates="reviewed_by")

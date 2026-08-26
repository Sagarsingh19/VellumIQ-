import decimal
import logging
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.usage_event import UsageEvent

logger = logging.getLogger(__name__)


class UsageTracker:
    @staticmethod
    def log_ocr_pages(
        db: Session,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        page_count: int,
    ) -> UsageEvent:
        """Logs page count usage event and calculates the estimated OCR processing cost."""
        cost = decimal.Decimal(page_count) * decimal.Decimal("0.0100")
        event = UsageEvent(
            organization_id=organization_id,
            user_id=user_id,
            event_type="ocr_pages",
            quantity=page_count,
            estimated_cost=cost,
        )
        db.add(event)
        db.commit()
        logger.info(f"Logged OCR usage event for org {organization_id}: {page_count} pages, cost: ${cost}")
        return event

    @staticmethod
    def log_vlm_extraction(
        db: Session,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
    ) -> UsageEvent:
        """Logs document extraction event and calculates the estimated VLM parsing cost."""
        cost = decimal.Decimal("0.0500")
        event = UsageEvent(
            organization_id=organization_id,
            user_id=user_id,
            event_type="vlm_extractions",
            quantity=1,
            estimated_cost=cost,
        )
        db.add(event)
        db.commit()
        logger.info(f"Logged VLM usage event for org {organization_id}: 1 extraction, cost: ${cost}")
        return event

import datetime
import logging
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.organization import Organization
from app.models.usage_event import UsageEvent

logger = logging.getLogger(__name__)


def check_quota(db: Session, organization_id: uuid.UUID, incoming_pages: int = 1) -> bool:
    """Checks if the organization has sufficient page processing quota remaining for the current month.

    Returns True if quota is available, False otherwise.
    """
    logger.info(f"Checking page quota for organization: {organization_id}")
    
    # 1. Fetch organization subscription settings
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        logger.error(f"Organization {organization_id} not found during quota check.")
        return False
        
    if not org.subscription_active:
        logger.warning(f"Organization {organization_id} subscription is INACTIVE. Quota rejected.")
        return False

    # 2. Compute start of current calendar month
    now = datetime.datetime.now()
    start_of_month = datetime.datetime(now.year, now.month, 1)

    # 3. Sum up all 'ocr_pages' usage events since start of month
    used_pages_query = (
        db.query(func.sum(UsageEvent.quantity))
        .filter(
            UsageEvent.organization_id == organization_id,
            UsageEvent.event_type == "ocr_pages",
            UsageEvent.created_at >= start_of_month,
        )
        .scalar()
    )
    
    used_pages = used_pages_query or 0
    remaining_quota = org.monthly_page_limit - used_pages

    logger.info(
        f"Org: {organization_id} ({org.plan_tier}). Limit: {org.monthly_page_limit}. "
        f"Used: {used_pages}. Remaining: {remaining_quota}. Requested: {incoming_pages}"
    )

    if used_pages + incoming_pages > org.monthly_page_limit:
        logger.warning(f"Organization {organization_id} has exceeded its page quota limit!")
        return False

    return True


async def check_quota_async(db: AsyncSession, organization_id: uuid.UUID, incoming_pages: int = 1) -> bool:
    """Checks if the organization has sufficient page processing quota remaining (Asynchronous)."""
    logger.info(f"Checking page quota async for organization: {organization_id}")
    
    # 1. Fetch organization
    org_res = await db.execute(select(Organization).where(Organization.id == organization_id))
    org = org_res.scalars().first()
    if not org:
        logger.error(f"Organization {organization_id} not found during quota check.")
        return False
        
    if not org.subscription_active:
        logger.warning(f"Organization {organization_id} subscription is INACTIVE. Quota rejected.")
        return False

    # 2. Get current month
    now = datetime.datetime.now()
    start_of_month = datetime.datetime(now.year, now.month, 1)

    # 3. Sum up pages
    result = await db.execute(
        select(func.sum(UsageEvent.quantity))
        .where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.event_type == "ocr_pages",
            UsageEvent.created_at >= start_of_month
        )
    )
    used_pages = result.scalar() or 0
    remaining_quota = org.monthly_page_limit - used_pages

    logger.info(
        f"Org Async: {organization_id} ({org.plan_tier}). Limit: {org.monthly_page_limit}. "
        f"Used: {used_pages}. Remaining: {remaining_quota}. Requested: {incoming_pages}"
    )

    if used_pages + incoming_pages > org.monthly_page_limit:
        logger.warning(f"Organization {organization_id} has exceeded its page quota limit!")
        return False

    return True

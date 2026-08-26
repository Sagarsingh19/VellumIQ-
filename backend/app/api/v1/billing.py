import json
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import stripe

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_organization_membership
from app.models.organization import Organization
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

# Plan definitions
PLAN_LIMITS = {
    "FREE": 100,
    "GROWTH": 1000,
    "ENTERPRISE": 10000,
}

# Stripe Mock Price IDs (in real setup these correspond to Stripe dashboard product price IDs)
PLAN_PRICES = {
    "GROWTH": "price_mock_growth_subscription",
    "ENTERPRISE": "price_mock_enterprise_subscription",
}


@router.post("/checkout")
async def create_checkout_session(
    organization_id: uuid.UUID,
    plan_tier: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a Stripe Checkout Session for subscription upgrades."""
    await get_current_organization_membership(
        organization_id=organization_id, db=db, current_user=current_user
    )

    plan_upper = plan_tier.upper()
    if plan_upper not in PLAN_PRICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subscription plan tier. Choose from: {list(PLAN_PRICES.keys())}",
        )

    # 1. Check if mock key is active to simulate checkout
    if settings.STRIPE_SECRET_KEY == "sk_test_mock":
        mock_checkout_url = f"https://checkout.stripe.com/pay/mock_session_{uuid.uuid4()}"
        logger.info(f"Generated Mock Stripe Checkout Session URL for org {organization_id}: {mock_checkout_url}")
        return {
            "session_id": f"cs_mock_{uuid.uuid4().hex[:12]}",
            "checkout_url": mock_checkout_url,
            "mock": True
        }

    try:
        # 2. Build live Stripe checkout session details
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": PLAN_PRICES[plan_upper],
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url="https://vellumiq.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://vellumiq.com/billing/cancel",
            metadata={
                "organization_id": str(organization_id),
                "plan_tier": plan_upper,
            },
        )
        return {
            "session_id": checkout_session.id,
            "checkout_url": checkout_session.url,
            "mock": False
        }
    except Exception as e:
        logger.error(f"Stripe Checkout Session generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stripe checkout integration failure: {str(e)}",
        )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receives and processes incoming events from Stripe webhook deliveries."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None

    # 1. Process Stripe Webhook signature verification
    if settings.STRIPE_SECRET_KEY == "sk_test_mock":
        # Bypass signature verification in local mock testing environment
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mock webhook payload JSON."
            )
    else:
        # Standard signature verification in production/live environments
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header."
            )
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook signature validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature verification."
            )
        except Exception as e:
            logger.error(f"Stripe Webhook parser failure: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    event_type = event.get("type")
    logger.info(f"Received Stripe webhook event: {event_type}")

    # 2. Handle completed checkout sessions (Successful Subscriptions)
    if event_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        metadata = session_obj.get("metadata", {})
        
        org_id_str = metadata.get("organization_id")
        plan_tier = metadata.get("plan_tier")
        
        if org_id_str and plan_tier:
            org_id = uuid.UUID(org_id_str)
            result = await db.execute(select(Organization).where(Organization.id == org_id))
            org = result.scalars().first()
            if org:
                # Update subscription details
                org.plan_tier = plan_tier
                org.stripe_customer_id = session_obj.get("customer")
                org.stripe_subscription_id = session_obj.get("subscription")
                org.monthly_page_limit = PLAN_LIMITS.get(plan_tier, 100)
                org.subscription_active = True
                
                db.add(org)
                await db.commit()
                logger.info(f"Successfully upgraded Organization {org_id} to plan {plan_tier} via Stripe Webhook.")

    # 3. Handle canceled/expired subscriptions
    elif event_type in ["customer.subscription.deleted", "customer.subscription.updated"]:
        sub_obj = event["data"]["object"]
        stripe_sub_id = sub_obj.get("id")
        status = sub_obj.get("status")
        
        if stripe_sub_id:
            result = await db.execute(
                select(Organization).where(Organization.stripe_subscription_id == stripe_sub_id)
            )
            org = result.scalars().first()
            if org:
                # Mark as inactive if subscription state is not active/trialing
                if status not in ["active", "trialing"]:
                    org.subscription_active = False
                    db.add(org)
                    await db.commit()
                    logger.info(f"Stripe Webhook: Marked sub {stripe_sub_id} as inactive for org {org.id}.")

    return {"status": "processed"}

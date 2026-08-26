import hashlib
import secrets
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_organization_membership
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyOut, ApiKeyCreatedOut

router = APIRouter()


@router.post("", response_model=ApiKeyCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    organization_id: uuid.UUID,
    key_in: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates a new secure API key for the organization."""
    # Validate user is a member of the organization
    await get_current_organization_membership(
        organization_id=organization_id, db=db, current_user=current_user
    )

    # 1. Generate unmasked key (e.g. vq_live_xxx)
    raw_token = secrets.token_urlsafe(32)
    raw_key = f"vq_live_{raw_token}"
    
    # 2. Generate SHA-256 hash for database matching
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    # 3. Generate masked representation for dashboard display
    masked_key = f"vq_live_...{raw_key[-6:]}"

    db_key = ApiKey(
        organization_id=organization_id,
        name=key_in.name,
        key_hash=key_hash,
        masked_key=masked_key,
        is_active=True,
    )
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)

    # Return output including raw_key (only shown once!)
    return ApiKeyCreatedOut(
        id=db_key.id,
        name=db_key.name,
        masked_key=db_key.masked_key,
        is_active=db_key.is_active,
        created_at=db_key.created_at,
        raw_key=raw_key,
    )


@router.get("", response_model=List[ApiKeyOut])
async def list_api_keys(
    organization_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all active and revoked API keys for the organization."""
    await get_current_organization_membership(
        organization_id=organization_id, db=db, current_user=current_user
    )

    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.organization_id == organization_id)
        .order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    organization_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revokes an API key, rendering it permanently inactive."""
    await get_current_organization_membership(
        organization_id=organization_id, db=db, current_user=current_user
    )

    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.organization_id == organization_id)
    )
    api_key = result.scalars().first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found."
        )

    # Disable the key (we retain it in DB for audit trail, but set is_active=False)
    api_key.is_active = False
    db.add(api_key)
    await db.commit()
    return None

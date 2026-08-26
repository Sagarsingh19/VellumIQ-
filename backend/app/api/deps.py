from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.membership import Membership
from app.schemas.auth import TokenPayload

import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_uuid = uuid.UUID(user_id_str)
        token_data = TokenPayload(sub=str(user_uuid))
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


from typing import Generator, Union

async def get_current_organization_membership(
    organization_id: Union[uuid.UUID, str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Membership:
    if isinstance(organization_id, str):
        try:
            org_uuid = uuid.UUID(organization_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID format."
            )
    else:
        org_uuid = organization_id

    result = await db.execute(
        select(Membership).where(
            Membership.organization_id == org_uuid,
            Membership.user_id == current_user.id,
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization",
        )
    return membership


import hashlib
from typing import Optional
from fastapi.security import APIKeyHeader, APIKeyQuery
from fastapi import Security
from app.models.api_key import ApiKey

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_current_user_optional(
    db: AsyncSession = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        user_uuid = uuid.UUID(user_id_str)
        result = await db.execute(select(User).where(User.id == user_uuid))
        return result.scalars().first()
    except (JWTError, ValueError):
        return None


async def verify_tenant_access(
    organization_id: uuid.UUID,
    api_key_hdr: Optional[str] = Security(api_key_header),
    api_key_qry: Optional[str] = Security(api_key_query),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Verifies that the request has access to the specified organization_id.

    Accepts EITHER a valid active API Key for that organization OR a logged-in User who is a member of the organization.
    """
    token = api_key_hdr or api_key_qry
    if token:
        # 1. API Key authentication path
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.organization_id == organization_id,
                ApiKey.is_active == True
            )
        )
        api_key = result.scalars().first()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API Key for this organization."
            )
        return organization_id

    if current_user:
        # 2. JWT authentication path
        await get_current_organization_membership(
            organization_id=organization_id, db=db, current_user=current_user
        )
        return organization_id

    # 3. No authentication supplied
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials missing. Provide a valid Bearer Token or X-API-Key."
    )

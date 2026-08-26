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

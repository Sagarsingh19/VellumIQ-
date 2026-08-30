from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership
from app.schemas.auth import UserCreate, UserResponse, Token, LoginResponse

router = APIRouter()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Sign up a new user, automatically creating their default organization."""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # Create user
    hashed_password = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_password)
    db.add(new_user)
    await db.flush()  # Flush to get the new_user.id

    # Create default organization
    org_name = user_in.organization_name or f"{user_in.email.split('@')[0]}'s Org"
    default_org = Organization(name=org_name)
    db.add(default_org)
    await db.flush()  # Flush to get default_org.id

    # Create owner membership
    membership = Membership(
        organization_id=default_org.id, user_id=new_user.id, role="owner"
    )
    db.add(membership)

    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """OAuth2 password flow token acquisition."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    # Query organization memberships
    mem_result = await db.execute(
        select(Membership)
        .where(Membership.user_id == user.id)
        .options(selectinload(Membership.organization))
    )
    memberships = mem_result.scalars().all()

    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
        "memberships": memberships
    }

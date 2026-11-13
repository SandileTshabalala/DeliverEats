from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password
from app.core.roles import Role
from app.core.redis import get_async_redis

def create_user(
    db: Session,
    name: str,
    sur_name: str,
    email: str,
    password: str,
    contact_number: int,
    role: Role = Role.CUSTOMER
):
    user = User(
        name=name,
        sur_name=sur_name,
        email=email,
        password_hash=hash_password(password),
        contact_number=contact_number,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_id(db: Session, user_id: str):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

async def update_user(db: Session, user_id: str, update_data: dict):
    """
    Update a user's details and invalidate their Redis cache.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    new_email = update_data.get("email")
    if new_email and new_email != user.email:
        if db.query(User).filter(User.email == new_email, User.id != user_id).first():
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="That email address is already used by another account")

    # Update fields
    for key, value in update_data.items():
        if hasattr(user, key) and value is not None:
            # Hash password if it's being updated
            if key == "password":
                setattr(user, "password_hash", hash_password(value))
            else:
                setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    
    # Invalidate cache
    redis = await get_async_redis()
    await redis.delete(f"user_profile:{user_id}")
    
    return user

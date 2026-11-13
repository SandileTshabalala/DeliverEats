from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from app.models.user import User
from app.models.driver import Driver
from app.models.restaurant import Restaurant
from app.schemas.admin import (
    AdminUserUpdate, 
    AdminCreateUser, 
    AdminDriverCreate, 
    AdminRestaurantCreate
)
from app.core.security import hash_password
from app.core.roles import Role


class AdminService:

    @staticmethod
    def ensure_admin(user: User):
        if user.role != Role.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )

    @staticmethod
    def get_all_users(db: Session) -> List[User]:
        return db.query(User).all()

    @staticmethod
    def get_user_by_id(user_id: str, db: Session) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @staticmethod
    def update_user(
        user_id: str,
        payload: AdminUserUpdate,
        db: Session
    ) -> User:
        user = AdminService.get_user_by_id(user_id, db)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)
        AdminService._drop_user_cache(user_id)
        return user

    @staticmethod
    def deactivate_user(user_id: str, db: Session):
        user = AdminService.get_user_by_id(user_id, db)
        user.is_active = False
        # A deactivated user must not keep working sessions
        from app.models.refresh_tokens import RefreshToken
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).update({"is_revoked": True})
        db.commit()
        AdminService._drop_user_cache(user_id)
        return {"message": "User deactivated"}

    @staticmethod
    def _drop_user_cache(user_id: str):
        try:
            from app.core.redis import redis_client
            redis_client.delete(f"lvovo:user_profile:{user_id}")
        except Exception:
            pass

    @staticmethod
    def create_admin_user(
        payload: AdminCreateUser,
        db: Session
    ) -> User:
        exists = db.query(User).filter(User.email == payload.email).first()
        if exists:
            # If user exists but is not active, we might want to reactivate? 
            # For now, just error.
            raise HTTPException(status_code=400, detail="Email already exists")

        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            name=payload.name,
            sur_name=payload.sur_name,
            contact_number=payload.contact_number,
            role=payload.role,
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def create_driver_user(
        payload: AdminDriverCreate,
        db: Session
    ) -> User:
        # Create User first
        user = AdminService.create_admin_user(
            AdminCreateUser(
                email=payload.email,
                password=payload.password,
                name=payload.name,
                sur_name=payload.sur_name,
                contact_number=payload.contact_number,
                role=Role.DRIVER
            ),
            db
        )
        
        # Create Driver profile
        driver = Driver(
            id=user.id,
            vehicle_type=payload.vehicle_type,
            vehicle_number=payload.vehicle_number,
            restaurant_id=payload.restaurant_id,
            is_available=True
        )
        db.add(driver)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def create_restaurant_with_admin(
        payload: AdminRestaurantCreate,
        db: Session
    ) -> Restaurant:
        # Create Restaurant Admin User
        admin_user = AdminService.create_admin_user(
            AdminCreateUser(
                email=payload.admin_email,
                password=payload.admin_password,
                name=payload.admin_name,
                sur_name=payload.admin_sur_name,
                contact_number=payload.admin_contact_number,
                role=Role.RESTAURANT_ADMIN
            ),
            db
        )

        # Create Restaurant
        restaurant = Restaurant(
            name=payload.name,
            address=payload.address,
            description=payload.description,
            admin_id=admin_user.id,
            is_active=True
        )
        db.add(restaurant)
        db.commit()
        db.refresh(restaurant)
        # The public restaurant list is cached in Redis for 60s
        try:
            from app.core.redis import redis_client
            redis_client.delete("lvovo:restaurants:list")
        except Exception:
            pass
        return restaurant

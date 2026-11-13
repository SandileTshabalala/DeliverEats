"""
One-off setup:  python -m app.db.init_db

Creates the tables and the FIRST platform owner account, taken from the
environment (ADMIN_EMAIL, ADMIN_PASSWORD, ...). There is deliberately no
built-in account: the old version created admin@lvovo.com / admin123, a login
anyone reading the code could use.
"""
import sys

from app.core.config import settings
from app.core.roles import Role
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
import app.models  # noqa: F401  (registers every table)
from app.models.user import User
from app.services.payment_service import ensure_default_payment_providers


def init_db() -> int:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        ensure_default_payment_providers(db)

        if db.query(User).filter(User.role == Role.SUPER_ADMIN).first():
            print("A platform owner account already exists. Nothing to do.")
            return 0

        missing = [name for name in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "ADMIN_CONTACT_NUMBER") if not getattr(settings, name)]
        if missing:
            print("Cannot create the platform owner account. Set these in the env file first: " + ", ".join(missing))
            return 1
        if len(settings.ADMIN_PASSWORD) < 12:
            print("ADMIN_PASSWORD must be at least 12 characters.")
            return 1

        db.add(User(
            name=settings.ADMIN_NAME,
            sur_name=settings.ADMIN_SURNAME,
            email=settings.ADMIN_EMAIL.strip().lower(),
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            contact_number=settings.ADMIN_CONTACT_NUMBER,
            role=Role.SUPER_ADMIN,
            is_active=True,
        ))
        db.commit()
        print(f"Platform owner account created for {settings.ADMIN_EMAIL}. "
              "You can now remove ADMIN_PASSWORD from the env file.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Error initializing database: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(init_db())

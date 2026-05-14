import sys
import os

# Add the server directory to Python path
server_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, server_dir)

# Import directly to avoid circular imports
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.core.security import hash_password
from app.core.roles import Role
from app.models.user import User
from sqlalchemy.orm import Session

def init_db():
    """Initialize database with tables and initial data"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    db = Session(engine)
    
    try:
        # Check if super admin exists
        super_admin = db.query(User).filter(User.role == Role.SUPER_ADMIN).first()
        
        if not super_admin:
            # Create initial super admin with shorter password
            admin_user = User(
                name="Super",
                sur_name="Admin",
                email="admin@lvovo.com",
                password_hash=hash_password("admin123"),  # Short password to avoid bcrypt limit
                contact_number="+1234567890",
                role=Role.SUPER_ADMIN,
                is_active=True
            )
            
            db.add(admin_user)
            db.commit()
            print("Super admin created successfully")
        else:
            print("Super admin already exists")
            
        # Seed default payment providers
        from app.models.payment_provider import PaymentProvider
        
        defaults = [
            {
                "provider_name": "cash_delivery",
                "display_name": "Cash on Delivery",
                "enabled": True,
                "is_active": True,
                "config": {}
            },
            {
                "provider_name": "card_delivery",
                "display_name": "Card on Delivery",
                "enabled": True,
                "is_active": True,
                "config": {}
            }
        ]
        
        for p in defaults:
            exists = db.query(PaymentProvider).filter(PaymentProvider.provider_name == p["provider_name"]).first()
            if not exists:
                new_p = PaymentProvider(**p)
                db.add(new_p)
                print(f"Seeded provider: {p['display_name']}")
        
        db.commit()
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
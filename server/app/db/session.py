from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Neon requires SSL, and pooling is handled by Neon itself
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,   # IMPORTANT for Neon
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
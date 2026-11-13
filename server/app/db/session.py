from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    # tests
    engine = create_engine(settings.DATABASE_URL, echo=False)
else:
    # Keep a few connections open and reuse them.
    #
    # This used to be NullPool ("pooling is handled by Neon"), which opened a new
    # TLS connection to the database for every single request: measured at 3-8
    # seconds per request. A small pool makes requests take milliseconds.
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=5,
        # Neon suspends idle databases and drops their connections: test a
        # connection before using it, and do not keep one for more than 5 minutes.
        pool_pre_ping=True,
        pool_recycle=300,
        pool_timeout=30,
        echo=False,
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

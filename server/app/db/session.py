import time

from sqlalchemy import create_engine, event, exc
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
        # Do not keep a connection longer than Neon keeps an idle database awake
        pool_recycle=240,
        pool_timeout=30,
        # Let the operating system notice a dropped connection by itself
        connect_args={"keepalives": 1, "keepalives_idle": 30, "keepalives_interval": 10, "keepalives_count": 3},
        echo=False,
    )

    # pool_pre_ping tested EVERY connection before EVERY request: one extra trip
    # to the database each time, which costs 300-500 ms when the database is far
    # away (Neon in the US). Only a connection that sat unused for a while can
    # have been dropped, so only those are tested; a dead one is replaced.
    IDLE_BEFORE_CHECK_SECONDS = 30

    @event.listens_for(engine, "checkin")
    def _remember_last_use(dbapi_connection, record):
        record.info["last_used"] = time.monotonic()

    @event.listens_for(engine, "checkout")
    def _check_if_it_was_idle(dbapi_connection, record, proxy):
        last_used = record.info.get("last_used")
        if last_used is None or time.monotonic() - last_used < IDLE_BEFORE_CHECK_SECONDS:
            return  # brand new, or used moments ago: it is alive
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            dbapi_connection.rollback()
        except Exception:
            # the pool throws this connection away and hands out a fresh one
            raise exc.DisconnectionError()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

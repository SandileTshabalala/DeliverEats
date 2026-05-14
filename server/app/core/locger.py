import logging
import os
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# Constants
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"
MAX_BYTES = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
# ----------------------------
# Ensure request_id exists
# ----------------------------
_old_factory = logging.getLogRecordFactory()

def record_factory(*args, **kwargs):
    record = _old_factory(*args, **kwargs)
    if not hasattr(record, "request_id"):
        record.request_id = "-"  # default if not provided
    return record

logging.setLogRecordFactory(record_factory)
 
def setup_logging() -> None:
    """Initialize logging configuration."""
    # Create logs directory if it doesn't exist
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Failed to create logs directory: {e}", file=sys.stderr)
        # Fall back to a temporary file in the system temp directory
        temp_log_file = Path(os.environ.get("TEMP", ".")) / "lvovo_app.log"
        setup_basic_logging(temp_log_file)
        return

    try:
        # Create a logger
        logger = logging.getLogger("lvovo_app")
        logger.setLevel(logging.INFO)

        # Clear any existing handlers
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # File handler (rotating logs)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8',
            delay=False
        )
        file_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(LOG_FORMAT)
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # Prevent double logging in case of module reload
        logger.propagate = False

        # Log successful initialization
        logger.info("Logging initialized successfully")
        return logger

    except Exception as e:
        # Fallback to basic logging if file logging fails
        print(f"Failed to initialize file logging: {e}", file=sys.stderr)
        return setup_basic_logging()


def setup_basic_logging(log_file: Optional[Path] = None) -> logging.Logger:
    """Set up basic logging as a fallback."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            *([logging.FileHandler(log_file)] if log_file else [])
        ]
    )
    logger = logging.getLogger("lvovo_app")
    logger.warning("Using basic logging configuration")
    return logger


def get_logger() -> logging.Logger:
    """Get the application logger."""
    logger = logging.getLogger("lvovo_app")
    if not logger.handlers:  # Only add handlers if they haven't been added before
        setup_logging() or setup_basic_logging()
    return logger


# Create a module-level logger instance
logger = get_logger()

# Usage:
# from app.core.logging import logger
# logger.info("Order created", extra={"order_id": order_id})

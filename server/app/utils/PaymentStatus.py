from enum import Enum as PyEnum
from typing import Optional


class PaymentStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# Providers that are settled in person, so the order can go ahead immediately.
OFFLINE_PROVIDER_HINTS = ("delivery", "cash", "cod", "offline", "collection", "pos", "terminal")


def is_offline_provider(provider_name: Optional[str]) -> bool:
    name = (provider_name or "").lower()
    return any(hint in name for hint in OFFLINE_PROVIDER_HINTS)

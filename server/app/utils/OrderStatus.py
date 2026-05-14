from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    WAITING_FOR_DRIVER = "waiting_for_driver"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

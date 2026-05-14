from enum import Enum

class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    RESTAURANT_ADMIN = "restaurant_admin"
    DRIVER = "driver"
    CUSTOMER = "customer"
    # GUEST = "guest"
from .auth import router as auth
from .users import router as users
from .restaurants import router as restaurants
from .menus import router as menus
from .orders import router as orders
from .ws_orders import router as ws_orders
from .drivers import router as drivers
from .payments import router as payments
from .notifications import router as notifications
from .admin import router as admin
from .customer import router as customer

# Export all routers
__all__ = [
    'auth',
    'users',
    'restaurants',
    'menus',
    'orders',
    'ws_orders',
    'drivers',
    'payments',
    'notifications',
    'admin',
    'customer'
]

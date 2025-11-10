from .action import router as action_router
from .auth import router as auth_router
from .booking import router as booking_router
from .cafe import router as cafe_router
from .dish import router as dish_router
from .media import router as media_router
from .slot import router as slot_router
from .table import router as table_router
from .user import router as user_router

__all__ = [
    'auth_router',
    'user_router',
    'cafe_router',
    'table_router',
    'slot_router',
    'booking_router',
    'action_router',
    'dish_router',
    'media_router',
]

routers = [
    auth_router,
    user_router,
    cafe_router,
    table_router,
    slot_router,
    booking_router,
    action_router,
    dish_router,
    media_router,
]

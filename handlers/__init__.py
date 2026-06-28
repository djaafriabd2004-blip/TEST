from aiogram import Router
from .admin import router as admin_router
from .shop import router as shop_router
from .charge import router as charge_router
from .support import router as support_router
from .user import router as user_router

def get_handlers_router() -> Router:
    main_router = Router()
    
    # Include admin router first to prioritize admin command captures
    main_router.include_router(admin_router)
    main_router.include_router(shop_router)
    main_router.include_router(charge_router)
    main_router.include_router(support_router)
    main_router.include_router(user_router)
    
    return main_router

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import config
from database import db_init
from middlewares.db_middleware import DbUserMiddleware
from middlewares.fsm_clear_middleware import FsmStateClearMiddleware
from handlers import get_handlers_router
from crypto_verifier import start_auto_verification_loop

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing database...")
    await db_init()
    logger.info("Database initialized successfully.")

    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("BOT_TOKEN is not configured in .env! Please set it and restart.")
        sys.exit(1)

    logger.info("Setting up Bot and Dispatcher...")
    bot = Bot(token=config.BOT_TOKEN)
    
    # Using local memory storage for FSM
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register outer database middleware for all update events
    dp.update.outer_middleware(DbUserMiddleware())
    
    # Register FSM state clear middleware for text message events
    dp.message.outer_middleware(FsmStateClearMiddleware())
    
    # Register handlers router
    dp.include_router(get_handlers_router())
    
    # Start background auto-verification loop
    asyncio.create_task(start_auto_verification_loop(bot))
    
    # Start background reseller API pre-order verification loop
    from database import start_api_preorder_auto_verification_loop
    asyncio.create_task(start_api_preorder_auto_verification_loop(bot))
    
    # Start background auto sales proof loop
    from utils import start_auto_sales_proof_loop
    asyncio.create_task(start_auto_sales_proof_loop(bot))
    
    # Start the REST API web server in background
    from api import create_api_app
    from aiohttp import web
    import os
    
    api_app = create_api_app(bot)
    runner = web.AppRunner(api_app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"API web server started on port {port}")
    
    # Register error handler to suppress harmless "query is too old" errors
    from aiogram.types import ErrorEvent
    from aiogram.exceptions import TelegramBadRequest
    
    @dp.errors()
    async def global_error_handler(event: ErrorEvent):
        if isinstance(event.exception, TelegramBadRequest):
            msg = str(event.exception)
            if "query is too old" in msg or "query ID is invalid" in msg:
                # Silently ignore these harmless Telegram timeout warnings
                return True
        logger.error("Unhandled exception: %s", event.exception, exc_info=event.exception)
        return True
        
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.critical(f"Critical error in polling: {e}")
    finally:
        try:
            await runner.cleanup()
        except Exception:
            pass
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

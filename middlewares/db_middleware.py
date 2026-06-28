from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from database import get_user, create_user
import config

class DbUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        tg_event = getattr(event, "event", None)
        tg_user = None
        if tg_event and hasattr(tg_event, "from_user"):
            tg_user = tg_event.from_user
            
        if tg_user:
            user_id = tg_user.id
            username = tg_user.username or ""
            first_name = tg_user.first_name or ""
            
            # Retrieve or register user
            user = await get_user(user_id)
            if not user:
                referred_by = None
                referrer_lang = 'en'
                if getattr(tg_event, "text", None) and tg_event.text.startswith("/start ref_"):
                    ref_code = tg_event.text.split(" ", 1)[1].replace("ref_", "")
                    from database import get_user_by_ref_code
                    referrer = await get_user_by_ref_code(ref_code)
                    if referrer:
                        referred_by = referrer['user_id']
                        referrer_lang = referrer['language']
                        
                await create_user(user_id, username, first_name, referred_by=referred_by)
                user = await get_user(user_id)
                
                bot = data.get("bot")
                if referred_by and bot:
                    from localization import get_text
                    try:
                        msg_text = get_text('referral_new_user_joined', referrer_lang, name=first_name)
                        await bot.send_message(chat_id=referred_by, text=msg_text, parse_mode="Markdown")
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Could not send referral notification to {referred_by}: {e}")
                
            data['db_user'] = user
            data['is_admin'] = user_id in config.ADMIN_IDS
            user_lang = user['language'] if (user and user['language']) else 'en'
            if user_lang not in ['en', 'ar', 'ru']:
                user_lang = 'en'
            data['lang'] = user_lang
        else:
            data['is_admin'] = False
            data['lang'] = 'en'
            
        return await handler(event, data)

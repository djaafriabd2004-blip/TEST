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
                
            data['db_user'] = user
            data['is_admin'] = user_id in config.ADMIN_IDS
            user_lang = user['language'] if (user and user['language']) else 'en'
            if user_lang not in ['en', 'ar', 'ru']:
                user_lang = 'en'
            data['lang'] = user_lang
            
            # Ban Check Interceptor
            if user and dict(user).get('is_banned') == 1 and not data['is_admin']:
                ban_msg = {
                    'ar': "❌ *حسابك محظور من استخدام البوت.*\n💬 للتواصل مع الدعم يرجى التواصل مع المسؤول مباشرة.",
                    'en': "❌ *Your account has been banned from using this bot.*\n💬 For support, please contact the admin.",
                    'ru': "❌ *Ваش аккаунт заблокирован.*\n💬 Для связи с поддержкой обратитесь к администратору."
                }
                msg_text = ban_msg.get(user_lang, ban_msg['en'])
                from aiogram.types import Message, CallbackQuery
                try:
                    if isinstance(tg_event, Message):
                        await tg_event.answer(msg_text, parse_mode="Markdown")
                    elif isinstance(tg_event, CallbackQuery):
                        await tg_event.answer("❌ Your account is banned / حسابك محظور", show_alert=True)
                except Exception:
                    pass
                return
        else:
            data['is_admin'] = False
            data['lang'] = 'en'
            
        return await handler(event, data)

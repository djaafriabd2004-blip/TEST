from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable

def is_menu_button_text(text: str) -> bool:
    if not text:
        return False
        
    clean_text = text.strip()
    
    # Common static buttons & emojis
    static_menu_buttons = {
        "📊 Statistics", "📊 الإحصائيات", "📊 Статистика",
        "🔍 Inspect User", "🔍 فحص مستخدم", "🔍 Проверка пользователя",
        "📦 Manage Products", "📦 إدارة المنتجات", "📦 Управление товарами",
        "📥 Add Stock", "📥 إضافة ستوك", "📥 Добавить сток",
        "📦 Bulk Add Stock", "📦 إضافة ستوك جماعي", "📦 Массовое добавление",
        "⏳ Pending Deposits", "⏳ الإيداعات المعلقة", "⏳ Ожидающие платежи",
        "⏳ Manage Pre-orders", "⏳ إدارة الحجوزات", "⏳ Управление предзаказами",
        "📢 Channels Settings", "📢 إعدادات القنوات", "📢 Настройки каналов",
        "🎧 Support Settings", "🎧 إعدادات الدعم", "🎧 Настройки поддержки",
        "💳 Charge Section", "💳 إعدادات الدفع", "💳 Настройки оплаты",
        "👥 Referral System", "👥 نظام الإحالة", "👥 Реферальная система",
        "🔑 API Keys Settings", "🔑 إعدادات مفاتيح API", "🔑 Настройки API ключей",
        "👥 Manage Users", "👥 إدارة المستخدمين", "👥 Управление пользователями",
        "🚫 Ban / Unban System", "🚫 نظام الحظر / فك الحظر", "🚫 Система банов",
        "📣 Broadcast", "📣 رسالة جماعية", "📣 Рассылка",
        "✏️ Edit Store Name", "✏️ تعديل اسم المتجر", "✏️ Изменить имя магазина",
        "🎨 Button Emojis", "🎨 إيموجيات الأزرار", "🎨 Эмодзи кнопок",
        "🔌 Pull External Product", "🔌 سحب منتج خارجي", "🔌 Импорт товара",
        "🔙 Back to Main Menu", "🔙 العودة للقائمة الرئيسية", "🔙 Главное меню",
        "🔙 Back", "🔙 Back to Admin Panel", "🔙 Cancel", "🔙 رجوع", "🔙 إلغاء",
        "/start", "/menu", "/admin"
    }
    
    if clean_text in static_menu_buttons:
        return True
        
    try:
        from localization import LOCALIZATION
        for key, translations in LOCALIZATION.items():
            if key.startswith('btn_') and isinstance(translations, dict):
                for lang, val in translations.items():
                    if clean_text == str(val).strip():
                        return True
    except Exception:
        pass
                
    return False

class FsmStateClearMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        state = data.get('state')
        if state and event.text:
            if is_menu_button_text(event.text):
                current_state = await state.get_state()
                if current_state:
                    await state.clear()
                    data['raw_state'] = None
                    
        return await handler(event, data)

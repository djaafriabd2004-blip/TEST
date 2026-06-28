from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable

def is_menu_button_text(text: str) -> bool:
    if not text:
        return False
        
    static_menu_buttons = {
        "📊 Statistics",
        "🔍 Inspect User",
        "📦 Manage Products",
        "📥 Add Stock",
        "📦 Bulk Add Stock",
        "⏳ Pending Deposits",
        "📢 Channels Settings",
        "🎧 Support Settings",
        "💳 Charge Section",
        "👥 Referral System",
        "🔑 API Keys Settings",
        "👥 Manage Users",
        "📣 Broadcast",
        "✏️ Edit Store Name",
        "🔙 Back to Main Menu",
        "🔙 Back",
        "🔙 Back to Admin Panel",
        "🔙 Cancel"
    }
    
    if text in static_menu_buttons:
        return True
        
    from localization import LOCALIZATION
    button_keys = [
        'btn_shop', 'btn_my_orders', 'btn_support', 'btn_charge_balance',
        'btn_referral', 'btn_language', 'btn_admin_panel', 'btn_back',
        'btn_reseller_api'
    ]
    for key in button_keys:
        translations = LOCALIZATION.get(key, {})
        for lang, val in translations.items():
            if text == val:
                return True
                
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

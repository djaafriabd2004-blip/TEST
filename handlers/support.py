from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_user, get_setting
from localization import get_text
from handlers.states import SupportStates, AdminStates
import keyboards
try:
    import bot_config as config
except ImportError:
    import config
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text.in_([
    get_text('btn_support', 'en'),
    get_text('btn_support', 'ar'),
    get_text('btn_support', 'ru')
]))
async def cmd_support(message: Message, lang='en'):
    support_username = await get_setting("support_username", "None")
    if not support_username or support_username == "None":
        await message.answer(get_text('support_no_handle', lang))
        return
        
    username_clean = support_username.strip()
    if username_clean.startswith('@'):
        username_clean = username_clean[1:]
        
    text = get_text('support_info', lang, username=username_clean)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text('btn_contact_support', lang), url=f"https://t.me/{username_clean}")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot, lang='en'):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    msg_text = message.text
    
    await state.clear()
    
    # Notify support team (Admins)
    for admin_id in config.ADMIN_IDS:
        try:
            admin_user = await get_user(admin_id)
            admin_lang = admin_user['language'] if admin_user else 'en'
            
            kb = keyboards.get_admin_support_ticket_keyboard(user_id)
            admin_text = get_text(
                'support_new_ticket',
                admin_lang,
                name=first_name,
                user_id=user_id,
                message=msg_text
            )
            from utils import send_message_with_retry
            await send_message_with_retry(bot.send_message, chat_id=admin_id, text=admin_text, reply_markup=kb, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to forward ticket to admin {admin_id}: {e}")
            
    await message.answer(get_text('support_ticket_sent', lang))

# Admin Reply Callback Query
@router.callback_query(F.data.startswith("ticket_reply_"))
async def cb_admin_reply_ticket(callback: CallbackQuery, state: FSMContext, is_admin=False):
    if not is_admin:
        await callback.answer("You are not authorized.", show_alert=True)
        return
        
    target_user_id = int(callback.data.replace("ticket_reply_", ""))
    await state.update_data(reply_target_id=target_user_id)
    await state.set_state(AdminStates.waiting_for_reply_text)
    
    target_user = await get_user(target_user_id)
    name = target_user['first_name'] if target_user else "User"
    
    await callback.message.answer(f"✍️ *Replying to {name}* (`{target_user_id}`).\nPlease enter your reply message:")
    await callback.answer()

# Admin sends reply text
@router.message(AdminStates.waiting_for_reply_text)
async def process_admin_reply_text(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    from database import get_admin_ids
    admin_ids = await get_admin_ids()
    if user_id not in admin_ids:
        await state.clear()
        return
        
    data = await state.get_data()
    target_user_id = data.get("reply_target_id")
    reply_text = message.text or message.caption or ""
    
    await state.clear()
    
    if not target_user_id:
        await message.answer("❌ Error: Reply target user not found in session.")
        return
        
    target_user = await get_user(target_user_id)
    target_lang = target_user['language'] if target_user else 'en'
    
    # Send message to user
    try:
        from utils import send_message_with_retry
        if message.text:
            delivered_msg = get_text('support_reply_delivered', target_lang, reply=reply_text)
            await send_message_with_retry(bot.send_message, chat_id=target_user_id, text=delivered_msg, parse_mode="Markdown")
        else:
            await message.copy_to(chat_id=target_user_id)
        await message.answer("✅ Reply has been delivered to the user.")
    except Exception as e:
        logger.error(f"Failed to send reply to user {target_user_id}: {e}")
        await message.answer(f"❌ Failed to deliver reply: {e}")

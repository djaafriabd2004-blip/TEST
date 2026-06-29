from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from database import create_user, get_user, update_user_lang, get_referral_count, get_user_by_ref_code, get_setting, get_orders, get_button_emojis
from localization import get_text
import keyboards
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, bot: Bot, db_user=None, is_admin=False, lang='en'):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username or ""
    
    # Force Join Channel check (if enabled in settings)
    force_channels_str = await get_setting('force_join_channels', '')
    if force_channels_str:
        force_channels = [c.strip() for c in force_channels_str.split(",") if c.strip()]
        unjoined_channels = []
        for channel in force_channels:
            try:
                member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
                if member.status in ['left', 'kicked']:
                    unjoined_channels.append(channel)
            except Exception as e:
                logger.warning(f"Could not verify join for channel {channel}: {e}")
                
        if unjoined_channels:
            kb = await keyboards.get_force_sub_keyboard(bot, unjoined_channels, lang)
            await message.answer(
                get_text('force_join_msg', lang),
                reply_markup=kb,
                parse_mode="Markdown"
            )
            return

    # Referral check is now handled in db_middleware.py when creating a new user

    # Fetch referrer name
    ref_by_name = "None"
    if db_user and db_user['referred_by']:
        referrer_profile = await get_user(db_user['referred_by'])
        if referrer_profile:
            ref_by_name = referrer_profile['first_name']
            
    ref_count = await get_referral_count(user_id)
    balance = db_user['balance'] if db_user else 0.0
    
    store_name = await get_setting('store_name', 'Digital Store')
    welcome_emoji_id = await get_setting('welcome_emoji_id', '')
    if welcome_emoji_id:
        welcome_emoji = f'<tg-emoji emoji-id="{welcome_emoji_id}">🔷</tg-emoji>'
    else:
        welcome_emoji = '🔷'
    welcome_text = get_text(
        'welcome', 
        lang, 
        name=first_name, 
        balance=balance, 
        referred_by=ref_by_name, 
        ref_count=ref_count,
        store_name=store_name,
        welcome_emoji=welcome_emoji,
        user_id=user_id
    )
    
    button_emojis = await get_button_emojis()
    await message.answer(
        welcome_text,
        reply_markup=keyboards.get_main_menu(lang, is_admin, button_emojis=button_emojis),
        parse_mode="HTML"
    )

@router.message(F.text.in_([
    get_text('btn_language', 'en'),
    get_text('btn_language', 'ar'),
    get_text('btn_language', 'ru')
]))
async def show_language_menu(message: Message, lang='en'):
    await message.answer(
        get_text('select_lang', lang),
        reply_markup=keyboards.get_language_keyboard()
    )

@router.callback_query(F.data.startswith("set_lang_"))
async def process_set_lang(callback: CallbackQuery, is_admin=False):
    lang_code = callback.data.replace("set_lang_", "")
    user_id = callback.from_user.id
    await update_user_lang(user_id, lang_code)
    
    await callback.answer(get_text('lang_updated', lang_code))
    
    db_user = await get_user(user_id)
    ref_by_name = "None"
    if db_user and db_user['referred_by']:
        referrer_profile = await get_user(db_user['referred_by'])
        if referrer_profile:
            ref_by_name = referrer_profile['first_name']
            
    ref_count = await get_referral_count(user_id)
    balance = db_user['balance'] if db_user else 0.0
    
    store_name = await get_setting('store_name', 'Digital Store')
    welcome_emoji_id = await get_setting('welcome_emoji_id', '')
    if welcome_emoji_id:
        welcome_emoji = f'<tg-emoji emoji-id="{welcome_emoji_id}">🔷</tg-emoji>'
    else:
        welcome_emoji = '🔷'
    welcome_text = get_text(
        'welcome', 
        lang_code, 
        name=callback.from_user.first_name, 
        balance=balance, 
        referred_by=ref_by_name, 
        ref_count=ref_count,
        store_name=store_name,
        welcome_emoji=welcome_emoji,
        user_id=user_id
    )
    
    button_emojis = await get_button_emojis()
    await callback.message.answer(
        welcome_text,
        reply_markup=keyboards.get_main_menu(lang_code, is_admin, button_emojis=button_emojis),
        parse_mode="HTML"
    )
    await callback.message.delete()

@router.message(F.text.in_([
    get_text('btn_referral', 'en'),
    get_text('btn_referral', 'ar'),
    get_text('btn_referral', 'ru')
]))
async def show_referral_menu(message: Message, bot: Bot, db_user, lang='en'):
    user_id = message.from_user.id
    ref_code = db_user['referral_code']
    ref_count = await get_referral_count(user_id)
    ref_earned = db_user['referral_balance_earned']
    
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"
    
    bonus_percent = await get_setting('referral_bonus_percent', '10')
    
    msg_text = get_text(
        'referral_msg',
        lang,
        bonus=bonus_percent,
        count=ref_count,
        earned=ref_earned,
        link=ref_link
    )
    
    await message.answer(msg_text, parse_mode="Markdown", disable_web_page_preview=True)

@router.message(F.text.in_([
    get_text('btn_my_orders', 'en'),
    get_text('btn_my_orders', 'ar'),
    get_text('btn_my_orders', 'ru')
]))
async def show_orders_menu(message: Message, lang='en'):
    user_id = message.from_user.id
    orders = await get_orders(user_id)
    
    if not orders:
        await message.answer(get_text('my_orders_empty', lang))
        return
        
    await message.answer(get_text('my_orders_title', lang), parse_mode="Markdown")
    
    # Display products bought. Limit to recent 10 to keep it manageable.
    for order in orders[:10]:
        prod_name = order[f'product_name_{lang}'] or order['product_name_en']
        order_text = get_text(
            'order_item',
            lang,
            id=order['id'],
            name=prod_name,
            price=order['price_paid'],
            date=order['purchased_at'],
            data=order['stock_data']
        )
        try:
            await message.answer(order_text, parse_mode="Markdown")
        except Exception:
            await message.answer(order_text)
    
    # Show download button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    btn_text = {"en": "📥 Download as TXT", "ar": "📥 تحميل كملف TXT", "ru": "📥 Скачать как TXT"}
    builder.button(text=btn_text.get(lang, btn_text['en']), callback_data="download_orders_txt")
    builder.adjust(1)
    
    info_text = {"en": "📥 Want all your products in a file?", "ar": "📥 تريد جميع منتجاتك في ملف؟", "ru": "📥 Хотите все товары в файле?"}
    await message.answer(info_text.get(lang, info_text['en']), reply_markup=builder.as_markup())

@router.callback_query(F.data == "download_orders_txt")
async def cb_download_orders_txt(callback: CallbackQuery, lang='en'):
    user_id = callback.from_user.id
    orders = await get_orders(user_id)
    
    if not orders:
        await callback.answer(get_text('my_orders_empty', lang), show_alert=True)
        return
    
    # Build txt content
    lines = []
    store_name = await get_setting('store_name', 'Digital Store')
    lines.append(f"{'='*40}")
    lines.append(f"  {store_name} - Purchase History")
    lines.append(f"  User: {callback.from_user.first_name} (ID: {user_id})")
    lines.append(f"{'='*40}\n")
    
    for order in orders:
        prod_name = order[f'product_name_{lang}'] or order['product_name_en']
        lines.append(f"Order #{order['id']}")
        lines.append(f"Product: {prod_name}")
        lines.append(f"Price: ${order['price_paid']:.2f} USD")
        lines.append(f"Date: {order['purchased_at']}")
        lines.append(f"Data: {order['stock_data']}")
        lines.append(f"{'-'*40}")
    
    lines.append(f"\nTotal Orders: {len(orders)}")
    total_spent = sum(o['price_paid'] for o in orders)
    lines.append(f"Total Spent: ${total_spent:.2f} USD")
    
    content = "\n".join(lines)
    file = BufferedInputFile(content.encode('utf-8'), filename=f"my_orders_{user_id}.txt")
    
    await callback.message.answer_document(file)
    await callback.answer()


# --- User Reseller API Key Handlers ---
@router.message(Command("api"))
@router.message(F.text.in_([
    get_text('btn_reseller_api', 'en'),
    get_text('btn_reseller_api', 'ar'),
    get_text('btn_reseller_api', 'ru')
]))
async def cmd_user_api(message: Message, lang='en'):
    user_id = message.from_user.id
    
    from database import get_api_key, get_setting
    api_key = await get_api_key(user_id)
    
    import os
    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    if not domain:
        domain = await get_setting("api_domain", "your-bot-domain.com")
    
    api_base_url = f"https://{domain}" if not domain.startswith("http") else domain
    
    if not api_key:
        text = get_text('reseller_api_info_no_key', lang)
        await message.answer(text, reply_markup=keyboards.get_user_api_key_keyboard(has_key=False, lang=lang), parse_mode="Markdown")
    else:
        text = get_text('reseller_api_info_has_key', lang, api_key=api_key, api_base_url=api_base_url)
        await message.answer(text, reply_markup=keyboards.get_user_api_key_keyboard(has_key=True, lang=lang), parse_mode="Markdown")

@router.callback_query(F.data == "user_api_key_gen")
async def cb_user_api_key_gen(callback: CallbackQuery, lang='en'):
    user_id = callback.from_user.id
    
    from database import get_api_key, generate_api_key, get_setting
    api_key = await get_api_key(user_id)
    if not api_key:
        api_key = await generate_api_key(user_id)
        await callback.answer(get_text('btn_generate_api_key', lang) + " ✅")
    else:
        await callback.answer("Already exists.")
        
    import os
    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    if not domain:
        domain = await get_setting("api_domain", "your-bot-domain.com")
        
    api_base_url = f"https://{domain}" if not domain.startswith("http") else domain
    
    text = get_text('reseller_api_info_has_key', lang, api_key=api_key, api_base_url=api_base_url)
    await callback.message.edit_text(text, reply_markup=keyboards.get_user_api_key_keyboard(has_key=True, lang=lang), parse_mode="Markdown")

@router.callback_query(F.data == "user_api_key_regen")
async def cb_user_api_key_regen(callback: CallbackQuery, lang='en'):
    user_id = callback.from_user.id
    
    from database import generate_api_key, get_setting
    api_key = await generate_api_key(user_id)
    await callback.answer("🔄 API Key Regenerated!")
    
    import os
    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    if not domain:
        domain = await get_setting("api_domain", "your-bot-domain.com")
        
    api_base_url = f"https://{domain}" if not domain.startswith("http") else domain
    
    text = get_text('reseller_api_info_has_key', lang, api_key=api_key, api_base_url=api_base_url)
    await callback.message.edit_text(text, reply_markup=keyboards.get_user_api_key_keyboard(has_key=True, lang=lang), parse_mode="Markdown")

@router.callback_query(F.data == "user_api_key_revoke")
async def cb_user_api_key_revoke(callback: CallbackQuery, lang='en'):
    user_id = callback.from_user.id
    
    from database import revoke_api_key
    await revoke_api_key(user_id)
    await callback.answer("❌ API Key Deleted!")
    
    text = get_text('reseller_api_info_no_key', lang)
    await callback.message.edit_text(text, reply_markup=keyboards.get_user_api_key_keyboard(has_key=False, lang=lang), parse_mode="Markdown")

@router.callback_query(F.data == "user_api_key_doc")
async def cb_user_api_key_doc(callback: CallbackQuery, lang='en'):
    try:
        await callback.answer()
    except Exception:
        pass
        
    user_id = callback.from_user.id
    
    from database import get_api_key, get_setting
    api_key = await get_api_key(user_id) or "YOUR_API_KEY_HERE"
    store_name = await get_setting("store_name", "Digital Store")
    
    doc_content = f"""==================================================
        {store_name.upper()} - RESELLER API DOCUMENTATION
==================================================

1. Base URL:
   https://worker-production-53ca.up.railway.app

2. Authentication:
   Header Name: X-API-Key
   Your Key: {api_key}

3. Endpoints:

   A. Health Check (Public):
      GET /api/health
      Response: {{"ok": true, "status": "healthy"}}

   B. Account Balance & Details:
      GET /api/me
      Response: {{"ok": true, "user": {{"user_id": {user_id}, "username": "username", "first_name": "name", "balance": 100.0, "language": "en"}}}}

   C. Get Products List:
      GET /api/products
      Response: {{"ok": true, "products": [{{"id": 1, "name_en": "Product Name", "price": 0.71, "stock_count": 97}}]}}

   D. Purchase Product:
      POST /api/buy
      Body: {{"product_id": 1, "quantity": 1}}
      Response: {{"ok": true, "transaction_id": "tx_...", "product_id": 1, "quantity": 1, "total_price": 0.71, "new_balance": 99.29, "items": ["item_content"]}}

==================================================
Python Example:
==================================================
import requests

headers = {{
    "X-API-Key": "{api_key}",
    "Content-Type": "application/json"
}}
res = requests.get("https://worker-production-53ca.up.railway.app/api/products", headers=headers)
print(res.json())
"""
    file = BufferedInputFile(doc_content.encode('utf-8'), filename="api_documentation.txt")
    await callback.message.answer_document(file)

@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery, bot: Bot, db_user=None, is_admin=False, lang='en'):
    user_id = callback.from_user.id
    force_channels_str = await get_setting('force_join_channels', '')
    
    unjoined_channels = []
    if force_channels_str:
        force_channels = [c.strip() for c in force_channels_str.split(",") if c.strip()]
        for channel in force_channels:
            try:
                member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
                if member.status in ['left', 'kicked']:
                    unjoined_channels.append(channel)
            except Exception as e:
                logger.warning(f"Could not verify join for channel {channel}: {e}")
                
    if unjoined_channels:
        alert_msg = {
            'ar': "❌ لم تقم بالانضمام إلى جميع القنوات المطلوبة بعد! يرجى الانضمام والضغط على تحقق مرة أخرى.",
            'en': "❌ You haven't joined all required channels yet! Please join and try again.",
            'ru': "❌ Вы еще не подписались на все необходимые каналы! Пожалуйста, подпишитесь и попробуйте снова."
        }
        await callback.answer(alert_msg.get(lang, alert_msg['en']), show_alert=True)
        try:
            kb = await keyboards.get_force_sub_keyboard(bot, unjoined_channels, lang)
            await callback.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass
    else:
        success_msg = {
            'ar': "🎉 تم التأكد من اشتراكك بنجاح! مرحباً بك.",
            'en': "🎉 Subscription verified successfully! Welcome.",
            'ru': "🎉 Подписка успешно подтверждена! Добро пожаловать."
        }
        await callback.answer(success_msg.get(lang, success_msg['en']), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
            
        first_name = callback.from_user.first_name
        ref_by_name = "None"
        if db_user and db_user['referred_by']:
            referrer_profile = await get_user(db_user['referred_by'])
            if referrer_profile:
                ref_by_name = referrer_profile['first_name']
                
        ref_count = await get_referral_count(user_id)
        balance = db_user['balance'] if db_user else 0.0
        
        store_name = await get_setting('store_name', 'Digital Store')
        welcome_emoji_id = await get_setting('welcome_emoji_id', '')
        if welcome_emoji_id:
            welcome_emoji = f'<tg-emoji emoji-id="{welcome_emoji_id}">🔷</tg-emoji>'
        else:
            welcome_emoji = '🔷'
        welcome_text = get_text(
            'welcome', 
            lang, 
            name=first_name, 
            balance=balance, 
            referred_by=ref_by_name, 
            ref_count=ref_count,
            store_name=store_name,
            welcome_emoji=welcome_emoji,
            user_id=user_id
        )
        
        button_emojis = await get_button_emojis()
        await callback.message.answer(
            welcome_text,
            reply_markup=keyboards.get_main_menu(lang, is_admin, button_emojis=button_emojis),
            parse_mode="HTML"
        )

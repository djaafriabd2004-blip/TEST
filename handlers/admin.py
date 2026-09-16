from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, BufferedInputFile, TelegramObject
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable
from database import (
    get_products, get_product, add_product, update_product, delete_product,
    add_stock, bulk_add_stock, get_stock_count, get_setting, set_setting, get_all_users,
    get_user, get_referral_count, get_all_pending_payments, get_stats,
    get_stock_notification_subscribers, clear_stock_notifications, get_user_full_report,
    get_sales_last_24h, get_button_emojis, ban_user, unban_user, is_user_banned, get_all_banned_users
)
from localization import get_text
from utils import get_product_name
from handlers.states import ProductStates, StockStates, AdminStates
import keyboards
try:
    import bot_config as config
except ImportError:
    import config
import logging

logger = logging.getLogger(__name__)
router = Router()

class AdminAuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id
            
        if not user_id or user_id not in config.ADMIN_IDS:
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("❌ Unauthorized action.", show_alert=True)
                except Exception:
                    pass
            return None
            
        return await handler(event, data)

router.message.middleware(AdminAuthMiddleware())
router.callback_query.middleware(AdminAuthMiddleware())

def is_user_admin(user_id):
    return user_id in config.ADMIN_IDS

def escape_md(text):
    """Escape special Markdown characters in user-provided text."""
    if not text:
        return ""
    for ch in ['\\', '_', '*', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        text = text.replace(ch, '\\' + ch)
    return text

@router.message(Command("ban"))
async def cmd_ban_user(message: Message, command: CommandObject):
    if not is_user_admin(message.from_user.id):
        return
    if not command.args:
        await message.answer("⚠️ Usage: `/ban <user_id> [reason]`", parse_mode="Markdown")
        return
    parts = command.args.strip().split(" ", 1)
    try:
        target_id = int(parts[0])
    except ValueError:
        await message.answer("❌ Invalid numeric User ID.")
        return
    reason = parts[1] if len(parts) > 1 else "Violation of terms"
    await ban_user(target_id, reason)
    await message.answer(f"🔴 User `{target_id}` has been banned successfully.\nReason: {reason}", parse_mode="Markdown")

@router.message(Command("unban"))
async def cmd_unban_user(message: Message, command: CommandObject):
    if not is_user_admin(message.from_user.id):
        return
    if not command.args:
        await message.answer("⚠️ Usage: `/unban <user_id>`", parse_mode="Markdown")
        return
    try:
        target_id = int(command.args.strip().split()[0])
    except ValueError:
        await message.answer("❌ Invalid numeric User ID.")
        return
    await unban_user(target_id)
    await message.answer(f"🟢 User `{target_id}` has been unbanned successfully.", parse_mode="Markdown")

@router.callback_query(F.data.startswith("admin_actban_"))
async def cb_admin_ban_user(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    target_id = int(callback.data.replace("admin_actban_", ""))
    await ban_user(target_id, "Banned by admin panel")
    await callback.answer(get_text('admin_ban_success', lang, user_id=target_id, reason="Admin panel"), show_alert=True)
    try:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('btn_admin_unban_user_btn', lang), callback_data=f"admin_actunban_{target_id}")
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    except Exception:
        pass

@router.callback_query(F.data.startswith("admin_actunban_"))
async def cb_admin_unban_user(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    target_id = int(callback.data.replace("admin_actunban_", ""))
    await unban_user(target_id)
    await callback.answer(get_text('admin_unban_success', lang, user_id=target_id), show_alert=True)
    try:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('btn_admin_ban_user_btn', lang), callback_data=f"admin_actban_{target_id}")
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    except Exception:
        pass

@router.message(F.text.in_([
    get_text('btn_admin_panel', 'en'),
    get_text('btn_admin_panel', 'ar'),
    get_text('btn_admin_panel', 'ru'),
    "🔧 Admin Panel",
    "Admin Panel"
]))
async def cmd_admin_panel(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    await message.answer(
        get_text('admin_panel', lang),
        reply_markup=keyboards.get_admin_reply_keyboard(lang)
    )

@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    # Delete current inline message since ReplyKeyboardMarkup cannot be edited in
    await callback.message.delete()
    await callback.message.answer(
        get_text('admin_panel', lang),
        reply_markup=keyboards.get_admin_reply_keyboard(lang)
    )
    await callback.answer()

@router.message(F.text.in_([
    get_text('btn_admin_stats', 'en'),
    get_text('btn_admin_stats', 'ar'),
    get_text('btn_admin_stats', 'ru'),
    "📊 Statistics", "📊 الإحصائيات", "📊 Статистика"
]))
async def msg_admin_statistics(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return

    stats = await get_stats()
    store_name = await get_setting('store_name', 'Digital Store')

    text = get_text(
        'admin_stats_title',
        lang,
        store_name=store_name,
        total_users=stats['total_users'],
        users_today=stats['users_today'],
        total_deposit_count=stats['total_deposit_count'],
        total_deposits=stats['total_deposits'],
        deposits_today=stats['deposits_today'],
        total_orders=stats['total_orders'],
        total_order_revenue=stats['total_order_revenue'],
        orders_today=stats['orders_today'],
        order_revenue_today=stats['order_revenue_today'],
        pending_count=stats['pending_count']
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboards.get_admin_stats_keyboard(lang))

@router.callback_query(F.data == "admin_dl_sales_24h")
async def cb_admin_dl_sales_24h(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    sales = await get_sales_last_24h()
    
    if not sales:
        no_sales_msg = {
            "en": "📭 No sales recorded in the last 24 hours.",
            "ar": "📭 لم يتم تسجيل أي مبيعات في آخر 24 ساعة.",
            "ru": "📭 За последние 24 часа продаж не зарегистрировано."
        }
        await callback.answer(no_sales_msg.get(lang, no_sales_msg['en']), show_alert=True)
        return
        
    # Generate file content
    from datetime import datetime
    store_name = await get_setting('store_name', 'Digital Store')
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate totals
    total_rev = sum(s['price_paid'] for s in sales)
    total_sales = len(sales)
    
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  {store_name.upper()} - SALES REPORT (LAST 24 HOURS)")
    lines.append(f"  Generated at: {now_str}")
    lines.append(f"{'='*60}\n")
    
    lines.append(f"📊 SUMMARY STATISTICS:")
    lines.append(f"├ Total Sales (Units): {total_sales}")
    lines.append(f"└ Total Revenue: ${total_rev:.2f} USD")
    lines.append(f"{'='*60}\n")
    
    for idx, sale in enumerate(sales, 1):
        lines.append(f"[{idx}] ORDER #{sale['id']}")
        lines.append(f" ├ Date/Time: {sale['purchased_at']}")
        
        # Product
        prod_name = sale[f'product_name_{lang}'] or sale['product_name_en']
        lines.append(f" ├ Product: {prod_name}")
        lines.append(f" ├ Price Paid: ${sale['price_paid']:.2f} USD")
        
        # Buyer
        buyer_name = sale['first_name'] or "Unknown"
        buyer_username = f"@{sale['username']}" if sale['username'] else "No Username"
        lines.append(f" ├ Buyer: {buyer_name} ({buyer_username}) [ID: {sale['user_id']}]")
        
        # Delivered stock data
        lines.append(f" └ Delivered Content:")
        lines.append(f"   --------------------------------------------------")
        stock_data = sale['stock_data'] or ""
        # Indent stock data lines
        indented_data = "\n".join(f"   {line}" for line in stock_data.splitlines())
        lines.append(indented_data)
        lines.append(f"   --------------------------------------------------")
        lines.append(f"{'-'*60}\n")
        
    content = "\n".join(lines)
    file = BufferedInputFile(content.encode('utf-8'), filename=f"sales_last_24h_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
    
    # Send report file
    try:
        await callback.message.answer_document(
            file,
            caption=f"📋 Sales Report (Last 24 Hours)\n\n"
                    f"💰 Total Revenue: ${total_rev:.2f} USD\n"
                    f"📦 Total Units: {total_sales}"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to send 24h sales report: {e}")
        await callback.answer("❌ Error generating report file.", show_alert=True)

@router.message(F.text.in_([
    get_text('btn_admin_inspect_user', 'en'),
    get_text('btn_admin_inspect_user', 'ar'),
    get_text('btn_admin_inspect_user', 'ru'),
    "🔍 Inspect User", "🔍 فحص مستخدم", "🔍 Проверка пользователя"
]))
async def msg_admin_inspect_user(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_inspect_user_id)
    await message.answer(get_text('admin_inspect_prompt', lang), reply_markup=keyboards.get_admin_reply_keyboard(lang), parse_mode="Markdown")

@router.message(AdminStates.waiting_for_inspect_user_id)
async def process_inspect_user_id(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    if not message.text or not message.text.strip().isdigit():
        await message.answer(get_text('admin_inspect_invalid_id', lang))
        return
    user_id = int(message.text.strip())

    await state.clear()
    report = await get_user_full_report(user_id)

    if not report:
        await message.answer(get_text('admin_inspect_not_found', lang))
        return

    u = dict(report['user']) if report['user'] else {}
    name = escape_md(u.get('first_name', ''))
    username = f"@{escape_md(u.get('username', ''))}" if u.get('username') else "N/A"
    joined = u.get('joined_at', 'N/A')
    ref_by = escape_md(report['referred_by_name']) if report.get('referred_by_name') else "None"

    is_banned = u.get('is_banned', 0) == 1
    ban_status = f"🔴 BANNED (Reason: {u.get('ban_reason', 'N/A')})" if is_banned else "🟢 Active"

    # Build report text
    text = get_text(
        'admin_user_report_title',
        lang,
        name=name,
        username=username,
        user_id=user_id,
        ban_status=ban_status,
        balance=u.get('balance', 0),
        discount=report['discount'],
        language=u.get('language', 'en'),
        joined=joined,
        deposits_count=report['deposits_count'],
        deposits_total=report['deposits_total'],
        pending_count=report['pending_count'],
        pending_total=report['pending_total'],
        orders_count=report['orders_count'],
        orders_total=report['orders_total'],
        referred_by=ref_by,
        referral_count=report['referral_count'],
        ref_earnings=u.get('referral_balance_earned', 0)
    )

    # Recent deposits
    if report['recent_deposits']:
        recent_dep_title = {"en": "\n📝 *Recent Deposits (last 5)*\n", "ar": "\n📝 *آخر 5 عمليات إيداع*\n", "ru": "\n📝 *Последние 5 депозитов*\n"}.get(lang, "\n📝 *Recent Deposits (last 5)*\n")
        text += recent_dep_title
        for d in report['recent_deposits']:
            method = d['payment_method']
            if method.startswith('blockchain_'):
                parts = method.split('_')
                method = f"Crypto ({parts[1]})" if len(parts) > 1 else method
            elif method == 'telegram_stars':
                method = 'Stars'
            elif method.startswith('cryptobot_'):
                method = 'CryptoBot'
            status_icon = '✅' if d['status'] == 'completed' else '⏳' if d['status'] == 'pending' else '❌'
            text += f"├ {status_icon} `${d['amount']:.2f}` via {method} ({d['created_at'][:10]})\n"

    # Recent orders
    if report['recent_orders']:
        recent_ord_title = {"en": "\n📦 *Recent Orders (last 5)*\n", "ar": "\n📦 *آخر 5 طلبات شراء*\n", "ru": "\n📦 *Последние 5 заказов*\n"}.get(lang, "\n📦 *Recent Orders (last 5)*\n")
        text += recent_ord_title
        for o in report['recent_orders']:
            p_name = o.get(f'product_name_{lang}') or o['product_name_en']
            text += f"├ 🛍 `{escape_md(p_name)}` \u2014 `${o['price_paid']:.2f}` ({o['purchased_at'][:10]})\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    if is_banned:
        builder.button(text=get_text('btn_admin_unban_user_btn', lang), callback_data=f"admin_actunban_{user_id}")
    else:
        builder.button(text=get_text('btn_admin_ban_user_btn', lang), callback_data=f"admin_actban_{user_id}")

    # Send (split if too long)
    if len(text) > 4000:
        chunks = []
        current = ""
        for line in text.split('\n'):
            if len(current) + len(line) + 1 > 4000:
                chunks.append(current)
                current = line + '\n'
            else:
                current += line + '\n'
        if current:
            chunks.append(current)
        for idx, chunk in enumerate(chunks):
            try:
                if idx == len(chunks) - 1:
                    await message.answer(chunk, parse_mode="Markdown", reply_markup=builder.as_markup())
                else:
                    await message.answer(chunk, parse_mode="Markdown")
            except Exception:
                await message.answer(chunk)
    else:
        try:
            await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())
        except Exception:
            await message.answer(text, reply_markup=builder.as_markup())

@router.message(F.text.in_([
    get_text('btn_admin_manage_products', 'en'),
    get_text('btn_admin_manage_products', 'ar'),
    get_text('btn_admin_manage_products', 'ru'),
    "📦 Manage Products", "📦 إدارة المنتجات", "📦 Управление товарами"
]))
async def msg_admin_manage_products(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    products = await get_products()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_admin_add_product', lang), callback_data="admin_prod_add")
    for prod in products:
        name = get_product_name(prod, lang)
        builder.button(text=f"✏️ {name} (${prod['price']:.2f})", callback_data=f"admin_prod_view_{prod['id']}")
    builder.button(text=get_text('btn_admin_back_to_panel', lang), callback_data="admin_menu")
    builder.adjust(1)
    
    await message.answer(
        get_text('admin_prod_mgmt_title', lang),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.message(F.text.in_([
    get_text('btn_admin_add_stock', 'en'),
    get_text('btn_admin_add_stock', 'ar'),
    get_text('btn_admin_add_stock', 'ru'),
    get_text('btn_admin_bulk_stock', 'en'),
    get_text('btn_admin_bulk_stock', 'ar'),
    get_text('btn_admin_bulk_stock', 'ru'),
    "📥 Add Stock", "📥 إضافة ستوك", "📥 Добавить сток",
    "📦 Bulk Add Stock", "📦 إضافة ستوك جماعي", "📦 Массовое добавление"
]))
async def msg_admin_stock_select_prod(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    is_bulk = message.text in [
        get_text('btn_admin_bulk_stock', 'en'),
        get_text('btn_admin_bulk_stock', 'ar'),
        get_text('btn_admin_bulk_stock', 'ru'),
        "📦 Bulk Add Stock", "📦 إضافة ستوك جماعي", "📦 Массовое добавление"
    ]
    action = "admin_bulk_stock" if is_bulk else "admin_add_stock"
    products = await get_products()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for prod in products:
        name = get_product_name(prod, lang)
        builder.button(text=f"{name}", callback_data=f"admin_stk_{action.split('_')[1]}_{prod['id']}")
    builder.button(text=get_text('btn_admin_back_to_panel', lang), callback_data="admin_menu")
    builder.adjust(1)
    
    await message.answer(
        get_text('admin_stock_select_prod_prompt', lang),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.message(F.text.in_([
    get_text('btn_admin_pending_deposits', 'en'),
    get_text('btn_admin_pending_deposits', 'ar'),
    get_text('btn_admin_pending_deposits', 'ru'),
    "⏳ Pending Deposits", "⏳ الإيداعات المعلقة", "⏳ Ожидающие платежи"
]))
async def msg_admin_pending_deposits(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    pending_payments = await get_all_pending_payments()
    if not pending_payments:
        await message.answer(get_text('admin_pending_no_deposits', lang))
        return
        
    await message.answer(get_text('admin_pending_found', lang, count=len(pending_payments)))
    
    for payment in pending_payments:
        user_id = payment['user_id']
        user_info = f"`{user_id}`"
        db_user = await get_user(user_id)
        if db_user:
            user_info = escape_md(db_user['first_name'])
            if db_user['username']:
                user_info += f" (@{escape_md(db_user['username'])})"
            user_info += f" (`{user_id}`)"
            
        method_str = payment['payment_method']
        if method_str.startswith("blockchain_"):
            parts = method_str.split("_")
            coin = parts[1]
            txid = "_".join(parts[2:])
            method_desc = f"🪙 Crypto: `{coin}`\n🔗 TxID: `{txid}`"
        elif method_str == "telegram_stars":
            method_desc = "⭐️ Telegram Stars"
        else:
            method_desc = f"`{method_str}`"
            
        msg_text = (
            f"⏳ *Pending Deposit Request*\n\n"
            f"👤 *User:* {user_info}\n"
            f"💵 *Amount:* `${payment['amount']:.2f} USD`\n"
            f"ℹ️ *Method:* {method_desc}\n"
            f"📅 *Date:* `{payment['created_at']}`\n\n"
            f"Transaction ID: `{payment['transaction_id']}`"
        )
        kb = keyboards.get_admin_payment_approval_keyboard(payment['transaction_id'], lang)
        await message.answer(msg_text, reply_markup=kb, parse_mode="Markdown")

@router.message(F.text.in_([
    get_text('btn_admin_channels', 'en'), get_text('btn_admin_channels', 'ar'), get_text('btn_admin_channels', 'ru'),
    get_text('btn_admin_support', 'en'), get_text('btn_admin_support', 'ar'), get_text('btn_admin_support', 'ru'),
    get_text('btn_admin_charge', 'en'), get_text('btn_admin_charge', 'ar'), get_text('btn_admin_charge', 'ru'),
    get_text('btn_admin_referral', 'en'), get_text('btn_admin_referral', 'ar'), get_text('btn_admin_referral', 'ru'),
    get_text('btn_admin_api_keys', 'en'), get_text('btn_admin_api_keys', 'ar'), get_text('btn_admin_api_keys', 'ru'),
    get_text('btn_admin_button_emojis', 'en'), get_text('btn_admin_button_emojis', 'ar'), get_text('btn_admin_button_emojis', 'ru'),
    "📢 Channels Settings", "📢 إعدادات القنوات", "📢 Настройки каналов",
    "🎧 Support Settings", "🎧 إعدادات الدعم", "🎧 Настройки поддержки",
    "💳 Charge Section", "💳 إعدادات الدفع", "💳 Настройки оплаты",
    "👥 Referral System", "👥 نظام الإحالة", "👥 Реферальная система",
    "🔑 API Keys Settings", "🔑 إعدادات مفاتيح API", "🔑 Настройки API ключей",
    "🎨 Button Emojis", "🎨 إيموجيات الأزرار", "🎨 Эмодзи кнопок"
]))
async def get_admin_settings_content(menu: str, lang: str = 'en'):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    text = ""
    
    if menu == "admin_channels":
        force_join = await get_setting("force_join_channels", "None")
        news_ch = await get_setting("news_channel", "None")
        auto_proofs = await get_setting("auto_proofs_enabled", "0")
        proofs_icon = "🟢" if auto_proofs == "1" else "🔴"
        proofs_min = await get_setting("auto_proofs_min_minutes", "5")
        proofs_max = await get_setting("auto_proofs_max_minutes", "20")
        
        channels_list = ""
        if force_join and force_join != "None":
            ch_parts = [c.strip() for c in force_join.split(",") if c.strip()]
            for idx, c in enumerate(ch_parts, 1):
                channels_list += f"   {idx}. `{c}`\n"
        else:
            no_ch_dict = {
                'en': "   (No channels set)\n",
                'ar': "   (لم يتم تعيين قنوات)\n",
                'ru': "   (Каналы не заданы)\n"
            }
            channels_list = no_ch_dict.get(lang, no_ch_dict['en'])
            
        text = get_text(
            'admin_settings_channels_title',
            lang,
            channels_list=channels_list,
            news_ch=news_ch,
            auto_proofs="Enabled / مفعل" if auto_proofs == "1" else "Disabled / معطل",
            proofs_min=proofs_min,
            proofs_max=proofs_max
        )
        builder.button(text=get_text('btn_admin_set_force_join', lang), callback_data="admin_set_force_join")
        builder.button(text=get_text('btn_admin_set_news_ch', lang), callback_data="admin_set_news_ch")
        builder.button(text=get_text('btn_admin_auto_proofs_toggle', lang, status=proofs_icon), callback_data="admin_toggle_auto_proofs")
        builder.button(text=get_text('btn_admin_proofs_interval', lang, min_v=proofs_min, max_v=proofs_max), callback_data="admin_set_proofs_interval")
        
    elif menu == "admin_support_settings":
        support = await get_setting("support_username", "None")
        text = get_text('admin_settings_support_title', lang, support=support)
        builder.button(text=get_text('btn_admin_set_support', lang), callback_data="admin_set_support")
        
    elif menu == "admin_charge_settings":
        stars = await get_setting("stars_enabled", "1")
        stars_rate = await get_setting("stars_rate", "0.02")
        usdt_addr = await get_setting("crypto_addr_usdt", "0x89846777ea91dee2b25f0fcbf54884a4f79923d8")
        ltc_addr = await get_setting("crypto_addr_ltc", "LbEuNY2o5ePVyd7dqE4dTyNToAPDtcYMXR")
        ton_addr = await get_setting("crypto_addr_ton", "UQC8zbAwkf9-f8SzyYYITLU8Et4g-Cf7ffyQJIhip9nupHGo")
        binance_addr = await get_setting("crypto_addr_binance", "Not Configured")
        cryptotransfer = await get_setting("cryptotransfer_enabled", "1")
        cryptobot = await get_setting("cryptobot_enabled", "1")
        
        s_status = "✅ Enabled" if stars == "1" else "❌ Disabled"
        ct_status = "✅ Enabled" if cryptotransfer == "1" else "❌ Disabled"
        cb_status = "✅ Enabled" if cryptobot == "1" else "❌ Disabled"
        
        text = get_text(
            'admin_settings_charge_title',
            lang,
            stars_status=s_status,
            stars_rate=stars_rate,
            cb_status=cb_status,
            ct_status=ct_status,
            usdt_addr=usdt_addr,
            ltc_addr=ltc_addr,
            ton_addr=ton_addr,
            binance_addr=binance_addr
        )
        builder.button(text=get_text('btn_admin_toggle_stars', lang), callback_data="admin_toggle_stars")
        builder.button(text=get_text('btn_admin_set_stars_rate', lang), callback_data="admin_set_stars_rate")
        builder.button(text=get_text('btn_admin_toggle_cryptobot', lang), callback_data="admin_toggle_cryptobot")
        builder.button(text=get_text('btn_admin_toggle_cryptotransfer', lang), callback_data="admin_toggle_cryptotransfer")
        builder.button(text=get_text('btn_admin_set_usdt_addr', lang), callback_data="admin_set_crypto_addr_usdt")
        builder.button(text=get_text('btn_admin_set_ltc_addr', lang), callback_data="admin_set_crypto_addr_ltc")
        builder.button(text=get_text('btn_admin_set_ton_addr', lang), callback_data="admin_set_crypto_addr_ton")
        builder.button(text=get_text('btn_admin_set_binance_addr', lang), callback_data="admin_set_crypto_addr_binance")
        
    elif menu == "admin_referral_settings":
        fixed_bonus = await get_setting("referral_bonus_percent", "1.0")
        text = get_text('admin_settings_referral_title', lang, fixed_bonus=fixed_bonus)
        builder.button(text=get_text('btn_admin_set_ref_bonus', lang), callback_data="admin_set_ref_pct")
        
    elif menu == "admin_api_keys_settings":
        bscscan_key = (await get_setting("bscscan_api_key", "")) or "None"
        blockcypher_key = (await get_setting("blockcypher_api_key", "")) or "None"
        toncenter_key = (await get_setting("toncenter_api_key", "")) or "None"
        cryptobot_key = (await get_setting("cryptobot_token", "")) or "None"
        cryptobot_testnet = await get_setting("cryptobot_use_testnet", "0")
        cb_testnet_status = "🔌 TESTNET" if cryptobot_testnet == "1" else "⚡️ MAINNET"
        
        binance_proxy = (await get_setting("binance_api_proxy", "")) or "None"
        binance_api_key = (await get_setting("binance_api_key", "")) or "None"
        binance_secret_key = (await get_setting("binance_secret_key", "")) or "None"
        b_api_display = f"{binance_api_key[:8]}...{binance_api_key[-4:]}" if binance_api_key and binance_api_key != "None" and len(binance_api_key) > 12 else binance_api_key
        b_secret_display = f"{binance_secret_key[:8]}...{binance_secret_key[-4:]}" if binance_secret_key and binance_secret_key != "None" and len(binance_secret_key) > 12 else binance_secret_key
        
        text = get_text(
            'admin_settings_api_keys_title',
            lang,
            bscscan_key=bscscan_key,
            blockcypher_key=blockcypher_key,
            toncenter_key=toncenter_key,
            cryptobot_key=cryptobot_key,
            cb_testnet_status=cb_testnet_status,
            b_api_display=b_api_display,
            b_secret_display=b_secret_display,
            binance_proxy=binance_proxy
        )
        builder.button(text="✍️ Set BscScan API Key", callback_data="admin_set_bscscan_api_key")
        builder.button(text="✍️ Set Blockcypher API Token", callback_data="admin_set_blockcypher_api_key")
        builder.button(text="✍️ Set Toncenter API Key", callback_data="admin_set_toncenter_api_key")
        builder.button(text="✍️ Set Crypto Bot Token", callback_data="admin_set_cryptobot_api_key")
        builder.button(text="Toggle Crypto Bot Env", callback_data="admin_toggle_cryptobot_testnet")
        builder.button(text="🔶 Set Binance API Key", callback_data="admin_set_binance_api_key")
        builder.button(text="🔶 Set Binance Secret Key", callback_data="admin_set_binance_secret_key")
        builder.button(text="🌐 Set Binance Proxy", callback_data="admin_set_binance_api_proxy")
        
    elif menu == "admin_emoji_settings":
        emojis = await get_button_emojis()
        welcome_eid = await get_setting('welcome_emoji_id', '')
        btn_names = {
            'shop': get_text('btn_shop', lang),
            'orders': get_text('btn_my_orders', lang),
            'charge': get_text('btn_charge', lang),
            'referral': get_text('btn_referral', lang),
            'support': get_text('btn_support', lang),
            'language': get_text('btn_language', lang),
            'admin': get_text('btn_admin_panel', lang),
        }
        w_status = f"`{welcome_eid[:12]}...`" if welcome_eid else "❌ None"
        text = get_text('admin_settings_emoji_title', lang) + "\n\n"
        text += f"🔷 *Welcome Emoji:* {w_status}\n"
        text += "──────────────\n"
        for key, name in btn_names.items():
            emoji_id = emojis.get(key)
            status = f"`{emoji_id[:12]}...`" if emoji_id else "❌ None"
            text += f"▫️ {name}: {status}\n"
        
        builder.button(text="🔷 Welcome Emoji", callback_data="admin_set_btn_emoji_welcome")
        for key, name in btn_names.items():
            builder.button(text=f"🎨 {name}", callback_data=f"admin_set_btn_emoji_{key}")
    
    builder.button(text=get_text('btn_admin_back_to_panel', lang), callback_data="admin_menu")
    builder.adjust(1)
    return text, builder.as_markup()

async def msg_admin_settings_menu(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    
    t = message.text
    if t in [get_text('btn_admin_channels', 'en'), get_text('btn_admin_channels', 'ar'), get_text('btn_admin_channels', 'ru'), "📢 Channels Settings", "📢 إعدادات القنوات", "📢 Настройки каналов"]:
        menu = "admin_channels"
    elif t in [get_text('btn_admin_support', 'en'), get_text('btn_admin_support', 'ar'), get_text('btn_admin_support', 'ru'), "🎧 Support Settings", "🎧 إعدادات الدعم", "🎧 Настройки поддержки"]:
        menu = "admin_support_settings"
    elif t in [get_text('btn_admin_charge', 'en'), get_text('btn_admin_charge', 'ar'), get_text('btn_admin_charge', 'ru'), "💳 Charge Section", "💳 إعدادات الدفع", "💳 Настройки оплаты"]:
        menu = "admin_charge_settings"
    elif t in [get_text('btn_admin_referral', 'en'), get_text('btn_admin_referral', 'ar'), get_text('btn_admin_referral', 'ru'), "👥 Referral System", "👥 نظام الإحالة", "👥 Реферальная система"]:
        menu = "admin_referral_settings"
    elif t in [get_text('btn_admin_api_keys', 'en'), get_text('btn_admin_api_keys', 'ar'), get_text('btn_admin_api_keys', 'ru'), "🔑 API Keys Settings", "🔑 إعدادات مفاتيح API", "🔑 Настройки API ключей"]:
        menu = "admin_api_keys_settings"
    elif t in [get_text('btn_admin_button_emojis', 'en'), get_text('btn_admin_button_emojis', 'ar'), get_text('btn_admin_button_emojis', 'ru'), "🎨 Button Emojis", "🎨 إيموجيات الأزرار", "🎨 Эмодзи кнопок"]:
        menu = "admin_emoji_settings"
    else:
        menu = "admin_channels"
    
    text, reply_markup = await get_admin_settings_content(menu, lang)
    await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.message(F.text.in_([
    get_text('btn_admin_broadcast', 'en'),
    get_text('btn_admin_broadcast', 'ar'),
    get_text('btn_admin_broadcast', 'ru'),
    "📣 Broadcast", "📣 رسالة جماعية", "📣 Рассылка"
]))
async def msg_admin_broadcast_trigger(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await message.answer(get_text('admin_broadcast_prompt', lang), parse_mode="Markdown")

@router.message(F.text.in_([
    get_text('btn_admin_back_to_menu', 'en'),
    get_text('btn_admin_back_to_menu', 'ar'),
    get_text('btn_admin_back_to_menu', 'ru'),
    "🔙 Back to Main Menu", "🔙 العودة للقائمة الرئيسية", "🔙 Главное меню"
]))
async def msg_admin_back_to_user_menu(message: Message):
    if not is_user_admin(message.from_user.id):
        return
    user_id = message.from_user.id
    db_user = await get_user(user_id)
    lang = db_user['language'] if db_user else 'en'
    
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
        name=message.from_user.first_name, 
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
        reply_markup=keyboards.get_main_menu(lang, is_admin=True, button_emojis=button_emojis),
        parse_mode="HTML"
    )

# --- Manage Products ---
@router.callback_query(F.data == "admin_manage_products")
async def cb_admin_manage_products(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
        
    products = await get_products()
    
    # Inline buttons for managing products
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('btn_admin_add_product', lang), callback_data="admin_prod_add")
    
    for prod in products:
        name = get_product_name(prod, lang)
        builder.button(text=f"✏️ {name} (${prod['price']:.2f})", callback_data=f"admin_prod_view_{prod['id']}")
        
    builder.button(text=get_text('btn_admin_back_to_panel', lang), callback_data="admin_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        get_text('admin_prod_mgmt_title', lang),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_prod_view_"))
async def cb_admin_prod_view(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
        
    try:
        prod_id = int(callback.data.replace("admin_prod_view_", ""))
        product = await get_product(prod_id)
        if not product:
            await callback.answer("Product not found.")
            return
            
        stock = await get_stock_count(prod_id)
        from utils import format_product_message
        text, entities, parse_mode = format_product_message(product, lang, stock, discount_pct=0.0)
        
        kb = keyboards.get_admin_product_edit_keyboard(prod_id, lang)
        if entities:
            try:
                await callback.message.edit_text(text, reply_markup=kb, entities=entities)
            except Exception as e:
                logger.warning(f"admin edit_text with entities failed: {e}, falling back to plain text")
                await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
        else:
            try:
                await callback.message.edit_text(text, reply_markup=kb, parse_mode=parse_mode)
            except Exception as e:
                logger.warning(f"admin edit_text with parse_mode={parse_mode} failed: {e}, falling back to plain text")
                await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
    except Exception as outer_err:
        logger.error(f"Error in cb_admin_prod_view: {outer_err}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

@router.callback_query(F.data.startswith("admin_prod_del_"))
async def cb_admin_prod_del(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    prod_id = int(callback.data.replace("admin_prod_del_", ""))
    await delete_product(prod_id)
    await callback.answer(get_text('admin_prod_del_success', lang), show_alert=True)
    await cb_admin_manage_products(callback, lang)

# --- Add Product FSM ---
@router.callback_query(F.data == "admin_prod_add")
async def cb_admin_prod_add(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(ProductStates.waiting_for_name)
    await callback.message.answer(get_text('admin_prod_add_name_prompt', lang))
    await callback.answer()

@router.message(ProductStates.waiting_for_name)
async def add_prod_name(message: Message, state: FSMContext, lang='en'):
    await state.update_data(name=message.text.strip())
    await state.set_state(ProductStates.waiting_for_desc)
    await message.answer(get_text('admin_prod_add_desc_prompt', lang))

@router.message(ProductStates.waiting_for_desc)
async def add_prod_desc(message: Message, state: FSMContext, lang='en'):
    desc_text = (message.text or message.caption or "").strip()
    entities = message.entities or message.caption_entities
    from utils import serialize_entities
    entities_json = serialize_entities(entities)
    
    await state.update_data(desc=desc_text, desc_entities=entities_json)
    await state.set_state(ProductStates.waiting_for_price)
    await message.answer(get_text('admin_prod_add_price_prompt', lang), parse_mode="Markdown")

@router.message(ProductStates.waiting_for_price)
async def add_prod_price(message: Message, state: FSMContext, bot: Bot, lang='en'):
    try:
        price = float(message.text.strip().replace("$", ""))
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('admin_invalid_price', lang))
        return
        
    await state.update_data(price=price)
    await state.set_state(ProductStates.waiting_for_custom_emoji)
    await message.answer(
        get_text('admin_prod_add_emoji_prompt', lang),
        reply_markup=keyboards.get_admin_back_keyboard(lang)
    )

@router.message(ProductStates.waiting_for_custom_emoji)
async def add_prod_custom_emoji(message: Message, state: FSMContext, bot: Bot, lang='en'):
    custom_emoji_id = None
    if message.text != '/skip' and message.entities:
        for entity in message.entities:
            if entity.type == 'custom_emoji':
                custom_emoji_id = entity.custom_emoji_id
                break
                
    data = await state.get_data()
    await state.clear()
    
    product_name = data.get('name')
    product_desc = data.get('desc')
    desc_entities = data.get('desc_entities')
    price = data.get('price')
    
    if not product_name:
        await message.answer("❌ Session expired. Please try again.")
        return
        
    product_id = await add_product(
        name_ar=product_name,
        name_en=product_name,
        name_ru=product_name,
        description_ar=product_desc,
        description_en=product_desc,
        description_ru=product_desc,
        price=price,
        custom_emoji_id=custom_emoji_id,
        description_entities_ar=desc_entities,
        description_entities_en=desc_entities,
        description_entities_ru=desc_entities
    )
    
    await message.answer(
        get_text('admin_prod_add_success', lang),
        reply_markup=keyboards.get_admin_back_keyboard(lang)
    )
    
    # Broadcast to all users in private chat
    from database import broadcast_new_product_to_users
    await broadcast_new_product_to_users(message.bot, product_id)
    
    # Broadcast to news channel if configured
    news_channel = await get_setting('news_channel', '')
    if news_channel:
        try:
            import html
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            escaped_name = html.escape(product_name)
            escaped_desc = html.escape(product_desc)
            announce_text = (
                f"🔥 <b>NEW PRODUCT AVAILABLE</b> 🔥\n"
                f"──────────────────\n"
                f"📦 <b>Name:</b> <code>{escaped_name}</code>\n"
                f"💵 <b>Price:</b> <code>${price:.2f} USD</code>\n\n"
                f"📝 <b>Description:</b>\n"
                f"<i>{escaped_desc}</i>\n"
                f"──────────────────\n"
                f"👉 <i>Get it now:</i> @{bot_username}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Buy Now", url=f"https://t.me/{bot_username}")]
            ])
            await bot.send_message(chat_id=news_channel, text=announce_text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to log new product announcement: {e}")

# --- Edit Product FSM ---
@router.callback_query(F.data.startswith("admin_edit_fields_"))
async def cb_admin_edit_fields(callback: CallbackQuery, state: FSMContext, lang='en'):
    prod_id = int(callback.data.replace("admin_edit_fields_", ""))
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_admin_field_name', lang), callback_data=f"admin_edit_spec_{prod_id}_name")
    builder.button(text=get_text('btn_admin_field_desc', lang), callback_data=f"admin_edit_spec_{prod_id}_desc")
    builder.button(text=get_text('btn_admin_field_price', lang), callback_data=f"admin_edit_spec_{prod_id}_price")
    builder.button(text=get_text('btn_admin_back', lang), callback_data=f"admin_prod_view_{prod_id}")
    builder.adjust(1)
    
    prod_name = get_product_name(product, lang)
    await callback.message.edit_text(
        get_text('admin_prod_edit_fields_title', lang, name=prod_name),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_edit_spec_"))
async def cb_admin_edit_specific(callback: CallbackQuery, state: FSMContext, lang='en'):
    parts = callback.data.split("_")
    prod_id = int(parts[3])
    field = "_".join(parts[4:])
    
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    await state.update_data(edit_prod_id=prod_id, edit_field=field)
    
    field_labels = {
        "name": get_text('btn_admin_field_name', lang),
        "desc": get_text('btn_admin_field_desc', lang),
        "price": get_text('btn_admin_field_price', lang)
    }
    
    field_label = field_labels.get(field, field)
    await state.set_state(ProductStates.waiting_for_edit_specific_value)
    
    await callback.message.answer(
        get_text('admin_prod_edit_val_prompt', lang, field=field_label),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(ProductStates.waiting_for_edit_specific_value)
async def process_edit_specific_value(message: Message, state: FSMContext, bot: Bot, lang='en'):
    data = await state.get_data()
    prod_id = data.get("edit_prod_id")
    field = data.get("edit_field")
    
    if not prod_id or not field:
        await state.clear()
        await message.answer("❌ Session expired. Try again.")
        return
        
    val = message.text.strip()
    
    product = await get_product(prod_id)
    if not product:
        await state.clear()
        await message.answer("❌ Product not found.")
        return
        
    prod_dict = dict(product) if product else {}
    name_ar = product['name_ar']
    name_en = product['name_en']
    name_ru = product['name_ru']
    description_ar = product['description_ar']
    description_en = product['description_en']
    description_ru = product['description_ru']
    description_entities_ar = prod_dict.get('description_entities_ar')
    description_entities_en = prod_dict.get('description_entities_en')
    description_entities_ru = prod_dict.get('description_entities_ru')
    price = product['price']
    
    # Check if column exists in row (it should since we added it, but just in case)
    custom_emoji_id = prod_dict.get('custom_emoji_id')
    
    if field == "name":
        name_ar = val
        name_en = val
        name_ru = val
    elif field == "desc":
        desc_text = (message.text or message.caption or "").strip()
        description_ar = desc_text
        description_en = desc_text
        description_ru = desc_text
        from utils import serialize_entities
        entities_json = serialize_entities(message.entities or message.caption_entities)
        description_entities_ar = entities_json
        description_entities_en = entities_json
        description_entities_ru = entities_json
    elif field == "price":
        try:
            price = float(val.replace("$", ""))
            if price < 0:
                raise ValueError()
        except ValueError:
            await message.answer(get_text('admin_invalid_price', lang))
            return
            
    await state.clear()
    
    await update_product(
        product_id=prod_id,
        name_ar=name_ar,
        name_en=name_en,
        name_ru=name_ru,
        description_ar=description_ar,
        description_en=description_en,
        description_ru=description_ru,
        price=price,
        custom_emoji_id=custom_emoji_id,
        bot=bot,
        description_entities_ar=description_entities_ar,
        description_entities_en=description_entities_en,
        description_entities_ru=description_entities_ru
    )
    
    field_labels = {
        "name": get_text('btn_admin_field_name', lang),
        "desc": get_text('btn_admin_field_desc', lang),
        "price": get_text('btn_admin_field_price', lang)
    }
    field_label = field_labels.get(field, field)
    
    await message.answer(
        get_text('admin_prod_edit_success', lang, field=field_label),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_edit_emoji_"))
async def cb_admin_edit_emoji(callback: CallbackQuery, state: FSMContext, lang='en'):
    prod_id = int(callback.data.replace("admin_edit_emoji_", ""))
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    await state.update_data(edit_prod_id=prod_id)
    await state.set_state(ProductStates.waiting_for_edit_custom_emoji)
    
    prod_name = get_product_name(product, lang)
    await callback.message.answer(
        get_text('admin_prod_edit_emoji_prompt', lang, name=prod_name),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(ProductStates.waiting_for_edit_custom_emoji)
async def process_edit_emoji(message: Message, state: FSMContext, bot: Bot, lang='en'):
    data = await state.get_data()
    prod_id = data.get("edit_prod_id")
    
    if not prod_id:
        await state.clear()
        await message.answer("❌ Session expired. Try again.")
        return
        
    product = await get_product(prod_id)
    if not product:
        await state.clear()
        await message.answer("❌ Product not found.")
        return
        
    custom_emoji_id = None
    if message.text != '/skip' and message.text != 'remove' and message.entities:
        for entity in message.entities:
            if entity.type == 'custom_emoji':
                custom_emoji_id = entity.custom_emoji_id
                break
                
    prod_dict = dict(product) if product else {}
    await update_product(
        product_id=prod_id,
        name_ar=product['name_ar'],
        name_en=product['name_en'],
        name_ru=product['name_ru'],
        description_ar=product['description_ar'],
        description_en=product['description_en'],
        description_ru=product['description_ru'],
        price=product['price'],
        custom_emoji_id=custom_emoji_id,
        bot=bot,
        description_entities_ar=prod_dict.get('description_entities_ar'),
        description_entities_en=prod_dict.get('description_entities_en'),
        description_entities_ru=prod_dict.get('description_entities_ru')
    )
    
    await state.clear()
    await message.answer(
        get_text('admin_prod_edit_emoji_success', lang),
        reply_markup=keyboards.get_admin_back_keyboard(lang)
    )

# --- Product Tier Prices Management ---
@router.callback_query(F.data.startswith("admin_prod_tiers_"))
async def cb_admin_prod_tiers(callback: CallbackQuery, lang='en'):
    prod_id = int(callback.data.replace("admin_prod_tiers_", ""))
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    from utils import format_product_tier_prices_text
    tiers_text = format_product_tier_prices_text(product, lang=lang)
    if not tiers_text:
        tiers_text = {"en": "❌ No tier prices added yet.", "ar": "❌ لا توجد أسعار جملة مضافة لهذا المنتج حالياً.", "ru": "❌ Оптовые цены пока не настроены."}.get(lang, "❌ No tier prices added yet.")
        
    prod_name = get_product_name(product, lang)
    text = get_text('admin_tier_prices_title', lang, name=prod_name, price=product['price'], tiers_text=tiers_text)
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_tier_prices_keyboard(prod_id, lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_add_tier_"))
async def cb_admin_add_tier(callback: CallbackQuery, state: FSMContext, lang='en'):
    prod_id = int(callback.data.replace("admin_add_tier_", ""))
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    await state.set_state(ProductStates.waiting_for_tier_min_qty)
    await state.update_data(tier_prod_id=prod_id)
    
    await callback.message.answer(
        get_text('admin_tier_min_qty_prompt', lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(ProductStates.waiting_for_tier_min_qty)
async def process_tier_min_qty(message: Message, state: FSMContext, lang='en'):
    try:
        min_qty = int(message.text.strip())
        if min_qty <= 1:
            raise ValueError()
    except ValueError:
        err_msg = {"en": "❌ Invalid quantity. Minimum quantity must be a positive integer greater than 1 (e.g. `5`):", "ar": "❌ كمية غير صالحة. يجب أن يكون الحد الأدنى للكمية رقماً صحيحاً أكبر من 1 (مثال: `5`):", "ru": "❌ Неверное количество. Минимальное количество должно быть больше 1 (например `5`):"}.get(lang, "❌ Invalid quantity.")
        await message.answer(err_msg, parse_mode="Markdown")
        return
        
    await state.update_data(tier_min_qty=min_qty)
    await state.set_state(ProductStates.waiting_for_tier_unit_price)
    
    await message.answer(
        get_text('admin_tier_unit_price_prompt', lang, qty=min_qty),
        parse_mode="Markdown"
    )

@router.message(ProductStates.waiting_for_tier_unit_price)
async def process_tier_unit_price(message: Message, state: FSMContext, lang='en'):
    try:
        unit_price = float(message.text.strip().replace("$", ""))
        if unit_price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('admin_invalid_price', lang))
        return
        
    data = await state.get_data()
    prod_id = data.get("tier_prod_id")
    min_qty = data.get("tier_min_qty")
    await state.clear()
    
    if not prod_id or not min_qty:
        await message.answer("❌ Session expired. Try again.")
        return
        
    product = await get_product(prod_id)
    if not product:
        await message.answer("❌ Product not found.")
        return
        
    prod_dict = dict(product) if product else {}
    tier_json = prod_dict.get('tier_prices')
    import json
    tiers = []
    if tier_json:
        try:
            tiers = json.loads(tier_json)
            if not isinstance(tiers, list):
                tiers = []
        except Exception:
            tiers = []
            
    # Remove existing tier with same min_qty if exists, then add new tier
    tiers = [t for t in tiers if int(t.get('min_qty', 0)) != min_qty]
    tiers.append({"min_qty": min_qty, "unit_price": unit_price})
    
    from database import update_product_tier_prices
    await update_product_tier_prices(prod_id, json.dumps(tiers))
    
    await message.answer(
        get_text('admin_tier_add_success', lang, qty=min_qty, unit_price=unit_price),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_clear_tiers_"))
async def cb_admin_clear_tiers(callback: CallbackQuery, lang='en'):
    prod_id = int(callback.data.replace("admin_clear_tiers_", ""))
    from database import update_product_tier_prices
    await update_product_tier_prices(prod_id, None)
    
    await callback.message.edit_text(
        get_text('admin_tier_clear_success', lang),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- Product Pricing Strategy Management ---
@router.callback_query(F.data.startswith("admin_prod_pricing_"))
async def cb_admin_prod_pricing(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    prod_id = int(callback.data.replace("admin_prod_pricing_", ""))
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    prod_dict = dict(product)
    p_type = prod_dict.get('pricing_type') or 'fixed'
    m_val = float(prod_dict.get('margin_value') or 0.0)
    min_p = float(prod_dict.get('min_price') or 0.0)
    cost = float(prod_dict.get('last_provider_cost') or 0.0)
    cur_price = float(prod_dict.get('price') or 0.0)
    prod_name = get_product_name(product, lang)
    
    type_labels = {
        'fixed': get_text('btn_pricing_type_fixed', lang),
        'margin_fixed': f"{get_text('btn_pricing_type_margin_fixed', lang)} (+${m_val:.2f})",
        'margin_percent': f"{get_text('btn_pricing_type_margin_percent', lang)} (+{m_val:.1f}%)"
    }
    
    text = (
        f"🏷️ *{get_text('btn_admin_pricing_strategy', lang)}*\n\n"
        f"📦 *Product:* `{prod_name}`\n"
        f"⚙️ *Current Strategy:* `{type_labels.get(p_type, p_type)}`\n"
        f"💵 *Wholesale Cost:* `${cost:.2f} USD`\n"
        f"🛡️ *Minimum Floor Price:* `${min_p:.2f} USD`\n"
        f"🛍️ *Current Selling Price:* `${cur_price:.2f} USD`\n\n"
        f"Select a new pricing strategy below:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_pricing_type_keyboard(lang=lang, is_import=False, product_id=prod_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_edit_ptype_"))
async def cb_admin_edit_ptype(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    parts = callback.data.replace("admin_edit_ptype_", "").split("_")
    prod_id = int(parts[0])
    ptype = "_".join(parts[1:])
    
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    prod_dict = dict(product)
    cost = float(prod_dict.get('last_provider_cost') or prod_dict.get('price') or 0.0)
    await state.update_data(edit_pricing_prod_id=prod_id, edit_pricing_type=ptype, edit_pricing_cost=cost)
    
    if ptype == 'fixed':
        await state.set_state(ProductStates.waiting_for_edit_price)
        await callback.message.edit_text(get_text('pricing_prompt_fixed', lang), parse_mode="Markdown")
    elif ptype == 'margin_fixed':
        await state.set_state(ProductStates.waiting_for_margin_value)
        await callback.message.edit_text(get_text('pricing_prompt_margin_fixed', lang, cost=cost), parse_mode="Markdown")
    elif ptype == 'margin_percent':
        await state.set_state(ProductStates.waiting_for_margin_value)
        await callback.message.edit_text(get_text('pricing_prompt_margin_percent', lang, cost=cost), parse_mode="Markdown")
    await callback.answer()

@router.message(ProductStates.waiting_for_edit_price)
async def process_edit_prod_fixed_price(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    try:
        price = float(message.text.strip().replace("$", ""))
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('admin_invalid_price', lang))
        return
        
    await state.update_data(edit_fixed_price=price, edit_pricing_type='fixed', edit_margin_value=0.0)
    await finalize_edit_product_pricing(message, state, min_price=0.0, lang=lang)

@router.message(ProductStates.waiting_for_margin_value)
async def process_edit_prod_margin_value(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    try:
        val = float(message.text.strip().replace("$", "").replace("%", ""))
        if val < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid margin value. Please enter a valid non-negative number:")
        return
        
    await state.update_data(edit_margin_value=val)
    data = await state.get_data()
    prod_id = data.get('edit_pricing_prod_id')
    ptype = data.get('edit_pricing_type')
    cost = float(data.get('edit_pricing_cost') or 0.0)
    
    from utils import calculate_dynamic_selling_price
    suggested_floor = calculate_dynamic_selling_price(ptype, val, 0.0, cost)
    await state.set_state(ProductStates.waiting_for_min_price)
    await message.answer(
        get_text('pricing_prompt_min_price', lang, suggested=suggested_floor),
        reply_markup=keyboards.get_admin_min_price_skip_keyboard(lang=lang, is_import=False, product_id=prod_id),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_edit_skip_min_"))
async def cb_admin_edit_skip_min(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    prod_id = int(callback.data.replace("admin_edit_skip_min_", ""))
    await finalize_edit_product_pricing(callback.message, state, min_price=0.0, lang=lang, prod_id_override=prod_id)
    await callback.answer()

@router.message(ProductStates.waiting_for_min_price)
async def process_edit_prod_min_price(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    try:
        min_p = float(message.text.strip().replace("$", ""))
        if min_p < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid floor price. Please enter a valid number:")
        return
    await finalize_edit_product_pricing(message, state, min_price=min_p, lang=lang)

async def finalize_edit_product_pricing(message_or_msg, state: FSMContext, min_price: float = 0.0, lang='en', prod_id_override=None):
    data = await state.get_data()
    prod_id = prod_id_override or data.get('edit_pricing_prod_id')
    ptype = data.get('edit_pricing_type', 'fixed')
    m_val = float(data.get('edit_margin_value') or 0.0)
    fixed_p = data.get('edit_fixed_price')
    
    if not prod_id:
        await message_or_msg.answer("❌ Session expired. Try again.")
        await state.clear()
        return
        
    from database import update_product_pricing_strategy
    await update_product_pricing_strategy(
        product_id=prod_id,
        pricing_type=ptype,
        margin_value=m_val,
        min_price=min_price,
        fixed_price=fixed_p,
        bot=message_or_msg.bot
    )
    
    prod = await get_product(prod_id)
    prod_name = get_product_name(prod, lang)
    new_price = float(prod['price'] if prod else 0.0)
    
    type_labels = {
        'fixed': get_text('btn_pricing_type_fixed', lang),
        'margin_fixed': f"{get_text('btn_pricing_type_margin_fixed', lang)} (+${m_val:.2f})",
        'margin_percent': f"{get_text('btn_pricing_type_margin_percent', lang)} (+{m_val:.1f}%)"
    }
    
    text = get_text('pricing_strategy_updated', lang, name=prod_name, type_name=type_labels.get(ptype, ptype), price=new_price)
    await message_or_msg.answer(text, reply_markup=keyboards.get_admin_back_keyboard(lang), parse_mode="Markdown")
    await state.clear()

# --- Stock Settings ---
@router.callback_query(F.data.in_(["admin_add_stock", "admin_bulk_stock"]))
async def cb_admin_stock_select_prod(callback: CallbackQuery, state: FSMContext, lang='en'):
    action = callback.data
    products = await get_products()
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for prod in products:
        name = get_product_name(prod, lang)
        builder.button(text=f"{name}", callback_data=f"admin_stk_{action.split('_')[1]}_{prod['id']}")
        
    builder.button(text=get_text('btn_admin_back_to_panel', lang), callback_data="admin_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        get_text('admin_stock_select_prod_prompt', lang),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_stk_"))
async def cb_admin_stock_prod_selected(callback: CallbackQuery, state: FSMContext, lang='en'):
    parts = callback.data.split("_")
    # format: admin_stk_add_PRODID or admin_stk_bulk_PRODID
    action_type = parts[2]
    prod_id = int(parts[3])
    
    await state.update_data(stock_prod_id=prod_id)
    
    product = await get_product(prod_id)
    prod_name = get_product_name(product, lang) if product else "Product"
    
    if action_type == "add":
        await state.set_state(StockStates.waiting_for_stock_data)
        await callback.message.answer(get_text('admin_stock_data_prompt', lang, name=prod_name), parse_mode="Markdown")
    else:
        await state.set_state(StockStates.waiting_for_bulk_stock)
        await callback.message.answer(get_text('admin_bulk_stock_prompt', lang, name=prod_name), parse_mode="Markdown")
        
    await callback.answer()

@router.message(StockStates.waiting_for_stock_data)
async def process_single_stock(message: Message, state: FSMContext, lang='en'):
    data = await state.get_data()
    prod_id = data.get("stock_prod_id")
    await state.clear()
    
    if not prod_id:
        await message.answer("❌ Session expired. Try again.")
        return
    
    if not message.text or not message.text.strip():
        await message.answer("❌ Please send a text message with the stock data.")
        return
        
    import re
    cleaned_text = re.sub(r'^\d+[\.\-\)]?\s+', '', message.text.strip()).strip()
    await add_stock(prod_id, cleaned_text)
    
    # Process any pending pre-order reservations first before restock broadcast
    from database import process_pending_pre_orders
    await process_pending_pre_orders(message.bot, prod_id)
    
    product = await get_product(prod_id)
    prod_name = get_product_name(product, lang) if product else "Product"
    total_stock = await get_stock_count(prod_id)
    
    await message.answer(
        get_text('admin_stock_add_success', lang, name=prod_name, stock=total_stock),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )
    
    # Notify admins about restock
    from database import notify_admins_stock_change
    await notify_admins_stock_change(message.bot, prod_id, 'refill', 1)
    
    # Broadcast restock notification to all subscribed users in private chats
    from database import broadcast_restock_to_users
    await broadcast_restock_to_users(message.bot, prod_id, 1)
    
    # Send News Channel announcement
    news_channel = await get_setting('news_channel', '')
    if news_channel and product:
        try:
            import html
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            bot_info = await message.bot.get_me()
            bot_username = bot_info.username
            prod_name_en = product['name_en'] or product['name_ar'] or "Product"
            escaped_prod_name = html.escape(prod_name_en)
            announce_text = (
                f"⚡️ <b>PRODUCT RESTOCKED</b> ⚡️\n"
                f"──────────────────\n"
                f"🛍 <b>Product:</b> <code>{escaped_prod_name}</code>\n"
                f"📦 <b>Items Added:</b> <code>1 unit</code>\n"
                f"💵 <b>Price:</b> <code>${product['price']:.2f} USD</code>\n"
                f"──────────────────\n"
                f"👉 <i>Available now at:</i> @{bot_username}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Shop Now", url=f"https://t.me/{bot_username}")]
            ])
            await message.bot.send_message(chat_id=news_channel, text=announce_text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to send single restock announcement to news channel: {e}")

@router.message(StockStates.waiting_for_bulk_stock)
async def process_bulk_stock(message: Message, state: FSMContext, bot: Bot, lang='en'):
    data = await state.get_data()
    prod_id = data.get("stock_prod_id")
    await state.clear()
    
    if not prod_id:
        await message.answer("❌ Session expired. Try again. / انتهت الجلسة، أعد المحاولة.")
        return
        
    text_content = ""
    if message.document:
        file_name = message.document.file_name or ""
        if not file_name.lower().endswith('.txt'):
            await message.answer("❌ Please upload a text file (.txt). / يرجى رفع ملف نصي بصيغة .txt")
            return
            
        from io import BytesIO
        file_buffer = BytesIO()
        await bot.download(message.document, destination=file_buffer)
        file_buffer.seek(0)
        text_content = file_buffer.read().decode('utf-8', errors='ignore')
    elif message.text:
        text_content = message.text
    else:
        await message.answer("❌ Please send stock items as text or upload a .txt file. / يرجى إرسال مخزون كنص أو رفع ملف .txt")
        return
        
    import re
    raw_lines = [line.strip() for line in text_content.split("\n") if line.strip()]
    
    # Check if there are any lines starting with a list number prefix (e.g. "1. ", "2- ")
    has_numbered_list = any(re.match(r'^\d+[\.\-\)]?\s+', line) for line in raw_lines)
    
    lines = []
    if has_numbered_list:
        current_item = []
        for line in raw_lines:
            match = re.match(r'^(\d+[\.\-\)]?\s+)(.*)', line)
            if match:
                if current_item:
                    lines.append("".join(current_item))
                remainder = match.group(2).strip()
                current_item = [remainder]
            else:
                if current_item:
                    current_item.append(line)
        if current_item:
            lines.append("".join(current_item))
    else:
        # Non-numbered list, treat each line as a separate item
        lines = raw_lines
        
    if not lines:
        await message.answer("❌ No valid items found in the input. / لم يتم العثور على عناصر صالحة.")
        return
        
    await bulk_add_stock(prod_id, lines)
    
    # Process any pending pre-orders immediately
    from database import process_pending_pre_orders
    await process_pending_pre_orders(message.bot, prod_id)
    
    product = await get_product(prod_id)
    prod_name = get_product_name(product, lang) if product else "Product"
    total_stock = await get_stock_count(prod_id)
    
    await message.answer(
        get_text('admin_bulk_stock_add_success', lang, count=len(lines), name=prod_name, stock=total_stock),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )
    
    # Notify admins about restock
    from database import notify_admins_stock_change
    await notify_admins_stock_change(message.bot, prod_id, 'refill', len(lines))
    
    # Broadcast restock notification to all subscribed users in private chats
    from database import broadcast_restock_to_users
    await broadcast_restock_to_users(message.bot, prod_id, len(lines))
            
    # Send News Channel announcement
    news_channel = await get_setting('news_channel', '')
    if news_channel and product:
        try:
            import html
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            escaped_prod_name = html.escape(product['name_en'] or product['name_ar'] or "Product")
            announce_text = (
                f"⚡️ <b>PRODUCT RESTOCKED</b> ⚡️\n"
                f"──────────────────\n"
                f"🛍 <b>Product:</b> <code>{escaped_prod_name}</code>\n"
                f"📦 <b>Items Added:</b> <code>{len(lines)} units</code>\n"
                f"💵 <b>Price:</b> <code>${product['price']:.2f} USD</code>\n"
                f"──────────────────\n"
                f"👉 <i>Available now at:</i> @{bot_username}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Shop Now", url=f"https://t.me/{bot_username}")]
            ])
            await bot.send_message(chat_id=news_channel, text=announce_text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to send restock announcement to news channel: {e}")

# --- Config Settings ---
@router.callback_query(F.data.in_([
    "admin_channels", "admin_support_settings", 
    "admin_charge_settings", "admin_referral_settings",
    "admin_api_keys_settings", "admin_emoji_settings"
]))
async def cb_admin_settings_menu(callback: CallbackQuery, menu: str = None, lang='en'):
    menu = menu or callback.data
    text, reply_markup = await get_admin_settings_content(menu, lang)
    await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    await callback.answer()

# --- Button Emoji Settings ---
@router.callback_query(F.data.startswith("admin_set_btn_emoji_"))
async def cb_admin_set_btn_emoji(callback: CallbackQuery, state: FSMContext, lang='en'):
    btn_key = callback.data.replace("admin_set_btn_emoji_", "")
    btn_names = {
        'welcome': {'en': "🔷 Welcome", 'ar': "🔷 الترحيب", 'ru': "🔷 Приветствие"},
        'shop': {'en': "🛒 Shop", 'ar': "🛒 المتجر", 'ru': "🛒 Магазин"},
        'orders': {'en': "📦 My Orders", 'ar': "📦 مشترياتي", 'ru': "📦 Мои заказы"},
        'charge': {'en': "💳 Charge", 'ar': "💳 شحن الرصيد", 'ru': "💳 Пополнить"},
        'referral': {'en': "👥 Referral", 'ar': "👥 الإحالة", 'ru': "👥 Рефералы"},
        'support': {'en': "🎧 Support", 'ar': "🎧 الدعم", 'ru': "🎧 Поддержка"},
        'language': {'en': "🌐 Language", 'ar': "🌐 اللغة", 'ru': "🌐 Язык"},
        'admin': {'en': "⚙️ Admin", 'ar': "⚙️ الإدارة", 'ru': "⚙️ Админ-панель"},
    }
    name_dict = btn_names.get(btn_key, {'en': btn_key, 'ar': btn_key, 'ru': btn_key})
    name = name_dict.get(lang, name_dict['en'])
    await state.update_data(btn_emoji_key=btn_key)
    await state.set_state(AdminStates.waiting_for_btn_emoji)
    
    prompt_dict = {
        'en': f"🎨 Send an animated Premium Custom Emoji for *{name}*, or type /skip to remove the current emoji.",
        'ar': f"🎨 أرسل إيموجي مميز ومتحرك (Premium Custom Emoji) لـ *{name}*، أو أرسل /skip لإزالة الإيموجي الحالي.",
        'ru': f"🎨 Отправьте анимированный эмодзи (Telegram Premium) для *{name}*, или введите /skip для удаления эмодзи."
    }
    await callback.message.answer(prompt_dict.get(lang, prompt_dict['en']), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_btn_emoji)
async def process_btn_emoji(message: Message, state: FSMContext, lang='en'):
    data = await state.get_data()
    btn_key = data.get("btn_emoji_key")
    await state.clear()
    
    if not btn_key:
        await message.answer("❌ Session expired. Try again.")
        return
    
    custom_emoji_id = ""
    if message.text != '/skip' and message.entities:
        for entity in message.entities:
            if entity.type == 'custom_emoji':
                custom_emoji_id = entity.custom_emoji_id
                break
    
    # Welcome emoji uses a different setting key
    if btn_key == 'welcome':
        await set_setting("welcome_emoji_id", custom_emoji_id)
    else:
        await set_setting(f"btn_emoji_{btn_key}", custom_emoji_id)
    
    if custom_emoji_id:
        success_dict = {
            'en': f"✅ Emoji set successfully for *{btn_key}* button!\nID: `{custom_emoji_id}`\n\n💡 Send /start to see the changes.",
            'ar': f"✅ تم تعيين الإيموجي بنجاح للزر *{btn_key}*!\nالمعرف: `{custom_emoji_id}`\n\n💡 أرسل /start لمشاهدة التغييرات.",
            'ru': f"✅ Эмодзи успешно установлен для кнопки *{btn_key}*!\nID: `{custom_emoji_id}`\n\n💡 Введите /start чтобы увидеть изменения."
        }
        await message.answer(
            success_dict.get(lang, success_dict['en']),
            reply_markup=keyboards.get_admin_back_keyboard(lang),
            parse_mode="Markdown"
        )
    else:
        removed_dict = {
            'en': f"✅ Emoji removed from *{btn_key}* button.\n\n💡 Send /start to see the changes.",
            'ar': f"✅ تم إزالة الإيموجي من الزر *{btn_key}*.\n\n💡 أرسل /start لمشاهدة التغييرات.",
            'ru': f"✅ Эмодзи удален с кнопки *{btn_key}*.\n\n💡 Введите /start чтобы увидеть изменения."
        }
        await message.answer(
            removed_dict.get(lang, removed_dict['en']),
            reply_markup=keyboards.get_admin_back_keyboard(lang),
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "admin_toggle_auto_proofs")
async def cb_admin_toggle_auto_proofs(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    current = await get_setting("auto_proofs_enabled", "0")
    new_val = "0" if current == "1" else "1"
    await set_setting("auto_proofs_enabled", new_val)
    
    status_msg = "مفعل 🟢" if new_val == "1" else "معطل 🔴"
    await callback.answer(f"📢 {status_msg}", show_alert=False)
    
    text, reply_markup = await get_admin_settings_content("admin_channels", lang)
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        pass

# Settings FSM triggers
@router.callback_query(F.data.startswith("admin_set_"))
async def cb_admin_set_setting(callback: CallbackQuery, state: FSMContext, lang='en'):
    setting_key = callback.data.replace("admin_set_", "")
    await state.update_data(setting_key=setting_key)
    await state.set_state(AdminStates.waiting_for_setting_value)
    
    prompts = {
        "force_join": {
            'en': "📢 Enter channels list (comma-separated, e.g. `@channel1,@my_channel` or leave blank to disable):",
            'ar': "📢 أدخل قائمة القنوات مفصولة بفاصلة (مثال: `@channel1,@my_channel` أو اتركها فارغة للتعطيل):",
            'ru': "📢 Введите список каналов через запятую (напр. `@channel1,@my_channel` или оставьте пустым):"
        },
        "news_ch": {
            'en': "📣 Enter news channel username or ID (e.g. `@my_news_channel` or `-10012345678`):",
            'ar': "📣 أدخل معرف قناة الأخبار أو الآيدي (مثال: `@my_news_channel` أو `-10012345678`):",
            'ru': "📣 Введите юзернейм или ID новостного канала (напр. `@my_news_channel` или `-10012345678`):"
        },
        "support": {
            'en': "🎧 Enter support handler username (e.g. `@support_username`):",
            'ar': "🎧 أدخل يوزر حساب الدعم الفني (مثال: `@support_username`):",
            'ru': "🎧 Введите юзернейм аккаунта поддержки (напр. `@support_username`):"
        },
        "stars_rate": {
            'en': "💱 Enter exchange rate (USD value per 1 Star, e.g. `0.02`):",
            'ar': "💱 أدخل سعر الصرف (قيمة النجمة بالدولار، مثال: `0.02`):",
            'ru': "💱 Введите курс обмена (стоимость 1 Star в USD, напр. `0.02`):"
        },
        "ref_pct": {
            'en': "👥 Enter fixed referral bonus in USD (awarded instantly on sign up, e.g. `1.50`):",
            'ar': "👥 أدخل مكافأة الإحالة الثابتة بالدولار (تمنح فوراً عند التسجيل، مثال: `1.50`):",
            'ru': "👥 Введите фиксированный реферальный бонус в USD (напр. `1.50`):"
        },
        "crypto_addr_usdt": {
            'en': "🪙 Enter new USDT BEP20 address:",
            'ar': "🪙 أدخل عنوان USDT BEP20 الجديد:",
            'ru': "🪙 Введите новый адрес USDT BEP20:"
        },
        "crypto_addr_ltc": {
            'en': "🪙 Enter new Litecoin (LTC) address:",
            'ar': "🪙 أدخل عنوان Litecoin (LTC) الجديد:",
            'ru': "🪙 Введите новый адрес Litecoin (LTC):"
        },
        "crypto_addr_ton": {
            'en': "🪙 Enter new TON address:",
            'ar': "🪙 أدخل عنوان TON الجديد:",
            'ru': "🪙 Введите новый адрес TON:"
        },
        "crypto_addr_binance": {
            'en': "🪙 Enter new Binance Pay ID / Email / Phone:",
            'ar': "🪙 أدخل معرف / إيميل / رقم Binance Pay الجديد:",
            'ru': "🪙 Введите новый Binance Pay ID / Email / Phone:"
        },
        "bscscan_api_key": {
            'en': "🔸 Enter BscScan API Key (get from https://bscscan.com/myapikey):",
            'ar': "🔸 أدخل مفتاح BscScan API:",
            'ru': "🔸 Введите BscScan API Key:"
        },
        "blockcypher_api_key": {
            'en': "🪙 Enter Blockcypher API Token (get from https://accounts.blockcypher.com/):",
            'ar': "🪙 أدخل توكن Blockcypher API:",
            'ru': "🪙 Введите Blockcypher API Token:"
        },
        "toncenter_api_key": {
            'en': "💎 Enter Toncenter API Key (get from @toncenter bot: https://t.me/toncenter):",
            'ar': "💎 أدخل مفتاح Toncenter API:",
            'ru': "💎 Введите Toncenter API Key:"
        },
        "cryptobot_api_key": {
            'en': "🤖 Enter Crypto Bot API token (get from @CryptoPayTestVar or @CryptoBot):",
            'ar': "🤖 أدخل توكن Crypto Bot API:",
            'ru': "🤖 Введите токен Crypto Bot API:"
        },
        "binance_api_proxy": {
            'en': "🌐 Enter Binance API Proxy (e.g. `http://user:pass@ip:port` or `socks5://ip:port`, or leave blank to disable):",
            'ar': "🌐 أدخل بروكسي بينانس (مثال: `http://user:pass@ip:port` أو اتركه فارغاً للتعطيل):",
            'ru': "🌐 Введите прокси Binance (напр. `http://user:pass@ip:port` или оставьте пустым):"
        },
        "binance_api_key": {
            'en': "🔶 Enter your Binance API Key (get from https://www.binance.com/en/my/settings/api-management):",
            'ar': "🔶 أدخل مفتاح Binance API الخاص بك:",
            'ru': "🔶 Введите ваш Binance API Key:"
        },
        "binance_secret_key": {
            'en': "🔶 Enter your Binance Secret Key:",
            'ar': "🔶 أدخل المفتاح السري Binance Secret Key:",
            'ru': "🔶 Введите ваш Binance Secret Key:"
        },
        "proofs_interval": {
            'en': "⏱️ Enter interval in minutes for auto sales proofs (e.g. `5-20` or `15`):",
            'ar': "⏱️ أدخل الفاصل الزمني بالدقائق للنشر التلقائي للمبيعات (مثال: `5-20` أو `15`):",
            'ru': "⏱️ Введите интервал в минутах для авто-публикации продаж (напр. `5-20` или `15`):"
        }
    }
    
    p_dict = prompts.get(setting_key, {'en': "Enter new value:", 'ar': "أدخل القيمة الجديدة:", 'ru': "Введите новое значение:"})
    prompt = p_dict.get(lang, p_dict['en'])
    await callback.message.answer(prompt, parse_mode="Markdown")
    await callback.answer()
 
@router.message(AdminStates.waiting_for_setting_value)
async def process_setting_value(message: Message, state: FSMContext, lang='en'):
    data = await state.get_data()
    setting_key = data.get("setting_key")
    await state.clear()
    
    val = message.text.strip()
    
    if setting_key == "proofs_interval":
        val_str = val.strip()
        if "-" in val_str:
            parts = val_str.split("-")
            try:
                v1 = abs(int(parts[0].strip()))
                v2 = abs(int(parts[1].strip()))
                min_v = max(1, min(v1, v2))
                max_v = max(min_v, max(v1, v2))
                await set_setting("auto_proofs_min_minutes", str(min_v))
                await set_setting("auto_proofs_max_minutes", str(max_v))
                await message.answer(f"✅ تم ضبط الفاصل الزمني للنشر التلقائي: من {min_v} إلى {max_v} دقيقة.", reply_markup=keyboards.get_admin_back_keyboard(lang))
            except Exception:
                await message.answer("❌ صيغة غير صحيحة. يرجى إدخال أرقام صحيحة مثل `5-20` أو `15`.")
        else:
            try:
                fixed_v = abs(int(val_str))
                if fixed_v > 0:
                    await set_setting("auto_proofs_min_minutes", str(fixed_v))
                    await set_setting("auto_proofs_max_minutes", str(fixed_v))
                    await message.answer(f"✅ تم ضبط الفاصل الزمني للنشر التلقائي: كل {fixed_v} دقيقة بالضبط.", reply_markup=keyboards.get_admin_back_keyboard(lang))
                else:
                    raise ValueError()
            except Exception:
                await message.answer("❌ صيغة غير صحيحة. يرجى إدخال أرقام صحيحة مثل `5-20` أو `15`.")
        return

    # Save setting key mappings
    db_keys = {
        "force_join": "force_join_channels",
        "news_ch": "news_channel",
        "support": "support_username",
        "stars_rate": "stars_rate",
        "ref_pct": "referral_bonus_percent",
        "crypto_addr_usdt": "crypto_addr_usdt",
        "crypto_addr_ltc": "crypto_addr_ltc",
        "crypto_addr_ton": "crypto_addr_ton",
        "crypto_addr_binance": "crypto_addr_binance",
        "bscscan_api_key": "bscscan_api_key",
        "blockcypher_api_key": "blockcypher_api_key",
        "toncenter_api_key": "toncenter_api_key",
        "cryptobot_api_key": "cryptobot_token",
        "binance_api_proxy": "binance_api_proxy",
        "binance_api_key": "binance_api_key",
        "binance_secret_key": "binance_secret_key"
    }
    
    db_key = db_keys.get(setting_key)
    if not db_key:
        await message.answer("❌ Invalid setting key.")
        return
        
    # Validate number keys
    if setting_key in ["stars_rate", "ref_pct"]:
        try:
            float(val)
        except ValueError:
            await message.answer("❌ Invalid number value. Change discarded.")
            return
            
    await set_setting(db_key, val)
    await message.answer(f"✅ Setting `{db_key}` updated to `{val}` successfully!", reply_markup=keyboards.get_admin_back_keyboard(lang))
 
# Toggle Settings
@router.callback_query(F.data == "admin_toggle_stars")
async def cb_admin_toggle_payment(callback: CallbackQuery, lang='en'):
    method = "stars_enabled"
    current = await get_setting(method, "1")
    new_val = "0" if current == "1" else "1"
    await set_setting(method, new_val)
    
    await callback.answer(f"✅")
    # Reload settings menu without mutating callback.data
    await cb_admin_settings_menu(callback, menu="admin_charge_settings", lang=lang)

@router.callback_query(F.data == "admin_toggle_cryptotransfer")
async def cb_admin_toggle_cryptotransfer(callback: CallbackQuery, lang='en'):
    method = "cryptotransfer_enabled"
    current = await get_setting(method, "1")
    new_val = "0" if current == "1" else "1"
    await set_setting(method, new_val)
    
    await callback.answer(f"✅")
    await cb_admin_settings_menu(callback, menu="admin_charge_settings", lang=lang)

@router.callback_query(F.data == "admin_toggle_cryptobot")
async def cb_admin_toggle_cryptobot(callback: CallbackQuery, lang='en'):
    method = "cryptobot_enabled"
    current = await get_setting(method, "1")
    new_val = "0" if current == "1" else "1"
    await set_setting(method, new_val)
    
    await callback.answer(f"✅")
    await cb_admin_settings_menu(callback, menu="admin_charge_settings", lang=lang)

@router.callback_query(F.data == "admin_toggle_cryptobot_testnet")
async def cb_admin_toggle_cryptobot_testnet(callback: CallbackQuery, lang='en'):
    method = "cryptobot_use_testnet"
    current = await get_setting(method, "0")
    new_val = "0" if current == "1" else "1"
    await set_setting(method, new_val)
    
    await callback.answer(f"✅")
    await cb_admin_settings_menu(callback, menu="admin_api_keys_settings", lang=lang)

# --- Admin Broadcast ---
@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast_trigger(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer(get_text('admin_broadcast_prompt', lang), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_admin_broadcast(message: Message, state: FSMContext, bot: Bot, lang='en'):
    user_id = message.from_user.id
    if not is_user_admin(user_id):
        await state.clear()
        return
        
    await state.clear()
    
    users = await get_all_users()
    if not users:
        await message.answer("❌ No users found in the database.")
        return
        
    wait_msg = await message.answer(get_text('admin_broadcast_started', lang, count=len(users)), parse_mode="Markdown")
    
    success = 0
    fail = 0
    from utils import send_message_with_retry
    import asyncio
    
    for u in users:
        try:
            # Copy exact message (supports text, photos, videos, custom emojis, buttons, documents)
            await message.copy_to(chat_id=u['user_id'])
            success += 1
        except Exception as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "deactivated" in err_str:
                fail += 1
            else:
                try:
                    b_text = message.text or message.caption or "Broadcast Message"
                    await send_message_with_retry(bot.send_message, chat_id=u['user_id'], text=b_text, parse_mode="Markdown")
                    success += 1
                except Exception as inner_e:
                    fail += 1
                    logger.warning(f"Could not broadcast to {u['user_id']}: {inner_e}")
                    
        await asyncio.sleep(0.04)
            
    await wait_msg.edit_text(
        get_text('admin_broadcast_finished', lang, success=success, failed=fail),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )

# --- Admin Payment Approval Handlers ---
@router.callback_query(F.data.startswith("admin_pay_approve_"))
async def cb_admin_pay_approve(callback: CallbackQuery, bot: Bot):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    transaction_id = callback.data.replace("admin_pay_approve_", "")
    
    from database import complete_payment
    result = await complete_payment(transaction_id)
    
    if not result:
        await callback.answer("❌ This transaction is not pending or has already been processed.", show_alert=True)
        return
        
    user_id = result['user_id']
    amount = result['amount']
    
    # Get user details for language and notifications
    db_user = await get_user(user_id)
    user_lang = db_user['language'] if db_user else 'en'
    new_balance = db_user['balance'] if db_user else 0.0
    
    # Notify user
    try:
        await bot.send_message(
            chat_id=user_id,
            text=get_text('payment_success', user_lang, amount=amount, new_balance=new_balance),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Could not notify user {user_id} of approval: {e}")
        
    # Notify referrer if any
    ref_notif = result['referrer_notif']
    if ref_notif:
        ref_id = ref_notif['referrer_id']
        ref_bonus = ref_notif['bonus']
        try:
            await bot.send_message(
                chat_id=ref_id,
                text=f"🎉 *Referral Bonus!*\n💰 You earned `${ref_bonus:.2f} USD` from your referral's deposit!",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not notify referrer {ref_id}: {e}")
            
    # Edit admin log message to show approval
    admin_user = callback.from_user.first_name
    original_text = callback.message.text or callback.message.caption or ""
    # Escape markdown characters in original plain text to prevent parse errors
    safe_text = original_text.replace("\\", "\\\\").replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
    updated_text = (
        f"{safe_text}\n\n"
        f"✅ *Approved by admin:* {admin_user}"
    )
    
    await callback.message.edit_text(updated_text, reply_markup=None, parse_mode="Markdown")
    await callback.answer("Transaction approved and user credited!")

@router.callback_query(F.data.startswith("admin_pay_reject_"))
async def cb_admin_pay_reject(callback: CallbackQuery, bot: Bot):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    transaction_id = callback.data.replace("admin_pay_reject_", "")
    
    from database import reject_payment
    payment = await reject_payment(transaction_id)
    
    if not payment:
        await callback.answer("❌ This transaction is not pending or has already been processed.", show_alert=True)
        return
        
    user_id = payment['user_id']
    amount = payment['amount']
    
    # Get user details for language and notifications
    db_user = await get_user(user_id)
    user_lang = db_user['language'] if db_user else 'en'
    
    # Notify user of rejection
    try:
        await bot.send_message(
            chat_id=user_id,
            text=get_text('payment_rejected', user_lang, amount=amount),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Could not notify user {user_id} of rejection: {e}")
        
    # Edit admin log message to show rejection
    admin_user = callback.from_user.first_name
    original_text = callback.message.text or callback.message.caption or ""
    # Escape markdown characters in original plain text to prevent parse errors
    safe_text = original_text.replace("\\", "\\\\").replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
    updated_text = (
        f"{safe_text}\n\n"
        f"❌ *Rejected by admin:* {admin_user}"
    )
    
    await callback.message.edit_text(updated_text, reply_markup=None, parse_mode="Markdown")
    await callback.answer("Transaction rejected!")

# --- Custom Product Prices Management ---
@router.message(F.text.in_([
    get_text('btn_admin_custom_prices', 'en'),
    get_text('btn_admin_custom_prices', 'ar'),
    get_text('btn_admin_custom_prices', 'ru'),
    "🎯 Custom Product Prices"
]))
async def msg_admin_custom_prices_menu(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    from database import get_all_custom_product_prices
    custom_prices = await get_all_custom_product_prices()
    text = get_text('admin_custom_prices_title', lang)
    if not custom_prices:
        text += "\n\n" + get_text('admin_custom_price_no_items', lang)
    await message.answer(
        text,
        reply_markup=keyboards.get_admin_custom_prices_keyboard(custom_prices, lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_custom_prices_menu")
async def cb_admin_custom_prices_menu(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    from database import get_all_custom_product_prices
    custom_prices = await get_all_custom_product_prices()
    text = get_text('admin_custom_prices_title', lang)
    if not custom_prices:
        text += "\n\n" + get_text('admin_custom_price_no_items', lang)
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_custom_prices_keyboard(custom_prices, lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_custom_price_add")
async def cb_admin_custom_price_add(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_custom_price_user_id)
    await callback.message.answer(get_text('admin_custom_price_user_prompt', lang), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_custom_price_user_id)
async def process_custom_price_user_id(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    val = message.text.strip()
    try:
        user_id = int(val)
    except ValueError:
        await message.answer("❌ Invalid User ID. Please enter a valid numerical User ID:")
        return
    
    from database import get_user, get_products
    db_user = await get_user(user_id)
    if not db_user:
        await message.answer("❌ User not found in the database. The user must start/use the bot at least once. Please check the ID and try again:")
        return
        
    products = await get_products()
    if not products:
        await message.answer("❌ No products available in the store.")
        await state.clear()
        return
        
    await state.update_data(cp_user_id=user_id)
    user_name = escape_md(db_user['first_name'])
    if db_user['username']:
        user_name += f" (@{escape_md(db_user['username'])})"
    
    prompt = get_text('admin_custom_price_select_prod', lang, user_id=user_id, user_name=user_name)
    await message.answer(
        prompt,
        reply_markup=keyboards.get_admin_select_product_for_custom_price_keyboard(products, user_id, lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_cp_set_"))
async def cb_admin_cp_select_product(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    # admin_cp_set_{user_id}_{product_id}
    parts = callback.data.split("_")
    user_id = int(parts[3])
    prod_id = int(parts[4])
    
    from database import get_product
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
        
    prod_name = get_product_name(product, lang)
    orig_price = float(product['price'])
    
    await state.update_data(cp_user_id=user_id, cp_product_id=prod_id, cp_orig_price=orig_price, cp_prod_name=prod_name)
    await state.set_state(AdminStates.waiting_for_custom_price_value)
    
    prompt = get_text('admin_custom_price_val_prompt', lang, product_name=prod_name, original_price=orig_price, user_id=user_id)
    await callback.message.answer(prompt, parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_custom_price_value)
async def process_custom_price_value(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    val = message.text.strip().replace("$", "")
    try:
        custom_price = float(val)
        if custom_price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid price. Please enter a valid positive number (e.g. `4.50`):")
        return
        
    data = await state.get_data()
    user_id = data.get("cp_user_id")
    prod_id = data.get("cp_product_id")
    await state.clear()
    
    if not user_id or not prod_id:
        await message.answer("❌ Session expired. Please try again.")
        return
        
    from database import set_user_product_price, get_user, get_product
    await set_user_product_price(user_id, prod_id, custom_price)
    
    db_user = await get_user(user_id)
    user_name = db_user['first_name'] if db_user else f"ID: {user_id}"
    prod = await get_product(prod_id)
    prod_name = get_product_name(prod, lang) if prod else f"Product #{prod_id}"
    orig_price = float(prod['price']) if prod else 0.0
    
    success_text = get_text('admin_custom_price_success', lang, user_id=user_id, user_name=user_name, product_name=prod_name, custom_price=custom_price, original_price=orig_price)
    await message.answer(
        success_text,
        reply_markup=keyboards.get_admin_back_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_cp_del_"))
async def cb_admin_cp_del(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    user_id = int(parts[3])
    prod_id = int(parts[4])
    
    from database import delete_user_product_price, get_product, get_all_custom_product_prices
    await delete_user_product_price(user_id, prod_id)
    
    prod = await get_product(prod_id)
    prod_name = get_product_name(prod, lang) if prod else f"Product #{prod_id}"
    
    del_msg = get_text('admin_custom_price_deleted', lang, product_name=prod_name, user_id=user_id)
    await callback.answer(del_msg, show_alert=True)
    
    # Refresh view
    custom_prices = await get_all_custom_product_prices()
    text = get_text('admin_custom_prices_title', lang)
    if not custom_prices:
        text += "\n\n" + get_text('admin_custom_price_no_items', lang)
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_custom_prices_keyboard(custom_prices, lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_cp_sel_"))
async def cb_admin_cp_sel(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    user_id = int(parts[3])
    prod_id = int(parts[4])
    
    from database import get_product, get_user_product_price
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
        
    prod_name = get_product_name(product, lang)
    orig_price = float(product['price'])
    current_custom_price = await get_user_product_price(user_id, prod_id) or 0.0
    
    await state.update_data(cp_user_id=user_id, cp_product_id=prod_id, cp_orig_price=orig_price, cp_prod_name=prod_name)
    await state.set_state(AdminStates.waiting_for_custom_price_value)
    
    prompt = get_text('admin_custom_price_val_prompt', lang, product_name=prod_name, original_price=orig_price, user_id=user_id)
    prompt += f"\n*(Current Custom Price: ${current_custom_price:.2f})*"
    await callback.message.answer(prompt, parse_mode="Markdown")
    await callback.answer()

# --- User Discounts Management ---
@router.message(F.text.in_([
    get_text('btn_admin_user_discounts', 'en'),
    get_text('btn_admin_user_discounts', 'ar'),
    get_text('btn_admin_user_discounts', 'ru'),
    "👥 User Discounts", "👥 خصومات المستخدمين", "👥 Скидки пользователей"
]))
async def msg_admin_discounts_menu(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    from database import get_all_user_discounts
    discounts = await get_all_user_discounts()
    
    text = get_text('admin_discounts_title', lang)
    
    await message.answer(
        text,
        reply_markup=keyboards.get_admin_discounts_keyboard(discounts, lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_discounts_menu")
async def cb_admin_discounts_menu(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
        
    from database import get_all_user_discounts
    discounts = await get_all_user_discounts()
    
    text = get_text('admin_discounts_title', lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_discounts_keyboard(discounts, lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_discount_del_"))
async def cb_admin_discount_del(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
        
    user_id = int(callback.data.replace("admin_discount_del_", ""))
    from database import delete_user_discount
    await delete_user_discount(user_id)
    
    await callback.answer(get_text('admin_discount_deleted', lang), show_alert=True)
    
    # Refresh view
    from database import get_all_user_discounts
    discounts = await get_all_user_discounts()
    text = get_text('admin_discounts_title', lang)
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_discounts_keyboard(discounts, lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_discount_add")
async def cb_admin_discount_add(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
        
    await state.set_state(AdminStates.waiting_for_discount_user_id)
    await callback.message.answer(get_text('admin_discount_user_prompt', lang), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_discount_user_id)
async def process_discount_user_id(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    val = message.text.strip()
    try:
        user_id = int(val)
    except ValueError:
        await message.answer(get_text('admin_inspect_invalid_id', lang))
        return
        
    # Check if user exists in database
    from database import get_user
    db_user = await get_user(user_id)
    if not db_user:
        await message.answer(get_text('admin_inspect_not_found', lang))
        return
        
    await state.update_data(discount_target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_discount_percent)
    
    name = escape_md(db_user['first_name'])
    if db_user['username']:
        name += f" (@{escape_md(db_user['username'])})"
    await message.answer(get_text('admin_discount_pct_prompt', lang, name=name, user_id=user_id), parse_mode="Markdown")

@router.message(AdminStates.waiting_for_discount_percent)
async def process_discount_percent(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    val = message.text.strip().replace("%", "")
    try:
        percent = float(val)
        if percent < 0 or percent > 100:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid percentage. Please enter a number between `0` and `100`:")
        return
        
    data = await state.get_data()
    user_id = data.get("discount_target_user_id")
    await state.clear()
    
    if not user_id:
        await message.answer("❌ Session expired. Please try again.")
        return
        
    from database import set_user_discount, get_user
    await set_user_discount(user_id, percent)
    
    db_user = await get_user(user_id)
    name = db_user['first_name'] if db_user else f"ID: {user_id}"
    await message.answer(
        get_text('admin_discount_success', lang, percent=percent, name=name),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("admin_discount_edit_"))
async def cb_admin_discount_edit(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
        
    user_id = int(callback.data.replace("admin_discount_edit_", ""))
    await state.update_data(discount_target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_edit_discount_percent)
    
    from database import get_user
    db_user = await get_user(user_id)
    name = db_user['first_name'] if db_user else f"ID: {user_id}"
    await callback.message.answer(get_text('admin_discount_pct_prompt', lang, name=name, user_id=user_id), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_edit_discount_percent)
async def process_edit_discount_percent(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    val = message.text.strip().replace("%", "")
    try:
        percent = float(val)
        if percent < 0 or percent > 100:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid percentage. Please enter a number between `0` and `100`:")
        return
        
    data = await state.get_data()
    user_id = data.get("discount_target_user_id")
    await state.clear()
    
    if not user_id:
        await message.answer("❌ Session expired. Please try again.")
        return
        
    from database import set_user_discount, get_user
    await set_user_discount(user_id, percent)
    
    db_user = await get_user(user_id)
    name = db_user['first_name'] if db_user else f"ID: {user_id}"
    await message.answer(
        get_text('admin_discount_success', lang, percent=percent, name=name),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )

# --- Edit Store Name ---
@router.message(F.text.in_([
    get_text('btn_admin_edit_store_name', 'en'),
    get_text('btn_admin_edit_store_name', 'ar'),
    get_text('btn_admin_edit_store_name', 'ru'),
    "✏️ Edit Store Name", "✏️ تعديل اسم المتجر", "✏️ Изменить имя магазина"
]))
async def msg_admin_edit_store_name(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    
    current_name = await get_setting('store_name', 'Digital Store')
    await state.set_state(AdminStates.waiting_for_store_name)
    await message.answer(
        get_text('admin_store_name_current', lang, name=current_name),
        parse_mode="Markdown"
    )

@router.message(AdminStates.waiting_for_store_name)
async def process_admin_store_name(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    new_name = message.text.strip()
    if not new_name:
        await message.answer("❌ Store name cannot be empty. Please enter a valid name:")
        return
        
    await set_setting('store_name', new_name)
    await state.clear()
    
    await message.answer(
        get_text('admin_store_name_success', lang, name=new_name),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )

# --- User Balances Management ---
@router.message(F.text.in_([
    get_text('btn_admin_manage_users', 'en'),
    get_text('btn_admin_manage_users', 'ar'),
    get_text('btn_admin_manage_users', 'ru'),
    "👥 Manage Users", "👥 إدارة المستخدمين", "👥 Управление пользователями"
]))
async def msg_admin_manage_users(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    await state.clear()
    title = get_text('admin_manage_users_title', lang)
    await message.answer(
        title,
        reply_markup=keyboards.get_admin_manage_users_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_manage_users")
async def cb_admin_manage_users(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    await state.clear()
    title = get_text('admin_manage_users_title', lang)
    await callback.message.edit_text(
        title,
        reply_markup=keyboards.get_admin_manage_users_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- Ban Management Menu & Handlers ---
@router.message(F.text.in_([
    get_text('btn_admin_ban_system', 'en'),
    get_text('btn_admin_ban_system', 'ar'),
    get_text('btn_admin_ban_system', 'ru'),
    "🚫 Ban / Unban System", "🚫 نظام الحظر / فك الحظر", "🚫 Система банов"
]))
async def msg_admin_ban_unban_system(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        get_text('admin_ban_menu_title', lang),
        reply_markup=keyboards.get_admin_ban_menu_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_ban_unban_menu")
async def cb_admin_ban_unban_menu(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        get_text('admin_ban_menu_title', lang),
        reply_markup=keyboards.get_admin_ban_menu_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_ban_prompt")
async def cb_admin_ban_prompt(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_ban_user_id)
    await callback.message.edit_text(
        get_text('admin_ban_user_prompt', lang),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_ban_user_id)
async def process_ban_user_id(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(get_text('admin_inspect_invalid_id', lang))
        return
    target_id = int(text)
    await state.update_data(ban_target_id=target_id)
    await state.set_state(AdminStates.waiting_for_ban_reason)
    await message.answer(
        get_text('admin_ban_reason_prompt', lang, user_id=target_id),
        reply_markup=keyboards.get_admin_ban_reason_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_ban_skip_reason")
async def cb_admin_ban_skip_reason(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    data = await state.get_data()
    target_id = data.get("ban_target_id")
    await state.clear()
    if not target_id:
        await callback.message.edit_text("❌ Session expired. Try again.", reply_markup=keyboards.get_admin_ban_menu_keyboard(lang))
        await callback.answer()
        return
    reason = "Banned by admin panel"
    await ban_user(target_id, reason)
    await callback.message.edit_text(
        get_text('admin_ban_success', lang, user_id=target_id, reason=reason),
        reply_markup=keyboards.get_admin_ban_menu_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_ban_reason)
async def process_ban_reason(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    target_id = data.get("ban_target_id")
    await state.clear()
    if not target_id:
        await message.answer("❌ Session expired. Try again.")
        return
    reason = message.text.strip()
    if reason.lower() in ["تخطي", "skip", "/skip", "-"]:
        reason = "Banned by admin panel"
    await ban_user(target_id, reason)
    await message.answer(
        get_text('admin_ban_success', lang, user_id=target_id, reason=reason),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_unban_prompt")
async def cb_admin_unban_prompt(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_unban_user_id)
    await callback.message.edit_text(
        get_text('admin_unban_user_prompt', lang),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_unban_user_id)
async def process_unban_user_id(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(get_text('admin_inspect_invalid_id', lang))
        return
    target_id = int(text)
    await state.clear()
    await unban_user(target_id)
    await message.answer(
        get_text('admin_unban_success', lang, user_id=target_id),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_show_banned")
async def cb_admin_show_banned(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    banned_users = await get_all_banned_users()
    if not banned_users:
        await callback.message.edit_text(get_text('admin_no_banned_users', lang), reply_markup=keyboards.get_admin_ban_menu_keyboard(lang), parse_mode="Markdown")
        await callback.answer()
        return
    
    text = get_text('admin_banned_list_title', lang)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for u in banned_users:
        u_id = u['user_id']
        u_name = escape_md(u['first_name'] or str(u_id))
        reason = u['ban_reason'] or "No reason specified"
        text += f"🔴 {u_name} (`{u_id}`) — {reason}\n"
        builder.button(text=f"🟢 Unban {u_id}", callback_data=f"admin_actunban_{u_id}")
    builder.button(text=get_text('btn_admin_back', lang), callback_data="admin_ban_unban_menu")
    builder.adjust(2)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_user_balances")
async def cb_admin_user_balances(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_balance_user_id)
    await callback.message.edit_text(get_text('admin_user_bal_prompt', lang), reply_markup=keyboards.get_admin_balances_menu_keyboard(lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_show_balances")
async def cb_admin_show_balances(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    from database import get_users_with_balance
    users = await get_users_with_balance()
    if not users:
        await callback.message.answer("📭 No users have any balance greater than 0.")
        await callback.answer()
        return
    
    def escape_md(text):
        if not text:
            return ""
        for ch in ['_', '*', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
            text = text.replace(ch, '\\' + ch)
        return text
    
    title_text = {"en": "👥 *Users with Balance:*\n", "ar": "👥 *المستخدمون الذين يملكون رصيداً:*\n", "ru": "👥 *Пользователи с балансом:*\n"}.get(lang, "👥 *Users with Balance:*\n")
    lines = [title_text]
    for u in users:
        name = escape_md(u['first_name'] or "")
        username_part = f" (@{escape_md(u['username'])})" if u['username'] else ""
        lines.append(f"👤 {name}{username_part} (`{u['user_id']}`) \\- `${u['balance']:.2f}`")
    
    # Split into chunks at line boundaries, keeping each chunk under 4000 chars
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > 4000:
            chunks.append(current_chunk)
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    if current_chunk:
        chunks.append(current_chunk)
    
    for chunk in chunks:
        try:
            await callback.message.answer(chunk, parse_mode="MarkdownV2")
        except Exception:
            # Fallback: send without formatting
            await callback.message.answer(chunk)
    await callback.answer()

@router.message(AdminStates.waiting_for_balance_user_id)
async def process_balance_user_id(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer(get_text('admin_inspect_invalid_id', lang))
        return
    from database import get_user
    db_user = await get_user(user_id)
    if not db_user:
        await message.answer(get_text('admin_inspect_not_found', lang))
        return
        
    await state.clear()
    
    name = escape_md(db_user['first_name'])
    if db_user['username']:
        name += f" (@{escape_md(db_user['username'])})"
        
    balance = db_user['balance']
    
    text = (
        f"👤 User: {name}\n"
        f"🆔 ID: `{user_id}`\n"
        f"💵 Current Balance: `${balance:.2f} USD`"
    )
    
    await message.answer(text, reply_markup=keyboards.get_admin_user_balance_keyboard(user_id, lang))

@router.callback_query(F.data.startswith("admin_edit_bal_"))
async def cb_admin_edit_balance(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    user_id = int(callback.data.replace("admin_edit_bal_", ""))
    await state.update_data(balance_edit_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_new_balance)
    
    from database import get_user
    db_user = await get_user(user_id)
    name = db_user['first_name'] if db_user else f"ID: {user_id}"
    cur_bal = db_user['balance'] if db_user else 0.0
    
    await callback.message.answer(get_text('admin_user_new_bal_prompt', lang, name=name, user_id=user_id, current_balance=cur_bal), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_new_balance)
async def process_new_balance(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    try:
        new_balance = float(message.text.strip().replace("$", ""))
        if new_balance < 0:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('admin_invalid_price', lang))
        return
        
    data = await state.get_data()
    user_id = data.get("balance_edit_user_id")
    await state.clear()
    
    if not user_id:
        await message.answer("❌ Session expired. Try again.")
        return
        
    from database import set_user_balance, get_user
    await set_user_balance(user_id, new_balance)
    
    db_user = await get_user(user_id)
    name = db_user['first_name'] if db_user else f"ID: {user_id}"
    
    await message.answer(get_text('admin_user_bal_updated', lang, name=name, balance=new_balance), reply_markup=keyboards.get_admin_back_keyboard(lang), parse_mode="Markdown")


# --- Secret Database Backup & Restore Commands ---
@router.message(F.text == "/backup_db")
async def cmd_backup_db(message: Message, bot: Bot):
    if not is_user_admin(message.from_user.id):
        return
        
    from aiogram.types import FSInputFile
    import os
    try:
        from bot_config import DB_NAME
    except ImportError:
        from config import DB_NAME
    
    if not os.path.exists(DB_NAME):
        await message.answer("❌ Database file not found.")
        return
        
    try:
        db_file = FSInputFile(DB_NAME, filename="store.db")
        await message.answer_document(db_file, caption="📦 Database Backup")
    except Exception as e:
        await message.answer(f"❌ Failed to backup database: {e}")

@router.message(F.text == "/restore_db")
async def cmd_restore_db(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        return
        
    await state.set_state(AdminStates.waiting_for_restore_db)
    await message.answer("📤 Please send the `store.db` file as a document to restore the database:", reply_markup=keyboards.get_admin_back_keyboard())

@router.message(AdminStates.waiting_for_restore_db, F.document)
async def process_restore_db(message: Message, state: FSMContext, bot: Bot):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    # Check if the file is a .db file
    if not message.document.file_name.endswith('.db'):
        await message.answer("❌ Invalid file. Please upload a database file ending in `.db`:")
        return
        
    try:
        # Get file info and download
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        try:
            from bot_config import DB_NAME
        except ImportError:
            from config import DB_NAME
        import os
        
        # Ensure parent folder exists
        parent = os.path.dirname(DB_NAME)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        # Download and overwrite
        await bot.download_file(file_path, DB_NAME)
        await state.clear()
        
        # Initialize DB to make sure schema is fine and WAL mode is active
        from database import db_init
        await db_init()
        
        await message.answer("✅ Database restored and initialized successfully! All data has been updated.", reply_markup=keyboards.get_admin_back_keyboard())
    except Exception as e:
        await message.answer(f"❌ Failed to restore database: {e}", reply_markup=keyboards.get_admin_back_keyboard())


# --- Reseller API Keys Management Handlers ---
@router.callback_query(F.data == "admin_api_keys")
async def cb_admin_api_keys(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    await state.clear()
    
    from database import get_all_api_keys
    keys = await get_all_api_keys()
    
    title_dict = {
        'en': "🔑 *Reseller API Keys*\n\n",
        'ar': "🔑 *مفاتيح API للموزعين والشركاء*\n\n",
        'ru': "🔑 *API ключи реселлеров*\n\n"
    }
    empty_dict = {
        'en': "No active reseller API keys found.",
        'ar': "لا توجد مفاتيح API نشطة حالياً.",
        'ru': "Активных API ключей не найдено."
    }
    text = title_dict.get(lang, title_dict['en'])
    if not keys:
        text += empty_dict.get(lang, empty_dict['en'])
    else:
        for idx, k in enumerate(keys, 1):
            name = k['first_name'] or f"ID: {k['user_id']}"
            if k['username']:
                name += f" (@{k['username']})"
            text += f"{idx}. *{name}*\n`{k['api_key']}`\n\n"
            
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_api_keys_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_api_key_gen")
async def cb_admin_api_key_gen(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    await state.set_state(AdminStates.waiting_for_api_key_user_id)
    gen_prompt_dict = {
        'en': "➕ *Generate API Key*\n\nPlease enter the numeric *Telegram User ID* of the user you want to generate an API key for:",
        'ar': "➕ *توليد مفتاح API جديد*\n\nيرجى إدخال *معرف تيليجرام الرقمي (User ID)* للمستخدم المراد إنشاء المفتاح له:",
        'ru': "➕ *Создать API ключ*\n\nВведите цифровой *Telegram User ID* пользователя:"
    }
    await callback.message.edit_text(
        gen_prompt_dict.get(lang, gen_prompt_dict['en']),
        reply_markup=keyboards.get_admin_back_keyboard(lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_api_key_user_id)
async def process_api_key_user_id(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    user_id_str = message.text.strip()
    if not user_id_str.isdigit():
        await message.answer(get_text('admin_inspect_invalid_id', lang))
        return
        
    user_id = int(user_id_str)
    
    from database import get_user, generate_api_key
    user = await get_user(user_id)
    if not user:
        await message.answer(get_text('admin_inspect_not_found', lang))
        return
        
    await state.clear()
    try:
        api_key = await generate_api_key(user_id)
        name = user['first_name'] or f"ID: {user_id}"
        if user['username']:
            name += f" (@{user['username']})"
            
        success_dict = {
            'en': (
                f"✅ *API Key Generated Successfully!*\n\n"
                f"👤 *Partner:* {name}\n"
                f"🔑 *API Key:* `{api_key}`\n\n"
                f"💡 Give this key to the partner. They should include it in their requests headers as `X-API-Key`."
            ),
            'ar': (
                f"✅ *تم إنشاء مفتاح API بنجاح!*\n\n"
                f"👤 *الشريك:* {name}\n"
                f"🔑 *المفتاح:* `{api_key}`\n\n"
                f"💡 أعط هذا المفتاح للشريك ليقوم بإرساله في ترويسة الطلبات كـ `X-API-Key`."
            ),
            'ru': (
                f"✅ *API ключ успешно сгенерирован!*\n\n"
                f"👤 *Партнер:* {name}\n"
                f"🔑 *Ключ:* `{api_key}`\n\n"
                f"💡 Передайте этот ключ партнеру для заголовка `X-API-Key`."
            )
        }
        await message.answer(success_dict.get(lang, success_dict['en']), reply_markup=keyboards.get_admin_back_keyboard(lang), parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error: {e}", reply_markup=keyboards.get_admin_back_keyboard(lang))

@router.callback_query(F.data == "admin_api_key_revoke_select")
async def cb_admin_api_key_revoke_select(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    from database import get_all_api_keys
    keys = await get_all_api_keys()
    if not keys:
        await callback.answer("No active API keys to revoke.", show_alert=True)
        return
        
    revoke_prompt_dict = {
        'en': "❌ *Select API Key to Revoke*\n\nChoose the partner whose API key you want to delete/revoke:",
        'ar': "❌ *اختيار مفتاح للإلغاء والحذف*\n\nاختر الشريك المراد حذف وإلغاء مفتاح الـ API الخاص به:",
        'ru': "❌ *Отказ API ключа*\n\nВыберите партнера, чей ключ хотите отозвать:"
    }
    await callback.message.edit_text(
        revoke_prompt_dict.get(lang, revoke_prompt_dict['en']),
        reply_markup=keyboards.get_admin_api_key_revoke_keyboard(keys, lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_api_key_rev_"))
async def cb_admin_api_key_rev_confirm(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    user_id = int(callback.data.replace("admin_api_key_rev_", ""))
    
    from database import revoke_api_key, get_user
    await revoke_api_key(user_id)
    
    user = await get_user(user_id)
    name = user['first_name'] if user else f"ID: {user_id}"
    
    await callback.answer(f"✅ Revoked API key for {name} successfully!", show_alert=True)
    
    # Return to the keys list
    from database import get_all_api_keys
    keys = await get_all_api_keys()
    title_dict = {
        'en': "🔑 *Reseller API Keys*\n\n",
        'ar': "🔑 *مفاتيح API للموزعين والشركاء*\n\n",
        'ru': "🔑 *API ключи реселлеров*\n\n"
    }
    empty_dict = {
        'en': "No active reseller API keys found.",
        'ar': "لا توجد مفاتيح API نشطة حالياً.",
        'ru': "Активных API ключей не найдено."
    }
    text = title_dict.get(lang, title_dict['en'])
    if not keys:
        text += empty_dict.get(lang, empty_dict['en'])
    else:
        for idx, k in enumerate(keys, 1):
            name_k = k['first_name'] or f"ID: {k['user_id']}"
            if k['username']:
                name_k += f" (@{k['username']})"
            text += f"{idx}. *{name_k}*\n`{k['api_key']}`\n\n"
            
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_api_keys_keyboard(lang),
        parse_mode="Markdown"
    )


# --- Provider Integration Admin Handlers ---
from handlers.states import ProvidersStates

async def fetch_provider_store_name(base_url, api_key):
    import aiohttp
    from utils import normalize_provider_url
    base_url = normalize_provider_url(base_url)
    is_supabase = "supabase.co" in base_url
    
    headers = {
        "X-Reseller-Key": api_key,
        "X-API-Key": api_key,
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    endpoints = [
        f"{base_url}?action=balance" if is_supabase else f"{base_url}/api/reseller/me",
        f"{base_url}/reseller/me",
        f"{base_url}/api/me",
        f"{base_url}/api/v1/me",
        f"{base_url}/v1/me",
        f"{base_url}/me"
    ]
    
    try:
        async with aiohttp.ClientSession() as session:
            for url in endpoints:
                try:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if is_supabase:
                                return "Supabase Reseller API"
                            if isinstance(data, dict):
                                if data.get('key_name'):
                                    return f"VenteBot ({data['key_name']})"
                                elif data.get('store_name'):
                                    return data['store_name']
                                elif data.get('name'):
                                    return data['name']
                                elif data.get('ok') and 'user' in data and isinstance(data['user'], dict):
                                    return f"Partner: {data['user'].get('first_name') or data['user'].get('username')}"
                except Exception:
                    continue
    except Exception:
        pass
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        domain = parsed.netloc or parsed.path
        return domain.replace("www.", "")
    except Exception:
        return base_url

async def fetch_provider_products(base_url, api_key):
    from providers_engine import get_provider_adapter
    try:
        adapter = get_provider_adapter(base_url, api_key)
        catalog = await adapter.fetch_catalog()
        if catalog is not None:
            return catalog
    except Exception as e:
        logger.error(f"Error fetching provider products from {base_url}: {e}")
    return None

@router.callback_query(F.data == "admin_pull_external")
async def cb_admin_pull_external(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    from database import get_providers
    providers = await get_providers()
    
    text = get_text('prov_list_title', lang)
    await callback.message.edit_text(text, reply_markup=keyboards.get_providers_list_keyboard(providers, lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_prov_setup_new")
async def cb_admin_prov_setup_new(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    await state.set_state(ProvidersStates.waiting_for_url)
    await callback.message.edit_text(get_text('prov_url_prompt', lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_prov_manage_"))
async def cb_admin_prov_manage(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    provider_id = int(callback.data.replace("admin_prov_manage_", ""))
    from database import get_provider
    prov = await get_provider(provider_id)
    if not prov:
        await callback.answer("❌ Provider not found", show_alert=True)
        return
        
    prov_dict = dict(prov)
    display_name = prov_dict['store_name'] if prov_dict.get('store_name') else prov_dict['base_url']
    text = get_text('prov_manage_title', lang, url=display_name)
    await callback.message.edit_text(text, reply_markup=keyboards.get_provider_manage_keyboard(provider_id, lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_prov_delete_"))
async def cb_admin_prov_delete(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    provider_id = int(callback.data.replace("admin_prov_delete_", ""))
    from database import delete_provider, get_providers
    await delete_provider(provider_id)
    await callback.answer("✅ Provider deleted successfully!", show_alert=True)
    
    providers = await get_providers()
    text = get_text('prov_list_title', lang)
    await callback.message.edit_text(text, reply_markup=keyboards.get_providers_list_keyboard(providers, lang), parse_mode="Markdown")

@router.callback_query(F.data.startswith("admin_prov_editkey_"))
async def cb_admin_prov_edit_key(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    provider_id = int(callback.data.replace("admin_prov_editkey_", ""))
    await state.set_state(ProvidersStates.waiting_for_edit_key)
    await state.update_data(edit_provider_id=provider_id)
    await callback.message.edit_text("🔑 *Please send the new API Key / Token for this provider:*", parse_mode="Markdown")
    await callback.answer()

@router.message(ProvidersStates.waiting_for_edit_key)
async def process_provider_edit_key(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    new_key = message.text.strip()
    data = await state.get_data()
    provider_id = data.get('edit_provider_id')
    await state.clear()
    
    from database import get_provider, save_provider
    prov = await get_provider(provider_id)
    if not prov:
        await message.answer("❌ Provider not found.")
        return
        
    base_url = prov['base_url']
    store_name = dict(prov).get('store_name')
    
    await message.answer("⏳ Testing new API key connection...")
    products = await fetch_provider_products(base_url, new_key)
    if products is None:
        await message.answer("❌ Connection test failed with new API key! Please check the key and try again.")
    else:
        await save_provider(base_url, new_key, store_name=store_name)
        await message.answer("✅ API Key updated successfully for provider!")

@router.callback_query(F.data.startswith("admin_prov_pull_"))
async def cb_admin_prov_pull(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    provider_id = int(callback.data.replace("admin_prov_pull_", ""))
    from database import get_provider
    prov = await get_provider(provider_id)
    if not prov:
        await callback.answer("❌ Provider not found", show_alert=True)
        return
        
    await callback.message.edit_text("⏳ Fetching products from provider bot...")
    products = await fetch_provider_products(prov['base_url'], prov['api_key'])
    
    if products is None:
        await callback.message.edit_text("❌ Failed to fetch products from provider bot. Please make sure the URL and API key are correct.", reply_markup=keyboards.get_admin_back_keyboard())
    elif len(products) == 0:
        empty_msg = {
            'ar': "📭 لا توجد أي منتجات معروضة للبيع في متجر هذا المزود حالياً.\n(تأكد من إضافة وتفعيل منتجات في البوت المزود أولاً).",
            'en': "📭 No products available in this provider's store currently.\n(Make sure to add products in the provider bot first).",
            'ru': "📭 В магазине этого поставщика пока нет доступных товаров."
        }
        await callback.message.edit_text(empty_msg.get(lang, empty_msg['en']), reply_markup=keyboards.get_admin_back_keyboard(), parse_mode="Markdown")
    else:
        await state.update_data(prov_products=products, prov_id=prov['id'])
        await callback.message.edit_text(get_text('prov_select_product', lang), reply_markup=keyboards.get_provider_products_keyboard(products, lang))
    await callback.answer()

@router.message(ProvidersStates.waiting_for_url)
async def process_provider_url(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    url = message.text.strip()
    await state.update_data(prov_url=url)
    await state.set_state(ProvidersStates.waiting_for_key)
    await message.answer(get_text('prov_key_prompt', lang))

@router.message(ProvidersStates.waiting_for_key)
async def process_provider_key(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    key = message.text.strip()
    data = await state.get_data()
    url = data.get('prov_url')
    
    await message.answer("⏳ Connecting to provider bot and verifying API key...")
    products = await fetch_provider_products(url, key)
    
    if products is None:
        await message.answer("❌ Failed to connect to provider bot. Please verify the URL and Reseller API key, and try again by clicking 'Pull External Product'.")
        await state.clear()
    elif len(products) == 0:
        # Fetch remote store name and save provider
        store_name = await fetch_provider_store_name(url, key)
        from database import save_provider
        await save_provider(url, key, store_name=store_name)
        
        empty_msg = {
            'ar': (
                f"✅ *تم الاتصال وحفظ المزود بنجاح! ({store_name})*\n\n"
                f"⚠️ *ملاحظة:* متجر المزود لا يحتوي على أي منتجات حالياً (0 منتج).\n"
                f"قم بإضافة منتجات داخل البوت المزود، ثم اضغط '🔌 سحب منتج خارجي' لاستيرادها فوراً!"
            ),
            'en': (
                f"✅ *Connected and saved provider successfully! ({store_name})*\n\n"
                f"⚠️ *Note:* The provider store currently has no products (0 products).\n"
                f"Please add products in the provider bot, then click 'Pull External Product' to import them!"
            ),
            'ru': (
                f"✅ *Поставщик успешно подключен! ({store_name})*\n\n"
                f"⚠️ В магазине поставщика пока нет товаров (0 товаров).\n"
                f"Добавьте товары в боте поставщика, затем нажмите 'Импортировать товары'!"
            )
        }
        await message.answer(empty_msg.get(lang, empty_msg['en']), reply_markup=keyboards.get_admin_back_keyboard(), parse_mode="Markdown")
        await state.clear()
    else:
        # Fetch remote store name
        store_name = await fetch_provider_store_name(url, key)
        
        from database import save_provider, get_providers
        await save_provider(url, key, store_name=store_name)
        
        # Get the ID of the newly saved provider
        providers = await get_providers()
        prov_id = 1
        from utils import normalize_provider_url
        clean_url = normalize_provider_url(url)
        for p in providers:
            p_url = normalize_provider_url(p['base_url'])
            if p_url == clean_url:
                prov_id = p['id']
                break
                
        await state.update_data(prov_products=products, prov_id=prov_id)
        await message.answer(get_text('prov_select_product', lang), reply_markup=keyboards.get_provider_products_keyboard(products, lang))

@router.callback_query(F.data.startswith("admin_prov_pg_"))
async def cb_admin_prov_page(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    page = int(callback.data.replace("admin_prov_pg_", ""))
    data = await state.get_data()
    products = data.get('prov_products', [])
    
    if not products:
        await callback.answer("Session expired. Please pull provider products again.", show_alert=True)
        return
        
    kb = keyboards.get_provider_products_keyboard(products, lang=lang, page=page)
    try:
        await callback.message.edit_text(get_text('prov_select_product', lang), reply_markup=kb)
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("admin_prov_sel_"))
async def cb_admin_prov_select_product(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    raw_prod_id = callback.data.replace("admin_prov_sel_", "")
    data = await state.get_data()
    products = data.get('prov_products', [])
    
    selected_prod = None
    for p in products:
        if str(p['id']) == raw_prod_id:
            selected_prod = p
            break
            
    if not selected_prod:
        await callback.answer("❌ Selected product not found", show_alert=True)
        return
        
    cost = float(selected_prod.get('price', 0.0))
    prod_name = selected_prod.get('name_en') or selected_prod.get('name_ar') or f"Product #{raw_prod_id}"
    await state.update_data(selected_prov_prod=selected_prod)
    
    text = get_text('pricing_select_strategy_title', lang, name=prod_name, cost=cost)
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_pricing_type_keyboard(lang=lang, is_import=True),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_imp_ptype_"))
async def cb_admin_imp_ptype(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
        
    ptype = callback.data.replace("admin_imp_ptype_", "")
    data = await state.get_data()
    selected_prod = data.get('selected_prov_prod')
    if not selected_prod:
        await callback.answer("❌ Session expired", show_alert=True)
        return
        
    cost = float(selected_prod.get('price', 0.0))
    await state.update_data(pricing_type=ptype)
    
    if ptype == 'fixed':
        await state.set_state(ProvidersStates.waiting_for_price)
        await callback.message.edit_text(get_text('pricing_prompt_fixed', lang), parse_mode="Markdown")
    elif ptype == 'margin_fixed':
        await state.set_state(ProvidersStates.waiting_for_margin_value)
        await callback.message.edit_text(get_text('pricing_prompt_margin_fixed', lang, cost=cost), parse_mode="Markdown")
    elif ptype == 'margin_percent':
        await state.set_state(ProvidersStates.waiting_for_margin_value)
        await callback.message.edit_text(get_text('pricing_prompt_margin_percent', lang, cost=cost), parse_mode="Markdown")
    await callback.answer()

@router.message(ProvidersStates.waiting_for_margin_value)
async def process_provider_margin_value(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    try:
        val = float(message.text.strip().replace("$", "").replace("%", ""))
        if val < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid value. Please enter a valid non-negative number:")
        return
        
    await state.update_data(margin_value=val)
    data = await state.get_data()
    ptype = data.get('pricing_type', 'margin_fixed')
    selected_prod = data.get('selected_prov_prod', {})
    cost = float(selected_prod.get('price', 0.0))
    
    from utils import calculate_dynamic_selling_price
    suggested_floor = calculate_dynamic_selling_price(ptype, val, 0.0, cost)
    await state.set_state(ProvidersStates.waiting_for_min_price)
    await message.answer(
        get_text('pricing_prompt_min_price', lang, suggested=suggested_floor),
        reply_markup=keyboards.get_admin_min_price_skip_keyboard(lang=lang, is_import=True),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_imp_skip_min")
async def cb_admin_imp_skip_min(callback: CallbackQuery, state: FSMContext, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    await finalize_imported_product(callback.message, state, min_price=0.0, lang=lang)
    await callback.answer()

@router.message(ProvidersStates.waiting_for_min_price)
async def process_provider_min_price(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
    try:
        min_p = float(message.text.strip().replace("$", ""))
        if min_p < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid floor price. Please enter a valid number:")
        return
    await finalize_imported_product(message, state, min_price=min_p, lang=lang)

async def finalize_imported_product(message_or_msg, state: FSMContext, min_price: float = 0.0, lang='en'):
    data = await state.get_data()
    prod = data.get('selected_prov_prod')
    prov_id = data.get('prov_id')
    ptype = data.get('pricing_type', 'fixed')
    m_val = float(data.get('margin_value', 0.0))
    cost = float(prod.get('price', 0.0)) if prod else 0.0
    
    if not prod or not prov_id:
        await message_or_msg.answer("❌ Error: session expired. Please restart the import process.")
        await state.clear()
        return
        
    from utils import calculate_dynamic_selling_price
    final_price = calculate_dynamic_selling_price(ptype, m_val, min_price, cost, fallback_fixed_price=data.get('fixed_price', cost))
    
    from database import add_imported_product, broadcast_new_product_to_users, get_setting
    product_id = await add_imported_product(
        name_ar=prod.get('name_ar', prod.get('name_en')),
        name_en=prod.get('name_en'),
        name_ru=prod.get('name_ru', prod.get('name_en')),
        description_ar="",
        description_en="",
        description_ru="",
        price=final_price,
        custom_emoji_id=prod.get('custom_emoji_id'),
        provider_id=prov_id,
        provider_product_id=prod['id'],
        pricing_type=ptype,
        margin_value=m_val,
        min_price=min_price,
        last_provider_cost=cost
    )
    
    bot_inst = message_or_msg.bot
    if product_id:
        await broadcast_new_product_to_users(bot_inst, product_id)
        
    news_channel = await get_setting('news_channel', '')
    if news_channel:
        try:
            import html
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            bot_info = await bot_inst.get_me()
            bot_username = bot_info.username
            product_name = prod.get('name_en') or prod.get('name_ar') or "Product"
            escaped_name = html.escape(product_name)
            announce_text = (
                f"🔥 <b>NEW PRODUCT AVAILABLE</b> 🔥\n"
                f"──────────────────\n"
                f"📦 <b>Name:</b> <code>{escaped_name}</code>\n"
                f"💵 <b>Price:</b> <code>${final_price:.2f} USD</code>\n"
                f"──────────────────\n"
                f"👉 <i>Get it now:</i> @{bot_username}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Buy Now", url=f"https://t.me/{bot_username}")]
            ])
            await bot_inst.send_message(chat_id=news_channel, text=announce_text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to log imported product announcement to news channel: {e}")
            
    text = get_text('prov_import_success', lang, name=prod.get('name_en'), price=final_price)
    await message_or_msg.answer(text, parse_mode="Markdown")
    await state.clear()

@router.message(ProvidersStates.waiting_for_price)
async def process_provider_price(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    try:
        price = float(message.text.strip().replace("$", ""))
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('prov_invalid_price', lang))
        return
        
    await state.update_data(fixed_price=price, pricing_type='fixed', margin_value=0.0)
    await finalize_imported_product(message, state, min_price=0.0, lang=lang)

@router.message(F.text.in_([
    get_text('btn_admin_pull_external', 'en'),
    get_text('btn_admin_pull_external', 'ar'),
    get_text('btn_admin_pull_external', 'ru'),
    "🔌 Pull External Product", "🔌 سحب منتج خارجي", "🔌 Импорт товара"
]))
async def msg_admin_pull_external(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    from database import get_providers
    providers = await get_providers()
    
    text = get_text('prov_list_title', lang)
    await message.answer(text, reply_markup=keyboards.get_providers_list_keyboard(providers, lang), parse_mode="Markdown")

# --- Admin Pre-orders Management Handlers ---
@router.message(F.text.in_([
    get_text('btn_admin_manage_preorders', 'en'),
    get_text('btn_admin_manage_preorders', 'ar'),
    get_text('btn_admin_manage_preorders', 'ru'),
    "⏳ Manage Pre-orders", "⏳ إدارة الحجوزات", "⏳ Управление предзаказами"
]))
async def msg_admin_preorders_summary(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    from database import get_preorders_summary
    summary = await get_preorders_summary()
    
    if not summary:
        await message.answer(get_text('admin_preorders_no_active', lang))
        return
        
    text = get_text('admin_preorders_summary_title', lang)
    await message.answer(text, reply_markup=keyboards.get_admin_preorders_summary_keyboard(summary, lang), parse_mode="Markdown")

@router.callback_query(F.data == "admin_preorders_summary")
async def cb_admin_preorders_summary(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    from database import get_preorders_summary
    summary = await get_preorders_summary()
    
    if not summary:
        await callback.message.edit_text(get_text('admin_preorders_no_active', lang), reply_markup=keyboards.get_admin_back_keyboard(lang))
        await callback.answer()
        return
        
    text = get_text('admin_preorders_summary_title', lang)
    await callback.message.edit_text(text, reply_markup=keyboards.get_admin_preorders_summary_keyboard(summary, lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_po_list_"))
async def cb_admin_product_preorders(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    product_id = int(callback.data.replace("adm_po_list_", ""))
    from database import get_all_active_preorders_for_product, get_product
    preorders = await get_all_active_preorders_for_product(product_id)
    product = await get_product(product_id)
    
    if not preorders or not product:
        await callback.answer(get_text('admin_preorders_no_active', lang), show_alert=True)
        # Return to summary
        await cb_admin_preorders_summary(callback, lang=lang)
        return
        
    prod_name = get_product_name(product, lang)
    text = get_text('admin_preorders_prod_title', lang, name=prod_name)
    await callback.message.edit_text(text, reply_markup=keyboards.get_admin_product_preorders_keyboard(preorders, lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_po_view_"))
async def cb_admin_preorder_detail(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    po_id = int(callback.data.replace("adm_po_view_", ""))
    
    # Query database directly for pre-order details
    import aiosqlite
    try:
        from bot_config import DB_NAME
    except ImportError:
        from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT po.*, p.name_en, p.name_ar, p.name_ru, u.first_name, u.username 
               FROM pre_orders po
               JOIN products p ON po.product_id = p.id
               LEFT JOIN users u ON po.user_id = u.user_id
               WHERE po.id = ?;""", (po_id,)
        ) as cursor:
            po = await cursor.fetchone()
            
    if not po:
        not_found_msg = {"en": "Pre-order not found.", "ar": "الحجز غير موجود.", "ru": "Предзаказ не найден."}.get(lang, "Pre-order not found.")
        await callback.answer(not_found_msg, show_alert=True)
        return
        
    buyer_name = po['first_name'] or "Unknown"
    buyer_uname = f"@{po['username']}" if po['username'] else ""
    buyer_str = f"{buyer_name} ({buyer_uname})" if buyer_uname else buyer_name
    prod_name = get_product_name(dict(po), lang)
    
    text = get_text(
        'admin_preorder_detail_title',
        lang,
        id=po['id'],
        name=prod_name,
        buyer=buyer_str,
        user_id=po['user_id'],
        qty=po['quantity'],
        price=po['price_paid'],
        date=po['created_at']
    )
    await callback.message.edit_text(text, reply_markup=keyboards.get_admin_preorder_actions_keyboard(po_id, po['product_id'], lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_po_cancel_"))
async def cb_admin_preorder_cancel(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    po_id = int(callback.data.replace("adm_po_cancel_", ""))
    from database import cancel_pre_order_by_admin
    
    try:
        user_id, refunded = await cancel_pre_order_by_admin(po_id)
        
        # Send a direct notification to the user about the admin refund
        try:
            notification_text = {
                "ar": f"⚠️ **[إلغاء حجز مسبق من الإدارة]**\n\nقام المسؤول بإلغاء حجزك المعلق. تم إرجاع مبلغ **`${refunded:.2f} USD`** كاملاً إلى محفظتك بالبوت.",
                "en": f"⚠️ **[Pre-order Cancelled by Admin]**\n\nYour active pre-order has been cancelled by the administrator. **`${refunded:.2f} USD`** has been refunded back to your wallet.",
                "ru": f"⚠️ **[Предзаказ отменен администратором]**\n\nВаш предзаказ был отменен администратором. **`${refunded:.2f} USD`** возвращены на ваш баланс."
            }
            # Fetch user language
            import aiosqlite
            try:
                from bot_config import DB_NAME
            except ImportError:
                from config import DB_NAME
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT language FROM users WHERE user_id = ?;", (user_id,)) as cur:
                    row = await cur.fetchone()
                    user_lang = row[0] if row else 'en'
            await callback.message.bot.send_message(chat_id=user_id, text=notification_text.get(user_lang, notification_text['en']), parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} of admin pre-order cancellation: {e}")
            
        cancel_alert = {
            "en": f"✅ Pre-order cancelled and ${refunded:.2f} USD refunded to user successfully!",
            "ar": f"✅ تم إلغاء الحجز وإرجاع ${refunded:.2f} دولار للمستخدم بنجاح!",
            "ru": f"✅ Предзаказ отменен, ${refunded:.2f} USD возвращены пользователю!"
        }.get(lang, f"✅ Pre-order cancelled and ${refunded:.2f} USD refunded to user successfully!")
        await callback.answer(cancel_alert, show_alert=True)
        
        # Return to summary
        await cb_admin_preorders_summary(callback, lang=lang)
        
    except Exception as err:
        await callback.answer(f"❌ Error: {err}", show_alert=True)


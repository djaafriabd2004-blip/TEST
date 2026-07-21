from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from database import (
    get_products, get_product, add_product, update_product, delete_product,
    add_stock, bulk_add_stock, get_stock_count, get_setting, set_setting, get_all_users,
    get_user, get_referral_count, get_all_pending_payments, get_stats,
    get_stock_notification_subscribers, clear_stock_notifications, get_user_full_report,
    get_sales_last_24h, get_button_emojis, ban_user, unban_user, is_user_banned, get_all_banned_users
)
from localization import get_text
from handlers.states import ProductStates, StockStates, AdminStates
import keyboards
import config
import logging

logger = logging.getLogger(__name__)
router = Router()

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
async def cb_admin_ban_user(callback: CallbackQuery):
    if not is_user_admin(callback.from_user.id):
        return
    target_id = int(callback.data.replace("admin_actban_", ""))
    await ban_user(target_id, "Banned by admin panel")
    await callback.answer(f"🔴 User {target_id} banned!", show_alert=True)
    try:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🟢 Unban User / إلغاء حظر المستخدم", callback_data=f"admin_actunban_{target_id}")
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    except Exception:
        pass

@router.callback_query(F.data.startswith("admin_actunban_"))
async def cb_admin_unban_user(callback: CallbackQuery):
    if not is_user_admin(callback.from_user.id):
        return
    target_id = int(callback.data.replace("admin_actunban_", ""))
    await unban_user(target_id)
    await callback.answer(f"🟢 User {target_id} unbanned!", show_alert=True)
    try:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🔴 Ban User / حظر المستخدم", callback_data=f"admin_actban_{target_id}")
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

@router.message(F.text == "📊 Statistics")
async def msg_admin_statistics(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return

    stats = await get_stats()
    store_name = await get_setting('store_name', 'Digital Store')

    text = (
        f"📊 *{store_name} — Statistics*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 *Users*\n"
        f"├ Total: `{stats['total_users']}`\n"
        f"└ Joined Today: `{stats['users_today']}`\n\n"
        f"💰 *Deposits*\n"
        f"├ Total: `{stats['total_deposit_count']}` — `${stats['total_deposits']:.2f}`\n"
        f"└ Today: `${stats['deposits_today']:.2f}`\n\n"
        f"🛍 *Orders (Sales)*\n"
        f"├ Total: `{stats['total_orders']}` — `${stats['total_order_revenue']:.2f}`\n"
        f"└ Today: `{stats['orders_today']}` — `${stats['order_revenue_today']:.2f}`\n\n"
        f"⏳ *Pending Deposits:* `{stats['pending_count']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
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

@router.message(F.text == "🔍 Inspect User")
async def msg_admin_inspect_user(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_inspect_user_id)
    await message.answer("🔍 Enter the User ID to inspect:", reply_markup=keyboards.get_admin_reply_keyboard())

@router.message(AdminStates.waiting_for_inspect_user_id)
async def process_inspect_user_id(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    if not message.text or not message.text.strip().isdigit():
        await message.answer("❌ Invalid User ID. Please enter a valid numeric User ID:")
        return
    user_id = int(message.text.strip())

    await state.clear()
    report = await get_user_full_report(user_id)

    if not report:
        await message.answer("❌ User not found in the database.")
        return

    u = report['user']
    name = escape_md(u.get('first_name', ''))
    username = f"@{escape_md(u.get('username', ''))}" if u.get('username') else "N/A"
    joined = u.get('joined_at', 'N/A')
    ref_by = escape_md(report['referred_by_name']) if report['referred_by_name'] else "None"

    is_banned = dict(u).get('is_banned', 0) == 1
    ban_status = f"🔴 BANNED (Reason: {u.get('ban_reason', 'N/A')})" if is_banned else "🟢 Active"

    # Build report text
    text = (
        f"🔍 *User Inspection Report*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *Profile*\n"
        f"├ Name: {name}\n"
        f"├ Username: {username}\n"
        f"├ ID: `{user_id}`\n"
        f"├ Status: {ban_status}\n"
        f"├ Balance: `${u.get('balance', 0):.2f} USD`\n"
        f"├ Discount: `{report['discount']:.0f}%`\n"
        f"├ Language: `{u.get('language', 'en')}`\n"
        f"└ Joined: `{joined}`\n\n"
        f"💰 *Deposits*\n"
        f"├ Completed: `{report['deposits_count']}` \u2014 `${report['deposits_total']:.2f}`\n"
        f"└ Pending: `{report['pending_count']}` \u2014 `${report['pending_total']:.2f}`\n\n"
        f"🛍 *Purchases*\n"
        f"├ Total Orders: `{report['orders_count']}`\n"
        f"└ Total Spent: `${report['orders_total']:.2f}`\n\n"
        f"👥 *Referrals*\n"
        f"├ Referred by: {ref_by}\n"
        f"├ Referrals count: `{report['referral_count']}`\n"
        f"└ Referral earnings: `${u.get('referral_balance_earned', 0):.2f}`\n"
    )

    # Recent deposits
    if report['recent_deposits']:
        text += "\n📝 *Recent Deposits (last 5)*\n"
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
        text += "\n📦 *Recent Orders (last 5)*\n"
        for o in report['recent_orders']:
            text += f"├ 🛍 `{escape_md(o['product_name_en'])}` \u2014 `${o['price_paid']:.2f}` ({o['purchased_at'][:10]})\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    if is_banned:
        builder.button(text="🟢 Unban User / إلغاء حظر المستخدم", callback_data=f"admin_actunban_{user_id}")
    else:
        builder.button(text="🔴 Ban User / حظر المستخدم", callback_data=f"admin_actban_{user_id}")

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

@router.message(F.text == "📦 Manage Products")
async def msg_admin_manage_products(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    products = await get_products()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Add Product", callback_data="admin_prod_add")
    for prod in products:
        name = prod['name_en']
        builder.button(text=f"✏️ {name} (${prod['price']:.2f})", callback_data=f"admin_prod_view_{prod['id']}")
    builder.button(text="🔙 Back to Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    
    await message.answer(
        "📦 *Product Management*\nSelect a product to edit/delete or add a new one:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.message(F.text.in_(["📥 Add Stock", "📦 Bulk Add Stock"]))
async def msg_admin_stock_select_prod(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        return
    action = "admin_add_stock" if message.text == "📥 Add Stock" else "admin_bulk_stock"
    products = await get_products()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for prod in products:
        builder.button(text=f"{prod['name_en']}", callback_data=f"admin_stk_{action.split('_')[1]}_{prod['id']}")
    builder.button(text="🔙 Back to Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    
    await message.answer(
        "📥 *Select Product for Stock adding*:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.message(F.text == "⏳ Pending Deposits")
async def msg_admin_pending_deposits(message: Message):
    if not is_user_admin(message.from_user.id):
        return
        
    pending_payments = await get_all_pending_payments()
    if not pending_payments:
        await message.answer("📭 No pending deposits at the moment.")
        return
        
    await message.answer(f"⏳ Found {len(pending_payments)} pending deposit request(s):")
    
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
        kb = keyboards.get_admin_payment_approval_keyboard(payment['transaction_id'])
        await message.answer(msg_text, reply_markup=kb, parse_mode="Markdown")

@router.message(F.text.in_([
    "📢 Channels Settings", 
    "🎧 Support Settings", 
    "💳 Charge Section", 
    "👥 Referral System",
    "🔑 API Keys Settings",
    "🎨 Button Emojis"
]))
async def msg_admin_settings_menu(message: Message):
    if not is_user_admin(message.from_user.id):
        return
    
    mapping = {
        "📢 Channels Settings": "admin_channels",
        "🎧 Support Settings": "admin_support_settings",
        "💳 Charge Section": "admin_charge_settings",
        "👥 Referral System": "admin_referral_settings",
        "🔑 API Keys Settings": "admin_api_keys_settings",
        "🎨 Button Emojis": "admin_emoji_settings"
    }
    menu = mapping[message.text]
    
    text = ""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    if menu == "admin_channels":
        force_join = await get_setting("force_join_channels", "None")
        news_ch = await get_setting("news_channel", "None")
        auto_proofs = await get_setting("auto_proofs_enabled", "0")
        proofs_icon = "🟢" if auto_proofs == "1" else "🔴"
        
        # Present channels as a clean list for the admin
        channels_list = ""
        if force_join and force_join != "None":
            ch_parts = [c.strip() for c in force_join.split(",") if c.strip()]
            for idx, c in enumerate(ch_parts, 1):
                channels_list += f"   {idx}. `{c}`\n"
        else:
            channels_list = "   (No channels set)\n"
            
        text = (
            f"📢 *Channel Settings*\n\n"
            f"🔗 *Compulsory Join Channels:*\n{channels_list}\n"
            f"📣 *News Channel:* `{news_ch}`\n"
            f"📢 *Auto Sales Proofs:* `{'Enabled' if auto_proofs == '1' else 'Disabled'}`\n\n"
            f"💡 *Tip:* When adding channels, enter them separated by a comma (e.g. `@channel1, @channel2`)\n"
            f"The bot will check them and display each channel as an individual button to the user!"
        )
        builder.button(text="✍️ Set Force Join Channels", callback_data="admin_set_force_join")
        builder.button(text="✍️ Set News Channel", callback_data="admin_set_news_ch")
        builder.button(text=f"📢 نشر المبيعات: {proofs_icon}", callback_data="admin_toggle_auto_proofs")
        
    elif menu == "admin_support_settings":
        support = await get_setting("support_username", "None")
        text = (
            f"🎧 *Support Settings*\n\n"
            f"👤 *Support Handle:* `{support}`"
        )
        builder.button(text="✍️ Edit Support Handle", callback_data="admin_set_support")
        
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
        
        text = (
            f"💳 *Deposit Settings*\n\n"
            f"⭐️ *Telegram Stars:* {s_status}\n"
            f"💱 *Stars Exchange Rate:* 1 Star = `{stars_rate}` USD\n\n"
            f"🤖 *Crypto Bot Gateway:* {cb_status}\n\n"
            f"🪙 *Manual Crypto Transfer:* {ct_status}\n"
            f"🪙 *USDT BEP20 Address:* `{usdt_addr}`\n"
            f"🪙 *LTC Address:* `{ltc_addr}`\n"
            f"🪙 *TON Address:* `{ton_addr}`\n"
            f"🪙 *Binance Pay ID / Email / Phone:* `{binance_addr}`"
        )
        builder.button(text="Toggle Telegram Stars", callback_data="admin_toggle_stars")
        builder.button(text="Set Stars Exchange Rate", callback_data="admin_set_stars_rate")
        builder.button(text="Toggle Crypto Bot", callback_data="admin_toggle_cryptobot")
        builder.button(text="Toggle Crypto Transfer", callback_data="admin_toggle_cryptotransfer")
        builder.button(text="✍️ Set USDT BEP20 Address", callback_data="admin_set_crypto_addr_usdt")
        builder.button(text="✍️ Set LTC Address", callback_data="admin_set_crypto_addr_ltc")
        builder.button(text="✍️ Set TON Address", callback_data="admin_set_crypto_addr_ton")
        builder.button(text="✍️ Set Binance ID/Email/Phone", callback_data="admin_set_crypto_addr_binance")
        
    elif menu == "admin_referral_settings":
        fixed_bonus = await get_setting("referral_bonus_percent", "1.0")
        text = (
            f"👥 *Referral System Settings*\n\n"
            f"💰 *Fixed Bonus Reward:* `${fixed_bonus} USD` immediately upon friend registration"
        )
        builder.button(text="✍️ Edit Fixed Bonus Reward", callback_data="admin_set_ref_pct")
        
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
        # Mask keys for display
        b_api_display = f"{binance_api_key[:8]}...{binance_api_key[-4:]}" if binance_api_key and binance_api_key != "None" and len(binance_api_key) > 12 else binance_api_key
        b_secret_display = f"{binance_secret_key[:8]}...{binance_secret_key[-4:]}" if binance_secret_key and binance_secret_key != "None" and len(binance_secret_key) > 12 else binance_secret_key
        
        text = (
            f"🔑 *API Keys & Proxy Configuration*\n\n"
            f"🔸 *BscScan API Key:* `{bscscan_key}`\n"
            f"🔗 [Get BscScan Key](https://bscscan.com/myapikey)\n\n"
            f"🪙 *Blockcypher API Token:* `{blockcypher_key}`\n"
            f"🔗 [Get Blockcypher Token](https://accounts.blockcypher.com/)\n\n"
            f"💎 *Toncenter API Key:* `{toncenter_key}`\n"
            f"🔗 [Get Toncenter Key](https://t.me/toncenter)\n\n"
            f"🤖 *Crypto Bot Token:* `{cryptobot_key}`\n"
            f"⚙️ *Crypto Bot Environment:* `{cb_testnet_status}`\n"
            f"🔗 [Get Crypto Bot Token](https://t.me/CryptoPayTestVar) (Testnet) or [@CryptoBot](https://t.me/CryptoBot?start=pay) (Mainnet)\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔶 *Binance API Key:* `{b_api_display}`\n"
            f"🔶 *Binance Secret Key:* `{b_secret_display}`\n"
            f"🌐 *Binance Proxy:* `{binance_proxy}`"
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
            'shop': '🛒 Shop / المتجر',
            'orders': '📦 My Orders / مشترياتي',
            'charge': '💳 Charge / شحن الرصيد',
            'referral': '👥 Referral / الإحالة',
            'support': '🎧 Support / الدعم',
            'language': '🌐 Language / اللغة',
            'admin': '⚙️ Admin / الإدارة',
        }
        w_status = f"`{welcome_eid[:12]}...`" if welcome_eid else "❌ None"
        text = "🎨 *Emoji Settings*\n\n"
        text += f"🔷 *Welcome Emoji:* {w_status}\n"
        text += "──────────────\n"
        for key, name in btn_names.items():
            emoji_id = emojis.get(key)
            status = f"`{emoji_id[:12]}...`" if emoji_id else "❌ None"
            text += f"▫️ {name}: {status}\n"
        text += "\nSelect an item to set its animated emoji:"
        
        builder.button(text="🔷 Welcome Emoji / إيموجي الترحيب", callback_data="admin_set_btn_emoji_welcome")
        for key, name in btn_names.items():
            builder.button(text=f"🎨 {name}", callback_data=f"admin_set_btn_emoji_{key}")
    
    builder.button(text="🔙 Back to Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.message(F.text == "📣 Broadcast")
async def msg_admin_broadcast_trigger(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await message.answer("📣 Send the message you want to broadcast to *all users* (can contain formatting or markdown):")

@router.message(F.text == "🔙 Back to Main Menu")
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
    
    builder.button(text="➕ Add Product", callback_data="admin_prod_add")
    
    for prod in products:
        name = prod['name_en']
        builder.button(text=f"✏️ {name} (${prod['price']:.2f})", callback_data=f"admin_prod_view_{prod['id']}")
        
    builder.button(text="🔙 Back to Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📦 *Product Management*\nSelect a product to edit/delete or add a new one:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_prod_view_"))
async def cb_admin_prod_view(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
        
    prod_id = int(callback.data.replace("admin_prod_view_", ""))
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    stock = await get_stock_count(prod_id)
    
    text = (
        f"📋 *Product Details (Admin)*\n\n"
        f"🇬🇧 *Name EN:* {product['name_en']}\n"
        f"🇸🇦 *Name AR:* {product['name_ar']}\n"
        f"🇷🇺 *Name RU:* {product['name_ru']}\n\n"
        f"🇬🇧 *Desc EN:* {product['description_en']}\n"
        f"🇸🇦 *Desc AR:* {product['description_ar']}\n"
        f"🇷🇺 *Desc RU:* {product['description_ru']}\n\n"
        f"💵 *Price:* ${product['price']:.2f} USD\n"
        f"📦 *Stock Count:* {stock} items available"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_product_edit_keyboard(prod_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_prod_del_"))
async def cb_admin_prod_del(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        return
    prod_id = int(callback.data.replace("admin_prod_del_", ""))
    await delete_product(prod_id)
    await callback.answer("Product deleted successfully!", show_alert=True)
    await cb_admin_manage_products(callback, lang)

# --- Add Product FSM ---
@router.callback_query(F.data == "admin_prod_add")
async def cb_admin_prod_add(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(ProductStates.waiting_for_name)
    await callback.message.answer("✏️ Enter Product Name:")
    await callback.answer()

@router.message(ProductStates.waiting_for_name)
async def add_prod_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ProductStates.waiting_for_desc)
    await message.answer("✏️ Enter Product Description:")

@router.message(ProductStates.waiting_for_desc)
async def add_prod_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text.strip())
    await state.set_state(ProductStates.waiting_for_price)
    await message.answer("✏️ Enter Product Price in *USD* (e.g. 5.50):")

@router.message(ProductStates.waiting_for_price)
async def add_prod_price(message: Message, state: FSMContext, bot: Bot, lang='en'):
    try:
        price = float(message.text)
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid price. Enter a positive decimal number:")
        return
        
    await state.update_data(price=price)
    await state.set_state(ProductStates.waiting_for_custom_emoji)
    await message.answer(
        "🎨 Now, send an animated Premium Custom Emoji for this product's icon, or type /skip to use no emoji.",
        reply_markup=keyboards.get_admin_back_keyboard()
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
        custom_emoji_id=custom_emoji_id
    )
    
    await message.answer(
        "✅ Product added successfully!",
        reply_markup=keyboards.get_admin_back_keyboard()
    )
    
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
# --- Edit Product FSM ---
@router.callback_query(F.data.startswith("admin_edit_fields_"))
async def cb_admin_edit_fields(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("admin_edit_fields_", ""))
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Name / الاسم", callback_data=f"admin_edit_spec_{prod_id}_name")
    builder.button(text="✏️ Description / الوصف", callback_data=f"admin_edit_spec_{prod_id}_desc")
    builder.button(text="✏️ Price / السعر", callback_data=f"admin_edit_spec_{prod_id}_price")
    builder.button(text="🔙 Back to Product Details", callback_data=f"admin_prod_view_{prod_id}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"✏️ *Editing Product:* {product['name_en']}\nSelect which field you want to edit:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_edit_spec_"))
async def cb_admin_edit_specific(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    prod_id = int(parts[3])
    field = "_".join(parts[4:])
    
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    await state.update_data(edit_prod_id=prod_id, edit_field=field)
    
    field_labels = {
        "name": "Name / الاسم",
        "desc": "Description / الوصف",
        "price": "Price / السعر"
    }
    
    field_label = field_labels.get(field, field)
    await state.set_state(ProductStates.waiting_for_edit_specific_value)
    
    await callback.message.answer(
        f"✏️ Enter new value for *{field_label}*:"
    )
    await callback.answer()

@router.message(ProductStates.waiting_for_edit_specific_value)
async def process_edit_specific_value(message: Message, state: FSMContext, bot: Bot):
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
        
    name_ar = product['name_ar']
    name_en = product['name_en']
    name_ru = product['name_ru']
    description_ar = product['description_ar']
    description_en = product['description_en']
    description_ru = product['description_ru']
    price = product['price']
    
    # Check if column exists in row (it should since we added it, but just in case)
    custom_emoji_id = product['custom_emoji_id'] if 'custom_emoji_id' in product.keys() else None
    
    if field == "name":
        name_ar = val
        name_en = val
        name_ru = val
    elif field == "desc":
        description_ar = val
        description_en = val
        description_ru = val
    elif field == "price":
        try:
            price = float(val)
            if price < 0:
                raise ValueError()
        except ValueError:
            await message.answer("❌ Invalid price. Enter a positive number:")
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
        bot=bot
    )
    
    await message.answer(
        f"✅ Product updated successfully!",
        reply_markup=keyboards.get_admin_back_keyboard()
    )

@router.callback_query(F.data.startswith("admin_edit_emoji_"))
async def cb_admin_edit_emoji(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("admin_edit_emoji_", ""))
    product = await get_product(prod_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    await state.update_data(edit_prod_id=prod_id)
    await state.set_state(ProductStates.waiting_for_edit_custom_emoji)
    
    await callback.message.answer(
        "🎨 Send a new animated Premium Custom Emoji for this product's icon, or type /skip to remove the current emoji."
    )
    await callback.answer()

@router.message(ProductStates.waiting_for_edit_custom_emoji)
async def process_edit_emoji(message: Message, state: FSMContext, bot: Bot):
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
    if message.text != '/skip' and message.entities:
        for entity in message.entities:
            if entity.type == 'custom_emoji':
                custom_emoji_id = entity.custom_emoji_id
                break
                
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
        bot=bot
    )
    
    await state.clear()
    await message.answer(
        "✅ Product emoji updated successfully!",
        reply_markup=keyboards.get_admin_back_keyboard()
    )

# --- Stock Settings ---
@router.callback_query(F.data.in_(["admin_add_stock", "admin_bulk_stock"]))
async def cb_admin_stock_select_prod(callback: CallbackQuery, state: FSMContext):
    action = callback.data
    products = await get_products()
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for prod in products:
        builder.button(text=f"{prod['name_en']}", callback_data=f"admin_stk_{action.split('_')[1]}_{prod['id']}")
        
    builder.button(text="🔙 Back to Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📥 *Select Product for Stock adding*:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_stk_"))
async def cb_admin_stock_prod_selected(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    # format: admin_stk_add_PRODID or admin_stk_bulk_PRODID
    action_type = parts[2]
    prod_id = int(parts[3])
    
    await state.update_data(stock_prod_id=prod_id)
    
    product = await get_product(prod_id)
    prod_name = product['name_en'] if product else "Product"
    
    if action_type == "add":
        await state.set_state(StockStates.waiting_for_stock_data)
        await callback.message.answer(f"📥 *Add Stock to {prod_name}*:\nPlease send the item credentials/text:")
    else:
        await state.set_state(StockStates.waiting_for_bulk_stock)
        await callback.message.answer(f"📦 *Bulk Add Stock to {prod_name}*:\nPlease send a list of items (one item per line):")
        
    await callback.answer()

@router.message(StockStates.waiting_for_stock_data)
async def process_single_stock(message: Message, state: FSMContext):
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
    
    await message.answer("✅ Stock item added successfully!", reply_markup=keyboards.get_admin_back_keyboard())
    
    # Notify admins about restock
    from database import notify_admins_stock_change
    await notify_admins_stock_change(message.bot, prod_id, 'refill', 1)
    
    # Broadcast restock notification to all users in private chats
    from database import broadcast_restock_to_users, clear_stock_notifications
    await broadcast_restock_to_users(message.bot, prod_id, 1)
    await clear_stock_notifications(prod_id)

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
    
    success_msg = (
        f"✅ Bulk added {len(lines)} stock items successfully!\n"
        f"✅ تم إضافة {len(lines)} منتج (مخزون) بنجاح!"
    )
    await message.answer(success_msg, reply_markup=keyboards.get_admin_back_keyboard())
    
    # Notify admins about restock
    from database import notify_admins_stock_change
    await notify_admins_stock_change(message.bot, prod_id, 'refill', len(lines))
    
    product = await get_product(prod_id)
    prod_name = product['name_en'] if product else "Product"
    prod_name_ar = product['name_ar'] if product else "منتج"
    
    # Broadcast restock notification to all users in private chats
    from database import broadcast_restock_to_users, clear_stock_notifications
    await broadcast_restock_to_users(message.bot, prod_id, len(lines))
    await clear_stock_notifications(prod_id)
            
    # Send News Channel announcement
    news_channel = await get_setting('news_channel', '')
    if news_channel and product:
        try:
            import html
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            escaped_prod_name = html.escape(prod_name)
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
async def cb_admin_settings_menu(callback: CallbackQuery, menu: str = None):
    menu = menu or callback.data
    text = ""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    if menu == "admin_channels":
        force_join = await get_setting("force_join_channels", "None")
        news_ch = await get_setting("news_channel", "None")
        
        # Present channels as a clean list for the admin
        channels_list = ""
        if force_join and force_join != "None":
            ch_parts = [c.strip() for c in force_join.split(",") if c.strip()]
            for idx, c in enumerate(ch_parts, 1):
                channels_list += f"   {idx}. `{c}`\n"
        else:
            channels_list = "   (No channels set)\n"
            
        text = (
            f"📢 *Channel Settings*\n\n"
            f"🔗 *Compulsory Join Channels:*\n{channels_list}\n"
            f"📣 *News Channel:* `{news_ch}`\n\n"
            f"💡 *Tip:* When adding channels, enter them separated by a comma (e.g. `@channel1, @channel2`)\n"
            f"The bot will check them and display each channel as an individual button to the user!"
        )
        builder.button(text="✍️ Set Force Join Channels", callback_data="admin_set_force_join")
        builder.button(text="✍️ Set News Channel", callback_data="admin_set_news_ch")
        
    elif menu == "admin_support_settings":
        support = await get_setting("support_username", "None")
        text = (
            f"🎧 *Support Settings*\n\n"
            f"👤 *Support Handle:* `{support}`"
        )
        builder.button(text="✍️ Edit Support Handle", callback_data="admin_set_support")
        
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
        
        text = (
            f"💳 *Deposit Settings*\n\n"
            f"⭐️ *Telegram Stars:* {s_status}\n"
            f"💱 *Stars Exchange Rate:* 1 Star = `{stars_rate}` USD\n\n"
            f"🤖 *Crypto Bot Gateway:* {cb_status}\n\n"
            f"🪙 *Manual Crypto Transfer:* {ct_status}\n"
            f"🪙 *USDT BEP20 Address:* `{usdt_addr}`\n"
            f"🪙 *LTC Address:* `{ltc_addr}`\n"
            f"🪙 *TON Address:* `{ton_addr}`\n"
            f"🪙 *Binance Pay ID / Email / Phone:* `{binance_addr}`"
        )
        builder.button(text="Toggle Telegram Stars", callback_data="admin_toggle_stars")
        builder.button(text="Set Stars Exchange Rate", callback_data="admin_set_stars_rate")
        builder.button(text="Toggle Crypto Bot", callback_data="admin_toggle_cryptobot")
        builder.button(text="Toggle Crypto Transfer", callback_data="admin_toggle_cryptotransfer")
        builder.button(text="✍️ Set USDT BEP20 Address", callback_data="admin_set_crypto_addr_usdt")
        builder.button(text="✍️ Set LTC Address", callback_data="admin_set_crypto_addr_ltc")
        builder.button(text="✍️ Set TON Address", callback_data="admin_set_crypto_addr_ton")
        builder.button(text="✍️ Set Binance ID/Email/Phone", callback_data="admin_set_crypto_addr_binance")
        
    elif menu == "admin_referral_settings":
        fixed_bonus = await get_setting("referral_bonus_percent", "1.0")
        text = (
            f"👥 *Referral System Settings*\n\n"
            f"💰 *Fixed Bonus Reward:* `${fixed_bonus} USD` immediately upon friend registration"
        )
        builder.button(text="✍️ Edit Fixed Bonus Reward", callback_data="admin_set_ref_pct")
        
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
        # Mask keys for display
        b_api_display = f"{binance_api_key[:8]}...{binance_api_key[-4:]}" if binance_api_key and binance_api_key != "None" and len(binance_api_key) > 12 else binance_api_key
        b_secret_display = f"{binance_secret_key[:8]}...{binance_secret_key[-4:]}" if binance_secret_key and binance_secret_key != "None" and len(binance_secret_key) > 12 else binance_secret_key
        
        text = (
            f"🔑 *API Keys & Proxy Configuration*\n\n"
            f"🔸 *BscScan API Key:* `{bscscan_key}`\n"
            f"🔗 [Get BscScan Key](https://bscscan.com/myapikey)\n\n"
            f"🪙 *Blockcypher API Token:* `{blockcypher_key}`\n"
            f"🔗 [Get Blockcypher Token](https://accounts.blockcypher.com/)\n\n"
            f"💎 *Toncenter API Key:* `{toncenter_key}`\n"
            f"🔗 [Get Toncenter Key](https://t.me/toncenter)\n\n"
            f"🤖 *Crypto Bot Token:* `{cryptobot_key}`\n"
            f"⚙️ *Crypto Bot Environment:* `{cb_testnet_status}`\n"
            f"🔗 [Get Crypto Bot Token](https://t.me/CryptoPayTestVar) (Testnet) or [@CryptoBot](https://t.me/CryptoBot?start=pay) (Mainnet)\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔶 *Binance API Key:* `{b_api_display}`\n"
            f"🔶 *Binance Secret Key:* `{b_secret_display}`\n"
            f"🌐 *Binance Proxy:* `{binance_proxy}`"
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
            'shop': '🛒 Shop / المتجر',
            'orders': '📦 My Orders / مشترياتي',
            'charge': '💳 Charge / شحن الرصيد',
            'referral': '👥 Referral / الإحالة',
            'support': '🎧 Support / الدعم',
            'language': '🌐 Language / اللغة',
            'admin': '⚙️ Admin / الإدارة',
        }
        w_status = f"`{welcome_eid[:12]}...`" if welcome_eid else "❌ None"
        text = "🎨 *Emoji Settings*\n\n"
        text += f"🔷 *Welcome Emoji:* {w_status}\n"
        text += "──────────────\n"
        for key, name in btn_names.items():
            emoji_id = emojis.get(key)
            status = f"`{emoji_id[:12]}...`" if emoji_id else "❌ None"
            text += f"▫️ {name}: {status}\n"
        text += "\nSelect an item to set its animated emoji:"
        
        builder.button(text="🔷 Welcome Emoji / إيموجي الترحيب", callback_data="admin_set_btn_emoji_welcome")
        for key, name in btn_names.items():
            builder.button(text=f"🎨 {name}", callback_data=f"admin_set_btn_emoji_{key}")
    
    builder.button(text="🔙 Back to Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

# --- Button Emoji Settings ---
@router.callback_query(F.data.startswith("admin_set_btn_emoji_"))
async def cb_admin_set_btn_emoji(callback: CallbackQuery, state: FSMContext):
    btn_key = callback.data.replace("admin_set_btn_emoji_", "")
    btn_names = {
        'welcome': '🔷 Welcome / الترحيب',
        'shop': '🛒 Shop / المتجر',
        'orders': '📦 My Orders / مشترياتي',
        'charge': '💳 Charge / شحن الرصيد',
        'referral': '👥 Referral / الإحالة',
        'support': '🎧 Support / الدعم',
        'language': '🌐 Language / اللغة',
        'admin': '⚙️ Admin / الإدارة',
    }
    name = btn_names.get(btn_key, btn_key)
    await state.update_data(btn_emoji_key=btn_key)
    await state.set_state(AdminStates.waiting_for_btn_emoji)
    await callback.message.answer(
        f"🎨 Send an animated Premium Custom Emoji for *{name}*, or type /skip to remove the current emoji."
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_btn_emoji)
async def process_btn_emoji(message: Message, state: FSMContext):
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
        await message.answer(
            f"✅ Emoji set successfully for *{btn_key}* button!\nID: `{custom_emoji_id}`\n\n💡 Send /start to see the changes.",
            reply_markup=keyboards.get_admin_back_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"✅ Emoji removed from *{btn_key}* button.\n\n💡 Send /start to see the changes.",
            reply_markup=keyboards.get_admin_back_keyboard(),
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "admin_toggle_auto_proofs")
async def cb_admin_toggle_auto_proofs(callback: CallbackQuery):
    if not is_user_admin(callback.from_user.id):
        return
    current = await get_setting("auto_proofs_enabled", "0")
    new_val = "0" if current == "1" else "1"
    await set_setting("auto_proofs_enabled", new_val)
    
    status_msg = "مفعل 🟢" if new_val == "1" else "معطل 🔴"
    await callback.answer(f"📢 النشر التلقائي للمبيعات الآن: {status_msg}", show_alert=True)
    
    force_join = await get_setting("force_join_channels", "None")
    news_ch = await get_setting("news_channel", "None")
    proofs_icon = "🟢" if new_val == "1" else "🔴"
    
    channels_list = ""
    if force_join and force_join != "None":
        ch_parts = [c.strip() for c in force_join.split(",") if c.strip()]
        for idx, c in enumerate(ch_parts, 1):
            channels_list += f"   {idx}. `{c}`\n"
    else:
        channels_list = "   (No channels set)\n"
        
    text = (
        f"📢 *Channel Settings*\n\n"
        f"🔗 *Compulsory Join Channels:*\n{channels_list}\n"
        f"📣 *News Channel:* `{news_ch}`\n"
        f"📢 *Auto Sales Proofs:* `{'Enabled' if new_val == '1' else 'Disabled'}`\n\n"
        f"💡 *Tip:* When adding channels, enter them separated by a comma (e.g. `@channel1, @channel2`)\n"
        f"The bot will check them and display each channel as an individual button to the user!"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Set Force Join Channels", callback_data="admin_set_force_join")
    builder.button(text="✍️ Set News Channel", callback_data="admin_set_news_ch")
    builder.button(text=f"📢 نشر المبيعات: {proofs_icon}", callback_data="admin_toggle_auto_proofs")
    builder.button(text="🔙 Back to Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    except Exception:
        pass

# Settings FSM triggers
@router.callback_query(F.data.startswith("admin_set_"))
async def cb_admin_set_setting(callback: CallbackQuery, state: FSMContext):
    setting_key = callback.data.replace("admin_set_", "")
    await state.update_data(setting_key=setting_key)
    await state.set_state(AdminStates.waiting_for_setting_value)
    
    prompts = {
        "force_join": "📢 Enter channels list (comma-separated, e.g. `@channel1,@my_channel` or leave blank to disable):",
        "news_ch": "📣 Enter news channel username or ID (e.g. `@my_news_channel` or `-10012345678`):",
        "support": "🎧 Enter support handler username (e.g. `@support_username`):",
        "stars_rate": "💱 Enter exchange rate (USD value per 1 Star, e.g. `0.02`):",
        "ref_pct": "👥 Enter fixed referral bonus in USD (awarded instantly on sign up, e.g. `1.50`):",
        "crypto_addr_usdt": "🪙 Enter new USDT BEP20 address:",
        "crypto_addr_ltc": "🪙 Enter new Litecoin (LTC) address:",
        "crypto_addr_ton": "🪙 Enter new TON address:",
        "crypto_addr_binance": "🪙 Enter new Binance Pay ID / Email / Phone:",
        "bscscan_api_key": "🔸 Enter BscScan API Key (get from https://bscscan.com/myapikey):",
        "blockcypher_api_key": "🪙 Enter Blockcypher API Token (get from https://accounts.blockcypher.com/):",
        "toncenter_api_key": "💎 Enter Toncenter API Key (get from @toncenter bot: https://t.me/toncenter):",
        "cryptobot_api_key": "🤖 Enter Crypto Bot API token (get from @CryptoPayTestVar or @CryptoBot):",
        "binance_api_proxy": "🌐 Enter Binance API Proxy (e.g. `http://user:pass@ip:port` or `socks5://ip:port`, or leave blank to disable):",
        "binance_api_key": "🔶 Enter your Binance API Key (get from https://www.binance.com/en/my/settings/api-management):",
        "binance_secret_key": "🔶 Enter your Binance Secret Key:"
    }
    
    prompt = prompts.get(setting_key, "Enter new value:")
    await callback.message.answer(prompt)
    await callback.answer()
 
@router.message(AdminStates.waiting_for_setting_value)
async def process_setting_value(message: Message, state: FSMContext):
    data = await state.get_data()
    setting_key = data.get("setting_key")
    await state.clear()
    
    val = message.text.strip()
    
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
    await message.answer(f"✅ Setting `{db_key}` updated to `{val}` successfully!", reply_markup=keyboards.get_admin_back_keyboard())
 
# Toggle Settings
@router.callback_query(F.data == "admin_toggle_stars")
async def cb_admin_toggle_payment(callback: CallbackQuery):
    method = "stars_enabled"
    current = await get_setting(method, "1")
    new_val = "0" if current == "1" else "1"
    await set_setting(method, new_val)
    
    await callback.answer(f"Toggled payment option!")
    # Reload settings menu without mutating callback.data
    await cb_admin_settings_menu(callback, menu="admin_charge_settings")

@router.callback_query(F.data == "admin_toggle_cryptotransfer")
async def cb_admin_toggle_cryptotransfer(callback: CallbackQuery):
    method = "cryptotransfer_enabled"
    current = await get_setting(method, "1")
    new_val = "0" if current == "1" else "1"
    await set_setting(method, new_val)
    
    await callback.answer(f"Toggled manual crypto transfer option!")
    await cb_admin_settings_menu(callback, menu="admin_charge_settings")

@router.callback_query(F.data == "admin_toggle_cryptobot")
async def cb_admin_toggle_cryptobot(callback: CallbackQuery):
    method = "cryptobot_enabled"
    current = await get_setting(method, "1")
    new_val = "0" if current == "1" else "1"
    await set_setting(method, new_val)
    
    await callback.answer(f"Toggled Crypto Bot gateway option!")
    await cb_admin_settings_menu(callback, menu="admin_charge_settings")

@router.callback_query(F.data == "admin_toggle_cryptobot_testnet")
async def cb_admin_toggle_cryptobot_testnet(callback: CallbackQuery):
    method = "cryptobot_use_testnet"
    current = await get_setting(method, "0")
    new_val = "0" if current == "1" else "1"
    await set_setting(method, new_val)
    
    await callback.answer(f"Toggled Crypto Bot testnet mode!")
    await cb_admin_settings_menu(callback, menu="admin_api_keys_settings")

# --- Admin Broadcast ---
@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast_trigger(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer("📣 Send the message you want to broadcast to *all users* (can contain formatting or markdown):")
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_admin_broadcast(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    if not is_user_admin(user_id):
        await state.clear()
        return
        
    broadcast_msg = message.text
    await state.clear()
    
    users = await get_all_users()
    if not users:
        await message.answer("❌ No users found in the database.")
        return
        
    wait_msg = await message.answer(f"⏳ Broadcasting to {len(users)} users...")
    
    success = 0
    fail = 0
    for u in users:
        try:
            # We broadcast the exact text
            await bot.send_message(chat_id=u['user_id'], text=broadcast_msg, parse_mode="Markdown")
            success += 1
        except Exception as e:
            fail += 1
            logger.warning(f"Could not broadcast to {u['user_id']}: {e}")
            
    await wait_msg.edit_text(
        f"📣 *Broadcast Completed!*\n\n"
        f"✅ *Successful:* `{success}`\n"
        f"❌ *Failed:* `{fail}`",
        reply_markup=keyboards.get_admin_back_keyboard(),
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

# --- User Discounts Management ---
@router.message(F.text == "👥 User Discounts")
async def msg_admin_discounts_menu(message: Message):
    if not is_user_admin(message.from_user.id):
        return
        
    from database import get_all_user_discounts
    discounts = await get_all_user_discounts()
    
    text = (
        "👥 *User Discounts Configuration*\n\n"
        "Here you can manage custom percentage discounts for specific users. "
        "A user with a discount will automatically get the corresponding price deduction at checkout."
    )
    
    await message.answer(
        text,
        reply_markup=keyboards.get_admin_discounts_keyboard(discounts),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_discounts_menu")
async def cb_admin_discounts_menu(callback: CallbackQuery):
    if not is_user_admin(callback.from_user.id):
        return
        
    from database import get_all_user_discounts
    discounts = await get_all_user_discounts()
    
    text = (
        "👥 *User Discounts Configuration*\n\n"
        "Here you can manage custom percentage discounts for specific users. "
        "A user with a discount will automatically get the corresponding price deduction at checkout."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_discounts_keyboard(discounts),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_discount_del_"))
async def cb_admin_discount_del(callback: CallbackQuery):
    if not is_user_admin(callback.from_user.id):
        return
        
    user_id = int(callback.data.replace("admin_discount_del_", ""))
    from database import delete_user_discount
    await delete_user_discount(user_id)
    
    await callback.answer("Discount deleted successfully!", show_alert=True)
    
    # Refresh view
    from database import get_all_user_discounts
    discounts = await get_all_user_discounts()
    await callback.message.edit_text(
        "👥 *User Discounts Configuration*\n\n"
        "Here you can manage custom percentage discounts for specific users. "
        "A user with a discount will automatically get the corresponding price deduction at checkout.",
        reply_markup=keyboards.get_admin_discounts_keyboard(discounts),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_discount_add")
async def cb_admin_discount_add(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
        
    await state.set_state(AdminStates.waiting_for_discount_user_id)
    await callback.message.answer("👥 Please enter the **User ID** of the user you want to grant a discount to:")
    await callback.answer()

@router.message(AdminStates.waiting_for_discount_user_id)
async def process_discount_user_id(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    val = message.text.strip()
    try:
        user_id = int(val)
    except ValueError:
        await message.answer("❌ Invalid User ID. Please enter a valid numerical User ID:")
        return
        
    # Check if user exists in database
    from database import get_user
    db_user = await get_user(user_id)
    if not db_user:
        await message.answer("❌ User not found in the database. The user must start/use the bot at least once. Please check the ID and try again:")
        return
        
    await state.update_data(discount_target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_discount_percent)
    
    name = escape_md(db_user['first_name'])
    if db_user['username']:
        name += f" (@{escape_md(db_user['username'])})"
    await message.answer(f"👤 Found User: {name} (`{user_id}`)\n\nNow, enter the Discount Percentage (e.g. `15` for 15%):")

@router.message(AdminStates.waiting_for_discount_percent)
async def process_discount_percent(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    val = message.text.strip()
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
        f"✅ Successfully set discount of **{percent}%** for *{name}*!",
        reply_markup=keyboards.get_admin_back_keyboard()
    )

@router.callback_query(F.data.startswith("admin_discount_edit_"))
async def cb_admin_discount_edit(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
        
    user_id = int(callback.data.replace("admin_discount_edit_", ""))
    await state.update_data(discount_target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_edit_discount_percent)
    
    from database import get_user
    db_user = await get_user(user_id)
    name = db_user['first_name'] if db_user else f"ID: {user_id}"
    await callback.message.answer(f"✏️ Enter the new discount percentage for *{name}* (e.g. `20` for 20%):")
    await callback.answer()

@router.message(AdminStates.waiting_for_edit_discount_percent)
async def process_edit_discount_percent(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    val = message.text.strip()
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
        f"✅ Successfully updated discount of **{percent}%** for *{name}*!",
        reply_markup=keyboards.get_admin_back_keyboard()
    )

# --- Edit Store Name ---
@router.message(F.text == "✏️ Edit Store Name")
async def msg_admin_edit_store_name(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        return
    
    current_name = await get_setting('store_name', 'Digital Store')
    await state.set_state(AdminStates.waiting_for_store_name)
    await message.answer(
        f"🏫 *Current Store Name:* `{current_name}`\n\n"
        f"✍️ *Please enter the new name for the store:*",
        parse_mode="Markdown"
    )

@router.message(AdminStates.waiting_for_store_name)
async def process_admin_store_name(message: Message, state: FSMContext):
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
        f"✅ *Store name successfully updated to:* `{new_name}`",
        reply_markup=keyboards.get_admin_back_keyboard(),
        parse_mode="Markdown"
    )

# --- User Balances Management ---
@router.message(F.text == "👥 Manage Users")
async def msg_admin_manage_users(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "👥 *Manage Users*\nSelect an option below:",
        reply_markup=keyboards.get_admin_manage_users_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_manage_users")
async def cb_admin_manage_users(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "👥 *Manage Users*\nSelect an option below:",
        reply_markup=keyboards.get_admin_manage_users_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- Ban Management Menu & Handlers ---
@router.message(F.text == "🚫 Ban / Unban System")
async def msg_admin_ban_unban_system(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🚫 *Ban / Unban Management System*\nاختر خياراً من الأسفل لربط وإدارة حظر المستخدمين:",
        reply_markup=keyboards.get_admin_ban_menu_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_ban_unban_menu")
async def cb_admin_ban_unban_menu(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "🚫 *Ban / Unban Management System*\nاختر خياراً من الأسفل لربط وإدارة حظر المستخدمين:",
        reply_markup=keyboards.get_admin_ban_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_ban_prompt")
async def cb_admin_ban_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_ban_user_id)
    await callback.message.edit_text(
        "🔴 *حظر مستخدم جديد*\n\nالرجاء إدخال **User ID الرقمي** للمستخدم المراد حظره:",
        reply_markup=keyboards.get_admin_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_ban_user_id)
async def process_ban_user_id(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ معرف مستخدم غير صحيح. يرجى كتابة أرقام فقط (User ID):")
        return
    target_id = int(text)
    await state.update_data(ban_target_id=target_id)
    await state.set_state(AdminStates.waiting_for_ban_reason)
    await message.answer(
        f"📝 تم اختيار المستخدم `{target_id}`.\nالرجاء إدخال **سبب الحظر** (أو إرسال /skip أو الضغط على زر التخطي أدناه):",
        reply_markup=keyboards.get_admin_ban_reason_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_ban_skip_reason")
async def cb_admin_ban_skip_reason(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    data = await state.get_data()
    target_id = data.get("ban_target_id")
    await state.clear()
    if not target_id:
        await callback.message.edit_text("❌ انتهت الجلسة أو حدث خطأ، يرجى إعادة المحاولة.", reply_markup=keyboards.get_admin_ban_menu_keyboard())
        await callback.answer()
        return
    reason = "Banned by admin panel"
    await ban_user(target_id, reason)
    await callback.message.edit_text(
        f"🔴 *تم حظر المستخدم بنجاح!*\n\n👤 ID: `{target_id}`\n💬 السبب: {reason}",
        reply_markup=keyboards.get_admin_ban_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_ban_reason)
async def process_ban_reason(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    target_id = data.get("ban_target_id")
    await state.clear()
    if not target_id:
        await message.answer("❌ حدث خطأ، يرجى إعادة المحاولة.")
        return
    reason = message.text.strip()
    if reason.lower() in ["تخطي", "skip", "/skip", "-"]:
        reason = "Banned by admin panel"
    await ban_user(target_id, reason)
    await message.answer(
        f"🔴 *تم حظر المستخدم بنجاح!*\n\n👤 ID: `{target_id}`\n💬 السبب: {reason}",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_unban_prompt")
async def cb_admin_unban_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_unban_user_id)
    await callback.message.edit_text(
        "🟢 *إلغاء حظر مستخدم*\n\nالرجاء إدخال **User ID الرقمي** للمستخدم المراد إلغاء حظره:",
        reply_markup=keyboards.get_admin_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_unban_user_id)
async def process_unban_user_id(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ معرف مستخدم غير صحيح. يرجى كتابة أرقام فقط (User ID):")
        return
    target_id = int(text)
    await state.clear()
    await unban_user(target_id)
    await message.answer(
        f"🟢 *تم إلغاء حظر المستخدم بنجاح!*\n\n👤 ID: `{target_id}`",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_show_banned")
async def cb_admin_show_banned(callback: CallbackQuery):
    if not is_user_admin(callback.from_user.id):
        return
    banned_users = await get_all_banned_users()
    if not banned_users:
        await callback.message.edit_text("✨ لا يوجد أي مستخدم محظور حالياً.", reply_markup=keyboards.get_admin_ban_menu_keyboard(), parse_mode="Markdown")
        await callback.answer()
        return
    
    text = "📋 *قائمة المستخدمين المحظورين حالياً:*\n━━━━━━━━━━━━━━━━━━━━\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for u in banned_users:
        u_id = u['user_id']
        u_name = escape_md(u['first_name'] or str(u_id))
        reason = u['ban_reason'] or "لا يوجد سبب"
        text += f"🔴 {u_name} (`{u_id}`) — السبب: {reason}\n"
        builder.button(text=f"🟢 Unban {u_id}", callback_data=f"admin_actunban_{u_id}")
    builder.button(text="🔙 Back", callback_data="admin_ban_unban_menu")
    builder.adjust(2)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_user_balances")
async def cb_admin_user_balances(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_balance_user_id)
    await callback.message.edit_text("💰 Please enter the **User ID** to view and edit their balance, or click the button below to see all users with balances:", reply_markup=keyboards.get_admin_balances_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_show_balances")
async def cb_admin_show_balances(callback: CallbackQuery, state: FSMContext):
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
    
    lines = ["👥 *Users with Balance:*\n"]
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
async def process_balance_user_id(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid User ID. Please enter a number:")
        return
    from database import get_user
    db_user = await get_user(user_id)
    if not db_user:
        await message.answer("❌ User not found. Try again:")
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
    
    await message.answer(text, reply_markup=keyboards.get_admin_user_balance_keyboard(user_id))

@router.callback_query(F.data.startswith("admin_edit_bal_"))
async def cb_admin_edit_balance(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        return
    user_id = int(callback.data.replace("admin_edit_bal_", ""))
    await state.update_data(balance_edit_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_new_balance)
    await callback.message.answer(f"💰 Enter the new balance for User ID `{user_id}` (e.g. `50.50`):", parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_new_balance)
async def process_new_balance(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
    try:
        new_balance = float(message.text.strip())
        if new_balance < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid amount. Enter a positive number:")
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
    
    await message.answer(f"✅ Successfully updated balance for {name} to ${new_balance:.2f}!", reply_markup=keyboards.get_admin_back_keyboard())


# --- Secret Database Backup & Restore Commands ---
@router.message(F.text == "/backup_db")
async def cmd_backup_db(message: Message, bot: Bot):
    if not is_user_admin(message.from_user.id):
        return
        
    from aiogram.types import FSInputFile
    import os
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
async def cb_admin_api_keys(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    await state.clear()
    
    from database import get_all_api_keys
    keys = await get_all_api_keys()
    
    text = "🔑 *Reseller API Keys*\n\n"
    if not keys:
        text += "No active reseller API keys found."
    else:
        for idx, k in enumerate(keys, 1):
            name = k['first_name'] or f"ID: {k['user_id']}"
            if k['username']:
                name += f" (@{k['username']})"
            text += f"{idx}. *{name}*\n`{k['api_key']}`\n\n"
            
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_api_keys_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_api_key_gen")
async def cb_admin_api_key_gen(callback: CallbackQuery, state: FSMContext):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    await state.set_state(AdminStates.waiting_for_api_key_user_id)
    await callback.message.edit_text(
        "➕ *Generate API Key*\n\nPlease enter the numeric *Telegram User ID* of the user you want to generate an API key for:",
        reply_markup=keyboards.get_admin_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_api_key_user_id)
async def process_api_key_user_id(message: Message, state: FSMContext):
    if not is_user_admin(message.from_user.id):
        await state.clear()
        return
        
    user_id_str = message.text.strip()
    if not user_id_str.isdigit():
        await message.answer("❌ Invalid User ID. Please enter a valid numeric Telegram User ID:")
        return
        
    user_id = int(user_id_str)
    
    from database import get_user, generate_api_key
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ User not found in the database. The user must start the bot at least once before you can generate an API key for them.")
        return
        
    await state.clear()
    try:
        api_key = await generate_api_key(user_id)
        name = user['first_name'] or f"ID: {user_id}"
        if user['username']:
            name += f" (@{user['username']})"
            
        success_text = (
            f"✅ *API Key Generated Successfully!*\n\n"
            f"👤 *Partner:* {name}\n"
            f"🔑 *API Key:* `{api_key}`\n\n"
            f"💡 Give this key to the partner. They should include it in their requests headers as `X-API-Key`."
        )
        await message.answer(success_text, reply_markup=keyboards.get_admin_back_keyboard(), parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error generating API key: {e}", reply_markup=keyboards.get_admin_back_keyboard())

@router.callback_query(F.data == "admin_api_key_revoke_select")
async def cb_admin_api_key_revoke_select(callback: CallbackQuery):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    from database import get_all_api_keys
    keys = await get_all_api_keys()
    if not keys:
        await callback.answer("No active API keys to revoke.", show_alert=True)
        return
        
    await callback.message.edit_text(
        "❌ *Select API Key to Revoke*\n\nChoose the partner whose API key you want to delete/revoke:",
        reply_markup=keyboards.get_admin_api_key_revoke_keyboard(keys),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_api_key_rev_"))
async def cb_admin_api_key_rev_confirm(callback: CallbackQuery):
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
    text = "🔑 *Reseller API Keys*\n\n"
    if not keys:
        text += "No active reseller API keys found."
    else:
        for idx, k in enumerate(keys, 1):
            name_k = k['first_name'] or f"ID: {k['user_id']}"
            if k['username']:
                name_k += f" (@{k['username']})"
            text += f"{idx}. *{name_k}*\n`{k['api_key']}`\n\n"
            
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_admin_api_keys_keyboard(),
        parse_mode="Markdown"
    )


# --- Provider Integration Admin Handlers ---
from handlers.states import ProvidersStates

async def fetch_provider_store_name(base_url, api_key):
    import aiohttp
    base_url = base_url.strip().rstrip('/')
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    is_supabase = "supabase.co" in base_url
    
    headers = {}
    if is_supabase:
        headers["Authorization"] = f"Bearer {api_key}"
        url = f"{base_url}?action=balance"
    else:
        headers["X-API-Key"] = api_key
        url = f"{base_url}/api/me"
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if is_supabase:
                        return "Supabase Reseller API"
                    if data.get('ok') and data.get('store_name'):
                        return data['store_name']
                    elif data.get('ok') and 'user' in data:
                        return f"Partner: {data['user']['first_name']}"
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
    import aiohttp
    base_url = base_url.strip().rstrip('/')
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    is_supabase = "supabase.co" in base_url
    
    headers = {}
    if is_supabase:
        headers["Authorization"] = f"Bearer {api_key}"
        url = f"{base_url}?action=products"
    else:
        headers["X-API-Key"] = api_key
        url = f"{base_url}/api/products"
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if is_supabase:
                        raw_list = data if isinstance(data, list) else data.get('products', [])
                        formatted = []
                        for p in raw_list:
                            formatted.append({
                                "id": p.get("id"),
                                "name_ar": p.get("name"),
                                "name_en": p.get("name"),
                                "name_ru": p.get("name"),
                                "description_ar": f"Imported Supabase Product: {p.get('name')}",
                                "description_en": f"Imported Supabase Product: {p.get('name')}",
                                "description_ru": f"Imported Supabase Product: {p.get('name')}",
                                "price": float(p.get("price", 0.0)),
                                "custom_emoji_id": None
                            })
                        return formatted
                    return data.get('products') if data.get('ok') else None
    except Exception as e:
        logger.error(f"Error fetching provider products: {e}")
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
    else:
        # Fetch remote store name
        store_name = await fetch_provider_store_name(url, key)
        
        from database import save_provider, get_providers
        await save_provider(url, key, store_name=store_name)
        
        # Get the ID of the newly saved provider
        providers = await get_providers()
        prov_id = 1
        for p in providers:
            p_url = p['base_url'].strip().rstrip('/')
            clean_url = url.strip().rstrip('/')
            if p_url == clean_url or p_url.replace("https://", "").replace("http://", "") == clean_url.replace("https://", "").replace("http://", ""):
                prov_id = p['id']
                break
                
        await state.update_data(prov_products=products, prov_id=prov_id)
        await message.answer(get_text('prov_select_product', lang), reply_markup=keyboards.get_provider_products_keyboard(products, lang))

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
        
    await state.update_data(selected_prov_prod=selected_prod)
    await state.set_state(ProvidersStates.waiting_for_price)
    
    text = get_text('prov_price_prompt', lang, price=selected_prod['price'])
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@router.message(ProvidersStates.waiting_for_price)
async def process_provider_price(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('prov_invalid_price', lang))
        return
        
    data = await state.get_data()
    prod = data.get('selected_prov_prod')
    prov_id = data.get('prov_id')
    
    if not prod or not prov_id:
        await message.answer("❌ Error: session expired. Please restart the import process.")
        await state.clear()
        return
        
    from database import add_imported_product
    
    await add_imported_product(
        name_ar=prod.get('name_ar', prod.get('name_en')),
        name_en=prod.get('name_en'),
        name_ru=prod.get('name_ru', prod.get('name_en')),
        description_ar=prod.get('description_ar', prod.get('description_en')),
        description_en=prod.get('description_en'),
        description_ru=prod.get('description_ru', prod.get('description_en')),
        price=price,
        custom_emoji_id=prod.get('custom_emoji_id'),
        provider_id=prov_id,
        provider_product_id=prod['id']
    )
    
    text = get_text('prov_import_success', lang, name=prod.get('name_en'), price=price)
    await message.answer(text, parse_mode="Markdown")
    await state.clear()

@router.message(F.text == "🔌 Pull External Product")
async def msg_admin_pull_external(message: Message, state: FSMContext, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    from database import get_providers
    providers = await get_providers()
    
    text = get_text('prov_list_title', lang)
    await message.answer(text, reply_markup=keyboards.get_providers_list_keyboard(providers, lang), parse_mode="Markdown")

# --- Admin Pre-orders Management Handlers ---
@router.message(F.text == "⏳ Manage Pre-orders")
async def msg_admin_preorders_summary(message: Message, lang='en'):
    if not is_user_admin(message.from_user.id):
        return
        
    from database import get_preorders_summary
    summary = await get_preorders_summary()
    
    if not summary:
        await message.answer("📭 No active pre-orders/reservations at the moment.")
        return
        
    text = (
        "⏳ *Active Pre-orders Summary*\n\n"
        "Here you can see all products that users have reserved due to being out of stock. "
        "Select a product to view individual reservations or cancel them:"
    )
    await message.answer(text, reply_markup=keyboards.get_admin_preorders_summary_keyboard(summary), parse_mode="Markdown")

@router.callback_query(F.data == "admin_preorders_summary")
async def cb_admin_preorders_summary(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    from database import get_preorders_summary
    summary = await get_preorders_summary()
    
    if not summary:
        await callback.message.edit_text("📭 No active pre-orders/reservations at the moment.", reply_markup=keyboards.get_admin_back_keyboard())
        await callback.answer()
        return
        
    text = (
        "⏳ *Active Pre-orders Summary*\n\n"
        "Here you can see all products that users have reserved due to being out of stock. "
        "Select a product to view individual reservations or cancel them:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.get_admin_preorders_summary_keyboard(summary), parse_mode="Markdown")
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
        await callback.answer("No active reservations for this product anymore.", show_alert=True)
        # Return to summary
        await cb_admin_preorders_summary(callback, lang)
        return
        
    prod_name = product['name_en']
    text = (
        f"📦 *Reservations for:* `{prod_name}`\n"
        f"Select a specific user's reservation to view actions:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.get_admin_product_preorders_keyboard(preorders), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("adm_po_view_"))
async def cb_admin_preorder_detail(callback: CallbackQuery, lang='en'):
    if not is_user_admin(callback.from_user.id):
        await callback.answer("Not authorized.")
        return
        
    po_id = int(callback.data.replace("adm_po_view_", ""))
    
    # Query database directly for pre-order details
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT po.*, p.name_en, u.first_name, u.username 
               FROM pre_orders po
               JOIN products p ON po.product_id = p.id
               LEFT JOIN users u ON po.user_id = u.user_id
               WHERE po.id = ?;""", (po_id,)
        ) as cursor:
            po = await cursor.fetchone()
            
    if not po:
        await callback.answer("Pre-order not found.", show_alert=True)
        return
        
    buyer_name = po['first_name'] or "Unknown"
    buyer_uname = f"@{po['username']}" if po['username'] else "No Username"
    
    text = (
        f"⏳ *Pre-order Reservation Details*\n\n"
        f"🆔 *Pre-order ID:* `{po['id']}`\n"
        f"📦 *Product:* `{po['name_en']}`\n"
        f"👤 *User:* {buyer_name} ({buyer_uname}) [ID: `{po['user_id']}`]\n"
        f"🔢 *Quantity:* `{po['quantity']}`\n"
        f"💰 *Amount Locked:* `${po['price_paid']:.2f} USD`\n"
        f"📅 *Created At:* `{po['created_at']}`\n\n"
        f"⚠️ *Admin Action:* You can cancel this reservation. Doing so will immediately delete the pre-order and refund the amount back to the user's wallet."
    )
    await callback.message.edit_text(text, reply_markup=keyboards.get_admin_preorder_actions_keyboard(po_id, po['product_id']), parse_mode="Markdown")
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
            from config import DB_NAME
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT language FROM users WHERE user_id = ?;", (user_id,)) as cur:
                    row = await cur.fetchone()
                    user_lang = row[0] if row else 'en'
            await callback.message.bot.send_message(chat_id=user_id, text=notification_text.get(user_lang, notification_text['en']), parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} of admin pre-order cancellation: {e}")
            
        await callback.answer(f"✅ Pre-order cancelled and ${refunded:.2f} USD refunded to user successfully!", show_alert=True)
        
        # Return to summary
        await cb_admin_preorders_summary(callback, lang)
        
    except Exception as err:
        await callback.answer(f"❌ Error cancelling pre-order: {err}", show_alert=True)


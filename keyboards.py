from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from localization import get_text
try:
    import bot_config as config
except ImportError:
    import config

def get_main_menu(lang='en', is_admin=False, button_emojis=None) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    if button_emojis is None:
        button_emojis = {}
    
    # Button keys for emoji mapping
    buttons = [
        ('btn_shop', 'shop', 'success'),
        ('btn_my_orders', 'orders', 'primary'),
        ('btn_my_preorders', 'preorders', 'primary'),
        ('btn_charge_balance', 'charge', 'primary'),
        ('btn_referral', 'referral', 'primary'),
        ('btn_support', 'support', None),
        ('btn_language', 'language', None),
        ('btn_reseller_api', 'reseller_api', None),
    ]
    
    for text_key, emoji_key, style in buttons:
        kwargs = {"text": get_text(text_key, lang)}
        if style:
            kwargs["style"] = style
        emoji_id = button_emojis.get(emoji_key)
        if emoji_id:
            kwargs["icon_custom_emoji_id"] = emoji_id
        builder.button(**kwargs)
    
    builder.adjust(2, 2, 2, 2)
    
    if is_admin:
        # Add admin panel on its own line
        admin_kwargs = {"text": get_text('btn_admin_panel', lang), "style": "danger"}
        admin_emoji = button_emojis.get('admin')
        if admin_emoji:
            admin_kwargs["icon_custom_emoji_id"] = admin_emoji
        builder.row(KeyboardButton(**admin_kwargs))
        
    return builder.as_markup(resize_keyboard=True)

def get_language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇸 English", callback_data="set_lang_en")
    builder.button(text="🇸🇦 العربية", callback_data="set_lang_ar")
    builder.button(text="🇷🇺 Русский", callback_data="set_lang_ru")
    builder.adjust(1)
    return builder.as_markup()

def get_products_keyboard(products, stock_counts=None, lang='en') -> InlineKeyboardMarkup:
    if not lang or lang not in ['en', 'ar', 'ru']:
        lang = 'en'
    builder = InlineKeyboardBuilder()
    if stock_counts is None:
        stock_counts = {}
    for product in products:
        # Show product name + price
        keys = product.keys() if hasattr(product, 'keys') else []
        name_key = f'name_{lang}'
        name = product[name_key] if name_key in keys else product['name_en']
        price = product['price']
        emoji_id = product['custom_emoji_id'] if 'custom_emoji_id' in product.keys() else None
        
        stock = stock_counts.get(product['id'], 0)
        style = "success" if stock > 0 else "danger"
        
        kwargs = {
            "text": f"{name} - ${price:.2f}",
            "callback_data": f"prod_view_{product['id']}",
            "style": style
        }
        if emoji_id:
            kwargs["icon_custom_emoji_id"] = emoji_id
        
        builder.button(**kwargs)
    builder.adjust(1)
    return builder.as_markup()

def get_product_view_keyboard(product_id, has_stock, lang='en', is_subscribed=False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_stock:
        builder.button(text=get_text('btn_buy', lang), callback_data=f"prod_buy_{product_id}", style="success", icon_custom_emoji_id="5368324170671202286")
    else:
        # Out of stock: Show Pre-order reservation button AND subscribe notifications button
        builder.button(text=get_text('btn_preorder', lang), callback_data=f"prod_preorder_{product_id}", style="success")
        if is_subscribed:
            builder.button(text=get_text('btn_cancel_notify_stock', lang), callback_data=f"notify_unsub_{product_id}")
        else:
            builder.button(text=get_text('btn_notify_stock', lang), callback_data=f"notify_sub_{product_id}", style="primary")
    builder.button(text=get_text('btn_back', lang), callback_data="shop_list", style="danger")
    builder.adjust(1)
    return builder.as_markup()

def get_checkout_keyboard(product_id, qty, balance, price_to_pay, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # 1. Pay with Balance (if user balance is enough)
    if round(balance, 2) >= price_to_pay:
        builder.button(text=get_text('btn_pay_balance', lang, balance=balance), callback_data=f"chk_bal_{product_id}_{qty}")
        
    # 2. Pay with Binance Pay
    builder.button(text=get_text('btn_pay_binance', lang), callback_data=f"chk_bin_{product_id}_{qty}")
    
    # 3. Direct button to other payment methods (charge balance menu)
    builder.button(text=get_text('btn_other_payment_methods', lang), callback_data="charge_menu", style="primary")
    
    # Back button
    builder.button(text=get_text('btn_back', lang), callback_data=f"prod_view_{product_id}", style="danger")
    builder.adjust(1)
    return builder.as_markup()

def get_binance_id_checkout_keyboard(product_id, qty, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_check_payment', lang), callback_data=f"chk_verify_binid_{product_id}_{qty}")
    builder.button(text=get_text('btn_back', lang), callback_data=f"prod_view_{product_id}", style="danger")
    builder.adjust(1)
    return builder.as_markup()

def get_charge_methods_keyboard(lang='en', stars_enabled=True, cryptobot_enabled=True, cryptotransfer_enabled=True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if stars_enabled:
        builder.button(text=get_text('btn_stars', lang), callback_data="charge_stars", style="primary")
    if cryptobot_enabled:
        builder.button(text=get_text('btn_cryptobot', lang), callback_data="charge_cryptobot", style="primary")
    if cryptotransfer_enabled:
        builder.button(text=get_text('btn_cryptotransfer', lang), callback_data="charge_cryptotransfer", style="primary")
    builder.button(text=get_text('btn_back', lang), callback_data="cancel_charge", style="danger")
    builder.adjust(1)
    return builder.as_markup()

def get_crypto_coins_keyboard(lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="USDT BEP20", callback_data="crypto_coin_USDT")
    builder.button(text="Litecoin (LTC)", callback_data="crypto_coin_LTC")
    builder.button(text="TON", callback_data="crypto_coin_TON")
    builder.button(text="Binance ID / Pay (USDT)", callback_data="crypto_coin_BINANCE")
    builder.button(text=get_text('btn_back', lang), callback_data="charge_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_payment_approval_keyboard(transaction_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Approve", callback_data=f"admin_pay_approve_{transaction_id}")
    builder.button(text="❌ Reject", callback_data=f"admin_pay_reject_{transaction_id}")
    builder.adjust(2)
    return builder.as_markup()

# Admin Keyboard
def get_admin_reply_keyboard(lang='en') -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text('btn_admin_stats', lang))
    builder.button(text=get_text('btn_admin_inspect_user', lang))
    builder.button(text=get_text('btn_admin_manage_products', lang))
    builder.button(text=get_text('btn_admin_add_stock', lang))
    builder.button(text=get_text('btn_admin_bulk_stock', lang))
    builder.button(text=get_text('btn_admin_pending_deposits', lang))
    builder.button(text=get_text('btn_admin_manage_preorders', lang))
    builder.button(text=get_text('btn_admin_channels', lang))
    builder.button(text=get_text('btn_admin_support', lang))
    builder.button(text=get_text('btn_admin_charge', lang))
    builder.button(text=get_text('btn_admin_referral', lang))
    builder.button(text=get_text('btn_admin_api_keys', lang))
    builder.button(text=get_text('btn_admin_manage_users', lang))
    builder.button(text=get_text('btn_admin_ban_system', lang))
    builder.button(text=get_text('btn_admin_broadcast', lang))
    builder.button(text=get_text('btn_admin_edit_store_name', lang))
    builder.button(text=get_text('btn_admin_button_emojis', lang))
    builder.button(text=get_text('btn_admin_pull_external', lang))
    builder.button(text=get_text('btn_admin_back_to_menu', lang))
    builder.adjust(2, 2, 2, 2, 2, 2, 3, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_user_balance_keyboard(user_id, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit Balance", callback_data=f"admin_edit_bal_{user_id}")
    builder.button(text=get_text('btn_admin_back', lang), callback_data="admin_manage_users")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_balances_menu_keyboard(lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_admin_show_balances', lang), callback_data="admin_show_balances")
    return builder.as_markup()

def get_admin_manage_users_keyboard(lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_admin_custom_prices', lang), callback_data="admin_custom_prices_menu")
    builder.button(text=get_text('btn_admin_user_discounts', lang), callback_data="admin_discounts_menu")
    builder.button(text=get_text('btn_admin_edit_balances', lang), callback_data="admin_user_balances")
    builder.button(text=get_text('btn_admin_show_balances', lang), callback_data="admin_show_balances")
    builder.button(text=get_text('btn_admin_ban_system', lang), callback_data="admin_ban_unban_menu")
    builder.button(text=get_text('btn_admin_back_to_panel', lang), callback_data="admin_menu")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def get_admin_custom_prices_keyboard(custom_prices, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_admin_add_custom_price', lang), callback_data="admin_custom_price_add")
    for cp in custom_prices:
        user_id = cp['user_id']
        prod_id = cp['product_id']
        custom_price = cp['custom_price']
        name_k = f'name_{lang}'
        prod_name = cp.get(name_k) or cp.get('name_en') or f"Product #{prod_id}"
        user_name = cp.get('first_name') or f"ID: {user_id}"
        if cp.get('username'):
            user_name += f" (@{cp['username']})"
        builder.button(text=f"👤 {user_name} | {prod_name}: ${custom_price:.2f}", callback_data=f"admin_cp_sel_{user_id}_{prod_id}")
        builder.button(text=get_text('btn_admin_delete', lang), callback_data=f"admin_cp_del_{user_id}_{prod_id}")
        
    adjust_pattern = [1]
    for _ in range(len(custom_prices)):
        adjust_pattern.append(2)
    adjust_pattern.append(1)
    builder.button(text=get_text('btn_admin_back', lang), callback_data="admin_manage_users")
    builder.adjust(*adjust_pattern)
    return builder.as_markup()

def get_admin_select_product_for_custom_price_keyboard(products, user_id, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for prod in products:
        name_k = f'name_{lang}'
        prod_name = prod.get(name_k) or prod.get('name_en') or f"Product #{prod['id']}"
        price = prod.get('price', 0.0)
        builder.button(text=f"🛍️ {prod_name} (${price:.2f})", callback_data=f"admin_cp_set_{user_id}_{prod['id']}")
    builder.button(text=get_text('btn_admin_back', lang), callback_data="admin_custom_prices_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_ban_menu_keyboard(lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ban_txt = {"en": "🔴 Ban User", "ar": "🔴 حظر مستخدم", "ru": "🔴 Забанить"}.get(lang, "🔴 Ban User")
    unban_txt = {"en": "🟢 Unban User", "ar": "🟢 فك حظر مستخدم", "ru": "🟢 Разбанить"}.get(lang, "🟢 Unban User")
    list_txt = {"en": "📋 Show Banned Users", "ar": "📋 عرض المحظورين", "ru": "📋 Список забаненных"}.get(lang, "📋 Show Banned Users")
    builder.button(text=ban_txt, callback_data="admin_ban_prompt")
    builder.button(text=unban_txt, callback_data="admin_unban_prompt")
    builder.button(text=list_txt, callback_data="admin_show_banned")
    builder.button(text=get_text('btn_admin_back', lang), callback_data="admin_manage_users")
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def get_admin_ban_reason_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭️ Skip Reason / تخطي السبب", callback_data="admin_ban_skip_reason")
    builder.button(text="🔙 Cancel / إلغاء", callback_data="admin_ban_unban_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_menu_keyboard(lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_admin_manage_products', lang), callback_data="admin_manage_products")
    builder.button(text=get_text('btn_admin_channels', lang), callback_data="admin_channels")
    builder.button(text=get_text('btn_admin_add_stock', lang), callback_data="admin_add_stock")
    builder.button(text=get_text('btn_admin_bulk_stock', lang), callback_data="admin_bulk_stock")
    builder.button(text=get_text('btn_admin_support', lang), callback_data="admin_support_settings")
    builder.button(text=get_text('btn_admin_charge', lang), callback_data="admin_charge_settings")
    builder.button(text=get_text('btn_admin_referral', lang), callback_data="admin_referral_settings")
    builder.button(text=get_text('btn_admin_manage_users', lang), callback_data="admin_manage_users")
    builder.button(text=get_text('btn_admin_broadcast', lang), callback_data="admin_broadcast")
    builder.button(text=get_text('btn_admin_button_emojis', lang), callback_data="admin_emoji_settings")
    builder.button(text=get_text('btn_admin_api_keys', lang), callback_data="admin_api_keys")
    builder.button(text=get_text('btn_admin_pull_external', lang), callback_data="admin_pull_external")
    builder.adjust(2)
    return builder.as_markup()

def get_admin_products_keyboard(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(text=f"✏️ {product['name_en']} (${product['price']:.2f})", callback_data=f"admin_prod_edit_{product['id']}")
    builder.button(text="➕ Add Product", callback_data="admin_prod_add")
    builder.button(text="🔙 Back to Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_product_edit_keyboard(product_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Edit Details", callback_data=f"admin_edit_fields_{product_id}")
    builder.button(text="🏷️ أسعار الجملة (Tier Prices)", callback_data=f"admin_prod_tiers_{product_id}")
    builder.button(text="🎨 Edit Emoji", callback_data=f"admin_edit_emoji_{product_id}")
    builder.button(text="🗑️ Delete Product", callback_data=f"admin_prod_del_{product_id}")
    builder.button(text="🔙 Back", callback_data="admin_manage_products")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_tier_prices_keyboard(product_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ إضافة سعر كمية جديد", callback_data=f"admin_add_tier_{product_id}")
    builder.button(text="🗑️ مسح جميع أسعار الجملة", callback_data=f"admin_clear_tiers_{product_id}")
    builder.button(text="🔙 Back", callback_data=f"admin_prod_view_{product_id}")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_support_ticket_keyboard(user_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Reply to User", callback_data=f"ticket_reply_{user_id}")
    return builder.as_markup()

def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Back to Admin Panel", callback_data="admin_menu")
    return builder.as_markup()

def get_admin_discounts_keyboard(discounts, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_admin_add_discount', lang), callback_data="admin_discount_add")
    for d in discounts:
        user_id = d['user_id']
        percent = d['discount_percent']
        name = d['first_name'] or f"ID: {user_id}"
        if d['username']:
            name += f" (@{d['username']})"
        builder.button(text=f"✏️ {name} - {percent}%", callback_data=f"admin_discount_edit_{user_id}")
        builder.button(text=get_text('btn_admin_delete', lang), callback_data=f"admin_discount_del_{user_id}")
    builder.button(text=get_text('btn_admin_back', lang), callback_data="admin_manage_users")
    
    # Adjust layout: Add button [1], each discount [2] (edit, delete), Back button [1]
    adjust_pattern = [1]
    for _ in range(len(discounts)):
        adjust_pattern.append(2)
    adjust_pattern.append(1)
    builder.adjust(*adjust_pattern)
    return builder.as_markup()

def get_admin_stats_keyboard(lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    btn_text = {
        "en": "📥 Download Last 24h Sales",
        "ar": "📥 تحميل مبيعات آخر 24 ساعة",
        "ru": "📥 Скачать продажи за 24ч"
    }
    builder.button(text=btn_text.get(lang, btn_text['en']), callback_data="admin_dl_sales_24h")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_api_keys_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Generate API Key", callback_data="admin_api_key_gen")
    builder.button(text="❌ Revoke API Key", callback_data="admin_api_key_revoke_select")
    builder.button(text="🔙 Back", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_api_key_revoke_keyboard(keys_list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in keys_list:
        name = row['first_name'] or f"ID: {row['user_id']}"
        builder.button(text=f"❌ Revoke: {name}", callback_data=f"admin_api_key_rev_{row['user_id']}")
    builder.button(text="🔙 Back", callback_data="admin_api_keys")
    builder.adjust(1)
    return builder.as_markup()

def get_user_api_key_keyboard(has_key=False, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not has_key:
        builder.button(text=get_text('btn_generate_api_key', lang), callback_data="user_api_key_gen")
    else:
        builder.button(text=get_text('btn_regenerate_api_key', lang), callback_data="user_api_key_regen")
        builder.button(text=get_text('btn_revoke_api_key', lang), callback_data="user_api_key_revoke")
    builder.button(text=get_text('btn_download_api_doc', lang), callback_data="user_api_key_doc")
    builder.adjust(1)
    return builder.as_markup()

def get_providers_list_keyboard(providers, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for prov in providers:
        prov_dict = dict(prov)
        # Display the store name if available, otherwise fallback to domain URL
        if prov_dict.get('store_name'):
            display = prov_dict['store_name']
        else:
            display = prov_dict['base_url'].replace("https://", "").replace("http://", "")
        builder.button(text=f"🔌 {display}", callback_data=f"admin_prov_manage_{prov_dict['id']}")
    builder.button(text=get_text('btn_setup_new_prov', lang) or "➕ Add New Provider", callback_data="admin_prov_setup_new")
    builder.button(text="🔙 Back", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_provider_manage_keyboard(provider_id, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Update API Token / تعديل المفتاح", callback_data=f"admin_prov_editkey_{provider_id}")
    builder.button(text="📥 Pull/Import Products", callback_data=f"admin_prov_pull_{provider_id}")
    builder.button(text="❌ Delete Provider", callback_data=f"admin_prov_delete_{provider_id}")
    builder.button(text="🔙 Back", callback_data="admin_pull_external")
    builder.adjust(1)
    return builder.as_markup()

def get_provider_products_keyboard(products, lang='en', page=0, per_page=12) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not products:
        builder.button(text="🔙 Cancel", callback_data="admin_menu")
        builder.adjust(1)
        return builder.as_markup()

    total_products = len(products)
    total_pages = (total_products + per_page - 1) // per_page
    page = max(0, min(page, total_pages - 1))

    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_products = products[start_idx:end_idx]

    for prod in page_products:
        name = prod.get('name_en') or prod.get('name_ar') or f"ID: {prod['id']}"
        if len(name) > 30:
            name = name[:27] + "..."
        price = prod.get('price', 0.0)
        builder.button(text=f"📥 {name} (${price:.2f})", callback_data=f"admin_prov_sel_{prod['id']}")

    adjust_pattern = [1] * len(page_products)

    # Navigation buttons
    if total_pages > 1:
        nav_count = 0
        if page > 0:
            builder.button(text="⬅️ Prev", callback_data=f"admin_prov_pg_{page - 1}")
            nav_count += 1
        
        builder.button(text=f"📄 {page + 1}/{total_pages}", callback_data="ignore")
        nav_count += 1

        if page < total_pages - 1:
            builder.button(text="Next ➡️", callback_data=f"admin_prov_pg_{page + 1}")
            nav_count += 1
        
        adjust_pattern.append(nav_count)

    builder.button(text="🔙 Cancel", callback_data="admin_menu")
    adjust_pattern.append(1)

    builder.adjust(*adjust_pattern)
    return builder.as_markup()

async def get_force_sub_keyboard(bot, channels: list, lang='en') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, ch in enumerate(channels, 1):
        clean_ch = ch.strip()
        if not clean_ch:
            continue
        url = ""
        title = f"📢 القناة {idx}" if lang == 'ar' else (f"📢 Канал {idx}" if lang == 'ru' else f"📢 Channel {idx}")
        try:
            if clean_ch.startswith("@") or clean_ch.replace("-", "").isdigit():
                chat = await bot.get_chat(clean_ch)
                if chat and chat.title:
                    title = f"📢 {chat.title}"
                if chat and chat.username:
                    url = f"https://t.me/{chat.username}"
                elif chat and chat.invite_link:
                    url = chat.invite_link
        except Exception:
            pass
            
        if not url:
            if clean_ch.startswith("https://t.me/"):
                url = clean_ch
            else:
                user_part = clean_ch.replace("@", "")
                url = f"https://t.me/{user_part}"
                
        builder.button(text=title, url=url)
        
    verify_text = {
        'ar': "✅ تحقق من الاشتراك",
        'en': "✅ Verify Subscription",
        'ru': "✅ Проверить подписку"
    }.get(lang, "✅ Verify Subscription")
    
    builder.button(text=verify_text, callback_data="check_subscription", style="success")
    builder.adjust(1)
    return builder.as_markup()

# --- Admin Pre-orders Keyboard Helpers ---
def get_admin_preorders_summary_keyboard(preorders_summary) -> InlineKeyboardMarkup:
    """Keyboard for listing all products with active pre-orders."""
    builder = InlineKeyboardBuilder()
    for item in preorders_summary:
        name = item['name_en'] or f"ID: {item['product_id']}"
        btn_text = f"📦 {name} (Qty: {item['total_quantity']} | Users: {item['total_preorders']})"
        builder.button(text=btn_text, callback_data=f"adm_po_list_{item['product_id']}")
    builder.button(text="🔙 Back", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_product_preorders_keyboard(preorders_list) -> InlineKeyboardMarkup:
    """Keyboard showing individual pre-orders for a specific product."""
    builder = InlineKeyboardBuilder()
    for po in preorders_list:
        buyer = po['first_name'] or f"ID: {po['user_id']}"
        btn_text = f"👤 {buyer} (x{po['quantity']}) - ${po['price_paid']:.2f}"
        builder.button(text=btn_text, callback_data=f"adm_po_view_{po['id']}")
    builder.button(text="🔙 Back to Summary", callback_data="admin_preorders_summary")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_preorder_actions_keyboard(pre_order_id, product_id) -> InlineKeyboardMarkup:
    """Keyboard for admin actions on an individual pre-order."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancel & Refund / إلغاء وإرجاع الرصيد", callback_data=f"adm_po_cancel_{pre_order_id}")
    builder.button(text="🔙 Back", callback_data=f"adm_po_list_{product_id}")
    builder.adjust(1)
    return builder.as_markup()


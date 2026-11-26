from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
import aiosqlite
import time
import uuid
try:
    import bot_config as config
    from bot_config import DB_NAME
except ImportError:
    import config
    from config import DB_NAME
from database import (
    get_products, get_product, get_stock_count, buy_product, get_user, get_setting,
    get_user_discount, is_subscribed_stock_notification, subscribe_stock_notification,
    unsubscribe_stock_notification, create_payment
)
from localization import get_text, get_button_variants
from handlers.states import ShopStates
import keyboards
import asyncio
from utils import (
    send_message_with_retry, send_private_with_effect,
    EFFECT_CONFETTI, EFFECT_HEART,
    get_product_name, get_product_desc, get_product_unit_price, format_stock_display
)
import logging

logger = logging.getLogger(__name__)
router = Router()

async def get_direct_pay_url(user_id: int, price_to_pay: float) -> str:
    try:
        from database import get_setting, create_payment_session
        from utils import get_bot_api_base_url
        gw_enabled = (await get_setting("global_web_enabled", "1")) == "1"
        if not gw_enabled or price_to_pay <= 0:
            return None
        token = await create_payment_session(user_id, amount=price_to_pay)
        base_url = await get_bot_api_base_url()
        return f"{base_url.rstrip('/')}/pay/{token}?uid={user_id}&amount={price_to_pay}"
    except Exception as err:
        logger.warning(f"Failed to generate direct pay URL: {err}")
        return None

async def _apply_user_effective_prices(products, user_id):
    if not products or not user_id:
        return products
    custom_prices_map = {}
    user_discount = 0.0
    try:
        async with aiosqlite.connect(DB_NAME, timeout=10.0) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT product_id, custom_price FROM user_product_prices WHERE user_id = ?;", (user_id,)) as cur:
                for r in await cur.fetchall():
                    custom_prices_map[r["product_id"]] = float(r["custom_price"])
            async with db.execute("SELECT discount_percent FROM user_discounts WHERE user_id = ?;", (user_id,)) as u_cur:
                u_row = await u_cur.fetchone()
                if u_row and u_row["discount_percent"]:
                    user_discount = float(u_row["discount_percent"])
    except Exception:
        return products

    if not custom_prices_map and user_discount <= 0:
        return products

    updated = []
    for p in products:
        p_dict = dict(p)
        pid = p_dict["id"]
        if pid in custom_prices_map:
            p_dict["price"] = round(custom_prices_map[pid], 2)
        elif user_discount > 0:
            base_u = get_product_unit_price(p_dict, 1)
            p_dict["price"] = round(base_u * (1.0 - user_discount / 100.0), 2)
        updated.append(p_dict)
    return updated

async def show_products_list(message_or_callback, lang='en', category_id=None):
    from database import get_categories, get_uncategorized_products, get_all_stock_counts
    user_id = message_or_callback.from_user.id if hasattr(message_or_callback, 'from_user') and message_or_callback.from_user else None
    
    grouping_enabled = await get_setting("grouping_enabled", "0")
    hide_oos = (await get_setting("hide_out_of_stock", "0")) == "1"
    
    if category_id is not None:
        products = await get_products(category_id=category_id)
        if not products:
            text = get_text('shop_empty', lang)
            kb = keyboards.get_products_keyboard([], {}, lang, category_id=category_id)
        else:
            stock_counts = await get_all_stock_counts(products, use_cache=True)
            products = await _apply_user_effective_prices(products, user_id)
            if hide_oos:
                products = [p for p in products if stock_counts.get(p['id'], 0) > 0]
            if not products:
                text = get_text('shop_empty', lang)
                kb = keyboards.get_products_keyboard([], {}, lang, category_id=category_id)
            else:
                text = get_text('shop_title', lang)
                kb = keyboards.get_products_keyboard(products, stock_counts, lang, category_id=category_id)
    elif grouping_enabled == "1":
        categories = await get_categories()
        standalone_products = await get_uncategorized_products()
        if categories:
            stock_counts = await get_all_stock_counts(standalone_products, use_cache=True) if standalone_products else {}
            standalone_products = await _apply_user_effective_prices(standalone_products, user_id)
            if hide_oos:
                standalone_products = [p for p in standalone_products if stock_counts.get(p['id'], 0) > 0]
            text = get_text('shop_title', lang)
            kb = keyboards.get_shop_home_keyboard(categories, standalone_products, stock_counts, lang)
        else:
            products = await get_products()
            if not products:
                text = get_text('shop_empty', lang)
                kb = keyboards.get_products_keyboard([], {}, lang)
            else:
                stock_counts = await get_all_stock_counts(products, use_cache=True)
                products = await _apply_user_effective_prices(products, user_id)
                if hide_oos:
                    products = [p for p in products if stock_counts.get(p['id'], 0) > 0]
                if not products:
                    text = get_text('shop_empty', lang)
                    kb = keyboards.get_products_keyboard([], {}, lang)
                else:
                    text = get_text('shop_title', lang)
                    kb = keyboards.get_products_keyboard(products, stock_counts, lang)
    else:
        products = await get_products()
        if not products:
            text = get_text('shop_empty', lang)
            kb = keyboards.get_products_keyboard([], {}, lang)
        else:
            stock_counts = await get_all_stock_counts(products, use_cache=True)
            products = await _apply_user_effective_prices(products, user_id)
            if hide_oos:
                products = [p for p in products if stock_counts.get(p['id'], 0) > 0]
            if not products:
                text = get_text('shop_empty', lang)
                kb = keyboards.get_products_keyboard([], {}, lang)
            else:
                text = get_text('shop_title', lang)
                kb = keyboards.get_products_keyboard(products, stock_counts, lang)
    
    if isinstance(message_or_callback, CallbackQuery):
        from aiogram.exceptions import TelegramBadRequest
        try:
            await message_or_callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                pass
            else:
                raise e
    else:
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.message(F.text.in_(get_button_variants('btn_shop')))
async def cmd_shop(message: Message, lang='en'):
    await show_products_list(message, lang)

@router.callback_query(F.data == "shop_list")
async def cb_shop_list(callback: CallbackQuery, lang='en'):
    await show_products_list(callback, lang)
    await callback.answer()

@router.callback_query(F.data.startswith("cat_view_"))
async def cb_cat_view(callback: CallbackQuery, lang='en'):
    try:
        cat_id = int(callback.data.replace("cat_view_", ""))
        await show_products_list(callback, lang=lang, category_id=cat_id)
    except Exception as e:
        logger.error(f"Error in cb_cat_view: {e}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

@router.callback_query(F.data == "shop_categories")
async def cb_shop_categories(callback: CallbackQuery, lang='en'):
    await show_products_list(callback, lang=lang, category_id=None)
    await callback.answer()

@router.callback_query(F.data.startswith("prod_view_"))
async def cb_product_view(callback: CallbackQuery, lang='en'):
    try:
        product_id = int(callback.data.replace("prod_view_", ""))
        from database import sync_single_provider_product
        product, stock_count = await sync_single_provider_product(product_id, bot=callback.bot)
        
        if not product:
            await callback.answer("Product not found.")
            return
            
        has_stock = stock_count > 0
        
        user_id = callback.from_user.id
        from database import get_user_product_price
        custom_price = await get_user_product_price(user_id, product_id)
        discount_pct = await get_user_discount(user_id) if not custom_price else 0.0
        
        from utils import format_product_message
        text, entities, parse_mode = format_product_message(product, lang, stock_count, discount_pct=discount_pct, custom_price=custom_price)
        
        is_sub = False
        if not has_stock:
            is_sub = await is_subscribed_stock_notification(user_id, product_id)
        
        prod_cat_id = None
        if hasattr(product, 'keys') and 'category_id' in product.keys() and product['category_id']:
            prod_cat_id = product['category_id']
        elif isinstance(product, dict) and product.get('category_id'):
            prod_cat_id = product['category_id']
            
        kb = keyboards.get_product_view_keyboard(product_id, has_stock, lang, is_subscribed=is_sub, category_id=prod_cat_id)
        if entities:
            try:
                await callback.message.edit_text(text, reply_markup=kb, entities=entities)
            except Exception as e:
                logger.warning(f"edit_text with entities failed: {e}, falling back to plain text")
                await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
        else:
            try:
                await callback.message.edit_text(text, reply_markup=kb, parse_mode=parse_mode)
            except Exception as e:
                logger.warning(f"edit_text with parse_mode={parse_mode} failed: {e}, falling back to plain text")
                await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
    except Exception as outer_err:
        logger.error(f"Error in cb_product_view: {outer_err}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

@router.callback_query(F.data.startswith("prod_buy_"))
async def cb_product_buy(callback: CallbackQuery, state: FSMContext, lang='en'):
    product_id = int(callback.data.replace("prod_buy_", ""))
    
    product = await get_product(product_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    stock_count = await get_stock_count(product_id)
    if stock_count == 0:
        await callback.answer(get_text('out_of_stock', lang), show_alert=True)
        return
        
    await state.set_state(ShopStates.waiting_for_buy_quantity)
    await state.update_data(buy_product_id=product_id, buy_stock_max=stock_count)
    
    prod_name = get_product_name(product, lang)
    stock_disp = format_stock_display(stock_count, product)
    
    msg = get_text('buy_quantity_prompt', lang, name=prod_name, stock=stock_disp)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_back', lang), callback_data=f"prod_view_{product_id}")
    
    await callback.message.edit_text(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


@router.message(ShopStates.waiting_for_buy_quantity)
async def process_buy_quantity(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    db_user = await get_user(user_id)
    lang = db_user['language'] if db_user else 'en'
    
    data = await state.get_data()
    product_id = data.get('buy_product_id')
    max_stock = data.get('buy_stock_max', 1)
    
    if not product_id:
        await state.clear()
        return
        
    product = await get_product(product_id)
    try:
        qty = int(message.text.strip())
        if qty < 1 or qty > max_stock:
            raise ValueError()
    except ValueError:
        max_disp = format_stock_display(max_stock, product) if product else format_stock_display(max_stock)
        await message.answer(get_text('invalid_quantity', lang, max_stock=max_disp))
        return
        
    if not product:
        await state.clear()
        await message.answer("Product not found.")
        return

    prod_name = get_product_name(product, lang)
    req_email = bool(dict(product).get('requires_email'))
    if req_email:
        await state.set_state(ShopStates.waiting_for_activation_email)
        await state.update_data(buy_product_id=product_id, buy_qty=qty)
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text('btn_back', lang), callback_data=f"prod_view_{product_id}")
        if qty == 1:
            msg = get_text('ask_activation_email_single', lang, name=prod_name)
        else:
            msg = get_text('ask_activation_email_multi', lang, name=prod_name, qty=qty)
        await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
        return
        
    await state.clear()
        
    from database import get_effective_product_price, sync_single_provider_product
    product, _ = await sync_single_provider_product(product_id, quantity=qty, bot=bot)
    unit_price = await get_effective_product_price(product, user_id, qty)
    price_to_pay = round(unit_price * qty, 2)
    
    pay_url = await get_direct_pay_url(user_id, price_to_pay)
    stars_enabled = (await get_setting('stars_enabled', '1')) == '1'
    stars_rate = float(await get_setting('stars_rate', '0.02'))
    stars_amount = max(1, int(price_to_pay / stars_rate)) if stars_rate > 0 else 1
    
    # Render checkout payment method prompt
    text = get_text('checkout_payment_prompt', lang, name=prod_name, qty=qty, price=price_to_pay)
    kb = keyboards.get_checkout_keyboard(
        product_id, qty, db_user['balance'], price_to_pay, lang,
        pay_url=pay_url, stars_enabled=stars_enabled, stars_amount=stars_amount
    )
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

_USER_ACTIVATION_EMAILS = {}

@router.message(ShopStates.waiting_for_activation_email)
async def process_activation_email(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    db_user = await get_user(user_id)
    lang = db_user['language'] if db_user else 'en'
    
    data = await state.get_data()
    product_id = data.get('buy_product_id')
    qty = int(data.get('buy_qty', 1))
    
    if not product_id:
        await state.clear()
        return
        
    raw_txt = (message.text or "").strip()
    email_list = [e.strip() for e in raw_txt.replace(',', '\n').split('\n') if e.strip()]
    
    def _is_valid_email(em: str) -> bool:
        return "@" in em and "." in em.split("@")[-1] and len(em) >= 5 and " " not in em

    if not email_list or not all(_is_valid_email(em) for em in email_list):
        await message.answer(get_text('invalid_activation_email', lang), parse_mode="Markdown")
        return
        
    if qty > 1 and len(email_list) not in [1, qty]:
        product = await get_product(product_id)
        prod_name = get_product_name(product, lang) if product else "Product"
        await message.answer(get_text('ask_activation_email_multi', lang, name=prod_name, qty=qty), parse_mode="Markdown")
        return
        
    _USER_ACTIVATION_EMAILS[(user_id, product_id)] = email_list
    await state.clear()
    
    product = await get_product(product_id)
    if not product:
        await message.answer("Product not found.")
        return
        
    from database import get_effective_product_price, sync_single_provider_product
    product, _ = await sync_single_provider_product(product_id, quantity=qty, bot=bot)
    unit_price = await get_effective_product_price(product, user_id, qty)
    price_to_pay = round(unit_price * qty, 2)
    prod_name = get_product_name(product, lang)
    
    pay_url = await get_direct_pay_url(user_id, price_to_pay)
    stars_enabled = (await get_setting('stars_enabled', '1')) == '1'
    stars_rate = float(await get_setting('stars_rate', '0.02'))
    stars_amount = max(1, int(price_to_pay / stars_rate)) if stars_rate > 0 else 1
    
    text = get_text('checkout_payment_prompt', lang, name=prod_name, qty=qty, price=price_to_pay)
    kb = keyboards.get_checkout_keyboard(
        product_id, qty, db_user['balance'], price_to_pay, lang,
        pay_url=pay_url, stars_enabled=stars_enabled, stars_amount=stars_amount
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# Callback handler for paying from balance
@router.callback_query(F.data.startswith("chk_bal_"))
async def cb_checkout_balance(callback: CallbackQuery, state: FSMContext, bot: Bot, lang='en'):
    user_id = callback.from_user.id
    db_user = await get_user(user_id)
    
    parts = callback.data.replace("chk_bal_", "").split("_")
    product_id = int(parts[0])
    qty = int(parts[1])
    
    from database import get_effective_product_price, sync_single_provider_product
    product, _ = await sync_single_provider_product(product_id, quantity=qty, bot=bot)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
        
    unit_price = await get_effective_product_price(product, user_id, qty)
    price_to_pay = round(unit_price * qty, 2)
    
    if round(db_user['balance'], 2) < price_to_pay:
        await callback.answer(get_text('insufficient_balance', lang, balance=db_user['balance'], price=price_to_pay), show_alert=True)
        pay_url = await get_direct_pay_url(user_id, price_to_pay)
        stars_enabled = (await get_setting('stars_enabled', '1')) == '1'
        stars_rate = float(await get_setting('stars_rate', '0.02'))
        stars_amount = max(1, int(price_to_pay / stars_rate)) if stars_rate > 0 else 1
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        ikb = InlineKeyboardBuilder()
        if pay_url:
            ikb.button(text=get_text('btn_pay_web_link', lang, price=price_to_pay), url=pay_url)
            if stars_enabled:
                stars_text = get_text('btn_pay_stars', lang, stars=stars_amount) if stars_amount > 0 else get_text('btn_stars', lang)
                ikb.button(text=stars_text, callback_data=f"chk_stars_{product_id}_{qty}")
        else:
            ikb.button(text=get_text('btn_pay_binance', lang), callback_data=f"chk_bin_{product_id}_{qty}")
            if stars_enabled:
                stars_text = get_text('btn_pay_stars', lang, stars=stars_amount) if stars_amount > 0 else get_text('btn_stars', lang)
                ikb.button(text=stars_text, callback_data=f"chk_stars_{product_id}_{qty}")
            ikb.button(text=get_text('btn_other_payment_methods', lang), callback_data="charge_menu", style="primary")
        ikb.button(text=get_text('btn_back', lang), callback_data=f"prod_view_{product_id}", style="danger")
        ikb.adjust(1)
        low_bal_msg = {
            'ar': f"⚠️ *رصيدك الحالي غير كافٍ لإتمام الشراء.*\n\n💰 *المطلوب:* `${price_to_pay:.2f} USD`\n💎 *رصيدك الحالي:* `${db_user['balance']:.2f} USD`\n\n👇 يمكنك اختيار وسيلة الدفع لإتمام الشراء فوراً:",
            'en': f"⚠️ *Your current balance is insufficient.*\n\n💰 *Required:* `${price_to_pay:.2f} USD`\n💎 *Your Balance:* `${db_user['balance']:.2f} USD`\n\n👇 Please select a payment method below to complete purchase:",
            'ru': f"⚠️ *Недостаточно средств на балансе.*\n\n💰 *Сумма:* `${price_to_pay:.2f} USD`\n\n👇 Вы можете оплатить этот заказ:"
        }
        await callback.message.answer(low_bal_msg.get(lang, low_bal_msg['en']), reply_markup=ikb.as_markup(), parse_mode="Markdown")
        return
        
    await callback.message.edit_text("⏳ Processing purchase...")
    await execute_delivery(callback.message, user_id, product_id, qty, price_to_pay, skip_balance_check=False, bot=bot, lang=lang, state=state)
    await callback.answer()

# Callback handler for Telegram Stars direct checkout
@router.callback_query(F.data.startswith("chk_stars_"))
async def cb_checkout_stars(callback: CallbackQuery, state: FSMContext, bot: Bot, lang='en'):
    user_id = callback.from_user.id
    parts = callback.data.replace("chk_stars_", "").split("_")
    product_id = int(parts[0])
    qty = int(parts[1])
    
    from database import get_effective_product_price, sync_single_provider_product, get_setting, create_payment
    product, stock_count = await sync_single_provider_product(product_id, quantity=qty, bot=bot)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
        
    if stock_count < qty:
        await callback.answer(get_text('out_of_stock_alert', lang), show_alert=True)
        return
        
    unit_price = await get_effective_product_price(product, user_id, qty)
    price_to_pay = round(unit_price * qty, 2)
    prod_name = get_product_name(product, lang)
    
    stars_rate = float(await get_setting('stars_rate', '0.02'))
    stars_amount = max(1, int(price_to_pay / stars_rate)) if stars_rate > 0 else 1
    
    import time
    import uuid
    transaction_id = f"STARS_BUY_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    await create_payment(user_id, price_to_pay, 'telegram_stars', transaction_id)
    
    title = f"{prod_name[:25]}"
    desc = f"Buy {qty}x {prod_name} for ${price_to_pay:.2f} USD"
    payload = f"stars_buy_{user_id}_{product_id}_{qty}_{transaction_id}"
    
    from aiogram.types import LabeledPrice
    try:
        await bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=desc,
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=stars_amount)],
            start_parameter="stars_checkout"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Stars invoice failed for checkout: {e}")
        await callback.message.answer(f"❌ Failed to generate Telegram Stars invoice: {e}")

# Callback handler for Binance Pay ID checkout instructions
@router.callback_query(F.data.startswith("chk_bin_"))
async def cb_checkout_binance(callback: CallbackQuery, state: FSMContext, bot: Bot, lang='en'):
    user_id = callback.from_user.id
    
    parts = callback.data.replace("chk_bin_", "").split("_")
    product_id = int(parts[0])
    qty = int(parts[1])
    
    from database import get_effective_product_price, sync_single_provider_product
    product, stock_count = await sync_single_provider_product(product_id, quantity=qty, bot=bot)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
        
    unit_price = await get_effective_product_price(product, user_id, qty)
    price_to_pay = round(unit_price * qty, 2)
    
    # Verify stock availability again
    if stock_count < qty:
        await callback.answer(get_text('out_of_stock', lang), show_alert=True)
        return
        
    # Pre-stage checkout state data so it persists
    await state.update_data(chk_prod_id=product_id, chk_qty=qty, order_time=int(time.time()))
    
    # Get Binance address / Pay ID config
    default_address = "Not Configured"
    address = await get_setting("crypto_addr_binance", default_address)
    
    prod_name = get_product_name(product, lang)
    
    # Render instructions
    text = get_text('checkout_binance_id_instructions', lang, name=prod_name, qty=qty, price=price_to_pay, address=address)
    kb = keyboards.get_binance_id_checkout_keyboard(product_id, qty, lang)
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# Callback when user clicks "Done / Verify"
@router.callback_query(F.data.startswith("chk_verify_binid_"))
async def cb_checkout_verify_binid(callback: CallbackQuery, state: FSMContext, bot: Bot, lang='en'):
    parts = callback.data.replace("chk_verify_binid_", "").split("_")
    product_id = int(parts[0])
    qty = int(parts[1])
    
    await state.set_state(ShopStates.waiting_for_checkout_binance_txid)
    await state.update_data(chk_prod_id=product_id, chk_qty=qty, order_time=int(time.time()))
    
    await callback.message.answer(get_text('checkout_binance_enter_txid', lang), parse_mode="Markdown")
    await callback.answer()

# Message handler for Binance checkout TxID input
@router.message(ShopStates.waiting_for_checkout_binance_txid)
async def process_checkout_binance_txid(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    raw_user = await get_user(user_id)
    db_user = dict(raw_user) if raw_user else {}
    lang = db_user.get('language') or 'en'
    
    txid = message.text.strip()
    if len(txid) < 5:
        await message.answer("❌ Invalid Transaction ID/Pay ID. Please try again:")
        return
        
    data = await state.get_data()
    product_id = data.get('chk_prod_id')
    qty = data.get('chk_qty')
    
    if not product_id or not qty:
        await state.clear()
        expired_msg = {
            'ar': "❌ انتهت صلاحية الجلسة أو لم يتم العثور على المنتج. يرجى اختيار المنتج مرة أخرى من المتجر.",
            'en': "❌ Session expired or product details not found. Please select the product again from the shop.",
            'ru': "❌ Сессия истекла. Пожалуйста, выберите товар снова в магазине."
        }
        await message.answer(expired_msg.get(lang, expired_msg['en']))
        return
        
    product = await get_product(product_id)
    if not product:
        await state.clear()
        await message.answer("Product not found.")
        return
        
    from database import get_effective_product_price
    effective_unit_price = await get_effective_product_price(product, user_id, qty)
    price_to_pay = round(effective_unit_price * qty, 2)
    prod_name = get_product_name(product, lang)
    
    # Check if this TxID is already in database to prevent double spending
    payment_method = f"blockchain_BINANCE_{txid}"
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM payments WHERE payment_method = ? OR payment_method LIKE ? ORDER BY id DESC LIMIT 1;",
                (payment_method, f"%_{txid}")
            ) as cursor:
                existing_payment = await cursor.fetchone()
        if existing_payment:
            status = existing_payment['status']
            if status == 'completed':
                await state.clear()
                await message.answer(get_text('crypto_already_processed', lang))
                return
            elif status == 'pending':
                await state.clear()
                pending_warn = {
                    'ar': "⏳ هذه المعاملة قيد التحقق بالفعل من قبل الإدارة. يرجى الانتظار.",
                    'en': "⏳ This transaction is already pending verification. Please wait.",
                    'ru': "⏳ Эта транзакция уже находится на проверке. Пожалуйста, подождите."
                }
                await message.answer(pending_warn.get(lang, pending_warn['en']))
                return
            elif status == 'rejected':
                await state.clear()
                await message.answer("❌ This transaction was previously rejected.")
                return
    except Exception as db_chk_err:
        logger.error(f"Error checking existing payment for txid {txid}: {db_chk_err}")

    # Generate unique merchant trade number and save pending payment
    merchant_trade_no = f"CHKP_{uuid.uuid4().hex[:8].upper()}"
    try:
        await create_payment(user_id, price_to_pay, payment_method, merchant_trade_no)
    except Exception as create_err:
        logger.error(f"Failed to create payment in DB for user {user_id}: {create_err}")

    # Clear state now that payment record is successfully registered
    await state.clear()

    # Always immediately acknowledge the user's TxID
    verif_msg = {
        'ar': "⏳ جاري التحقق من عملية الدفع عبر بايننس...",
        'en': "⏳ Verifying your Binance transaction ID...",
        'ru': "⏳ Проверка ID транзакции Binance..."
    }
    await message.answer(verif_msg.get(lang, verif_msg['en']))

    # Verify using Binance API
    from binance_client import verify_binance_payment
    from crypto_verifier import is_amount_matching
    order_time = data.get('order_time') if data else None
    min_ts = (int(order_time) - 120) if order_time else (int(time.time()) - 3600)

    success = False
    result_val = None
    try:
        success, result_val = await verify_binance_payment(txid, min_timestamp=min_ts)
    except Exception as verif_err:
        logger.error(f"verify_binance_payment error for txid {txid}: {verif_err}")
        success = False
        result_val = str(verif_err)

    # Verify both API success AND that the actual amount paid matches required price
    if success and is_amount_matching(price_to_pay, result_val, "BINANCE"):
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE payments SET status = 'completed' WHERE transaction_id = ?;", (merchant_trade_no,))
                await db.commit()
        except Exception as upd_err:
            logger.error(f"Failed to mark payment completed in DB: {upd_err}")

        await message.answer(get_text('checkout_binance_paid', lang), parse_mode="Markdown")
        await execute_delivery(message, user_id, product_id, qty, price_to_pay, skip_balance_check=True, bot=bot, lang=lang, state=state)

        # Notify admins
        user_info = f"{message.from_user.first_name}"
        if message.from_user.username:
            user_info += f" (@{message.from_user.username})"
        admin_notif = (
            f"🎯 *Direct Binance ID Checkout Purchase!*\n\n"
            f"👤 *User:* {user_info} (`{user_id}`)\n"
            f"🛍️ *Product:* `{prod_name} (x{qty})`\n"
            f"💵 *Amount Paid:* `${price_to_pay:.2f} USD`\n"
            f"🆔 *TxID/PayID:* `{txid}`"
        )
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=admin_notif, parse_mode="Markdown")
            except Exception:
                pass
    else:
        # Inform user that automatic check did not find it yet and order was forwarded to admin
        await message.answer(get_text('checkout_binance_failed', lang), parse_mode="Markdown")

        # Notify admins of pending checkout for manual review with 1-click Approve/Reject buttons!
        user_info = f"{message.from_user.first_name}"
        if message.from_user.username:
            user_info += f" (@{message.from_user.username})"
        admin_notif = (
            f"⏳ *[Pending Checkout] Binance ID Verification!*\n\n"
            f"👤 *User:* {user_info} (`{user_id}`)\n"
            f"🛍️ *Product:* `{prod_name} (x{qty})`\n"
            f"💵 *Amount Required:* `${price_to_pay:.2f} USD`\n"
            f"🔗 *TxID/PayID:* `{txid}`\n\n"
            f"You can verify and approve this manually below or from the Pending Deposits section."
        )
        kb = keyboards.get_admin_payment_approval_keyboard(merchant_trade_no)
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=admin_notif, reply_markup=kb, parse_mode="Markdown")
            except Exception:
                pass

async def execute_delivery(message: Message, user_id: int, product_id: int, qty: int, price_to_pay: float, skip_balance_check: bool, bot: Bot, lang: str, state: FSMContext = None):
    product = await get_product(product_id)
    customer_email = _USER_ACTIVATION_EMAILS.get((user_id, product_id))
    
    # 1. Perform DB buy transaction
    try:
        stock_data_list, price_paid, purchase_time, actual_qty = await buy_product(
            user_id, product_id, qty,
            skip_balance_check=skip_balance_check,
            allow_partial=True,
            customer_email=customer_email
        )
        _USER_ACTIVATION_EMAILS.pop((user_id, product_id), None)
    except Exception as e:
        logger.error(f"Purchase failed in DB for user {user_id}, product {product_id}, qty {qty}: {e}", exc_info=True)
        err_msg = str(e)
        err_lower = err_msg.lower()
        
        if "email requis" in err_lower or "email required" in err_lower or "requires email" in err_lower:
            # Auto-detected email activation requirement!
            if skip_balance_check:
                import aiosqlite
                try:
                    from bot_config import DB_NAME
                except ImportError:
                    from config import DB_NAME
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (price_to_pay, user_id))
                    await db.commit()
            prod_name = get_product_name(product, lang) if product else "Product"
            if state is not None:
                await state.set_state(ShopStates.waiting_for_activation_email)
                await state.update_data(buy_product_id=product_id, buy_qty=qty)
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                builder = InlineKeyboardBuilder()
                builder.button(text=get_text('btn_back', lang), callback_data=f"prod_view_{product_id}")
                if qty == 1:
                    prompt_msg = get_text('ask_activation_email_single', lang, name=prod_name)
                else:
                    prompt_msg = get_text('ask_activation_email_multi', lang, name=prod_name, qty=qty)
                await message.answer(prompt_msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
            else:
                await message.answer(
                    get_text('email_required_auto_detected', lang),
                    reply_markup=keyboards.get_product_view_keyboard(product_id, True, lang),
                    parse_mode="Markdown"
                )
            return
        
        # Send instant high-priority notification to admins about delivery error / provider failure
        admin_username = "admin"
        user_info = f"{message.from_user.first_name}"
        if message.from_user.username:
            user_info += f" (@{message.from_user.username})"
        prod_title = get_product_name(product, 'en')
        
        clean_err_msg = str(err_msg).replace('`', "'")
        admin_alert = (
            f"🚨 *DELIVERY ERROR ALERT! (Action Required)*\n\n"
            f"👤 *User:* {user_info} (`{user_id}`)\n"
            f"🛍️ *Product:* `{prod_title}` (ID: `{product_id}`)\n"
            f"🔢 *Quantity Requested:* `{qty}`\n"
            f"💵 *Total Price:* `${price_to_pay:.2f} USD`\n"
            f"❌ *Error Details:* `{clean_err_msg}`\n\n"
            f"⚠️ *Note:* Please review this order and deliver manually or check stock if needed."
        )
        from database import get_admin_ids
        admin_ids = await get_admin_ids()
        for admin_id in admin_ids:
            try:
                await send_message_with_retry(bot.send_message, chat_id=admin_id, text=admin_alert, parse_mode="Markdown")
            except Exception as ae:
                logger.warning(f"Could not send delivery error alert to admin {admin_id}: {ae}")
                
        if err_msg.startswith("PRICE_CHANGED:"):
            parts_pc = err_msg.split(":")
            old_p_s = parts_pc[1] if len(parts_pc) > 1 else "?"
            new_p_s = parts_pc[2] if len(parts_pc) > 2 else "?"
            if skip_balance_check:
                import aiosqlite
                try:
                    from bot_config import DB_NAME
                except ImportError:
                    from config import DB_NAME
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (price_to_pay, user_id))
                    await db.commit()
                msg_pc = {
                    "ar": f"⚠️ *تم تحديث سعر المنتج من قِبل المزود!*\n\nالسعر السابق: `${old_p_s}` ➡️ السعر الجديد: `${new_p_s}`\n\n💰 وحفاظاً على أموالك، تم إيداع مبلغ **`${price_to_pay:.2f} USD`** في محفظتك بالبوت. يمكنك الآن عرض المنتج والشراء بالسعر الجديد.",
                    "en": f"⚠️ *Product Price Updated by Provider!*\n\nOld Price: `${old_p_s}` ➡️ New Price: `${new_p_s}`\n\n💰 To protect your funds, **`${price_to_pay:.2f} USD`** has been credited to your wallet. You can now view the product and order at the updated price.",
                    "ru": f"⚠️ *Поставщик обновил цену товара!*\n\nСтарая цена: `${old_p_s}` ➡️ Новая цена: `${new_p_s}`\n\n💰 Сумма **`${price_to_pay:.2f} USD`** зачислена на ваш баланс в боте."
                }
            else:
                msg_pc = {
                    "ar": f"⚠️ *تم تحديث سعر المنتج من قِبل المزود!*\n\nالسعر السابق: `${old_p_s}` ➡️ السعر الجديد: `${new_p_s}`\n\nتم تحديث السعر في البوت تلقائياً، يرجى إعادة فتح المنتج والموافقة على السعر الجديد.",
                    "en": f"⚠️ *Product Price Updated by Provider!*\n\nPrevious: `${old_p_s}` ➡️ Updated Price: `${new_p_s}`\n\nThe bot price has been refreshed automatically. Please open the product again to purchase at the new price.",
                    "ru": f"⚠️ *Цена товара обновлена поставщиком!*\n\nПрежняя цена: `${old_p_s}` ➡️ Новая цена: `${new_p_s}`\n\nЦена в боте обновлена. Пожалуйста, откройте товар снова."
                }
            await message.answer(
                msg_pc.get(lang, msg_pc['en']),
                reply_markup=keyboards.get_product_view_keyboard(product_id, True, lang),
                parse_mode="Markdown"
            )
            return

        if err_msg.strip().lower() == "insufficient balance":
            db_u = await get_user(user_id)
            cur_b = float(db_u['balance'] or 0.0) if db_u else 0.0
            await message.answer(
                get_text('insufficient_balance', lang, balance=cur_b, price=price_to_pay),
                reply_markup=keyboards.get_product_view_keyboard(product_id, True, lang),
                parse_mode="Markdown"
            )
            return

        if "out of stock" in err_msg.lower():
            from database import set_cached_provider_stock
            set_cached_provider_stock(product_id, 0)
            if skip_balance_check:
                # Direct checkout payment went out of stock. Refund the full price_to_pay to user's wallet!
                import aiosqlite
                try:
                    from bot_config import DB_NAME
                except ImportError:
                    from config import DB_NAME
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (price_to_pay, user_id))
                    await db.commit()
                await message.answer(
                    get_text('checkout_refund_out_of_stock', lang, amount=price_to_pay),
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    get_text('out_of_stock', lang),
                    reply_markup=keyboards.get_product_view_keyboard(product_id, False, lang)
                )
        else:
            # Query database for the first admin username if configured
            import aiosqlite
            try:
                from bot_config import DB_NAME
            except ImportError:
                from config import DB_NAME
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                if config.ADMIN_IDS:
                    async with db.execute("SELECT username FROM users WHERE user_id = ? LIMIT 1;", (config.ADMIN_IDS[0],)) as u_cur:
                        u_row = await u_cur.fetchone()
                        if u_row and u_row['username']:
                            admin_username = u_row['username']
            
            refund_note = ""
            if skip_balance_check:
                # Refund the payment to user's wallet to protect funds
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (price_to_pay, user_id))
                    await db.commit()
                    
                refund_note_dict = {
                    "ar": f"\n\n💰 وحفاظاً على أموالك، تم تلقائياً شحن وإيداع مبلغ **`${price_to_pay:.2f} USD`** في محفظتك بالبوت.",
                    "en": f"\n\n💰 To secure your funds, **`${price_to_pay:.2f} USD`** has been automatically credited to your wallet balance.",
                    "ru": f"\n\n💰 Для безопасности ваших средств **`${price_to_pay:.2f} USD`** автоматически зачислены на баланс вашего кошелька."
                }
                refund_note = refund_note_dict.get(lang, refund_note_dict['en'])
            
            await message.answer(
                get_text('provider_insufficient_balance', lang, admin_username=admin_username) + refund_note,
                parse_mode="Markdown"
            )
        return

    # 2. Check if product is out of stock and notify admins
    try:
        new_stock = await get_stock_count(product_id)
        if new_stock == 0:
            from database import notify_admins_stock_change
            await notify_admins_stock_change(bot, product_id, 'empty')
    except Exception as e:
        logger.error(f"Failed to check/notify out-of-stock for product {product_id}: {e}")
        
    prod_name = dict(product).get(f'name_{lang}') or dict(product).get('name_en')
    
    # 3. Check for partial delivery refund
    refund_amount = 0.0
    if actual_qty < qty:
        # Calculate refund for undelivered items using effective unit price (custom price / tier / discount)
        from database import get_effective_product_price
        price_per_item = await get_effective_product_price(product, user_id, qty)
        diff_qty = qty - actual_qty
        refund_amount = round(price_per_item * diff_qty, 2)
        
        # Credit user wallet with the difference ONLY IF the purchase was paid directly (skip_balance_check=True).
        # For balance purchases, buy_product already deducted only actual_price from user balance.
        if skip_balance_check and refund_amount > 0:
            import aiosqlite
            try:
                from bot_config import DB_NAME
            except ImportError:
                from config import DB_NAME
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (refund_amount, user_id))
                await db.commit()
            
    # Split stock_data_list into chunks of text, each having length <= 4000 to be safe
    chunks = []
    current_chunk = []
    current_len = 0
    for item in stock_data_list:
        item_len = len(item) + (1 if current_chunk else 0)
        if current_len + item_len > 4000:
            chunks.append("\n".join(current_chunk))
            current_chunk = [item]
            current_len = len(item)
        else:
            current_chunk.append(item)
            current_len += item_len
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # 4. Deliver products via Telegram: Check text character length against Telegram limits
    from aiogram.types import BufferedInputFile
    txt_content = "\n\n".join(stock_data_list)
    total_char_len = len(txt_content)
    file_time_str = purchase_time.replace(':', '-').replace(' ', '_')
    txt_file = BufferedInputFile(txt_content.encode('utf-8'), filename=f"purchase_{user_id}_{file_time_str}.txt")

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_download_txt', lang), callback_data=f"dl_pur_{purchase_time.replace(' ', '_')}")
    builder.adjust(1)
    
    try:
        first_chunk = chunks[0] if chunks else ""
        
        # Send the TXT file directly as a document attachment!
        doc_caption = {
            "ar": f"📄 *ملف جميع المنتجات/الروابط (العدد: {actual_qty})*",
            "en": f"📄 *File containing all items (Total: {actual_qty})*",
            "ru": f"📄 *Файл со всеми товарами (Всего: {actual_qty})*"
        }
        try:
            await send_message_with_retry(message.answer_document, document=txt_file, caption=doc_caption.get(lang, doc_caption['en']), parse_mode="Markdown")
        except Exception as doc_err:
            logger.error(f"Failed to send TXT document directly: {doc_err}")
        
        # If text length exceeds Telegram single message limit (or >2500 chars / >5 items)
        if total_char_len > 2500 or len(chunks) > 1 or actual_qty > 5:
            note_msg = {
                "ar": f"\n\n📎 *تنويه:* نظراً لأن حجم البيانات يتجاوز الحد المسموح به في الرسائل النصية لتليجرام، تم إرفاق جميع المنتجات/الروابط (عدد: {actual_qty}) في ملف TXT المرفق أعلاه مباشرة لسهولة الفتح والتحميل.",
                "en": f"\n\n📎 *Note:* Since the total content exceeds Telegram message character limits, all {actual_qty} items have been sent directly in the TXT file attached above.",
                "ru": f"\n\n📎 *Примечание:* Поскольку общая длина превышает лимит сообщений Telegram, все {actual_qty} товаров отправлены прямо в файле TXT выше."
            }
            # Show small preview of first chunk (truncated to 500 chars max)
            preview = first_chunk[:500] + "...\n(باقي الروابط داخل الملف المرفق)" if len(first_chunk) > 500 else first_chunk
            success_text = get_text(
                'purchase_success',
                lang,
                name=f"{prod_name} (x{actual_qty})",
                price=price_paid,
                data=preview
            ) + note_msg.get(lang, note_msg['en'])
            
            await send_private_with_effect(message.answer, success_text, effect_id=EFFECT_CONFETTI, chat_type=message.chat.type, parse_mode="Markdown", reply_markup=builder.as_markup())
        else:
            success_text = get_text(
                'purchase_success',
                lang,
                name=f"{prod_name} (x{actual_qty})",
                price=price_paid,
                data=first_chunk
            )
            await send_private_with_effect(message.answer, success_text, effect_id=EFFECT_CONFETTI, chat_type=message.chat.type, parse_mode="Markdown", reply_markup=builder.as_markup())
                    
        # Send partial delivery warning and refund notification
        if refund_amount > 0:
            await message.answer(
                get_text('checkout_partial_delivery_refund', lang, actual=actual_qty, qty=qty, diff=(qty - actual_qty), refund=refund_amount),
                parse_mode="Markdown"
            )
            
    except Exception as deliv_err:
        logger.error(f"Error during product delivery to chat for user {user_id}: {deliv_err}")
        fallback_msg = {
            "ar": f"🎉 *تمت عملية الشراء بنجاح!* ({prod_name} x{actual_qty})\n\n⚠️ تم إرفاق كافة المنتجات/الروابط الآن كملف TXT المرفق أعلاه مباشرة.",
            "en": f"🎉 *Purchase Successful!* ({prod_name} x{actual_qty})\n\n⚠️ All your items have been sent directly in the attached TXT file above.",
            "ru": f"🎉 *Покупка успешно совершена!* ({prod_name} x{actual_qty})\n\n⚠️ Все ваши товары отправлены в прикрепленном файле TXT выше."
        }
        try:
            await send_private_with_effect(message.answer, fallback_msg.get(lang, fallback_msg['en']), effect_id=EFFECT_CONFETTI, chat_type=message.chat.type, parse_mode="Markdown", reply_markup=builder.as_markup())
        except Exception:
            pass
            
    # 5. Publish sale to news_channel if set
    news_channel = await get_setting('news_channel', '')
    if news_channel:
        try:
            import html
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            prod_name_en = html.escape(dict(product).get('name_en', ''))
            sale_text = (
                f"⚡️ <b>NEW PURCHASE</b> ⚡️\n"
                f"──────────────────\n"
                f"🛍 <b>Product:</b> <code>{prod_name_en} (x{actual_qty})</code>\n"
                f"💵 <b>Amount Paid:</b> <code>${price_paid:.2f} USD</code>\n"
                f"📅 <b>Status:</b> <code>Delivered Successfully</code>\n"
                f"──────────────────\n"
                f"👉 <i>Want to buy? Visit our bot:</i> @{bot_username}"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Shop Now", url=f"https://t.me/{bot_username}")]
            ])
            await send_message_with_retry(bot.send_message, chat_id=news_channel, text=sale_text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to log sale to news channel: {e}")

@router.callback_query(F.data.startswith("notify_sub_"))
async def cb_notify_subscribe(callback: CallbackQuery, lang='en'):
    product_id = int(callback.data.replace("notify_sub_", ""))
    user_id = callback.from_user.id
    
    product = await get_product(product_id)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
    
    await subscribe_stock_notification(user_id, product_id)
    
    name = get_product_name(product, lang)
    await callback.answer(get_text('notify_stock_subscribed', lang, name=name), show_alert=True)
    
    # Refresh the keyboard to show unsubscribe button
    kb = keyboards.get_product_view_keyboard(product_id, False, lang, is_subscribed=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass

@router.callback_query(F.data.startswith("notify_unsub_"))
async def cb_notify_unsubscribe(callback: CallbackQuery, lang='en'):
    product_id = int(callback.data.replace("notify_unsub_", ""))
    user_id = callback.from_user.id
    
    product = await get_product(product_id)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
    
    await unsubscribe_stock_notification(user_id, product_id)
    
    name = get_product_name(product, lang)
    await callback.answer(get_text('notify_stock_unsubscribed', lang, name=name), show_alert=True)
    
    # Refresh the keyboard to show subscribe button
    kb = keyboards.get_product_view_keyboard(product_id, False, lang, is_subscribed=False)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass

@router.callback_query(F.data.startswith("dl_pur_"))
async def cb_download_purchase_txt(callback: CallbackQuery, lang='en'):
    time_str = callback.data.replace("dl_pur_", "").replace("_", " ")
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE user_id = ? AND purchased_at = ? ORDER BY id ASC;", (user_id, time_str)) as cursor:
            orders = await cursor.fetchall()
            
    if not orders:
        await callback.answer("❌ No products found for this purchase.", show_alert=True)
        return
        
    lines = []
    for order in orders:
        lines.append(order['stock_data'].strip())
        
    content = "\n\n".join(lines)
    file = BufferedInputFile(content.encode('utf-8'), filename=f"purchase_{user_id}_{time_str.replace(':', '-').replace(' ', '_')}.txt")
    
    await callback.message.answer_document(file)
    await callback.answer()

# --- Pre-order Interactive Handlers ---
@router.callback_query(F.data.startswith("prod_preorder_"))
async def cb_product_preorder(callback: CallbackQuery, state: FSMContext, lang='en'):
    user_id = callback.from_user.id
    db_user = await get_user(user_id)
    product_id = int(callback.data.replace("prod_preorder_", ""))
    
    product = await get_product(product_id)
    if not product:
        await callback.answer("Product not found.")
        return
        
    # Check if they already have balance
    from database import get_effective_product_price
    price_to_pay_per_item = await get_effective_product_price(product, user_id, 1)
    
    if round(db_user['balance'], 2) < price_to_pay_per_item:
        await callback.answer(get_text('insufficient_balance', lang, balance=db_user['balance'], price=price_to_pay_per_item), show_alert=True)
        return
        
    await state.set_state(ShopStates.waiting_for_preorder_quantity)
    await state.update_data(preorder_product_id=product_id)
    
    prod_name = get_product_name(product, lang)
    msg = get_text('preorder_title', lang, name=prod_name, price=price_to_pay_per_item)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_back', lang), callback_data=f"prod_view_{product_id}")
    
    await callback.message.edit_text(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@router.message(ShopStates.waiting_for_preorder_quantity)
async def process_preorder_quantity(message: Message, state: FSMContext):
    user_id = message.from_user.id
    db_user = await get_user(user_id)
    lang = db_user['language'] if db_user else 'en'
    
    data = await state.get_data()
    product_id = data.get('preorder_product_id')
    
    if not product_id:
        await state.clear()
        return
        
    product = await get_product(product_id)
    if not product:
        await message.answer("Product not found.")
        await state.clear()
        return
        
    try:
        qty = int(message.text.strip())
        if qty < 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Please enter a positive integer for quantity.")
        return
        
    await state.clear()
    
    # Calculate price
    from database import get_effective_product_price
    price_to_pay_per_item = await get_effective_product_price(product, user_id, qty)
    total_price = round(price_to_pay_per_item * qty, 2)
    
    # Try creating pre-order
    from database import create_pre_order
    try:
        await create_pre_order(user_id, product_id, qty)
        success_text = get_text('preorder_success', lang, amount=total_price)
        await send_private_with_effect(message.answer, success_text, effect_id=EFFECT_HEART, chat_type=message.chat.type, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Failed to reserve: {e}")


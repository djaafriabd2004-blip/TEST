from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
import aiosqlite
from config import DB_NAME
from database import (
    get_products, get_product, get_stock_count, buy_product, get_user, get_setting,
    get_user_discount, is_subscribed_stock_notification, subscribe_stock_notification,
    unsubscribe_stock_notification
)
from localization import get_text
from handlers.states import ShopStates
import keyboards
import asyncio
from utils import send_message_with_retry, get_product_name, get_product_desc
import logging

logger = logging.getLogger(__name__)
router = Router()

async def show_products_list(message_or_callback, lang='en'):
    products = await get_products()
    if not products:
        text = get_text('shop_empty', lang)
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(text, reply_markup=keyboards.get_products_keyboard([], {}, lang))
        else:
            await message_or_callback.answer(text)
        return
        
    stock_counts = {}
    for p in products:
        stock_counts[p['id']] = await get_stock_count(p['id'])
        
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

@router.message(F.text.in_([
    get_text('btn_shop', 'en'),
    get_text('btn_shop', 'ar'),
    get_text('btn_shop', 'ru')
]))
async def cmd_shop(message: Message, lang='en'):
    await show_products_list(message, lang)

@router.callback_query(F.data == "shop_list")
async def cb_shop_list(callback: CallbackQuery, lang='en'):
    await show_products_list(callback, lang)
    await callback.answer()

@router.callback_query(F.data.startswith("prod_view_"))
async def cb_product_view(callback: CallbackQuery, lang='en'):
    try:
        product_id = int(callback.data.replace("prod_view_", ""))
        product = await get_product(product_id)
        
        if not product:
            await callback.answer("Product not found.")
            return
            
        stock_count = await get_stock_count(product_id)
        has_stock = stock_count > 0
        
        user_id = callback.from_user.id
        discount_pct = await get_user_discount(user_id)
        
        from utils import format_product_message
        text, entities, parse_mode = format_product_message(product, lang, stock_count, discount_pct)
        
        is_sub = False
        if not has_stock:
            is_sub = await is_subscribed_stock_notification(user_id, product_id)
        
        kb = keyboards.get_product_view_keyboard(product_id, has_stock, lang, is_subscribed=is_sub)
        if entities:
            try:
                await callback.message.edit_text(text, reply_markup=kb, entities=entities)
            except Exception as e:
                logger.warning(f"edit_text with entities failed: {e}, falling back to Markdown")
                name = get_product_name(product, lang)
                desc = get_product_desc(product, lang)
                fallback_text = get_text('product_details', lang, name=name, desc=desc, price=f"`${product['price']:.2f} USD`", stock=stock_count)
                await callback.message.edit_text(fallback_text, reply_markup=kb, parse_mode="Markdown")
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode=parse_mode)
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
    
    msg = get_text('buy_quantity_prompt', lang, name=prod_name, stock=stock_count)
    
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
        
    try:
        qty = int(message.text.strip())
        if qty < 1 or qty > max_stock:
            raise ValueError()
    except ValueError:
        await message.answer(get_text('invalid_quantity', lang, max_stock=max_stock))
        return
        
    await state.clear()
    product = await get_product(product_id)
    if not product:
        await message.answer("Product not found.")
        return
        
    discount_pct = await get_user_discount(user_id)
    price_to_pay = round((product['price'] * (1 - discount_pct / 100)) * qty, 2)
    prod_name = get_product_name(product, lang)
    
    # Render checkout payment method prompt
    text = get_text('checkout_payment_prompt', lang, name=prod_name, qty=qty, price=price_to_pay)
    kb = keyboards.get_checkout_keyboard(product_id, qty, db_user['balance'], price_to_pay, lang)
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# Callback handler for paying from balance
@router.callback_query(F.data.startswith("chk_bal_"))
async def cb_checkout_balance(callback: CallbackQuery, bot: Bot, lang='en'):
    user_id = callback.from_user.id
    db_user = await get_user(user_id)
    
    parts = callback.data.replace("chk_bal_", "").split("_")
    product_id = int(parts[0])
    qty = int(parts[1])
    
    product = await get_product(product_id)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
        
    discount_pct = await get_user_discount(user_id)
    price_to_pay = round((product['price'] * (1 - discount_pct / 100)) * qty, 2)
    
    if round(db_user['balance'], 2) < price_to_pay:
        await callback.answer(get_text('insufficient_balance', lang, balance=db_user['balance'], price=price_to_pay), show_alert=True)
        return
        
    await callback.message.edit_text("⏳ Processing purchase...")
    await execute_delivery(callback.message, user_id, product_id, qty, price_to_pay, skip_balance_check=False, bot=bot, lang=lang)
    await callback.answer()

# Callback handler for Binance Pay ID checkout instructions
@router.callback_query(F.data.startswith("chk_bin_"))
async def cb_checkout_binance(callback: CallbackQuery, state: FSMContext, bot: Bot, lang='en'):
    user_id = callback.from_user.id
    
    parts = callback.data.replace("chk_bin_", "").split("_")
    product_id = int(parts[0])
    qty = int(parts[1])
    
    product = await get_product(product_id)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return
        
    discount_pct = await get_user_discount(user_id)
    price_to_pay = round((product['price'] * (1 - discount_pct / 100)) * qty, 2)
    
    # Verify stock availability again
    stock_count = await get_stock_count(product_id)
    if stock_count < qty:
        await callback.answer(get_text('out_of_stock', lang), show_alert=True)
        return
        
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
    await state.update_data(chk_prod_id=product_id, chk_qty=qty)
    
    await callback.message.answer(get_text('checkout_binance_enter_txid', lang), parse_mode="Markdown")
    await callback.answer()

# Message handler for Binance checkout TxID input
@router.message(ShopStates.waiting_for_checkout_binance_txid)
async def process_checkout_binance_txid(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    db_user = await get_user(user_id)
    lang = db_user['language'] if db_user else 'en'
    
    txid = message.text.strip()
    if len(txid) < 5:
        await message.answer("❌ Invalid Transaction ID/Pay ID. Please try again:")
        return
        
    data = await state.get_data()
    product_id = data.get('chk_prod_id')
    qty = data.get('chk_qty')
    
    if not product_id or not qty:
        await state.clear()
        return
        
    product = await get_product(product_id)
    if not product:
        await state.clear()
        await message.answer("Product not found.")
        return
        
    discount_pct = await get_user_discount(user_id)
    price_to_pay = round((product['price'] * (1 - discount_pct / 100)) * qty, 2)
    prod_name = get_product_name(product, lang)
    
    await state.clear()
    
    # Check if this TxID is already in database to prevent double spending
    payment_method = f"blockchain_BINANCE_{txid}"
    from database import get_payment_by_method, create_payment, get_payment
    existing_payment = await get_payment_by_method(payment_method)
    if existing_payment:
        status = existing_payment['status']
        if status == 'completed':
            await message.answer(get_text('crypto_already_processed', lang))
            return
        elif status == 'pending':
            await message.answer("⏳ This transaction is already pending verification. Please wait.")
            return
        elif status == 'rejected':
            await message.answer("❌ This transaction was previously rejected.")
            return
            
    # Save pending direct checkout payment
    import uuid
    merchant_trade_no = f"CHKP_{uuid.uuid4().hex[:8].upper()}"
    await create_payment(user_id, price_to_pay, payment_method, merchant_trade_no)
    
    await message.answer("⏳ Verifying your Binance transaction ID...")
    
    # Verify using Binance API
    from binance_client import verify_binance_payment
    from crypto_verifier import is_amount_matching
    success, result_val = await verify_binance_payment(txid, min_timestamp=None)
    
    # Verify both API success AND that the actual amount paid matches required price
    if success and is_amount_matching(price_to_pay, result_val, "BINANCE"):
        # Complete payment in DB (Direct checkout: manually set completed to avoid adding balance)
        import aiosqlite
        from config import DB_NAME
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE payments SET status = 'completed' WHERE transaction_id = ?;", (merchant_trade_no,))
            await db.commit()
            
        await message.answer(get_text('checkout_binance_paid', lang), parse_mode="Markdown")
        await execute_delivery(message, user_id, product_id, qty, price_to_pay, skip_balance_check=True, bot=bot, lang=lang)
        
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
        import config
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=admin_notif, parse_mode="Markdown")
            except Exception:
                pass
    else:
        await message.answer(get_text('checkout_binance_failed', lang), parse_mode="Markdown")
        
        # Notify admins of pending checkout for manual review just in case
        user_info = f"{message.from_user.first_name}"
        if message.from_user.username:
            user_info += f" (@{message.from_user.username})"
        admin_notif = (
            f"⏳ *[Pending Checkout] Binance ID Verification!*\n\n"
            f"👤 *User:* {user_info} (`{user_id}`)\n"
            f"🛍️ *Product:* `{prod_name} (x{qty})`\n"
            f"💵 *Amount Required:* `${price_to_pay:.2f} USD`\n"
            f"🔗 *TxID/PayID:* `{txid}`\n\n"
            f"You can verify and approve this manually from the Pending Deposits section."
        )
        import config
        kb = keyboards.get_admin_payment_approval_keyboard(merchant_trade_no)
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=admin_notif, reply_markup=kb, parse_mode="Markdown")
            except Exception:
                pass

async def execute_delivery(message: Message, user_id: int, product_id: int, qty: int, price_to_pay: float, skip_balance_check: bool, bot: Bot, lang: str):
    product = await get_product(product_id)
    
    # 1. Perform DB buy transaction
    try:
        stock_data_list, price_paid, purchase_time, actual_qty = await buy_product(user_id, product_id, qty, skip_balance_check=skip_balance_check, allow_partial=True)
    except Exception as e:
        logger.error(f"Purchase failed in DB: {e}")
        err_msg = str(e)
        if "Out of stock" in err_msg:
            if skip_balance_check:
                # Direct checkout payment went out of stock. Refund the full price_to_pay to user's wallet!
                import aiosqlite
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
            # Obfuscate reseller API provider balance errors to protect admin privacy
            if "insufficient balance" in err_msg.lower() or "provider error" in err_msg.lower() or "insufficient items" in err_msg.lower():
                import config
                admin_username = "admin"
                
                # Direct checkout payment failed due to provider error. Refund the payment to user's wallet!
                if skip_balance_check:
                    import aiosqlite
                    from config import DB_NAME
                    async with aiosqlite.connect(DB_NAME) as db:
                        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (price_to_pay, user_id))
                        await db.commit()
                
                # Query database for the first admin username if configured
                import aiosqlite
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
            else:
                await message.answer(
                    f"❌ Error occurred: {err_msg}",
                    reply_markup=keyboards.get_product_view_keyboard(product_id, True, lang)
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
        # Calculate refund for undelivered items
        discount_pct = await get_user_discount(user_id)
        price_per_item = round(product['price'] * (1 - discount_pct / 100), 2)
        diff_qty = qty - actual_qty
        refund_amount = round(price_per_item * diff_qty, 2)
        
        # Credit user wallet with the difference
        import aiosqlite
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

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    btn_text = {"en": "📥 Download as TXT", "ar": "📥 تحميل كملف TXT", "ru": "📥 Скачать как TXT"}
    builder.button(text=btn_text.get(lang, btn_text['en']), callback_data=f"dl_pur_{purchase_time.replace(' ', '_')}")
    builder.adjust(1)
    
    # 4. Deliver products via Telegram: Check text character length against Telegram limits
    from aiogram.types import BufferedInputFile
    txt_content = "\n\n".join(stock_data_list)
    total_char_len = len(txt_content)
    file_time_str = purchase_time.replace(':', '-').replace(' ', '_')
    txt_file = BufferedInputFile(txt_content.encode('utf-8'), filename=f"purchase_{user_id}_{file_time_str}.txt")

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    btn_text = {"en": "📥 Download as TXT", "ar": "📥 تحميل كملف TXT", "ru": "📥 Скачать как TXT"}
    builder.button(text=btn_text.get(lang, btn_text['en']), callback_data=f"dl_pur_{purchase_time.replace(' ', '_')}")
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
            
            await send_message_with_retry(message.answer, success_text, parse_mode="Markdown", reply_markup=builder.as_markup())
        else:
            success_text = get_text(
                'purchase_success',
                lang,
                name=f"{prod_name} (x{actual_qty})",
                price=price_paid,
                data=first_chunk
            )
            await send_message_with_retry(message.answer, success_text, parse_mode="Markdown", reply_markup=builder.as_markup())
                    
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
            await send_message_with_retry(message.answer, fallback_msg.get(lang, fallback_msg['en']), parse_mode="Markdown", reply_markup=builder.as_markup())
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
    discount_pct = await get_user_discount(user_id)
    price_to_pay_per_item = round(product['price'] * (1 - discount_pct / 100), 2)
    
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
    discount_pct = await get_user_discount(user_id)
    price_to_pay_per_item = round(product['price'] * (1 - discount_pct / 100), 2)
    total_price = round(price_to_pay_per_item * qty, 2)
    
    # Try creating pre-order
    from database import create_pre_order
    try:
        await create_pre_order(user_id, product_id, qty)
        success_text = get_text('preorder_success', lang, amount=total_price)
        await message.answer(success_text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Failed to reserve: {e}")


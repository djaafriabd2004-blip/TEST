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
from utils import send_message_with_retry
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
        await message_or_callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
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
    product_id = int(callback.data.replace("prod_view_", ""))
    product = await get_product(product_id)
    
    if not product:
        await callback.answer("Product not found.")
        return
        
    stock_count = await get_stock_count(product_id)
    has_stock = stock_count > 0
    
    name = product[f'name_{lang}'] or product['name_en']
    desc = product[f'description_{lang}'] or product['description_en']
    
    # Check user discount
    user_id = callback.from_user.id
    discount_pct = await get_user_discount(user_id)
    if discount_pct > 0:
        price_val = product['price'] * (1 - discount_pct / 100)
        if lang == 'ar':
            price_str = f"~~${product['price']:.2f}~~ *${price_val:.2f} USD* (خصم {discount_pct:.0f}%)"
        elif lang == 'ru':
            price_str = f"~~${product['price']:.2f}~~ *${price_val:.2f} USD* (Скидка {discount_pct:.0f}%)"
        else:
            price_str = f"~~${product['price']:.2f}~~ *${price_val:.2f} USD* ({discount_pct:.0f}% Discount)"
    else:
        price_str = f"`${product['price']:.2f} USD`"
        
    text = get_text(
        'product_details',
        lang,
        name=name,
        desc=desc,
        price=price_str,
        stock=stock_count
    )
    
    user_id = callback.from_user.id
    is_sub = False
    if not has_stock:
        is_sub = await is_subscribed_stock_notification(user_id, product_id)
    
    kb = keyboards.get_product_view_keyboard(product_id, has_stock, lang, is_subscribed=is_sub)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

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
    
    prod_name = product[f'name_{lang}'] or product['name_en']
    
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
    
    if round(db_user['balance'], 2) < price_to_pay:
        # Alert insufficient balance
        await message.answer(
            get_text('insufficient_balance', lang, balance=db_user['balance'], price=price_to_pay),
            reply_markup=keyboards.get_product_view_keyboard(product_id, True, lang),
            parse_mode="Markdown"
        )
        return
        
    # 1. Perform DB buy transaction
    try:
        stock_data_list, price_paid, purchase_time = await buy_product(user_id, product_id, qty)
    except Exception as e:
        logger.error(f"Purchase failed in DB: {e}")
        err_msg = str(e)
        if "Out of stock" in err_msg:
            await message.answer(
                get_text('out_of_stock', lang),
                reply_markup=keyboards.get_product_view_keyboard(product_id, False, lang)
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
        
    prod_name = product[f'name_{lang}'] or product['name_en']
    
    # Split stock_data_list into chunks of text, each having length <= 3000 to be safe
    chunks = []
    current_chunk = []
    current_len = 0
    for item in stock_data_list:
        item_len = len(item) + (2 if current_chunk else 0)
        if current_len + item_len > 3000:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [item]
            current_len = len(item)
        else:
            current_chunk.append(item)
            current_len += item_len
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    btn_text = {"en": "📥 Download as TXT", "ar": "📥 تحميل كملف TXT", "ru": "📥 Скачать как TXT"}
    builder.button(text=btn_text.get(lang, btn_text['en']), callback_data=f"dl_pur_{purchase_time.replace(' ', '_')}")
    builder.adjust(1)
    
    # 3. Deliver products via Telegram with retry logic
    try:
        first_chunk = chunks[0] if chunks else ""
        success_text = get_text(
            'purchase_success',
            lang,
            name=f"{prod_name} (x{qty})",
            price=price_paid,
            data=first_chunk
        )
        
        if len(chunks) == 1:
            await send_message_with_retry(message.answer, success_text, parse_mode="Markdown", reply_markup=builder.as_markup())
        else:
            await send_message_with_retry(message.answer, success_text, parse_mode="Markdown")
            # Send remaining chunks in separate messages
            for idx, chunk in enumerate(chunks[1:], 1):
                await asyncio.sleep(0.4)  # Small pause to avoid network resets/flooding
                cont_text = get_text(
                    'purchase_success_continued',
                    lang,
                    data=chunk
                )
                if idx == len(chunks) - 1:
                    await send_message_with_retry(message.answer, cont_text, parse_mode="Markdown", reply_markup=builder.as_markup())
                else:
                    await send_message_with_retry(message.answer, cont_text, parse_mode="Markdown")
    except Exception as deliv_err:
        logger.error(f"Error during product delivery to chat for user {user_id}: {deliv_err}")
        fallback_msg = {
            "ar": f"🎉 *تمت عملية الشراء بنجاح!* ({prod_name} x{qty})\n\n⚠️ بسبب ضغط الاتصال في شبكة التليجرام، تعذر عرض جميع المنتجات في المحادثة مباشرة. يمكنك تحميل كافة المنتجات/الروابط الآن كملف TXT بالضغط على الزر أدناه أو مراجعة قائمة 'طلباتي'.",
            "en": f"🎉 *Purchase Successful!* ({prod_name} x{qty})\n\n⚠️ Due to network connection issues, some items could not be displayed in chat. You can download all your items right now using the button below as a TXT file or view 'My Orders'.",
            "ru": f"🎉 *Покупка успешно совершена!* ({prod_name} x{qty})\n\n⚠️ Из-за сетевых задержек часть товаров не удалось отобразить в чате. Вы можете скачать все товары по кнопке ниже в формате TXT или в меню 'Мои заказы'."
        }
        try:
            await send_message_with_retry(message.answer, fallback_msg.get(lang, fallback_msg['en']), parse_mode="Markdown", reply_markup=builder.as_markup())
        except Exception:
            pass
            
    # 4. Publish sale to news_channel if set
    news_channel = await get_setting('news_channel', '')
    if news_channel:
        try:
            import html
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            prod_name_en = html.escape(product['name_en'])
            sale_text = (
                f"⚡️ <b>NEW PURCHASE</b> ⚡️\n"
                f"──────────────────\n"
                f"🛍 <b>Product:</b> <code>{prod_name_en} (x{qty})</code>\n"
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
    
    name = product[f'name_{lang}'] or product['name_en']
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
    
    name = product[f'name_{lang}'] or product['name_en']
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
    store_name = await get_setting('store_name', 'Digital Store')
    lines.append(f"{'='*40}")
    lines.append(f"  {store_name} - Delivered Items")
    lines.append(f"  User: {callback.from_user.first_name} (ID: {user_id})")
    lines.append(f"  Date: {time_str}")
    lines.append(f"{'='*40}\n")
    
    for idx, order in enumerate(orders, 1):
        prod_name = order[f'product_name_{lang}'] or order['product_name_en']
        lines.append(f"Item #{idx}: {prod_name}")
        lines.append(f"Data: {order['stock_data']}")
        lines.append(f"{'-'*40}")
        
    content = "\n".join(lines)
    file = BufferedInputFile(content.encode('utf-8'), filename=f"purchase_{user_id}_{time_str.replace(':', '-').replace(' ', '_')}.txt")
    
    await callback.message.answer_document(file)
    await callback.answer()


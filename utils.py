import asyncio
import logging

logger = logging.getLogger(__name__)

async def send_message_with_retry(send_func, *args, retries=3, delay=1.5, **kwargs):
    """
    Executes a message sending coroutine function (like message.answer or bot.send_message)
    with retry logic in case of network glitches or connection resets on hosting platforms.
    Falls back to plain text if Markdown formatting entity parsing fails.
    """
    for attempt in range(1, retries + 1):
        try:
            return await send_func(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            if ("can't parse entities" in err_str or "bad request" in err_str or "entity" in err_str) and "parse_mode" in kwargs:
                kwargs_no_pm = kwargs.copy()
                kwargs_no_pm.pop("parse_mode", None)
                try:
                    return await send_func(*args, **kwargs_no_pm)
                except Exception as inner_e:
                    logger.warning(f"Fallback without parse_mode failed: {inner_e}")
            logger.warning(f"Attempt {attempt}/{retries} to send message failed: {e}")
            if attempt == retries:
                raise e
            await asyncio.sleep(delay * attempt)


async def start_auto_sales_proof_loop(bot):
    """
    Background loop that periodically posts simulated sales proofs to the news_channel
    if enabled by admin ('auto_proofs_enabled' == '1').
    Random interval between 5 and 20 minutes (300 to 1200 seconds).
    Uses available products in stock to build realistic proof posts.
    """
    import random
    import html
    from database import get_setting, get_products, get_stock_count
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    proof_logger = logging.getLogger("auto_sales_proof")
    proof_logger.info("Auto sales proof loop initialized.")

    while True:
        try:
            # Wait random interval between 5 and 20 minutes (300s to 1200s)
            wait_seconds = random.randint(300, 1200)
            await asyncio.sleep(wait_seconds)

            enabled = await get_setting("auto_proofs_enabled", "0")
            if enabled != "1":
                continue

            news_channel = await get_setting("news_channel", "")
            if not news_channel or news_channel == "None":
                continue

            products = await get_products()
            if not products:
                continue

            product_candidates = []
            weights = []
            stock_map = {}
            for p in products:
                try:
                    count = await get_stock_count(p['id'])
                    if count > 0:
                        product_candidates.append(p)
                        weights.append(count)
                        stock_map[p['id']] = count
                except Exception:
                    pass

            if product_candidates and sum(weights) > 0:
                selected_product = random.choices(product_candidates, weights=weights, k=1)[0]
            elif products:
                selected_product = random.choice(list(products))
            else:
                continue

            stock_available = stock_map.get(selected_product['id'], 1)
            raw_qty = random.choice([1, 1, 1, 2, 2, 3])
            qty = min(raw_qty, max(1, stock_available))
            
            prod_price = float(selected_product['price'])
            price_paid = round(prod_price * qty, 2)

            prod_name_en = html.escape(dict(selected_product).get('name_en') or dict(selected_product).get('name_ar') or 'Product')

            bot_info = await bot.get_me()
            bot_username = bot_info.username

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
            proof_logger.info(f"Auto sales proof published for product: {prod_name_en} (x{qty}) to {news_channel}")
        except Exception as e:
            proof_logger.error(f"Error in auto sales proof loop: {e}")
            await asyncio.sleep(60)

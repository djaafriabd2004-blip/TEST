import asyncio
import logging
import json
from aiogram.types import MessageEntity
from localization import get_text

logger = logging.getLogger(__name__)

def normalize_provider_url(url: str) -> str:
    """
    Normalizes a provider base URL by stripping trailing slashes, /api, /v1, or /api-docs
    to prevent double path issues.
    """
    if not url:
        return ""
    url = url.strip().rstrip('/')
    if not url.startswith('http'):
        url = 'https://' + url
    if url.endswith('/api-docs'):
        url = url[:-9]
    if url.endswith('/api'):
        url = url[:-4]
    if url.endswith('/v1'):
        url = url[:-3]
    return url.rstrip('/')

def extract_stock_from_dict(p, allow_boolean=True):
    """
    Universally extracts numeric stock from any provider's JSON product dictionary.
    Supports ShopDigital, ProdSeller, Supabase, Sellix, Whop, SMM Panels, WooCommerce,
    and custom Telegram store bots.
    """
    if not isinstance(p, dict):
        return None
    
    # 1. Check numeric stock fields FIRST
    for key in ['stock', 'stock_count', 'quantity', 'qty', 'count', 'amount', 'inventory', 'available', 'available_stock', 'max', 'remains', 'balance']:
        val = p.get(key)
        if val is not None and not isinstance(val, bool):
            try:
                return max(0, int(val))
            except (ValueError, TypeError):
                pass
    
    # 2. Check boolean inStock flags if allow_boolean is True
    if allow_boolean:
        for key in ['inStock', 'in_stock', 'is_available', 'available', 'active', 'enabled']:
            val = p.get(key)
            if val is True:
                return 999
            elif val is False:
                return 0
                
        # 3. Check string representations like "in stock", "out of stock"
        status_str = str(p.get('status') or p.get('stock_status') or '').lower()
        if 'instock' in status_str or 'available' in status_str:
            return 999
        elif 'outofstock' in status_str or 'empty' in status_str:
            return 0
        
    return None

def extract_products_list_from_json(data):
    """
    Universally extracts the list of products from any JSON response structure.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ['products', 'data', 'result', 'items', 'payload', 'services', 'goods']:
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                for subkey in ['products', 'items', 'list']:
                    subval = val.get(subkey)
                    if isinstance(subval, list):
                        return subval
                return [val]
        if 'id' in data or 'product_id' in data or 'productId' in data or 'service' in data:
            return [data]
    return []

def matches_product_id(p, target_id) -> bool:
    """
    Checks if a provider's product dictionary matches the specified target ID.
    """
    if not isinstance(p, dict):
        return False
    t_str = str(target_id).strip().lower()
    for key in ['id', '_id', 'product_id', 'productId', 'service', 'code', 'sku', 'slug']:
        val = p.get(key)
        if val is not None and str(val).strip().lower() == t_str:
            return True
    return False

def get_product_name(product, lang='en'):
    """
    Safely retrieves the localized product name from a database row or dict.
    Falls back gracefully if f'name_{lang}' does not exist in the row.
    """
    if not product:
        return "Product"
    p = dict(product) if not isinstance(product, dict) else product
    return p.get(f'name_{lang}') or p.get('name_en') or p.get('name_ar') or p.get('name_ru') or "Product"

def get_product_desc(product, lang='en'):
    """
    Safely retrieves the localized product description from a database row or dict.
    """
    if not product:
        return ""
    p = dict(product) if not isinstance(product, dict) else product
    return p.get(f'description_{lang}') or p.get('description_en') or p.get('description_ar') or p.get('description_ru') or ""

def get_product_unit_price(product, qty: int) -> float:
    """
    Returns the fixed unit price for a given quantity based on configured tier prices.
    Falls back to base product price if no tier matches.
    """
    if not product:
        return 0.0
    p = dict(product) if not isinstance(product, dict) else product
    base_price = float(p.get('price', 0.0))
    tier_json = p.get('tier_prices')
    if not tier_json:
        return base_price
    try:
        tiers = json.loads(tier_json)
        if isinstance(tiers, list):
            for t in sorted(tiers, key=lambda x: int(x.get('min_qty', 0)), reverse=True):
                min_q = int(t.get('min_qty', 0))
                if min_q > 0 and qty >= min_q:
                    return float(t.get('unit_price', base_price))
    except Exception as e:
        logger.warning(f"Error parsing tier_prices JSON: {e}")
    return base_price

def format_product_tier_prices_text(product, lang='en') -> str:
    """
    Formats localized text showing quantity tier prices for a product.
    """
    if not product:
        return ""
    p = dict(product) if not isinstance(product, dict) else product
    tier_json = p.get('tier_prices')
    if not tier_json:
        return ""
    try:
        tiers = json.loads(tier_json)
        if not isinstance(tiers, list) or not tiers:
            return ""
        
        sorted_tiers = sorted(tiers, key=lambda x: int(x.get('min_qty', 0)))
        lines = []
        header = {
            "ar": "🏷️ *أسعار الجملة حسب الكمية:*",
            "en": "🏷️ *Bulk Quantity Prices:*",
            "ru": "🏷️ *Оптовые цены от количества:*"
        }
        lines.append(header.get(lang, header['en']))
        
        for t in sorted_tiers:
            mq = int(t.get('min_qty', 0))
            up = float(t.get('unit_price', 0.0))
            if mq > 0 and up > 0:
                lines.append(f"🔹 *{mq}+* ⬅️ `${up:.2f} USD`")
        if len(lines) > 1:
            return "\n".join(lines)
    except Exception:
        pass
    return ""

def serialize_entities(entities):
    """
    Serializes a list of aiogram MessageEntity objects into a JSON string.
    Preserves all entity types, offsets, lengths, custom_emoji_id, url, user, language, etc.
    """
    if not entities:
        return None
    try:
        raw_list = []
        for e in entities:
            if hasattr(e, "model_dump"):
                d = e.model_dump(exclude_none=True)
            elif hasattr(e, "to_python"):
                d = e.to_python()
            else:
                d = dict(e)
            raw_list.append(d)
        return json.dumps(raw_list, ensure_ascii=False)
    except Exception as err:
        logger.error(f"Error serializing entities: {err}")
        return None

def deserialize_entities(entities_json):
    """
    Deserializes a JSON string back into a list of aiogram MessageEntity objects.
    """
    if not entities_json:
        return None
    try:
        if isinstance(entities_json, str):
            raw_list = json.loads(entities_json)
        else:
            raw_list = entities_json
        if isinstance(raw_list, list):
            res = []
            for item in raw_list:
                if isinstance(item, dict):
                    res.append(MessageEntity(**item))
            return res if res else None
    except Exception as err:
        logger.error(f"Error deserializing entities: {err}")
    return None

def get_utf16_len(text: str) -> int:
    """Returns length of text in UTF-16 code units (as required by Telegram Bot API)."""
    return len(text.encode('utf-16-le')) // 2

def format_product_message(product, lang, stock_count, discount_pct=0.0):
    """
    Constructs (text, entities, parse_mode) for displaying a product.
    If product has stored description entities (e.g. Premium Custom Emojis, bold, etc.),
    it constructs full_text and full_entities with correct offset shifting and parse_mode=None.
    Otherwise, returns fallback text with parse_mode="Markdown".
    """
    prod_dict = dict(product) if product else {}
    name = get_product_name(product, lang)
    desc = get_product_desc(product, lang)
    entities_json = prod_dict.get(f'description_entities_{lang}') or prod_dict.get('description_entities_en')
    desc_entities = deserialize_entities(entities_json)

    # Format price string
    prod_price = float(prod_dict.get('price', 0.0))
    if discount_pct > 0:
        price_val = prod_price * (1 - discount_pct / 100)
        if lang == 'ar':
            price_str_markdown = f"~~${prod_price:.2f}~~ *${price_val:.2f} USD* (خصم {discount_pct:.0f}%)"
            price_str_plain = f"${prod_price:.2f} -> ${price_val:.2f} USD (خصم {discount_pct:.0f}%)"
        elif lang == 'ru':
            price_str_markdown = f"~~${prod_price:.2f}~~ *${price_val:.2f} USD* (Скидка {discount_pct:.0f}%)"
            price_str_plain = f"${prod_price:.2f} -> ${price_val:.2f} USD (Скидка {discount_pct:.0f}%)"
        else:
            price_str_markdown = f"~~${prod_price:.2f}~~ *${price_val:.2f} USD* ({discount_pct:.0f}% Discount)"
            price_str_plain = f"${prod_price:.2f} -> ${price_val:.2f} USD ({discount_pct:.0f}% Discount)"
    else:
        price_str_markdown = f"`${prod_price:.2f} USD`"
        price_str_plain = f"${prod_price:.2f} USD"

    tier_text = format_product_tier_prices_text(product, lang)
    tier_str = f"\n\n{tier_text}" if tier_text else ""

    if not desc_entities:
        text = get_text(
            'product_details',
            lang,
            name=name,
            desc=desc,
            price=price_str_markdown,
            stock=stock_count
        ) + tier_str
        return text, None, "Markdown"

    # Rich formatting with MessageEntities (preserves Telegram Premium Custom Emojis)
    full_entities = []

    # Header section
    if lang == 'ar':
        h_label = "🛍️ المنتج: "
        d_label = "\n\n📝 الوصف:\n"
    elif lang == 'ru':
        h_label = "🛍️ Товар: "
        d_label = "\n\n📝 Описание:\n"
    else:
        h_label = "🛍️ Product: "
        d_label = "\n\n📝 Description:\n"

    full_entities.append(MessageEntity(type="bold", offset=0, length=get_utf16_len(h_label.strip())))
    header_text = h_label + name + d_label
    
    d_offset = get_utf16_len(h_label + name + "\n\n")
    full_entities.append(MessageEntity(type="bold", offset=d_offset, length=get_utf16_len(d_label.strip())))

    header_utf16_len = get_utf16_len(header_text)

    # Shift description entities by header_utf16_len
    for e in desc_entities:
        full_entities.append(MessageEntity(
            type=e.type,
            offset=e.offset + header_utf16_len,
            length=e.length,
            custom_emoji_id=e.custom_emoji_id,
            url=e.url,
            user=e.user,
            language=e.language
        ))

    # Footer section
    if lang == 'ar':
        footer_text = f"\n\n💵 السعر: {price_str_plain}\n📦 المخزون: {stock_count} متوفر" + (f"\n\n{tier_text}" if tier_text else "")
        p_label = "\n\n💵 السعر: "
        s_label = f"\n📦 المخزون: "
    elif lang == 'ru':
        footer_text = f"\n\n💵 Цена: {price_str_plain}\n📦 В наличии: {stock_count} шт." + (f"\n\n{tier_text}" if tier_text else "")
        p_label = "\n\n💵 Цена: "
        s_label = f"\n📦 В наличии: "
    else:
        footer_text = f"\n\n💵 Price: {price_str_plain}\n📦 Stock: {stock_count} available" + (f"\n\n{tier_text}" if tier_text else "")
        p_label = "\n\n💵 Price: "
        s_label = f"\n📦 Stock: "

    footer_offset = header_utf16_len + get_utf16_len(desc)
    
    full_entities.append(MessageEntity(type="bold", offset=footer_offset + 2, length=get_utf16_len(p_label.strip())))
    
    stock_label_offset = footer_offset + get_utf16_len(p_label + price_str_plain + "\n")
    full_entities.append(MessageEntity(type="bold", offset=stock_label_offset, length=get_utf16_len(s_label.strip())))

    full_text = header_text + desc + footer_text

    return full_text, full_entities, None

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
                kwargs_no_pm["parse_mode"] = None
                try:
                    return await send_func(*args, **kwargs_no_pm)
                except Exception as inner_e:
                    logger.warning(f"Fallback with parse_mode=None failed: {inner_e}")
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
            # Read admin configurable interval (defaults to 5 to 20 minutes)
            min_m_str = await get_setting("auto_proofs_min_minutes", "5")
            max_m_str = await get_setting("auto_proofs_max_minutes", "20")
            try:
                min_m = max(1, int(str(min_m_str).strip()))
                max_m = max(min_m, int(str(max_m_str).strip()))
            except Exception:
                min_m, max_m = 5, 20

            wait_seconds = random.randint(min_m * 60, max_m * 60)
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

            available_products = []
            weights = []
            for p in products:
                try:
                    count = await get_stock_count(p['id'])
                    if count > 0:
                        available_products.append(p)
                        weights.append(count)
                except Exception:
                    pass

            if not available_products:
                available_products = list(products)
                weights = [1] * len(products)

            # Weighted choice based on stock count
            selected_product = random.choices(available_products, weights=weights, k=1)[0]
            qty = random.choice([1, 1, 1, 2, 2, 3])
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

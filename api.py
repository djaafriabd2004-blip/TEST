import asyncio
from utils import send_message_with_retry
import logging
from aiohttp import web
import os

logger = logging.getLogger(__name__)

# Authentication Middleware
@web.middleware
async def api_key_auth_middleware(request, handler):
    # Allow public endpoints
    if request.path == "/" or request.path == "/api/health":
        return await handler(request)
        
    if request.path.startswith("/api/"):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return web.json_response({"ok": False, "error": "API Key missing in X-API-Key header"}, status=401)
            
        from database import get_user_by_api_key
        user = await get_user_by_api_key(api_key)
        if not user:
            return web.json_response({"ok": False, "error": "Invalid API Key"}, status=401)
            
        # Store user info in request context
        request["user"] = user
        
    return await handler(request)

# Endpoints
async def health_api(request):
    from database import get_setting
    store_name = await get_setting("store_name", "Digital Store")
    return web.json_response({"ok": True, "status": "healthy", "store_name": store_name})

async def index_api(request):
    from database import get_setting
    store_name = await get_setting("store_name", "Digital Store")
    return web.Response(text=f"Welcome to the {store_name} API server!")

async def get_me_api(request):
    user = request["user"]
    from database import get_setting
    store_name = await get_setting("store_name", "Digital Store")
    return web.json_response({
        "ok": True,
        "store_name": store_name,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "first_name": user["first_name"],
            "balance": user["balance"],
            "language": user["language"]
        }
    })

async def get_products_api(request):
    from database import get_products, get_stock_count
    products = await get_products()
    result = []
    for p in products:
        p_dict = dict(p)
        # Fetch actual stock count
        stock_count = await get_stock_count(p_dict["id"])
        p_dict["stock_count"] = stock_count
        result.append(p_dict)
    return web.json_response({"ok": True, "products": result})

async def get_product_detail_api(request):
    from database import get_product, get_stock_count
    try:
        product_id = int(request.match_info["id"])
    except ValueError:
        return web.json_response({"ok": False, "error": "Invalid product ID format"}, status=400)
        
    product = await get_product(product_id)
    if not product:
        return web.json_response({"ok": False, "error": "Product not found"}, status=404)
        
    p_dict = dict(product)
    p_dict["stock_count"] = await get_stock_count(product_id)
    return web.json_response({"ok": True, "product": p_dict})

async def buy_api(request):
    user = request["user"]
    user_id = user["user_id"]
    
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Invalid JSON body"}, status=400)
        
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    
    if not product_id or not isinstance(product_id, int):
        return web.json_response({"ok": False, "error": "product_id is required and must be an integer"}, status=400)
        
    if not isinstance(quantity, int) or quantity < 1:
        return web.json_response({"ok": False, "error": "quantity must be a positive integer"}, status=400)
        
    from database import buy_product, get_product
    product = await get_product(product_id)
    if not product:
        return web.json_response({"ok": False, "error": "Product not found"}, status=404)
        
    client_order_id = data.get("client_order_id") or data.get("idempotency_key")
    
    try:
        # Pass client_order_id to buy_product to enable idempotency checks
        stock_data_list, price_paid, purchase_time, actual_qty = await buy_product(
            user_id, product_id, quantity, client_order_id=client_order_id
        )
        
        # Log/Broadcast sale to news channel if set
        bot = request.app["bot"]
        
        # Send private message notification to the reseller/user on Telegram
        try:
            from localization import get_text
            lang = user.get("language", "en")
            prod_name = product.get(f"name_{lang}") or product.get("name_en")
            
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
                
            first_chunk = chunks[0] if chunks else ""
            
            success_text = (
                f"🔌 *API Purchase Notification*\n\n" +
                get_text(
                    'purchase_success',
                    lang,
                    name=f"{prod_name} (x{actual_qty})",
                    price=price_paid,
                    data=first_chunk
                )
            )
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            btn_text = {"en": "📥 Download as TXT", "ar": "📥 تحميل كملف TXT", "ru": "📥 Скачать как TXT"}
            builder.button(text=btn_text.get(lang, btn_text['en']), callback_data=f"dl_pur_{purchase_time.replace(' ', '_')}")
            builder.adjust(1)
            
            if len(chunks) == 1:
                await send_message_with_retry(bot.send_message, chat_id=user_id, text=success_text, parse_mode="Markdown", reply_markup=builder.as_markup())
            else:
                await send_message_with_retry(bot.send_message, chat_id=user_id, text=success_text, parse_mode="Markdown")
                for idx, chunk in enumerate(chunks[1:], 1):
                    await asyncio.sleep(0.4)
                    cont_text = get_text(
                        'purchase_success_continued',
                        lang,
                        data=chunk
                    )
                    if idx == len(chunks) - 1:
                        await send_message_with_retry(bot.send_message, chat_id=user_id, text=cont_text, parse_mode="Markdown", reply_markup=builder.as_markup())
                    else:
                        await send_message_with_retry(bot.send_message, chat_id=user_id, text=cont_text, parse_mode="Markdown")
                        
            # If partial delivery occurred, notify reseller/user as well
            if actual_qty < quantity:
                from database import get_user_discount
                discount_pct = await get_user_discount(user_id)
                price_per_item = round(product['price'] * (1 - discount_pct / 100), 2)
                diff_qty = quantity - actual_qty
                refund_amount = round(price_per_item * diff_qty, 2)
                
                # Refund user wallet locally since API purchase is using local balance logic
                import aiosqlite
                from config import DB_NAME
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (refund_amount, user_id))
                    await db.commit()
                
                await send_message_with_retry(
                    bot.send_message,
                    chat_id=user_id,
                    text=get_text('checkout_partial_delivery_refund', lang, actual=actual_qty, qty=quantity, diff=diff_qty, refund=refund_amount),
                    parse_mode="Markdown"
                )
        except Exception as pm_err:
            logger.error(f"Failed to send private Telegram notification for API purchase: {pm_err}")
        
        # Check if product is out of stock and notify admins
        try:
            from database import get_stock_count, notify_admins_stock_change
            new_stock = await get_stock_count(product_id)
            if new_stock == 0:
                await notify_admins_stock_change(bot, product_id, 'empty')
        except Exception as e:
            logger.error(f"Failed to check/notify out-of-stock for product {product_id} in API: {e}")
        try:
            from database import get_setting
            news_channel = await get_setting("news_channel", "")
            if news_channel:
                import html
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                bot_info = await bot.get_me()
                bot_username = bot_info.username
                prod_name_en = html.escape(product["name_en"])
                sale_text = (
                    f"⚡️ <b>NEW API PURCHASE</b> ⚡️\n"
                    f"──────────────────\n"
                    f"🛍 <b>Product:</b> <code>{prod_name_en} (x{actual_qty})</code>\n"
                    f"💵 <b>Amount Paid:</b> <code>${price_paid:.2f} USD</code>\n"
                    f"👤 <b>Partner:</b> <code>{user['first_name']}</code>\n"
                    f"📅 <b>Status:</b> <code>Delivered Successfully</code>\n"
                    f"──────────────────\n"
                    f"👉 <i>Available now at:</i> @{bot_username}"
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛍️ Shop Now", url=f"https://t.me/{bot_username}")]
                ])
                await send_message_with_retry(bot.send_message, chat_id=news_channel, text=sale_text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to log API sale to news channel: {e}")
            
        # Query updated user balance and order details to satisfy all parser formats
        from database import get_user
        updated_user = await get_user(user_id)
        new_balance = updated_user["balance"] if updated_user else 0.0
        
        # Query order ID to get transaction / order identity
        import aiosqlite
        from config import DB_NAME
        order_id = None
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT id FROM orders WHERE user_id = ? AND purchased_at = ? LIMIT 1;", (user_id, purchase_time)) as ord_cur:
                ord_row = await ord_cur.fetchone()
                if ord_row:
                    order_id = ord_row[0]
                    
        return web.json_response({
            "ok": True,
            "transaction_id": str(order_id) if order_id else None,
            "order_id": order_id,
            "product_id": product_id,
            "product_name": product["name_en"],
            "quantity": actual_qty,
            "price_paid": price_paid,
            "total_price": price_paid,
            "new_balance": new_balance,
            "purchase_time": purchase_time,
            "items": stock_data_list
        })
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)

def create_api_app(bot) -> web.Application:
    app = web.Application(middlewares=[api_key_auth_middleware])
    app["bot"] = bot
    
    # Register routes
    app.router.add_get("/", index_api)
    app.router.add_get("/api/health", health_api)
    app.router.add_get("/api/me", get_me_api)
    app.router.add_get("/api/products", get_products_api)
    app.router.add_get("/api/products/{id}", get_product_detail_api)
    app.router.add_post("/api/buy", buy_api)
    app.router.add_get("/api/orders", get_order_history_api)
    app.router.add_get("/api/orders/{id}", get_order_detail_api)
    
    return app

async def get_order_history_api(request):
    """
    Returns the list of recent orders for the authenticated API user.
    """
    user = request["user"]
    user_id = user["user_id"]
    
    import aiosqlite
    from config import DB_NAME
    
    # Fetch recent orders grouped by purchase time and product
    # In order to return cohesive multi-item purchases as single orders
    query = """
        SELECT id, product_id, price_paid, purchased_at, stock_data, product_name_en, client_order_id
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 50;
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            
    result = []
    for r in rows:
        row_dict = dict(r)
        result.append({
            "order_id": row_dict["id"],
            "transaction_id": str(row_dict["id"]),
            "product_id": row_dict["product_id"],
            "product_name": row_dict["product_name_en"],
            "price_paid": row_dict["price_paid"],
            "total_price": row_dict["price_paid"],
            "purchase_time": row_dict["purchased_at"],
            "client_order_id": row_dict["client_order_id"],
            "items": [row_dict["stock_data"]]
        })
    return web.json_response({"ok": True, "orders": result})

async def get_order_detail_api(request):
    """
    Retrieves the details of a specific order by ID (database order ID) or client_order_id.
    """
    user = request["user"]
    user_id = user["user_id"]
    order_param = request.match_info["id"]
    
    import aiosqlite
    from config import DB_NAME
    
    # Try looking it up by client_order_id first, then by numerical id
    query = """
        SELECT id, product_id, price_paid, purchased_at, stock_data, product_name_en, client_order_id
        FROM orders
        WHERE user_id = ? AND (client_order_id = ? OR CAST(id AS TEXT) = ?);
    """
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, (user_id, order_param, order_param)) as cursor:
            rows = await cursor.fetchall()
            
    if not rows:
        return web.json_response({"ok": False, "error": "Order not found"}, status=404)
        
    # Group items if there were multiple items in the same purchase time
    first_row = dict(rows[0])
    items = [dict(r)["stock_data"] for r in rows]
    total_paid = sum(dict(r)["price_paid"] for r in rows)
    
    return web.json_response({
        "ok": True,
        "order_id": first_row["id"],
        "transaction_id": str(first_row["id"]),
        "product_id": first_row["product_id"],
        "product_name": first_row["product_name_en"],
        "quantity": len(items),
        "price_paid": total_paid,
        "total_price": total_paid,
        "purchase_time": first_row["purchased_at"],
        "client_order_id": first_row["client_order_id"],
        "items": items
    })

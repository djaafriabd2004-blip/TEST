import aiosqlite
import logging
import os
import uuid
from datetime import datetime
from config import DB_NAME

logger = logging.getLogger(__name__)

async def db_init():
    if os.path.isdir(DB_NAME):
        raise RuntimeError(
            f"DB_NAME points to a directory ({DB_NAME}). "
            "On Railway, set the volume Mount Path to /data (folder only), "
            "and DB_NAME to /data/store.db."
        )

    parent = os.path.dirname(DB_NAME)
    if parent:
        os.makedirs(parent, exist_ok=True)
    logger.info("Opening database at %s", DB_NAME)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA synchronous = NORMAL;")
        
        # Users Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance REAL DEFAULT 0.0,
            language TEXT DEFAULT 'en',
            referred_by INTEGER,
            referral_code TEXT UNIQUE,
            referral_balance_earned REAL DEFAULT 0.0,
            referral_bonus_paid INTEGER DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Products Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT NOT NULL,
            name_en TEXT NOT NULL,
            name_ru TEXT NOT NULL,
            description_ar TEXT NOT NULL,
            description_en TEXT NOT NULL,
            description_ru TEXT NOT NULL,
            price REAL NOT NULL,
            custom_emoji_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Migration: Verify all expected columns in products table
        async with db.execute("PRAGMA table_info(products);") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            if "name_ar" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN name_ar TEXT;")
            if "name_en" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN name_en TEXT;")
            if "name_ru" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN name_ru TEXT;")
            if "description_ar" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN description_ar TEXT;")
            if "description_en" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN description_en TEXT;")
            if "description_ru" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN description_ru TEXT;")
            if "custom_emoji_id" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN custom_emoji_id TEXT;")
            if "provider_id" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN provider_id INTEGER;")
            if "provider_product_id" not in columns:
                await db.execute("ALTER TABLE products ADD COLUMN provider_product_id INTEGER;")
                
        # Migration: Verify expected columns in users table
        async with db.execute("PRAGMA table_info(users);") as cursor:
            user_columns = [row[1] for row in await cursor.fetchall()]
            if "is_banned" not in user_columns:
                await db.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0;")
            if "ban_reason" not in user_columns:
                await db.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT;")
            if "referral_bonus_paid" not in user_columns:
                await db.execute("ALTER TABLE users ADD COLUMN referral_bonus_paid INTEGER DEFAULT 0;")
                
        # Migration: Verify expected columns in orders table
        async with db.execute("PRAGMA table_info(orders);") as cursor:
            order_columns = [row[1] for row in await cursor.fetchall()]
            if "client_order_id" not in order_columns:
                await db.execute("ALTER TABLE orders ADD COLUMN client_order_id TEXT;")
        
        # Stocks Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            is_sold INTEGER DEFAULT 0,
            sold_to INTEGER DEFAULT NULL,
            sold_at TIMESTAMP DEFAULT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        """)
        
        # Orders Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            stock_id INTEGER NOT NULL,
            price_paid REAL NOT NULL,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            stock_data TEXT NOT NULL,
            product_name_ar TEXT NOT NULL,
            product_name_en TEXT NOT NULL,
            product_name_ru TEXT NOT NULL,
            client_order_id TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        """)
        
        # Payments Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            transaction_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Settings Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
        
        # User Discounts Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_discounts (
            user_id INTEGER PRIMARY KEY,
            discount_percent REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)
        
        # Stock Notifications Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS stock_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        """)
        
        # API Keys Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            user_id INTEGER PRIMARY KEY,
            api_key TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)
        
        # Providers Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_url TEXT NOT NULL,
            api_key TEXT NOT NULL,
            store_name TEXT
        );
        """)
        
        # Pre-orders Table
        await db.execute("""
        CREATE TABLE IF NOT EXISTS pre_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_paid REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );
        """)
        
        # Seed settings if they don't exist
        default_settings = {
            'support_username': '',
            'referral_bonus_percent': '10',
            'force_join_channels': '',  # comma separated e.g. "@channel1,@channel2"
            'news_channel': '',
            'stars_rate': '0.02',       # 1 Star = 0.02 USD
            'stars_enabled': '1',
            'crypto_addr_usdt': '0x89846777ea91dee2b25f0fcbf54884a4f79923d8',
            'crypto_addr_ltc': 'LbEuNY2o5ePVyd7dqE4dTyNToAPDtcYMXR',
            'crypto_addr_ton': 'UQC8zbAwkf9-f8SzyYYITLU8Et4g-Cf7ffyQJIhip9nupHGo',
            'bscscan_api_key': '',
            'blockcypher_api_key': '',
            'toncenter_api_key': '',
            'store_name': 'Digital Store',
            'max_tx_age_hours': '24',
            'cryptobot_token': '',
            'cryptobot_use_testnet': '0',
            'cryptotransfer_enabled': '1',
            'cryptobot_enabled': '1',
            'api_domain': 'worker-production-53ca.up.railway.app',
            'binance_api_proxy': '',
            'binance_api_base_url': 'https://api.binance.com',
            'binance_pay_base_url': 'https://bpay.binanceapi.com',
        }
        for key, val in default_settings.items():
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?);", (key, val))
            
        # Clean up any invalid language codes in users table
        await db.execute("UPDATE users SET language = 'en' WHERE language NOT IN ('en', 'ar', 'ru');")
        
        # Try adding store_name to providers table in case it was created without it
        try:
            await db.execute("ALTER TABLE providers ADD COLUMN store_name TEXT;")
        except Exception:
            pass
            
        await db.commit()

# Setting Helpers
async def get_setting(key, default=""):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?;", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default

async def set_setting(key, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);", (key, str(value)))
        await db.commit()

async def get_button_emojis():
    """Fetch all button emoji settings as a dict."""
    keys = [
        'btn_emoji_shop', 'btn_emoji_orders', 'btn_emoji_charge',
        'btn_emoji_referral', 'btn_emoji_support', 'btn_emoji_language',
        'btn_emoji_admin'
    ]
    result = {}
    async with aiosqlite.connect(DB_NAME) as db:
        for key in keys:
            async with db.execute("SELECT value FROM settings WHERE key = ?;", (key,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    # key is like 'btn_emoji_shop' -> extract 'shop'
                    short_key = key.replace('btn_emoji_', '')
                    result[short_key] = row[0]
    return result

# User Helpers
async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_user(user_id, username, first_name, referred_by=None):
    ref_code = str(uuid.uuid4())[:8]
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if user already exists
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            if await cursor.fetchone():
                return
        
        # Verify if referred_by user exists
        ref_by_id = None
        if referred_by:
            async with db.execute("SELECT user_id FROM users WHERE user_id = ?;", (referred_by,)) as cursor:
                if await cursor.fetchone() and referred_by != user_id:
                    ref_by_id = referred_by
                    
        await db.execute(
            "INSERT INTO users (user_id, username, first_name, referred_by, referral_code) VALUES (?, ?, ?, ?, ?);",
            (user_id, username, first_name, ref_by_id, ref_code)
        )
        await db.commit()

async def get_user_by_ref_code(ref_code):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE referral_code = ?;", (ref_code,)) as cursor:
            return await cursor.fetchone()

async def get_referral_count(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def update_user_lang(user_id, lang):
    if lang not in ['en', 'ar', 'ru']:
        lang = 'en'
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?;", (lang, user_id))
        await db.commit()

async def ban_user(user_id: int, reason: str = ""):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?;", (reason, user_id))
        await db.commit()

async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?;", (user_id,))
        await db.commit()

async def is_user_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT is_banned FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] == 1)

async def get_all_banned_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, username, first_name, ban_reason FROM users WHERE is_banned = 1;") as cursor:
            return await cursor.fetchall()

async def update_user_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (amount, user_id))
        await db.commit()

async def set_user_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?;", (amount, user_id))
        await db.commit()

async def get_users_with_balance():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, username, first_name, balance FROM users WHERE balance > 0 ORDER BY balance DESC LIMIT 100;") as cursor:
            return await cursor.fetchall()

# Product Helpers
async def add_product(name_ar, name_en, name_ru, description_ar, description_en, description_ru, price, custom_emoji_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            INSERT INTO products (name_ar, name_en, name_ru, description_ar, description_en, description_ru, price, custom_emoji_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name_ar, name_en, name_ru, description_ar, description_en, description_ru, price, custom_emoji_id))
        product_id = cursor.lastrowid
        await db.commit()
        return product_id

async def update_product(product_id, name_ar, name_en, name_ru, description_ar, description_en, description_ru, price, custom_emoji_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE products 
            SET name_ar=?, name_en=?, name_ru=?, description_ar=?, description_en=?, description_ru=?, price=?, custom_emoji_id=?
            WHERE id=?
        """, (name_ar, name_en, name_ru, description_ar, description_en, description_ru, price, custom_emoji_id, product_id))
        await db.commit()

async def delete_product(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM products WHERE id = ?;", (product_id,))
        await db.commit()

# Provider Integration Helpers
async def save_provider(base_url, api_key, store_name=None):
    base_url = base_url.strip().rstrip('/')
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if base_url exists
        async with db.execute("SELECT id FROM providers WHERE base_url = ?;", (base_url,)) as cursor:
            row = await cursor.fetchone()
            
        if row:
            await db.execute(
                "UPDATE providers SET api_key = ?, store_name = ? WHERE id = ?;",
                (api_key, store_name, row[0])
            )
        else:
            await db.execute(
                "INSERT INTO providers (base_url, api_key, store_name) VALUES (?, ?, ?);",
                (base_url, api_key, store_name)
            )
        await db.commit()

async def get_providers():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM providers ORDER BY id ASC;") as cursor:
            return await cursor.fetchall()

async def get_provider(provider_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM providers WHERE id = ?;", (provider_id,)) as cursor:
            return await cursor.fetchone()

async def delete_provider(provider_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # Delete all imported products from this provider
        await db.execute("DELETE FROM products WHERE provider_id = ?;", (provider_id,))
        # Delete the provider configuration
        await db.execute("DELETE FROM providers WHERE id = ?;", (provider_id,))
        await db.commit()

async def add_imported_product(name_ar, name_en, name_ru, description_ar, description_en, description_ru, price, custom_emoji_id, provider_id, provider_product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            INSERT INTO products (name_ar, name_en, name_ru, description_ar, description_en, description_ru, price, custom_emoji_id, provider_id, provider_product_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name_ar, name_en, name_ru, description_ar, description_en, description_ru, price, custom_emoji_id, provider_id, provider_product_id))
        product_id = cursor.lastrowid
        await db.commit()
        return product_id

async def get_products():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products;") as cursor:
            return await cursor.fetchall()

async def get_product(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?;", (product_id,)) as cursor:
            return await cursor.fetchone()

# Stock Helpers
async def add_stock(product_id, data):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO stocks (product_id, data) VALUES (?, ?);", (product_id, data))
        await db.commit()

async def bulk_add_stock(product_id, items):
    async with aiosqlite.connect(DB_NAME) as db:
        params = [(product_id, item) for item in items if item.strip()]
        await db.executemany("INSERT INTO stocks (product_id, data) VALUES (?, ?);", params)
        await db.commit()

async def get_stock_count(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Get local stock count first
        async with db.execute("SELECT COUNT(*) FROM stocks WHERE product_id = ? AND is_sold = 0;", (product_id,)) as local_cursor:
            local_row = await local_cursor.fetchone()
            local_count = local_row[0] if local_row else 0
            
        async with db.execute("SELECT provider_id, provider_product_id FROM products WHERE id = ?;", (product_id,)) as cursor:
            prod = await cursor.fetchone()
            if prod and prod['provider_id'] is not None:
                provider_id = prod['provider_id']
                provider_prod_id = prod['provider_product_id']
                
                async with db.execute("SELECT base_url, api_key FROM providers WHERE id = ?;", (provider_id,)) as prov_cursor:
                    prov = await prov_cursor.fetchone()
                    if not prov:
                        return local_count
                    base_url = prov['base_url']
                    api_key = prov['api_key']
                
                import aiohttp
                url = f"{base_url}/api/products"
                headers = {"X-API-Key": api_key}
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers, timeout=5) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data.get('ok') and 'products' in data:
                                    for p in data['products']:
                                        if p['id'] == provider_prod_id:
                                            return local_count + p.get('stock_count', 0)
                except Exception as e:
                    logger.error(f"Error fetching live stock for imported product {product_id}: {e}")
                return local_count
                
        return local_count

# Purchase Helpers
async def buy_product(user_id, product_id, quantity=1, skip_balance_check=False, allow_partial=True, client_order_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # 0. Idempotency Check: if client_order_id is provided, check if we already processed it
        if client_order_id:
            async with db.execute("SELECT * FROM orders WHERE client_order_id = ? AND user_id = ?;", (client_order_id, user_id)) as dup_cursor:
                existing_orders = await dup_cursor.fetchall()
                if existing_orders:
                    # Collect already delivered items for this order
                    all_stock_data = [item['stock_data'] for item in existing_orders]
                    price_paid = sum(item['price_paid'] for item in existing_orders)
                    purchase_time = existing_orders[0]['purchased_at']
                    actual_qty = len(existing_orders)
                    return all_stock_data, price_paid, purchase_time, actual_qty
        
        # Get product info
        async with db.execute("SELECT * FROM products WHERE id = ?;", (product_id,)) as cursor:
            product = await cursor.fetchone()
            if not product:
                raise Exception("Product not found")
        
        # Get user info
        async with db.execute("SELECT balance FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                raise Exception("User not found")
                
        # Check user discount
        async with db.execute("SELECT discount_percent FROM user_discounts WHERE user_id = ?;", (user_id,)) as cursor:
            discount_row = await cursor.fetchone()
            discount_percent = discount_row[0] if discount_row else 0.0
            
        final_price_per_item = round(product['price'] * (1 - discount_percent / 100), 2)
        total_price = round(final_price_per_item * quantity, 2)
        
        if not skip_balance_check and round(user['balance'], 2) < total_price:
            raise Exception("Insufficient balance")
            
        # Check local stock count first
        async with db.execute("SELECT COUNT(*) FROM stocks WHERE product_id = ? AND is_sold = 0;", (product_id,)) as local_cursor:
            local_count = (await local_cursor.fetchone())[0]
            
        local_stock_data = []
        local_stock_ids = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Deduct from local stock as much as possible first
        local_to_take = min(quantity, local_count)
        if local_to_take > 0:
            async with db.execute("SELECT * FROM stocks WHERE product_id = ? AND is_sold = 0 LIMIT ?;", (product_id, local_to_take)) as cursor:
                local_items = await cursor.fetchall()
                for item in local_items:
                    local_stock_data.append(item['data'])
                    local_stock_ids.append(item['id'])
                    
        remaining_qty = quantity - len(local_stock_data)
        
        # Check if imported product and we still need items from provider
        provider_stock_data = []
        if remaining_qty > 0 and product['provider_id'] is not None:
            # Fetch provider credentials
            async with db.execute("SELECT base_url, api_key FROM providers WHERE id = ?;", (product['provider_id'],)) as prov_cursor:
                prov = await prov_cursor.fetchone()
                if not prov:
                    raise Exception("Product provider configuration not found")
                base_url = prov['base_url']
                api_key = prov['api_key']
                
            # Perform external purchase via provider API
            import aiohttp
            import asyncio
            url = f"{base_url}/api/buy"
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            buy_payload = {
                "product_id": product['provider_product_id'],
                "quantity": remaining_qty
            }
            
            try:
                # Set a strict 30 second timeout on client session to avoid disconnections
                timeout_cfg = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
                    async with session.post(url, headers=headers, json=buy_payload) as resp:
                        if resp.status != 200:
                            try:
                                err_data = await resp.json()
                                err_msg = err_data.get('error', 'Unknown provider error')
                            except:
                                err_msg = await resp.text()
                            raise Exception(f"Provider error: {err_msg}")
                        
                        buy_data = await resp.json()
                        if not buy_data.get('ok') or 'items' not in buy_data:
                            raise Exception("Provider purchase response invalid")
                        
                        provider_stock_data = buy_data['items']
                        if len(provider_stock_data) < remaining_qty:
                            raise Exception(f"Provider returned insufficient items ({len(provider_stock_data)} received, {remaining_qty} requested)")
            except asyncio.TimeoutError:
                raise Exception("Provider request timed out. Please check if the purchase was debited before trying again.")
            except Exception as e:
                if "Provider error" in str(e) or "Provider purchase response invalid" in str(e) or "Provider returned insufficient items" in str(e):
                    raise e
                raise Exception(f"Failed to communicate with provider: {e}")
                
        # Calculate actual purchased quantity and final price
        actual_qty = len(local_stock_data) + len(provider_stock_data)
        if actual_qty == 0:
            raise Exception("Out of stock")
            
        actual_price = round(final_price_per_item * actual_qty, 2)
        
        # Check balance limit again for actual price
        if not skip_balance_check and round(user['balance'], 2) < actual_price:
            raise Exception("Insufficient balance")
            
        # Complete transaction
        # Deduct balance locally
        if not skip_balance_check:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?;", (actual_price, user_id))
            
        # Process local stock mark as sold
        for stock_id, item_data in zip(local_stock_ids, local_stock_data):
            await db.execute(
                "UPDATE stocks SET is_sold = 1, sold_to = ?, sold_at = ? WHERE id = ?;",
                (user_id, now, stock_id)
            )
            await db.execute(
                """INSERT INTO orders (user_id, product_id, stock_id, price_paid, purchased_at, stock_data, product_name_ar, product_name_en, product_name_ru, client_order_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (user_id, product['id'], stock_id, final_price_per_item, now, item_data, product['name_ar'], product['name_en'], product['name_ru'], client_order_id)
            )
            
        # Process provider items
        for item_data in provider_stock_data:
            await db.execute(
                """INSERT INTO orders (user_id, product_id, stock_id, price_paid, purchased_at, stock_data, product_name_ar, product_name_en, product_name_ru, client_order_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (user_id, product['id'], 0, final_price_per_item, now, item_data, product['name_ar'], product['name_en'], product['name_ru'], client_order_id)
            )
            
        await db.commit()
        all_stock_data = local_stock_data + provider_stock_data
        
        # Check and award referral bonus on first purchase
        try:
            await check_and_award_referral(user_id)
        except Exception as e:
            logger.error(f"Error checking/awarding referral for user {user_id}: {e}")
            
        return all_stock_data, actual_price, now, actual_qty

async def check_and_award_referral(user_id):
    """
    Checks if the user has a referrer and if their referral_bonus_paid is 0.
    If yes, awards the fixed referral bonus to the referrer and marks referral_bonus_paid as 1.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Fetch user details
        async with db.execute("SELECT referred_by, referral_bonus_paid, first_name FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user or not user['referred_by'] or user['referral_bonus_paid'] == 1:
                return
                
        ref_by_id = user['referred_by']
        referee_name = user['first_name'] or "User"
        
        # 2. Get fixed bonus settings
        async with db.execute("SELECT value FROM settings WHERE key = 'referral_bonus_percent';") as cursor:
            sett_row = await cursor.fetchone()
            fixed_bonus = float(sett_row[0]) if sett_row else 1.0  # default to 1.0 USD if not configured
            
        if fixed_bonus <= 0:
            return
            
        # 3. Credit referrer balance & update referee status
        await db.execute(
            "UPDATE users SET balance = balance + ?, referral_balance_earned = referral_balance_earned + ? WHERE user_id = ?;",
            (fixed_bonus, fixed_bonus, ref_by_id)
        )
        await db.execute("UPDATE users SET referral_bonus_paid = 1 WHERE user_id = ?;", (user_id,))
        await db.commit()
        
        # 4. Notify referrer via bot if possible
        try:
            # Import locally to avoid circular dependencies
            from bot import main
            # To notify, we can retrieve bot token and query or let middleware/handlers notify.
            # However, since bot instance is running, we can fetch from config or pass bot
            import config
            from aiogram import Bot
            bot_instance = Bot(token=config.BOT_TOKEN)
            
            async with db.execute("SELECT language FROM users WHERE user_id = ?;", (ref_by_id,)) as cursor:
                ref_row = await cursor.fetchone()
                ref_lang = ref_row['language'] if ref_row else 'en'
                
            from localization import get_text
            msg_text = get_text('referral_new_user_joined', ref_lang, name=referee_name, bonus=fixed_bonus)
            await bot_instance.send_message(chat_id=ref_by_id, text=msg_text, parse_mode="Markdown")
            await bot_instance.session.close()
        except Exception as notify_err:
            logger.error(f"Failed to send referral award notification to {ref_by_id}: {notify_err}")

# --- Pre-order Reservation Helpers ---
async def create_pre_order(user_id, product_id, quantity=1):
    """
    Creates a pre-order reservation for a product when it's out of stock.
    Deducts balance immediately and registers the pre-order.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Get product info
        async with db.execute("SELECT * FROM products WHERE id = ?;", (product_id,)) as cursor:
            product = await cursor.fetchone()
            if not product:
                raise Exception("Product not found")
                
        # 2. Get user info and calculate user-specific price
        async with db.execute("SELECT balance FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                raise Exception("User not found")
                
        from database import get_user_discount
        discount_percent = await get_user_discount(user_id)
        final_price_per_item = round(product['price'] * (1 - discount_percent / 100), 2)
        total_price = round(final_price_per_item * quantity, 2)
        
        # 3. Check user balance
        if round(user['balance'], 2) < total_price:
            raise Exception("Insufficient balance")
            
        # 4. Deduct user balance and create pre-order
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?;", (total_price, user_id))
        await db.execute(
            "INSERT INTO pre_orders (user_id, product_id, quantity, price_paid) VALUES (?, ?, ?, ?);",
            (user_id, product_id, quantity, total_price)
        )
        await db.commit()
        return total_price

async def get_user_pre_orders(user_id):
    """Retrieves all active pre-orders for a user with product name."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT po.*, p.name_ar, p.name_en, p.name_ru 
               FROM pre_orders po 
               JOIN products p ON po.product_id = p.id 
               WHERE po.user_id = ? 
               ORDER BY po.id DESC;""", (user_id,)
        ) as cursor:
            return await cursor.fetchall()

async def cancel_pre_order(pre_order_id, user_id):
    """Cancels a pre-order and refunds the exact price_paid back to the user's wallet."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Fetch pre-order details
        async with db.execute("SELECT * FROM pre_orders WHERE id = ? AND user_id = ?;", (pre_order_id, user_id)) as cursor:
            pre_order = await cursor.fetchone()
            if not pre_order:
                raise Exception("Pre-order not found")
                
        price_paid = pre_order['price_paid']
        
        # 2. Refund balance and delete pre-order
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (price_paid, user_id))
        await db.execute("DELETE FROM pre_orders WHERE id = ?;", (pre_order_id,))
        await db.commit()
        return price_paid

async def process_pending_pre_orders(bot, product_id):
    """
    Called whenever a product is restocked.
    Processes pending pre-orders for the product one by one in FIFO order.
    Attempts to buy the items from database using 'buy_product' with skip_balance_check=True.
    Delivers the codes to the users via bot messages.
    """
    import asyncio
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # Get all pending pre-orders for this product
        async with db.execute("SELECT * FROM pre_orders WHERE product_id = ? ORDER BY id ASC;", (product_id,)) as cursor:
            pre_orders = await cursor.fetchall()
            
        if not pre_orders:
            return
            
        from localization import get_text
        for po in pre_orders:
            po_id = po['id']
            po_user_id = po['user_id']
            po_qty = po['quantity']
            
            # Check current stock count of the product
            from database import get_stock_count, buy_product, get_product
            stock_avail = await get_stock_count(product_id)
            if stock_avail < po_qty:
                # Not enough stock for this pre-order, skip and try next (or wait for next restock)
                continue
                
            # Attempt to fulfill
            try:
                # Buy product (skip_balance_check = True since they already paid)
                stock_data_list, price_paid, purchase_time, actual_qty = await buy_product(
                    user_id=po_user_id,
                    product_id=product_id,
                    quantity=po_qty,
                    skip_balance_check=True,
                    allow_partial=False
                )
                
                # Delete pre-order record
                await db.execute("DELETE FROM pre_orders WHERE id = ?;", (po_id,))
                await db.commit()
                
                # Notify user and deliver items
                async with db.execute("SELECT language FROM users WHERE user_id = ?;", (po_user_id,)) as cursor:
                    u_row = await cursor.fetchone()
                    lang = u_row['language'] if u_row else 'en'
                    
                product = await get_product(product_id)
                prod_dict = dict(product) if product else {}
                prod_name = prod_dict.get(f"name_{lang}") or prod_dict.get("name_en") or "Product"
                
                # Split stock_data_list into chunks of text, each having length <= 3000 to be safe (just like checkout delivery)
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
                
                # Format success notifications (using exact purchase_success format styling)
                from localization import get_text
                first_chunk = chunks[0] if chunks else ""
                success_text = get_text(
                    'purchase_success',
                    lang,
                    name=f"{prod_name} (x{actual_qty})",
                    price=price_paid,
                    data=first_chunk
                )
                # Prefix with [Pre-order Fulfilled] tag to clarify context
                title_prefix = {
                    "ar": "🎉 **[تم تسليم الحجز المسبق المكتمل!]**\n\n",
                    "en": "🎉 **[Pre-order Fulfilled!]**\n\n",
                    "ru": "🎉 **[Предзаказ выполнен!]**\n\n"
                }
                success_text = title_prefix.get(lang, title_prefix['en']) + success_text
                
                # Send primary message text
                try:
                    sent_msg = await bot.send_message(chat_id=po_user_id, text=success_text, parse_mode="Markdown")
                    
                    # If multiple chunks, send rest
                    for chunk in chunks[1:]:
                        await asyncio.sleep(0.4)
                        cont_text = get_text('purchase_success_continued', lang, data=chunk)
                        await bot.send_message(chat_id=po_user_id, text=cont_text, parse_mode="Markdown")
                except Exception:
                    pass
                
                # Create and deliver TXT file for the user (exactly as done in download purchase callback)
                try:
                    from aiogram.types import BufferedInputFile
                    lines = []
                    for item in stock_data_list:
                        lines.append(item.strip())
                        
                    content = "\n\n".join(lines)
                    file_name_time = purchase_time.replace(':', '-').replace(' ', '_')
                    file = BufferedInputFile(content.encode('utf-8'), filename=f"preorder_{po_user_id}_{file_name_time}.txt")
                    
                    await bot.send_document(chat_id=po_user_id, document=file)
                except Exception as file_err:
                    logger.error(f"Failed to send txt file for preorder {po_id}: {file_err}")
                    
            except Exception as e:
                logger.error(f"Failed to fulfill pre-order {po_id}: {e}")
                # Keep the pre-order and try on next restock
                continue
            
            # Tiny delay between deliveries
            await asyncio.sleep(0.5)

async def start_api_preorder_auto_verification_loop(bot):
    """
    Background loop that runs every 5 minutes.
    Checks all products that have pending pre-orders.
    If the product is an imported Reseller API product, it fetches its live stock count.
    If live stock count >= required pre-order quantity, it calls process_pending_pre_orders
    to automatically purchase from provider API and deliver to users.
    """
    import asyncio
    logger.info("Blockchain/API Pre-order auto-fulfillment loop started.")
    while True:
        try:
            # 1. Fetch all product_ids with active pre-orders
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT DISTINCT product_id FROM pre_orders;") as cursor:
                    rows = await cursor.fetchall()
                    product_ids = [r['product_id'] for r in rows]
            
            # 2. Inspect each product
            for pid in product_ids:
                # Check if product is imported reseller product
                async with aiosqlite.connect(DB_NAME) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute("SELECT provider_id, provider_product_id FROM products WHERE id = ?;", (pid,)) as cur:
                        prod_row = await cur.fetchone()
                        
                if prod_row and prod_row['provider_id'] is not None:
                    # Fetch live stock from provider API
                    live_stock = await get_stock_count(pid)
                    if live_stock > 0:
                        # We have live stock available at provider! Let's process the pre-orders
                        logger.info(f"API product {pid} has active stock ({live_stock}). Processing pre-orders...")
                        await process_pending_pre_orders(bot, pid)
                        
        except Exception as e:
            logger.error(f"Error in api_preorder_auto_fulfillment loop: {e}")
            
        # Run check every 5 minutes
        await asyncio.sleep(300)

async def get_preorders_summary():
    """
    Returns a list of dictionaries summarizing active pre-orders per product:
    [ { product_id, name_en, name_ar, name_ru, total_quantity, total_preorders } ]
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT po.product_id, 
                   p.name_ar, p.name_en, p.name_ru,
                   SUM(po.quantity) as total_quantity, 
                   COUNT(po.id) as total_preorders
            FROM pre_orders po
            JOIN products p ON po.product_id = p.id
            GROUP BY po.product_id;
        """
        async with db.execute(query) as cursor:
            return await cursor.fetchall()

async def get_all_active_preorders_for_product(product_id):
    """Returns a list of all individual active pre-orders for a given product with buyer information."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT po.*, u.first_name, u.username 
            FROM pre_orders po
            LEFT JOIN users u ON po.user_id = u.user_id
            WHERE po.product_id = ?
            ORDER BY po.id ASC;
        """
        async with db.execute(query, (product_id,)) as cursor:
            return await cursor.fetchall()

async def cancel_pre_order_by_admin(pre_order_id):
    """
    Cancels a pre-order from the admin panel.
    Refunds the price_paid back to user's wallet and returns the refunded details.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pre_orders WHERE id = ?;", (pre_order_id,)) as cursor:
            po = await cursor.fetchone()
            if not po:
                raise Exception("Pre-order not found")
                
        user_id = po['user_id']
        price_paid = po['price_paid']
        
        # Refund user balance
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (price_paid, user_id))
        await db.execute("DELETE FROM pre_orders WHERE id = ?;", (pre_order_id,))
        await db.commit()
        return user_id, price_paid

async def get_orders(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC;", (user_id,)) as cursor:
            return await cursor.fetchall()

async def get_sales_last_24h():
    from datetime import datetime, timedelta
    since = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT o.*, u.username, u.first_name 
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.purchased_at >= ?
            ORDER BY o.id DESC;
        """
        async with db.execute(query, (since,)) as cursor:
            return await cursor.fetchall()

# Payments / Deposits Helpers
async def create_payment(user_id, amount, payment_method, transaction_id, created_at=None):
    async with aiosqlite.connect(DB_NAME) as db:
        if created_at:
            await db.execute(
                "INSERT INTO payments (user_id, amount, payment_method, transaction_id, created_at) VALUES (?, ?, ?, ?, ?);",
                (user_id, amount, payment_method, transaction_id, created_at)
            )
        else:
            await db.execute(
                "INSERT INTO payments (user_id, amount, payment_method, transaction_id) VALUES (?, ?, ?, ?);",
                (user_id, amount, payment_method, transaction_id)
            )
        await db.commit()

async def get_payment(transaction_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE transaction_id = ?;", (transaction_id,)) as cursor:
            return await cursor.fetchone()

async def complete_payment(transaction_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Get payment
        async with db.execute("SELECT * FROM payments WHERE transaction_id = ? AND status = 'pending';", (transaction_id,)) as cursor:
            payment = await cursor.fetchone()
            if not payment:
                return None  # already processed or doesn't exist
        
        # Mark payment as completed
        await db.execute("UPDATE payments SET status = 'completed' WHERE transaction_id = ?;", (transaction_id,))
        
        user_id = payment['user_id']
        amount = payment['amount']
        
        # Credit user balance
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?;", (amount, user_id))
        
        await db.commit()
        return {
            'user_id': user_id,
            'amount': amount,
            'referrer_notif': None
        }

async def reject_payment(transaction_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE transaction_id = ? AND status = 'pending';", (transaction_id,)) as cursor:
            payment = await cursor.fetchone()
            if not payment:
                return None
        await db.execute("UPDATE payments SET status = 'rejected' WHERE transaction_id = ?;", (transaction_id,))
        await db.commit()
        return payment

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, language FROM users;") as cursor:
            return await cursor.fetchall()

async def get_pending_blockchain_payments():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE status = 'pending' AND payment_method LIKE 'blockchain_%';"
        ) as cursor:
            return await cursor.fetchall()

async def get_pending_cryptobot_payments():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE status = 'pending' AND payment_method LIKE 'cryptobot_%';"
        ) as cursor:
            return await cursor.fetchall()

async def get_all_pending_payments():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE status = 'pending' ORDER BY id DESC;"
        ) as cursor:
            return await cursor.fetchall()

async def is_payment_processed(payment_method):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id FROM payments WHERE payment_method = ? AND status IN ('completed', 'rejected');", 
            (payment_method,)
        ) as cursor:
            return await cursor.fetchone() is not None

async def get_payment_by_method(payment_method):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE payment_method = ?;", (payment_method,)) as cursor:
            return await cursor.fetchone()

# User Discounts Helpers
async def get_user_discount(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT discount_percent FROM user_discounts WHERE user_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0

async def set_user_discount(user_id, percent):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_discounts (user_id, discount_percent) VALUES (?, ?);",
            (user_id, percent)
        )
        await db.commit()

async def delete_user_discount(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM user_discounts WHERE user_id = ?;", (user_id,))
        await db.commit()

async def get_all_user_discounts():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT ud.user_id, ud.discount_percent, u.username, u.first_name 
            FROM user_discounts ud 
            LEFT JOIN users u ON ud.user_id = u.user_id
            ORDER BY ud.discount_percent DESC;
        """
        async with db.execute(query) as cursor:
            return await cursor.fetchall()

async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        # Total users
        async with db.execute("SELECT COUNT(*) FROM users;") as cur:
            total_users = (await cur.fetchone())[0]

        # Users joined today
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(joined_at) = DATE('now');"
        ) as cur:
            users_today = (await cur.fetchone())[0]

        # Total completed deposits (revenue)
        async with db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'completed';"
        ) as cur:
            total_deposits = (await cur.fetchone())[0]

        # Deposits today
        async with db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'completed' AND DATE(created_at) = DATE('now');"
        ) as cur:
            deposits_today = (await cur.fetchone())[0]

        # Total completed deposit count
        async with db.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'completed';"
        ) as cur:
            total_deposit_count = (await cur.fetchone())[0]

        # Total orders (purchases)
        async with db.execute("SELECT COUNT(*) FROM orders;") as cur:
            total_orders = (await cur.fetchone())[0]

        # Orders today
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE DATE(purchased_at) = DATE('now');"
        ) as cur:
            orders_today = (await cur.fetchone())[0]

        # Total revenue from orders
        async with db.execute(
            "SELECT COALESCE(SUM(price_paid), 0) FROM orders;"
        ) as cur:
            total_order_revenue = (await cur.fetchone())[0]

        # Revenue today from orders
        async with db.execute(
            "SELECT COALESCE(SUM(price_paid), 0) FROM orders WHERE DATE(purchased_at) = DATE('now');"
        ) as cur:
            order_revenue_today = (await cur.fetchone())[0]

        # Pending deposits
        async with db.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending';"
        ) as cur:
            pending_count = (await cur.fetchone())[0]

        return {
            'total_users': total_users,
            'users_today': users_today,
            'total_deposits': total_deposits,
            'deposits_today': deposits_today,
            'total_deposit_count': total_deposit_count,
            'total_orders': total_orders,
            'orders_today': orders_today,
            'total_order_revenue': total_order_revenue,
            'order_revenue_today': order_revenue_today,
            'pending_count': pending_count,
        }

# Stock Notification Helpers
async def subscribe_stock_notification(user_id, product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO stock_notifications (user_id, product_id) VALUES (?, ?);",
            (user_id, product_id)
        )
        await db.commit()

async def unsubscribe_stock_notification(user_id, product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM stock_notifications WHERE user_id = ? AND product_id = ?;",
            (user_id, product_id)
        )
        await db.commit()

async def is_subscribed_stock_notification(user_id, product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT 1 FROM stock_notifications WHERE user_id = ? AND product_id = ?;",
            (user_id, product_id)
        ) as cursor:
            return await cursor.fetchone() is not None

async def get_stock_notification_subscribers(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT sn.user_id, u.language, u.first_name FROM stock_notifications sn "
            "LEFT JOIN users u ON sn.user_id = u.user_id "
            "WHERE sn.product_id = ?;",
            (product_id,)
        ) as cursor:
            return await cursor.fetchall()

async def clear_stock_notifications(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM stock_notifications WHERE product_id = ?;",
            (product_id,)
        )
        await db.commit()

async def get_user_full_report(user_id):
    """Get comprehensive report about a user: profile, deposits, orders, referrals."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        # User profile
        async with db.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)) as cur:
            user = await cur.fetchone()
        if not user:
            return None

        # Completed deposits
        async with db.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(amount), 0) as total FROM payments WHERE user_id = ? AND status = 'completed';",
            (user_id,)
        ) as cur:
            deposits = await cur.fetchone()

        # Pending deposits
        async with db.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(amount), 0) as total FROM payments WHERE user_id = ? AND status = 'pending';",
            (user_id,)
        ) as cur:
            pending = await cur.fetchone()

        # Recent deposits (last 5)
        async with db.execute(
            "SELECT amount, payment_method, status, created_at FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 5;",
            (user_id,)
        ) as cur:
            recent_deposits = await cur.fetchall()

        # Orders
        async with db.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(price_paid), 0) as total FROM orders WHERE user_id = ?;",
            (user_id,)
        ) as cur:
            orders = await cur.fetchone()

        # Recent orders (last 5)
        async with db.execute(
            "SELECT product_name_en, price_paid, purchased_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5;",
            (user_id,)
        ) as cur:
            recent_orders = await cur.fetchall()

        # Referrals (users referred by this user)
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE referred_by = ?;",
            (user_id,)
        ) as cur:
            referral_count = (await cur.fetchone())['cnt']

        # Who referred this user
        referred_by_name = None
        if user['referred_by']:
            async with db.execute(
                "SELECT first_name, username FROM users WHERE user_id = ?;",
                (user['referred_by'],)
            ) as cur:
                referrer = await cur.fetchone()
                if referrer:
                    referred_by_name = referrer['first_name']
                    if referrer['username']:
                        referred_by_name += f" (@{referrer['username']})"

        # Discount
        async with db.execute(
            "SELECT discount_percent FROM user_discounts WHERE user_id = ?;",
            (user_id,)
        ) as cur:
            discount_row = await cur.fetchone()
            discount = discount_row['discount_percent'] if discount_row else 0

        return {
            'user': dict(user),
            'deposits_count': deposits['cnt'],
            'deposits_total': deposits['total'],
            'pending_count': pending['cnt'],
            'pending_total': pending['total'],
            'recent_deposits': [dict(d) for d in recent_deposits],
            'orders_count': orders['cnt'],
            'orders_total': orders['total'],
            'recent_orders': [dict(o) for o in recent_orders],
            'referral_count': referral_count,
            'referred_by_name': referred_by_name,
            'discount': discount,
        }

# API Keys Helpers
async def generate_api_key(user_id) -> str:
    import secrets
    api_key = "sb_" + secrets.token_hex(24) # 'sb_' for store bot
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO api_keys (user_id, api_key) VALUES (?, ?);",
            (user_id, api_key)
        )
        await db.commit()
    return api_key

async def get_api_key(user_id) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT api_key FROM api_keys WHERE user_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_user_by_api_key(api_key):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # Join users table to get full user details
        query = """
            SELECT u.* 
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.user_id
            WHERE ak.api_key = ?;
        """
        async with db.execute(query, (api_key,)) as cursor:
            return await cursor.fetchone()

async def revoke_api_key(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM api_keys WHERE user_id = ?;", (user_id,))
        await db.commit()

async def get_all_api_keys():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT ak.*, u.username, u.first_name 
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.user_id
            ORDER BY ak.created_at DESC;
        """
        async with db.execute(query) as cursor:
            return await cursor.fetchall()

async def notify_admins_stock_change(bot, product_id, event_type, quantity=0):
    """
    event_type can be:
      - 'refill' (when stock is added)
      - 'empty' (when stock is depleted)
    """
    import config
    if not config.ADMIN_IDS:
        return
        
    product = await get_product(product_id)
    if not product:
        return
        
    prod_name = product['name_en']
    current_stock = await get_stock_count(product_id)
    
    if event_type == 'refill':
        msg = (
            f"📥 *Stock Refilled* 📥\n"
            f"══════════════════\n"
            f"🛍 *Product:* `{prod_name}`\n"
            f"📦 *Added:* `{quantity}` items\n"
            f"📈 *Total Stock:* `{current_stock}` items\n"
            f"💵 *Price:* `${product['price']:.2f} USD`\n"
            f"══════════════════"
        )
    elif event_type == 'empty':
        msg = (
            f"⚠️ *Stock Alert: Out of Stock* ⚠️\n"
            f"══════════════════\n"
            f"🛍 *Product:* `{prod_name}`\n"
            f"❌ *Status:* Out of Stock!\n"
            f"⚠️ *Action:* Please refill the stock as soon as possible.\n"
            f"══════════════════"
        )
    else:
        return
        
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=msg, parse_mode="Markdown")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not send stock notification to admin {admin_id}: {e}")

async def broadcast_restock_to_users(bot, product_id, added_qty):
    async def _run_broadcast():
        import asyncio
        product = await get_product(product_id)
        if not product:
            return
            
        stock_count = await get_stock_count(product_id)
        
        # Fetch all users
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user_id, language FROM users;") as cursor:
                users = await cursor.fetchall()
                
        from localization import get_text
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        for u in users:
            user_id = u['user_id']
            lang = 'en'  # Force English for all restock announcements
            
            prod_name = product['name_en']
            msg = get_text('notify_stock_available', lang, name=prod_name, stock=stock_count, price=product['price'])
            
            builder = InlineKeyboardBuilder()
            builder.button(text=get_text('btn_buy', lang), callback_data=f"prod_view_{product_id}")
            builder.adjust(1)
            
            try:
                await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown", reply_markup=builder.as_markup())
            except Exception:
                # Ignore blocked/deleted chats
                pass
            # Avoid hitting Telegram rate limits (30 msgs/sec -> ~0.05s delay)
            await asyncio.sleep(0.05)
            
    # Start broadcast in the background so it doesn't block the admin's UI
    import asyncio
    asyncio.create_task(_run_broadcast())




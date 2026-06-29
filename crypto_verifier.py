import asyncio
import logging
import base64
import time
import aiohttp
from datetime import datetime, timezone
from database import (
    get_setting, complete_payment, get_pending_blockchain_payments,
    get_user, update_user_balance, reject_payment, get_pending_cryptobot_payments
)
from cryptobot_client import get_cryptobot_invoice
import config

logger = logging.getLogger(__name__)

TX_TOO_OLD_PREFIX = "TX_TOO_OLD"


def is_tx_too_old_error(message) -> bool:
    return isinstance(message, str) and message.startswith(TX_TOO_OLD_PREFIX)


def is_amount_matching(requested_amount: float, actual_amount: float, coin: str) -> bool:
    """
    Checks if the actual on-chain amount matches the user's requested deposit amount.
    Allows small tolerances for exchange rate fluctuations or network gas fees.
    """
    try:
        req = float(requested_amount)
        act = float(actual_amount)
    except (TypeError, ValueError):
        return False
        
    if req <= 0 or act <= 0:
        return False
        
    diff = abs(act - req)
    
    if coin in ["USDT", "BINANCE"]:
        # Strict tolerance for USDT and Binance Pay (max $1.00 USD or 5% difference)
        return diff <= 1.0 or (diff / req) <= 0.05
    else:
        # Flexible tolerance for LTC/TON due to price fluctuations (max $3.00 USD or 15% difference)
        return diff <= 3.0 or (diff / req) <= 0.15


async def get_max_tx_age_seconds() -> int:
    raw = await get_setting("max_tx_age_hours", "24")
    try:
        hours = float(raw)
        if hours <= 0:
            return 24 * 3600
        return int(hours * 3600)
    except (TypeError, ValueError):
        return 24 * 3600


def parse_unix_timestamp(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        if text.isdigit():
            return int(text)
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            return 0
    return 0


def validate_tx_age(tx_unix: int, max_age_seconds: int, min_timestamp: int = None) -> tuple[bool, str]:
    if tx_unix <= 0:
        return False, f"{TX_TOO_OLD_PREFIX}: Could not determine transaction time."
    age_seconds = time.time() - tx_unix
    max_hours = max(1, max_age_seconds // 3600)
    if age_seconds > max_age_seconds:
        return False, (
            f"{TX_TOO_OLD_PREFIX}: Transaction exceeds maximum age of {max_hours} hours."
        )
    if age_seconds < -300:
        return False, f"{TX_TOO_OLD_PREFIX}: Invalid transaction timestamp."
    if min_timestamp is not None and tx_unix < min_timestamp:
        return False, f"{TX_TOO_OLD_PREFIX}: Transaction was executed on-chain before deposit amount entry time."
    return True, ""


async def fetch_bsc_block_timestamp(block_number_hex: str) -> int:
    if not block_number_hex:
        return 0
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://bsc-dataseed.binance.org/"
            rpc_data = {
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [block_number_hex, False],
                "id": 1,
            }
            async with session.post(url, json=rpc_data, timeout=10) as resp:
                if resp.status == 200:
                    payload = await resp.json()
                    block = payload.get("result")
                    if isinstance(block, dict):
                        ts = block.get("timestamp", "0x0")
                        if isinstance(ts, str):
                            return int(ts, 16)
                        return int(ts)
    except Exception as e:
        logger.warning(f"Failed to fetch BSC block timestamp: {e}")
    return 0

def base64_to_hex(b64_str):
    try:
        # Standardize padding
        b64_str = b64_str.strip()
        missing_padding = len(b64_str) % 4
        if missing_padding:
            b64_str += '=' * (4 - missing_padding)
        return base64.b64decode(b64_str).hex()
    except Exception:
        return ""

def match_ton_hash(h1, h2):
    if not h1 or not h2:
        return False
    h1_clean = h1.strip().replace("0x", "").lower()
    h2_clean = h2.strip().replace("0x", "").lower()
    if h1_clean == h2_clean:
        return True
        
    h1_hex = base64_to_hex(h1)
    h2_hex = base64_to_hex(h2)
    
    h1_final = h1_hex if h1_hex else h1_clean
    h2_final = h2_hex if h2_hex else h2_clean
    
    return h1_final.lower() == h2_final.lower() or h1_final.lower() == h2_clean or h1_clean == h2_final.lower()

async def get_coin_price(coin):
    if coin == "USDT":
        return 1.0
        
    symbol = f"{coin}USDT"
    base_url = await get_setting("binance_api_base_url", "https://api.binance.com")
    if not base_url:
        base_url = "https://api.binance.com"
    proxy = await get_setting("binance_api_proxy", "")
    proxy = proxy if proxy else None
    
    url = f"{base_url}/api/v3/ticker/price?symbol={symbol}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data.get("price", 0))
    except Exception as e:
        logger.error(f"Failed to get price for {coin}: {e}")
        
    fallbacks = {
        "LTC": 85.0,
        "TON": 6.5
    }
    return fallbacks.get(coin, 1.0)

async def verify_usdt_bep20(txid, recipient_address, max_age_seconds: int, min_timestamp: int = None):
    bscscan_key = await get_setting("bscscan_api_key", "")
    if bscscan_key:
        bscscan_key = bscscan_key.strip()
        if bscscan_key.lower() in ["", "none", "null"]:
            bscscan_key = ""
            
    result = None
    if bscscan_key:
        try:
            async with aiohttp.ClientSession() as session:
                # Use Etherscan API V2 multichain endpoint for BSC
                url = f"https://api.etherscan.io/v2/api?chainid=56&module=proxy&action=eth_getTransactionReceipt&txhash={txid}&apikey={bscscan_key}"
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        payload = await resp.json()
                        res = payload.get("result")
                        if isinstance(res, dict):
                            result = res
                        else:
                            logger.warning(f"BscScan proxy receipt returned non-dict result: {res}. Falling back to public RPC...")
        except Exception as e:
            logger.warning(f"BscScan proxy receipt fetch failed: {e}. Falling back to public RPC...")
            
    if not result:
        # Fallback to public BSC RPC node
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://bsc-dataseed.binance.org/"
                rpc_data = {
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionReceipt",
                    "params": [txid],
                    "id": 1
                }
                async with session.post(url, json=rpc_data, timeout=10) as resp:
                    if resp.status == 200:
                        payload = await resp.json()
                        res = payload.get("result")
                        if isinstance(res, dict):
                            result = res
                        else:
                            logger.warning(f"Public BSC RPC returned non-dict result: {res}")
        except Exception as e:
            logger.error(f"BSC receipt fetch error: {e}")
            return False, f"BSC RPC connection error: {e}"
            
    if not result:
        return False, "Transaction not found on BSC network yet."
        
    # Check transaction status
    status = result.get("status")
    if status != "0x1":
        return False, "Transaction failed on BSC network."

    block_number = result.get("blockNumber")
    tx_unix = await fetch_bsc_block_timestamp(block_number)
    age_ok, age_err = validate_tx_age(tx_unix, max_age_seconds, min_timestamp)
    if not age_ok:
        return False, age_err
        
    # Standard USDT BEP20 contract address (case-insensitive)
    usdt_contract = "0x55d398326f99059ff775485246999027b3197955"
    usdt_transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    
    recipient_clean = recipient_address.strip().lower().replace("0x", "")
    if not recipient_clean:
        return False, "Admin USDT address is not configured."
        
    # Iterate through logs to verify USDT Transfer event
    for log in result.get("logs", []):
        log_address = log.get("address", "").lower()
        if log_address != usdt_contract:
            continue
            
        topics = log.get("topics", [])
        if len(topics) < 3:
            continue
            
        event_signature = topics[0].lower()
        if event_signature != usdt_transfer_topic:
            continue
            
        # topics[2] is the receiver (padded to 32 bytes)
        receiver = topics[2].lower()
        if receiver.endswith(recipient_clean):
            # Parse amount (data is hex string)
            try:
                raw_val = int(log.get("data", "0"), 16)
                # USDT BEP20 has 18 decimals
                amount_usd = raw_val / 10**18
                return True, amount_usd
            except Exception as e:
                return False, f"Failed to parse amount from log: {e}"
                
    return False, "USDT transfer to recipient address not found in transaction logs."

async def verify_ltc(txid, recipient_address, max_age_seconds: int, min_timestamp: int = None):
    token = await get_setting("blockcypher_api_key", "")
    if token:
        token = token.strip()
        if token.lower() in ["", "none", "null"]:
            token = ""
            
    # Try blockcypher
    url = f"https://api.blockcypher.com/v1/ltc/main/txs/{txid}"
    if token:
        url += f"?token={token}"
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict):
                        confirmations = data.get("confirmations", 0)
                        if confirmations < 1:
                            return False, "Transaction found but has 0 confirmations on Litecoin."

                        tx_unix = parse_unix_timestamp(data.get("confirmed") or data.get("received"))
                        age_ok, age_err = validate_tx_age(tx_unix, max_age_seconds, min_timestamp)
                        if not age_ok:
                            return False, age_err
                            
                        for out in data.get("outputs", []):
                            addresses = out.get("addresses", [])
                            if recipient_address in addresses:
                                val_sats = out.get("value", 0)
                                val_ltc = val_sats / 10**8
                                price = await get_coin_price("LTC")
                                val_usd = val_ltc * price
                                return True, val_usd
                        return False, "USDT/LTC transfer to recipient address not found in transaction outputs."
                    else:
                        logger.warning(f"Blockcypher returned non-dict response: {data}")
    except Exception as e:
        logger.warning(f"Blockcypher LTC fetch failed: {e}. Trying fallback...")
        
    # Fallback to Blockchair API
    fallback_url = f"https://api.blockchair.com/litecoin/dashboards/transaction/{txid}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(fallback_url, timeout=10) as resp:
                if resp.status == 200:
                    payload = await resp.json()
                    if isinstance(payload, dict):
                        tx_data = payload.get("data", {}).get(txid, {})
                        if isinstance(tx_data, dict):
                            transaction = tx_data.get("transaction", {})
                            confirmations = transaction.get("confirmations", 0) if isinstance(transaction, dict) else 0
                            if confirmations < 1:
                                return False, "Transaction has 0 confirmations on Litecoin."

                            tx_unix = parse_unix_timestamp(transaction.get("time") if isinstance(transaction, dict) else 0)
                            age_ok, age_err = validate_tx_age(tx_unix, max_age_seconds, min_timestamp)
                            if not age_ok:
                                return False, age_err
                                
                            outputs = tx_data.get("outputs", [])
                            for out in outputs:
                                recipient = out.get("recipient")
                                if recipient == recipient_address:
                                    val_sats = out.get("value", 0)
                                    val_ltc = val_sats / 10**8
                                    price = await get_coin_price("LTC")
                                    val_usd = val_ltc * price
                                    return True, val_usd
                            return False, "USDT/LTC transfer to recipient address not found in transaction outputs."
    except Exception as e:
        logger.error(f"Fallback Blockchair LTC fetch failed: {e}")
        
    return False, "Could not fetch Litecoin transaction from APIs."

def normalize_ton_address(address_str):
    if not address_str:
        return ""
    address_str = address_str.strip()
    if ":" in address_str:
        parts = address_str.split(":")
        return f"{parts[0]}:{parts[1].lower()}"
    try:
        import base64
        missing_padding = len(address_str) % 4
        if missing_padding:
            address_str += '=' * (4 - missing_padding)
        address_str_clean = address_str.replace("-", "+").replace("_", "/")
        decoded = base64.b64decode(address_str_clean)
        if len(decoded) >= 36:
            workchain = decoded[1]
            if workchain > 127:
                workchain -= 256
            hash_bytes = decoded[2:34]
            return f"{workchain}:{hash_bytes.hex().lower()}"
    except Exception:
        pass
    return address_str.lower()

async def verify_ton(txid, recipient_address, max_age_seconds: int, min_timestamp: int = None):
    admin_raw = normalize_ton_address(recipient_address)
    
    # Try querying tonapi.io first (helps locate both sender and recipient transaction hashes)
    url = f"https://tonapi.io/v2/blockchain/transactions/{txid}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict):
                        tx_unix = parse_unix_timestamp(data.get("utime"))
                        age_ok, age_err = validate_tx_age(tx_unix, max_age_seconds, min_timestamp)
                        if not age_ok:
                            return False, age_err

                        # 1. Check if recipient is the destination of the incoming message
                        in_msg = data.get("in_msg", {})
                        if isinstance(in_msg, dict):
                            dest = in_msg.get("destination", {})
                            dest_addr = dest.get("address", "") if isinstance(dest, dict) else ""
                            if normalize_ton_address(dest_addr) == admin_raw:
                                value = int(in_msg.get("value", 0))
                                value_ton = value / 10**9
                                price = await get_coin_price("TON")
                                val_usd = value_ton * price
                                return True, val_usd
                                
                        # 2. Check if admin is the destination of any outgoing messages
                        for out in data.get("out_msgs", []):
                            if isinstance(out, dict):
                                dest = out.get("destination", {})
                                dest_addr = dest.get("address", "") if isinstance(dest, dict) else ""
                                if normalize_ton_address(dest_addr) == admin_raw:
                                    value = int(out.get("value", 0))
                                    value_ton = value / 10**9
                                    price = await get_coin_price("TON")
                                    val_usd = value_ton * price
                                    return True, val_usd
                                    
                        return False, "Transaction destination does not match admin TON wallet address."
                else:
                    logger.warning(f"tonapi.io query returned status {resp.status}. Trying fallback...")
    except Exception as e:
        logger.warning(f"tonapi.io query failed: {e}. Trying fallback to Toncenter...")

    # Fallback to Toncenter
    api_key = await get_setting("toncenter_api_key", "")
    if api_key:
        api_key = api_key.strip()
        if api_key.lower() in ["", "none", "null"]:
            api_key = ""
            
    toncenter_url = "https://toncenter.com/api/v2/getTransactions"
    params = {
        "address": recipient_address,
        "limit": 50
    }
    
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(toncenter_url, params=params, headers=headers, timeout=12) as resp:
                if resp.status == 200:
                    payload = await resp.json()
                    if isinstance(payload, dict) and payload.get("ok"):
                        transactions = payload.get("result", [])
                        if isinstance(transactions, list):
                            for tx in transactions:
                                if isinstance(tx, dict):
                                    tx_id_data = tx.get("transaction_id", {})
                                    tx_hash = tx_id_data.get("hash", "") if isinstance(tx_id_data, dict) else ""
                                    
                                    if match_ton_hash(tx_hash, txid):
                                        tx_unix = parse_unix_timestamp(tx.get("utime"))
                                        age_ok, age_err = validate_tx_age(tx_unix, max_age_seconds, min_timestamp)
                                        if not age_ok:
                                            return False, age_err

                                        in_msg = tx.get("in_msg", {})
                                        if isinstance(in_msg, dict):
                                            value_nanotons = int(in_msg.get("value", 0))
                                            value_ton = value_nanotons / 10**9
                                            price = await get_coin_price("TON")
                                            val_usd = value_ton * price
                                            return True, val_usd
                        return False, "Transaction not found in the latest 50 receipts of the TON address."
                    elif isinstance(payload, dict):
                        return False, f"Toncenter API error: {payload.get('error')}"
                    else:
                        return False, "Toncenter API returned non-dict response."
    except Exception as e:
        logger.error(f"TON transaction fetch failed via fallback: {e}")
        
    return False, "Could not verify TON transaction."

async def verify_crypto_transaction(coin, txid, recipient_address, min_timestamp: int = None):
    if coin != "BINANCE" and not recipient_address:
        return False, "Recipient address is empty."

    max_age_seconds = await get_max_tx_age_seconds()
        
    if coin == "USDT":
        return await verify_usdt_bep20(txid, recipient_address, max_age_seconds, min_timestamp)
    elif coin == "LTC":
        return await verify_ltc(txid, recipient_address, max_age_seconds, min_timestamp)
    elif coin == "TON":
        return await verify_ton(txid, recipient_address, max_age_seconds, min_timestamp)
    elif coin == "BINANCE":
        from binance_client import verify_binance_payment
        return await verify_binance_payment(txid, min_timestamp=min_timestamp)
    else:
        return False, f"Unsupported coin: {coin}"

async def start_auto_verification_loop(bot):
    logger.info("Starting blockchain automatic deposit verification loop...")
    
    import aiosqlite
    from database import DB_NAME
    
    while True:
        try:
            # Sleep first or wait (run every 60 seconds)
            await asyncio.sleep(60)
            
            # Fetch and process pending blockchain payments
            pending_payments = await get_pending_blockchain_payments()
            if pending_payments:
                for payment in pending_payments:
                    transaction_id = payment["transaction_id"]
                    user_id = payment["user_id"]
                    method = payment["payment_method"]
                    
                    # Age check to expire stale pending blockchain payments
                    from datetime import datetime, timezone
                    created_at_str = payment["created_at"]
                    try:
                        created_dt = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                        age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
                    except Exception:
                        try:
                            created_dt = datetime.fromisoformat(created_at_str)
                            if created_dt.tzinfo is None:
                                created_dt = created_dt.replace(tzinfo=timezone.utc)
                            age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
                        except Exception:
                            age_seconds = 0
                            
                    max_age = await get_max_tx_age_seconds()
                    if age_seconds > max_age:
                        logger.info(f"Expiring old pending blockchain payment {transaction_id} (age: {age_seconds:.0f}s)")
                        await reject_payment(transaction_id)
                        db_user = await get_user(user_id)
                        user_lang = db_user["language"] if db_user else "en"
                        max_hours = max(1, max_age // 3600)
                        from localization import get_text
                        try:
                            await bot.send_message(
                                chat_id=user_id,
                                text=get_text("crypto_tx_too_old", user_lang, hours=max_hours),
                                parse_mode="Markdown",
                            )
                        except Exception as ne:
                            logger.warning(f"Could not notify user of expired payment: {ne}")
                        continue
                    
                    parts = method.split("_")
                    if len(parts) < 3:
                        continue
                        
                    coin = parts[1]
                    txid = "_".join(parts[2:])
                    
                    recipient_address = await get_setting(f"crypto_addr_{coin.lower()}", "")
                    
                    min_timestamp = int(created_dt.timestamp()) if age_seconds > 0 else None
                    success, result_val = await verify_crypto_transaction(coin, txid, recipient_address, min_timestamp=min_timestamp)
                    if success:
                        requested_amount = payment["amount"]
                        if not is_amount_matching(requested_amount, result_val, coin):
                            logger.warning(f"Background check amount mismatch for payment {transaction_id}: requested {requested_amount}, on-chain {result_val}")
                            await reject_payment(transaction_id)
                            admin_alert = (
                                f"🚨 *SUSPICIOUS DEPOSIT (Background): Amount Mismatch!*\n\n"
                                f"👤 *User ID:* `{user_id}`\n"
                                f"🪙 *Coin:* `{coin}`\n"
                                f"🔗 *TxID:* `{txid}`\n"
                                f"📥 *Entered Amount:* `${requested_amount:.2f} USD`\n"
                                f"🔗 *Actual On-Chain:* `${result_val:.2f} USD`\n"
                                f"⚠️ *Status:* Automatically Rejected."
                            )
                            for admin_id in config.ADMIN_IDS:
                                try:
                                    await bot.send_message(chat_id=admin_id, text=admin_alert, parse_mode="Markdown")
                                except Exception:
                                    pass
                            continue

                        async with aiosqlite.connect(DB_NAME) as db:
                            await db.execute(
                                "UPDATE payments SET amount = ? WHERE transaction_id = ?;", 
                                (result_val, transaction_id)
                            )
                            await db.commit()
                            
                        res = await complete_payment(transaction_id)
                        if res:
                            db_user = await get_user(user_id)
                            new_balance = db_user['balance'] if db_user else 0.0
                            lang = db_user['language'] if db_user else 'en'
                            
                            from localization import get_text
                            try:
                                await bot.send_message(
                                    chat_id=user_id,
                                    text=get_text('payment_success', lang, amount=result_val, new_balance=new_balance),
                                    parse_mode="Markdown"
                                )
                            except Exception as ne:
                                logger.warning(f"Could not notify user of verified payment: {ne}")
                                
                            admin_notif = (
                                f"✅ *Auto-Verified Crypto Deposit!*\n\n"
                                f"👤 *User ID:* `{user_id}`\n"
                                f"🪙 *Coin:* `{coin}`\n"
                                f"💵 *Amount Credited:* `${result_val:.2f} USD`\n"
                                f"🔗 *TxID:* `{txid}`"
                            )
                            for admin_id in config.ADMIN_IDS:
                                try:
                                    await bot.send_message(chat_id=admin_id, text=admin_notif, parse_mode="Markdown")
                                except Exception:
                                    pass
                    else:
                        if is_tx_too_old_error(result_val):
                            await reject_payment(transaction_id)
                            
                            # Send alert to admins about the potential fraud/older TxID reuse in background check
                            admin_alert = (
                                f"⚠️ *Potential Fraud / Older TxID Reuse Attempt (Auto-Check)!*\n\n"
                                f"👤 *User ID:* `{user_id}`\n"
                                f"🪙 *Coin:* `{coin}`\n"
                                f"🔗 *TxID/PayID:* `{txid}`\n"
                                f"❌ *Reason:* {result_val.replace('TX_TOO_OLD: ', '')}"
                            )
                            for admin_id in config.ADMIN_IDS:
                                try:
                                    await bot.send_message(chat_id=admin_id, text=admin_alert, parse_mode="Markdown")
                                except Exception:
                                    pass
                                    
                            db_user = await get_user(user_id)
                            user_lang = db_user["language"] if db_user else "en"
                            max_hours = max(1, (await get_max_tx_age_seconds()) // 3600)
                            from localization import get_text
                            try:
                                await bot.send_message(
                                    chat_id=user_id,
                                    text=get_text("crypto_tx_too_old", user_lang, hours=max_hours),
                                    parse_mode="Markdown",
                                )
                            except Exception as ne:
                                logger.warning(f"Could not notify user of expired tx: {ne}")
                            logger.info(f"Rejected expired transaction {transaction_id}: {result_val}")
                            continue

                        logger.debug(f"Verification pending for {transaction_id}: {result_val}")

            # Fetch and process pending Crypto Bot payments
            cb_payments = await get_pending_cryptobot_payments()
            if cb_payments:
                for payment in cb_payments:
                    transaction_id = payment["transaction_id"]
                    user_id = payment["user_id"]
                    method = payment["payment_method"]
                    
                    # Age check to expire stale pending Crypto Bot payments
                    from datetime import datetime, timezone
                    created_at_str = payment["created_at"]
                    try:
                        created_dt = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                        age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
                    except Exception:
                        try:
                            created_dt = datetime.fromisoformat(created_at_str)
                            if created_dt.tzinfo is None:
                                created_dt = created_dt.replace(tzinfo=timezone.utc)
                            age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
                        except Exception:
                            age_seconds = 0
                            
                    if age_seconds > 86400: # 24 hours
                        logger.info(f"Expiring old pending Crypto Bot payment {transaction_id} (age: {age_seconds:.0f}s)")
                        await reject_payment(transaction_id)
                        continue
                        
                    invoice_id_str = method.replace("cryptobot_", "")
                    try:
                        invoice_id = int(invoice_id_str)
                    except ValueError:
                        continue
                        
                    invoice = await get_cryptobot_invoice(invoice_id)
                    if invoice:
                        status = invoice.get("status")
                        if status == "paid":
                            res = await complete_payment(transaction_id)
                            if res:
                                db_user = await get_user(user_id)
                                new_balance = db_user['balance'] if db_user else 0.0
                                lang = db_user['language'] if db_user else 'en'
                                
                                from localization import get_text
                                try:
                                    await bot.send_message(
                                        chat_id=user_id,
                                        text=get_text('payment_success', lang, amount=payment['amount'], new_balance=new_balance),
                                        parse_mode="Markdown"
                                    )
                                except Exception as ne:
                                    logger.warning(f"Could not notify user of verified Crypto Bot payment: {ne}")
                                    
                                admin_notif = (
                                    f"✅ *Auto-Verified Crypto Bot Deposit!*\n\n"
                                    f"👤 *User ID:* `{user_id}`\n"
                                    f"💵 *Amount Credited:* `${payment['amount']:.2f} USD`\n"
                                    f"🆔 *Invoice ID:* `{invoice_id}`"
                                )
                                for admin_id in config.ADMIN_IDS:
                                    try:
                                        await bot.send_message(chat_id=admin_id, text=admin_notif, parse_mode="Markdown")
                                    except Exception:
                                        pass
                        elif status == "expired":
                            logger.info(f"Expiring old Crypto Bot payment {transaction_id} (Invoice status: expired)")
                            await reject_payment(transaction_id)
                            db_user = await get_user(user_id)
                            user_lang = db_user["language"] if db_user else "en"
                            from localization import get_text
                            try:
                                await bot.send_message(
                                    chat_id=user_id,
                                    text=get_text("crypto_tx_too_old", user_lang, hours=24),
                                    parse_mode="Markdown",
                                )
                            except Exception as ne:
                                logger.warning(f"Could not notify user of expired Crypto Bot payment: {ne}")
        except Exception as e:
            logger.error(f"Error in automatic verification loop: {e}")

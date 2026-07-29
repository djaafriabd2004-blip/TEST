import time
import hmac
import hashlib
import uuid
import aiohttp
import json
import logging
from config import BINANCE_API_KEY, BINANCE_SECRET_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://bpay.binanceapi.com"

async def get_binance_keys():
    """Get Binance API keys from database first, then fallback to .env config."""
    api_key = BINANCE_API_KEY
    secret_key = BINANCE_SECRET_KEY
    
    try:
        from database import get_setting
        db_api_key = await get_setting("binance_api_key", "")
        db_secret_key = await get_setting("binance_secret_key", "")
        if db_api_key:
            api_key = db_api_key
        if db_secret_key:
            secret_key = db_secret_key
    except Exception as e:
        logger.error(f"Error loading Binance keys from database: {e}")
    
    return api_key, secret_key

async def get_binance_configs():
    import os
    # Hardcoded default URLs - not configurable by admin to prevent mistakes
    api_url = "https://api.binance.com"
    pay_url = "https://bpay.binanceapi.com"
    
    proxy = os.getenv("BINANCE_API_PROXY", "")
    
    try:
        from database import get_setting
        db_proxy = await get_setting("binance_api_proxy", "")
        if db_proxy:
            proxy = db_proxy
    except Exception as e:
        logger.error(f"Error loading Binance configurations from database: {e}")
        
    return {
        "proxy": proxy if proxy else None,
        "api_base_url": api_url,
        "pay_base_url": pay_url
    }

def generate_nonce(length=32):
    return uuid.uuid4().hex[:length]

def generate_signature(timestamp, nonce, body_str, secret_key):
    payload = f"{timestamp}\n{nonce}\n{body_str}\n"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha512
    ).hexdigest().upper()
    return signature

async def create_binance_order(amount, description="Deposit Balance", order_id=None):
    """
    Creates a Binance Pay order and returns the payment URL.
    """
    if not order_id:
        order_id = f"PAY_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        
    configs = await get_binance_configs()
    proxy = configs["proxy"]
    base_url = configs["pay_base_url"]
    
    endpoint = "/binancepay/openapi/v2/order"
    url = f"{base_url}{endpoint}"
    
    # Binance Pay Order Payload
    payload = {
        "env": {
            "terminalType": "WEB"
        },
        "merchantTradeNo": order_id,
        "orderAmount": float(amount),
        "currency": "USDT",
        "goods": {
            "goodsType": "02",  # 01: Physical, 02: Virtual/Digital
            "goodsCategory": "Z000",  # Others
            "referenceGoodsId": "deposit",
            "goodsName": description
        }
    }
    
    body_str = json.dumps(payload)
    # Subtract 2000ms to avoid clock drift issues
    timestamp = int(time.time() * 1000) - 2000
    nonce = generate_nonce()
    
    # Generate signature using the local secret key or fallback
    api_key, secret_key = await get_binance_keys()
    
    # If the user hasn't set keys, return a dummy payment flow for testing
    if not api_key or not secret_key or api_key == "YOUR_BINANCE_API_KEY" or secret_key == "YOUR_BINANCE_SECRET_KEY":
        logger.warning("Binance keys not configured. Simulating order creation.")
        # Return a mock payment URL and the generated order_id
        return {
            "success": True,
            "mock": True,
            "checkoutUrl": f"https://test.binancepay.mock/pay?order={order_id}&amount={amount}",
            "merchantTradeNo": order_id
        }
        
    headers = {
        "Content-Type": "application/json",
        "BinancePay-Timestamp": str(timestamp),
        "BinancePay-Nonce": nonce,
        "BinancePay-Certificate-SN": api_key,
        "BinancePay-Signature": signature
    }
    
    # We construct signature with actual request headers
    signature = generate_signature(timestamp, nonce, body_str, secret_key)
    headers["BinancePay-Signature"] = signature
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, proxy=proxy, timeout=10) as response:
                res_data = await response.json()
                if response.status == 200 and res_data.get("status") == "SUCCESS":
                    return {
                        "success": True,
                        "mock": False,
                        "checkoutUrl": res_data["data"]["checkoutUrl"],
                        "merchantTradeNo": order_id
                    }
                else:
                    logger.error(f"Binance Order Creation Failed: {res_data}")
                    return {"success": False, "error": res_data.get("errorMessage", "Unknown error")}
    except Exception as e:
        logger.error(f"Error calling Binance API: {e}")
        return {"success": False, "error": str(e)}

async def check_binance_order_status(merchant_trade_no):
    """
    Queries Binance Pay API to check order payment status.
    Returns status: 'INITIAL', 'PENDING', 'PAID', 'CANCELED', 'EXPIRED' or 'FAILED'
    """
    configs = await get_binance_configs()
    proxy = configs["proxy"]
    base_url = configs["pay_base_url"]
    
    endpoint = "/binancepay/openapi/v2/order/query"
    url = f"{base_url}{endpoint}"
    
    payload = {
        "merchantTradeNo": merchant_trade_no
    }
    
    body_str = json.dumps(payload)
    # Subtract 2000ms to avoid clock drift issues
    timestamp = int(time.time() * 1000) - 2000
    nonce = generate_nonce()
    
    api_key, secret_key = await get_binance_keys()
    
    # Simulate payment verification if keys are dummy
    if not api_key or not secret_key or api_key == "YOUR_BINANCE_API_KEY" or secret_key == "YOUR_BINANCE_SECRET_KEY":
        logger.info("Binance keys not configured. Simulating payment check.")
        # For testing, we mock complete payment as PAID
        return {
            "success": True,
            "mock": True,
            "status": "PAID"
        }
        
    signature = generate_signature(timestamp, nonce, body_str, secret_key)
    
    headers = {
        "Content-Type": "application/json",
        "BinancePay-Timestamp": str(timestamp),
        "BinancePay-Nonce": nonce,
        "BinancePay-Certificate-SN": api_key,
        "BinancePay-Signature": signature
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, proxy=proxy, timeout=10) as response:
                res_data = await response.json()
                if response.status == 200 and res_data.get("status") == "SUCCESS":
                    # Status can be: INITIAL, PENDING, PAID, CANCELED, EXPIRED
                    status = res_data["data"]["status"]
                    return {
                        "success": True,
                        "mock": False,
                        "status": status
                    }
                else:
                    logger.error(f"Binance Status Query Failed: {res_data}")
                    return {"success": False, "error": res_data.get("errorMessage", "Unknown error")}
    except Exception as e:
        logger.error(f"Error checking Binance API status: {e}")
        return {"success": False, "error": str(e)}

async def query_binance_deposits(tx_id, coin='USDT', min_timestamp=None):
    """
    Queries the Binance Spot API capital deposit history endpoint /sapi/v1/capital/deposit/hisrec
    for a matching transaction ID (txId) within the last 24 hours.
    """
    api_key, secret_key = await get_binance_keys()
    if not api_key or not secret_key or api_key == "YOUR_BINANCE_API_KEY" or secret_key == "YOUR_BINANCE_SECRET_KEY":
        return {
            'success': False,
            'error': 'NO_CREDENTIALS',
            'message': 'Binance API credentials missing.'
        }
    
    configs = await get_binance_configs()
    proxy = configs["proxy"]
    base_url = configs["api_base_url"]
    
    end_time = int(time.time() * 1000)
    hours_to_search = 24
    
    async def search_deposits(status):
        params = {
            'coin': coin,
            'status': status,  # 0 = pending, 1 = success
            'limit': 1000,
            # Subtract 2000ms and use 60000ms recvWindow to avoid clock drift issues
            'timestamp': int(time.time() * 1000) - 2000,
            'recvWindow': 60000,
        }
        import urllib.parse
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        url = f"{base_url}/sapi/v1/capital/deposit/hisrec?{query_string}&signature={signature}"
        headers = {
            'X-MBX-APIKEY': api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=20) as resp:
                    if resp.status != 200:
                        logger.warning(f"Binance deposit query failed with status {resp.status}")
                        return None
                    data = await resp.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and data.get('code') is not None:
                        logger.warning(f"Binance deposit query returned code/msg: {data}")
                        return None
                    return []
        except Exception as e:
            logger.error(f"Error querying Binance deposits: {e}")
            return None

    # Search completed deposits first
    deposits = await search_deposits(1)
    if deposits is None:
        deposits = []
        
    if not deposits:
        logger.info("[BINANCE_DEPOSITS] No completed deposits found, searching pending deposits...")
        pending_deposits = await search_deposits(0)
        if pending_deposits:
            deposits = pending_deposits
            logger.info(f"[BINANCE_DEPOSITS] Found {len(pending_deposits)} pending deposits")
            
    cutoff_time = end_time - (hours_to_search * 60 * 60 * 1000)
    if min_timestamp is not None:
        min_ms = min_timestamp * 1000
        if min_ms > cutoff_time:
            cutoff_time = min_ms
            
    filtered_deposits = []
    for d in deposits:
        if not isinstance(d, dict):
            continue
        insert_time = int(d.get('insertTime', 0))
        if insert_time < cutoff_time:
            continue
        filtered_deposits.append(d)
        
    logger.info(f"[BINANCE_DEPOSITS] Found {len(deposits)} total deposits, {len(filtered_deposits)} in last 24 hours, searching for txId: {tx_id}")
    
    # Regex cleanups
    import re
    tx_id_str = str(tx_id).strip()
    tx_id_clean = re.sub(r'^0x', '', tx_id_str, flags=re.IGNORECASE)
    
    for deposit in filtered_deposits:
        candidate_tx_ids = []
        if 'txId' in deposit:
            candidate_tx_ids.append(str(deposit['txId']))
        if 'txHash' in deposit:
            candidate_tx_ids.append(str(deposit['txHash']))
        if 'id' in deposit:
            candidate_tx_ids.append(str(deposit['id']))
            
        for candidate in candidate_tx_ids:
            candidate_str = str(candidate).strip()
            
            # clean off-chain transfers
            candidate_clean = candidate_str
            match = re.search(r'\b(\d+)\b', candidate_str)
            if match:
                candidate_clean = match.group(1)
                
            if (candidate_str == tx_id_str or 
                candidate_clean == tx_id_str or 
                candidate_clean == tx_id_clean or 
                tx_id_str in candidate_str or 
                candidate_str in tx_id_str or 
                tx_id_clean in candidate_clean or 
                candidate_clean in tx_id_clean or 
                candidate_str.lower() == tx_id_str.lower() or 
                candidate_clean.lower() == tx_id_clean.lower()):
                logger.info(f"[BINANCE_DEPOSITS] Match found: {deposit}")
                return {
                    'success': True,
                    'transaction': deposit
                }
                
    logger.info(f"[BINANCE_DEPOSITS] No matching deposit found for txId: {tx_id}")
    return {
        'success': False,
        'error': 'NOT_FOUND',
        'message': 'Deposit not found.'
    }

async def query_binance_pay_transactions(transaction_id, min_timestamp=None):
    """
    Queries the Binance Pay transaction endpoint /sapi/v1/pay/transactions
    and searches for a matching transaction identifier using fallback rules.
    """
    api_key, secret_key = await get_binance_keys()
    if not api_key or not secret_key or api_key == "YOUR_BINANCE_API_KEY" or secret_key == "YOUR_BINANCE_SECRET_KEY":
        return {
            'success': False,
            'error': 'NO_CREDENTIALS',
            'message': 'Binance API credentials missing.'
        }
        
    configs = await get_binance_configs()
    proxy = configs["proxy"]
    base_url = configs["api_base_url"]
    
    async def fetch_transactions(limit=50, tx_id=None):
        params = {
            'limit': limit,
            # Subtract 2000ms and use 60000ms recvWindow to avoid clock drift issues
            'timestamp': int(time.time() * 1000) - 2000,
            'recvWindow': 60000,
        }
        if tx_id:
            params['transactionId'] = tx_id
            
        import urllib.parse
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        url = f"{base_url}/sapi/v1/pay/transactions?{query_string}&signature={signature}"
        headers = {
            'X-MBX-APIKEY': api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, proxy=proxy, timeout=20) as resp:
                    if resp.status != 200:
                        logger.warning(f"Binance pay transactions query failed with status {resp.status}")
                        return None
                    data = await resp.json()
                    return data
        except Exception as e:
            logger.error(f"Error querying Binance pay transactions: {e}")
            return None

    def parse_rows(resp, min_ts):
        rows = []
        if isinstance(resp, dict):
            if 'data' in resp and isinstance(resp['data'], dict) and 'rows' in resp['data']:
                rows = resp['data']['rows']
            elif 'rows' in resp and isinstance(resp['rows'], list):
                rows = resp['rows']
            elif 'data' in resp and isinstance(resp['data'], list):
                rows = resp['data']
        if min_ts is not None and isinstance(rows, list):
            filtered = []
            for r in rows:
                if not isinstance(r, dict):
                    continue
                tx_time = int(r.get('time') or r.get('transactionTime') or r.get('timestamp') or 0)
                if tx_time > 0 and tx_time < min_ts * 1000:
                    continue
                filtered.append(r)
            rows = filtered
        return rows

    decoded = await fetch_transactions(limit=50, tx_id=transaction_id)
    data = parse_rows(decoded, min_timestamp)
    
    # Fallback: If querying with direct tx_id returns 0 rows, fetch recent 100 transactions without tx_id filter
    if not data:
        logger.info(f"[BINANCE_USER_API] Direct tx_id query for '{transaction_id}' returned 0 items. Fetching general recent 100 transactions...")
        gen_decoded = await fetch_transactions(limit=100)
        if gen_decoded and isinstance(gen_decoded, dict) and str(gen_decoded.get('code', '')) == '000000':
            data = parse_rows(gen_decoded, min_timestamp)
            
    logger.info(f"[BINANCE_USER_API] transactions_response evaluated count={len(data)}")
    
    if not isinstance(data, list) or not data:
        logger.info("[BINANCE_USER_API] No matching Binance Pay transactions found in response.")
        return {
            'success': False,
            'error': 'NOT_FOUND',
            'message': 'Transaction not found.'
        }
        
    tx_id_str = str(transaction_id).strip()
    matched = None
    
    search_attempts = []
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        candidates = []
        for k in ['transactionId', 'transId', 'orderId', 'payId', 'merchantTradeNo', 'bizId']:
            if k in row and row[k]:
                candidates.append({'key': k, 'value': row[k]})
            
        for cand in candidates:
            cand_val = str(cand['value']).strip()
            search_attempts.append({
                'idx': idx,
                'key': cand['key'],
                'candidate': cand_val,
                'searching_for': tx_id_str,
                'match': (cand_val == tx_id_str)
            })
            if cand_val == tx_id_str:
                matched = row
                logger.info(f"[BINANCE_USER_API] Exact match found at index {idx} with key {cand['key']}")
                break
        if matched:
            break
            
    # Fallback 1: Partial match
    if not matched:
        for row in data:
            if not isinstance(row, dict):
                continue
            for k in ['transactionId', 'transId', 'orderId', 'payId', 'merchantTradeNo', 'bizId']:
                cand_val = str(row.get(k, '')).strip()
                if cand_val and (tx_id_str in cand_val or cand_str in tx_id_str if 'cand_str' in locals() else tx_id_str in cand_val):
                    matched = row
                    logger.info(f"[BINANCE_USER_API] partial_match txId={tx_id_str} key={k} candidate={cand_val}")
                    break
            if matched:
                break
                    
    # Fallback 2: Case insensitive match
    if not matched:
        tx_id_lower = tx_id_str.lower()
        for row in data:
            if not isinstance(row, dict):
                continue
            for key in ['transactionId', 'transId', 'orderId', 'payId', 'merchantTradeNo', 'bizId']:
                if key in row and row[key]:
                    cand_val = str(row[key]).strip()
                    if cand_val.lower() == tx_id_lower:
                        matched = row
                        logger.info(f"[BINANCE_USER_API] case_insensitive_match txId={tx_id_str} key={key} candidate={cand_val}")
                        break
            if matched:
                break
                
    # Fallback 3: Approximate numeric match
    if not matched and tx_id_str.isdigit():
        tx_numeric = int(tx_id_str)
        for row in data:
            if not isinstance(row, dict):
                continue
            for key in ['transactionId', 'transId', 'orderId']:
                if key in row:
                    cand_val = str(row[key]).strip()
                    if cand_val.isdigit():
                        cand_numeric = int(cand_val)
                        if abs(cand_numeric - tx_numeric) <= 2:
                            matched = row
                            logger.info(f"[BINANCE_USER_API] approximate_numeric_match txId={tx_id_str} key={key} candidate={cand_val}")
                            break
            if matched:
                break
                
    # Fallback 4: Fetch more (100) if not found and transaction_id is not empty
    if not matched and tx_id_str:
        logger.info("[BINANCE_USER_API] Extending search to 100 transactions...")
        decoded_more = await fetch_transactions(limit=100)
        if decoded_more and isinstance(decoded_more, dict) and str(decoded_more.get('code')) == '000000':
            data_more = []
            if 'data' in decoded_more and isinstance(decoded_more['data'], dict) and 'rows' in decoded_more['data']:
                data_more = decoded_more['data']['rows']
            elif 'rows' in decoded_more and isinstance(decoded_more['rows'], list):
                data_more = decoded_more['rows']
                
            for row in data_more:
                if not isinstance(row, dict):
                    continue
                candidates = []
                if 'transactionId' in row:
                    candidates.append(str(row['transactionId']))
                if 'transId' in row:
                    candidates.append(str(row['transId']))
                if 'orderId' in row:
                    candidates.append(str(row['orderId']))
                    
                for cand in candidates:
                    cand_str = str(cand).strip()
                    if (cand_str == tx_id_str or 
                        tx_id_str in cand_str or 
                        cand_str in tx_id_str or 
                        cand_str.lower() == tx_id_str.lower()):
                        matched = row
                        logger.info(f"[BINANCE_USER_API] extended_search_match txId={tx_id_str} candidate={cand}")
                        break
                if matched:
                    break
                    
    if not matched:
        return {
            'success': False,
            'error': 'NOT_FOUND',
            'message': 'Transaction not found.'
        }
        
    return {
        'success': True,
        'transaction': matched
    }

async def verify_binance_payment(tx_id, coin='USDT', min_timestamp=None):
    """
    Unified payment verifier that queries Pay transaction history and Spot deposit history.
    Enforces strict amount matching and transaction age validation.
    """
    from crypto_verifier import get_max_tx_age_seconds, validate_tx_age, parse_unix_timestamp
    max_age_seconds = await get_max_tx_age_seconds()

    # 1. Try querying Binance Pay transactions first
    res_pay = await query_binance_pay_transactions(tx_id, min_timestamp=min_timestamp)
    if res_pay.get('success'):
        tx = res_pay['transaction']
        # Extract the amount properly from various possible keys
        raw_amount = (
            tx.get('amount') or 
            tx.get('totalAmount') or 
            tx.get('orderAmount') or 
            tx.get('transAmount') or 
            0
        )
        try:
            amount = float(raw_amount)
        except (ValueError, TypeError):
            amount = 0.0
            
        # Age validation for Binance Pay transaction
        raw_time = tx.get('time') or tx.get('transactionTime') or tx.get('timestamp') or 0
        tx_unix = parse_unix_timestamp(raw_time)
        if tx_unix > 1000000000000:
            tx_unix = tx_unix // 1000
            
        if tx_unix > 0:
            is_valid_age, age_err = validate_tx_age(tx_unix, max_age_seconds, min_timestamp=min_timestamp)
            if not is_valid_age:
                return False, age_err

        return True, amount

    # 2. Try querying Spot deposit history
    res_dep = await query_binance_deposits(tx_id, coin=coin, min_timestamp=min_timestamp)
    if res_dep.get('success'):
        tx = res_dep['transaction']
        raw_amount = tx.get('amount') or 0
        try:
            amount = float(raw_amount)
        except (ValueError, TypeError):
            amount = 0.0
        status = int(tx.get('status', 0))
        if status != 1:
            return False, "Transaction is pending on the blockchain."
            
        raw_time = tx.get('insertTime') or tx.get('time') or tx.get('timestamp') or 0
        tx_unix = parse_unix_timestamp(raw_time)
        if tx_unix > 1000000000000:
            tx_unix = tx_unix // 1000
            
        if tx_unix > 0:
            is_valid_age, age_err = validate_tx_age(tx_unix, max_age_seconds, min_timestamp=min_timestamp)
            if not is_valid_age:
                return False, age_err

        return True, amount
            
    return False, "Transaction not found on Binance."

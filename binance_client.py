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

async def get_binance_configs():
    import os
    # Default values from environment or defaults
    default_proxy = os.getenv("BINANCE_API_PROXY", "")
    default_api_url = os.getenv("BINANCE_API_BASE_URL", "https://api.binance.com")
    default_pay_url = os.getenv("BINANCE_PAY_API_BASE_URL", "https://bpay.binanceapi.com")
    
    proxy = default_proxy
    api_url = default_api_url
    pay_url = default_pay_url
    
    try:
        from database import get_setting
        db_proxy = await get_setting("binance_api_proxy", "")
        if db_proxy:
            proxy = db_proxy
            
        db_api_url = await get_setting("binance_api_base_url", "")
        if db_api_url:
            api_url = db_api_url
            
        db_pay_url = await get_setting("binance_pay_base_url", "")
        if db_pay_url:
            pay_url = db_pay_url
    except Exception as e:
        logger.error(f"Error loading Binance configurations from database: {e}")
        
    return {
        "proxy": proxy if proxy else None,
        "api_base_url": api_url.rstrip("/"),
        "pay_base_url": pay_url.rstrip("/")
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
    api_key = BINANCE_API_KEY
    secret_key = BINANCE_SECRET_KEY
    
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
    
    api_key = BINANCE_API_KEY
    secret_key = BINANCE_SECRET_KEY
    
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
    api_key = BINANCE_API_KEY
    secret_key = BINANCE_SECRET_KEY
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
    api_key = BINANCE_API_KEY
    secret_key = BINANCE_SECRET_KEY
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

    decoded = await fetch_transactions(limit=50, tx_id=transaction_id)
    if decoded is None:
        return {
            'success': False,
            'error': 'API_ERROR',
            'message': 'Unable to fetch Binance Pay transactions.'
        }
        
    if isinstance(decoded, dict) and decoded.get('success') is False:
        return {
            'success': False,
            'error': decoded.get('code', 'API_ERROR'),
            'message': decoded.get('msg', 'Binance API error.')
        }
        
    if isinstance(decoded, dict) and decoded.get('code') is not None and str(decoded.get('code')) != '000000':
        return {
            'success': False,
            'error': decoded.get('code'),
            'message': decoded.get('message') or decoded.get('msg') or 'Binance API error.'
        }
        
    # extract rows
    data = []
    if isinstance(decoded, dict):
        if 'data' in decoded and isinstance(decoded['data'], dict) and 'rows' in decoded['data']:
            data = decoded['data']['rows']
        elif 'rows' in decoded and isinstance(decoded['rows'], list):
            data = decoded['rows']
        elif 'data' in decoded and isinstance(decoded['data'], list):
            data = decoded['data']
            
    # Filter rows by min_timestamp if provided to prevent TxID reuse fraud
    if min_timestamp is not None and isinstance(data, list):
        filtered_data = []
        for row in data:
            if not isinstance(row, dict):
                continue
            tx_time_ms = int(row.get('time') or row.get('transactionTime') or row.get('timestamp') or 0)
            if tx_time_ms > 0 and tx_time_ms < min_timestamp * 1000:
                continue
            filtered_data.append(row)
        data = filtered_data
            
    logger.info(f"[BINANCE_USER_API] transactions_response code={decoded.get('code')} count={len(data)}")
    
    if not isinstance(data, list) or not data:
        logger.info("[BINANCE_USER_API] No transactions found in response")
        return {
            'success': False,
            'error': 'NOT_FOUND',
            'message': 'Transaction not found.'
        }
        
    tx_id_str = str(transaction_id).strip()
    
    matched = None
    
    # search attempts tracking
    search_attempts = []
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        candidates = []
        if 'transactionId' in row:
            candidates.append({'key': 'transactionId', 'value': row['transactionId']})
        if 'transId' in row:
            candidates.append({'key': 'transId', 'value': row['transId']})
        if 'orderId' in row:
            candidates.append({'key': 'orderId', 'value': row['orderId']})
            
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
            candidate = row.get('transactionId') or row.get('transId')
            if candidate is not None:
                cand_str = str(candidate).strip()
                if tx_id_str in cand_str or cand_str in tx_id_str:
                    matched = row
                    logger.info(f"[BINANCE_USER_API] partial_match txId={tx_id_str} candidate={candidate}")
                    break
                    
    # Fallback 2: Case insensitive match
    if not matched:
        tx_id_lower = tx_id_str.lower()
        for row in data:
            if not isinstance(row, dict):
                continue
            for key in ['transactionId', 'transId', 'orderId']:
                if key in row:
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
    """
    # 1. Try querying Binance Pay transactions first
    res_pay = await query_binance_pay_transactions(tx_id, min_timestamp=min_timestamp)
    if res_pay.get('success'):
        tx = res_pay['transaction']
        amount = float(tx.get('amount') or tx.get('totalAmount') or 0)
        # Verify status is successful if present
        # Status "P" or similar is sometimes returned, but if we found it under transactions, it's credited.
        return True, amount

    # 2. Try querying Spot deposit history
    res_dep = await query_binance_deposits(tx_id, coin=coin, min_timestamp=min_timestamp)
    if res_dep.get('success'):
        tx = res_dep['transaction']
        amount = float(tx.get('amount') or 0)
        status = int(tx.get('status', 0))
        if status == 1:
            return True, amount
        else:
            return False, "Transaction is pending on the blockchain."
            
    return False, "Transaction not found on Binance."

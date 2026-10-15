import aiohttp
import logging
from database import get_setting

logger = logging.getLogger(__name__)

async def get_xrocket_config():
    """
    Retrieves xRocket API token and base URL from database settings.
    Supports both Production and Testnet environments.
    """
    api_key = await get_setting('xrocket_token', '')
    use_testnet = (await get_setting('xrocket_use_testnet', '0')) == '1'
    if use_testnet:
        base_url = "https://pay.api.testnet.xrocket.exchange"
    else:
        base_url = "https://pay.api.xrocket.exchange"
    return api_key.strip(), base_url

def _get_headers(api_key: str):
    """
    Provides headers compatible with both Pay API (Bearer) and Legacy API (Rocket-Pay-Key).
    """
    clean_token = api_key.replace("Bearer ", "").strip()
    return {
        "Authorization": f"Bearer {clean_token}",
        "Rocket-Pay-Key": clean_token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

async def create_xrocket_invoice(amount: float, client_invoice_id: str, description: str = "", currency: str = "USDT"):
    """
    Creates an xRocket crypto invoice.
    Returns a dict with 'invoice_id', 'pay_url', and 'status', or None on failure.
    """
    api_key, base_url = await get_xrocket_config()
    if not api_key:
        logger.error("xrocket_token is not configured in settings!")
        return None

    headers = _get_headers(api_key)
    
    # Payload for Pay API
    payload = {
        "amount": round(float(amount), 2),
        "currency": currency.upper(),
        "description": (description[:1024] if description else "Digital Store Deposit"),
        "clientInvoiceId": str(client_invoice_id)[:64],
        "expiredIn": 3600  # 1 hour expiration
    }

    # Primary and fallback endpoints
    endpoints = [
        f"{base_url}/api/v1/invoices",
        f"https://pay.xrocket.tg/tg-invoices",
        f"https://pay.xrocket.tg/invoices"
    ]

    try:
        async with aiohttp.ClientSession() as session:
            for url in endpoints:
                try:
                    async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        res_json = await resp.json(content_type=None)
                        if resp.status in [200, 201]:
                            data = res_json.get("data") if isinstance(res_json.get("data"), dict) else res_json
                            # Extract invoice id
                            invoice_id = (
                                data.get("invoiceId") or 
                                data.get("id") or 
                                data.get("invoice_id")
                            )
                            # Extract payment link / telegram URL
                            pay_url = (
                                data.get("link") or 
                                data.get("url") or 
                                data.get("payUrl") or 
                                data.get("botInvoiceUrl") or
                                (f"https://t.me/xrocket?start=inv_{invoice_id}" if invoice_id else None)
                            )
                            
                            if invoice_id and pay_url:
                                return {
                                    "invoice_id": invoice_id,
                                    "pay_url": pay_url,
                                    "status": data.get("status", "active"),
                                    "amount": amount,
                                    "currency": currency.upper()
                                }
                        logger.warning(f"xRocket createInvoice endpoint {url} returned HTTP {resp.status}: {res_json}")
                except Exception as ep_err:
                    logger.debug(f"xRocket probe {url} failed: {ep_err}")
    except Exception as e:
        logger.error(f"xRocket createInvoice exception: {e}")
    return None

async def get_xrocket_invoice(invoice_id: Any):
    """
    Fetches the current status and details of an xRocket invoice.
    Returns a dict with 'status' (e.g. 'paid', 'active', 'expired') or None.
    """
    api_key, base_url = await get_xrocket_config()
    if not api_key:
        logger.error("xrocket_token is not configured in settings!")
        return None

    headers = _get_headers(api_key)
    inv_str = str(invoice_id).strip()

    endpoints = [
        f"{base_url}/api/v1/invoice?invoiceId={inv_str}",
        f"{base_url}/api/v1/invoices/{inv_str}",
        f"https://pay.xrocket.tg/tg-invoices/{inv_str}",
        f"https://pay.xrocket.tg/invoices/{inv_str}"
    ]

    try:
        async with aiohttp.ClientSession() as session:
            for url in endpoints:
                try:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            res_json = await resp.json(content_type=None)
                            data = res_json.get("data") if isinstance(res_json.get("data"), dict) else res_json
                            if isinstance(data, dict):
                                status_raw = str(data.get("status", "")).lower()
                                return {
                                    "status": status_raw,
                                    "invoice_id": data.get("invoiceId") or data.get("id") or inv_str,
                                    "amount": data.get("amount"),
                                    "currency": data.get("currency") or data.get("asset"),
                                    "raw": data
                                }
                except Exception as ep_err:
                    logger.debug(f"xRocket getInvoice probe {url} failed: {ep_err}")
    except Exception as e:
        logger.error(f"xRocket getInvoice exception: {e}")
    return None

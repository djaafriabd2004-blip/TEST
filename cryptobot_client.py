import aiohttp
import logging
from database import get_setting

logger = logging.getLogger(__name__)

async def get_cryptobot_config():
    api_key = await get_setting('cryptobot_token', '')
    use_testnet = (await get_setting('cryptobot_use_testnet', '0')) == '1'
    if use_testnet:
        base_url = "https://testnet-pay.crypt.bot/api/"
    else:
        base_url = "https://pay.crypt.bot/api/"
    return api_key, base_url

async def create_cryptobot_invoice(amount: float, payload: str, description: str = ""):
    api_key, base_url = await get_cryptobot_config()
    if not api_key:
        logger.error("cryptobot_token is not configured in settings!")
        return None
        
    url = base_url + "createInvoice"
    headers = {
        "Crypto-Pay-API-Token": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "amount": f"{amount:.2f}",
        "currency_type": "fiat",
        "fiat": "USD",
        "payload": payload
    }
    if description:
        data["description"] = description[:1024]
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    if res_json.get("ok"):
                        return res_json.get("result")
                    else:
                        logger.error(f"CryptoBot createInvoice API error: {res_json}")
                else:
                    logger.error(f"CryptoBot createInvoice http error: {resp.status} - {await resp.text()}")
    except Exception as e:
        logger.error(f"CryptoBot createInvoice exception: {e}")
    return None

async def get_cryptobot_invoice(invoice_id: int):
    api_key, base_url = await get_cryptobot_config()
    if not api_key:
        logger.error("cryptobot_token is not configured in settings!")
        return None
        
    url = base_url + "getInvoices"
    headers = {
        "Crypto-Pay-API-Token": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "invoice_ids": str(invoice_id)
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    if res_json.get("ok"):
                        items = res_json.get("result", {}).get("items", [])
                        if items:
                            return items[0]
                    else:
                        logger.error(f"CryptoBot getInvoices API error: {res_json}")
                else:
                    logger.error(f"CryptoBot getInvoices http error: {resp.status} - {await resp.text()}")
    except Exception as e:
        logger.error(f"CryptoBot getInvoices exception: {e}")
    return None

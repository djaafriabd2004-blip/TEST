import logging
import asyncio
import aiohttp
import uuid
import time
from typing import List, Dict, Any, Optional

from utils import (
    normalize_provider_url,
    extract_stock_from_dict,
    extract_products_list_from_json,
    matches_product_id
)

logger = logging.getLogger(__name__)


class BaseProviderAdapter:
    """
    Abstract base class defining standardized methods for all API providers.
    """
    def __init__(self, base_url: str, api_key: str):
        self.raw_base_url = base_url.strip()
        self.base_url = normalize_provider_url(base_url)
        self.api_key = api_key.strip()
        self.provider_type = "generic"

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        """
        Fetches full catalog from provider and returns a list of standardized dicts:
        [{ "id": str/int, "name": str, "name_ar": str, "name_en": str, "name_ru": str,
           "description": str, "price": float, "stock": int, "custom_emoji_id": str }]
        """
        endpoints = [
            f"{self.base_url}/api/v1/products",
            f"{self.base_url}/v1/products",
            f"{self.base_url}/api/products",
            f"{self.base_url}/products"
        ]
        
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw_list = extract_products_list_from_json(data)
                            if raw_list:
                                return self._standardize_catalog(raw_list)
                except Exception as e:
                    logger.debug(f"Catalog probe {url} failed: {e}")
            return []

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_stock(self, provider_product_id: Any, session: Optional[aiohttp.ClientSession] = None) -> Optional[int]:
        """
        Fetches live stock count for a single product from provider API.
        """
        prov_pid = str(provider_product_id).strip()
        endpoints = [
            f"{self.base_url}/api/v1/products/{prov_pid}",
            f"{self.base_url}/v1/products/{prov_pid}",
            f"{self.base_url}/api/products/{prov_pid}",
            f"{self.base_url}/products/{prov_pid}"
        ]

        async def _req(s):
            fallback_stock = None
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=4)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, dict):
                                single_p = data.get('product') or data.get('data') or data
                                if matches_product_id(single_p, prov_pid) or ('stock' in single_p or 'quantity' in single_p or 'inStock' in single_p):
                                    num_s = extract_stock_from_dict(single_p, allow_boolean=False)
                                    if num_s is not None:
                                        return num_s
                                    if fallback_stock is None:
                                        fallback_stock = extract_stock_from_dict(single_p, allow_boolean=True)
                            
                            raw_list = extract_products_list_from_json(data)
                            for p in raw_list:
                                if matches_product_id(p, prov_pid):
                                    num_s = extract_stock_from_dict(p, allow_boolean=False)
                                    if num_s is not None:
                                        return num_s
                                    if fallback_stock is None:
                                        fallback_stock = extract_stock_from_dict(p, allow_boolean=True)
                except Exception:
                    pass
            if fallback_stock is not None:
                return fallback_stock
            
            # Fallback: fetch full catalog and search
            catalog = await self.fetch_catalog(s)
            for p in catalog:
                if matches_product_id(p, prov_pid):
                    return int(p.get('stock', 0))
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def execute_order(
        self,
        provider_product_id: Any,
        quantity: int,
        expected_price: Optional[float] = None,
        client_order_ref: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[str]:
        """
        Executes order and returns delivered keys/items as list of strings.
        Raises Exception if order failed or provider returned error.
        """
        prov_pid = str(provider_product_id).strip()
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "productId": prov_pid,
            "product_id": prov_pid,
            "quantity": quantity,
            "external_order_id": order_ref,
            "client_order_reference": order_ref
        }
        
        endpoints = [
            f"{self.base_url}/api/v1/orders",
            f"{self.base_url}/api/buy",
            f"{self.base_url}/v1/orders",
            f"{self.base_url}/api/purchase"
        ]

        async def _req(s):
            last_err = "No response from provider"
            headers = self.get_headers({"Idempotency-Key": order_ref})
            
            for ep in endpoints:
                try:
                    logger.info(f"Executing provider order on {ep} with payload: {payload}")
                    async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                        if resp.status in [200, 201]:
                            try:
                                buy_data = await resp.json()
                            except Exception:
                                raw_txt = await resp.text()
                                buy_data = {"credentials": raw_txt}
                            return self._parse_delivery_data(buy_data, order_ref)
                        else:
                            last_err = await self._parse_error_response(resp)
                            logger.warning(f"Provider {ep} returned status {resp.status}: {last_err}")
                            break
                except Exception as ep_err:
                    logger.warning(f"Provider request error on {ep}: {ep_err}")
                    last_err = str(ep_err)
            
            if "$slice" in str(last_err) or "must be positive: 0" in str(last_err) or "no items in stock" in str(last_err).lower():
                last_err = "Out of stock (Product depleted at provider)"
                raise Exception(f"Out of stock ({last_err})")
            raise Exception(f"Provider error: {last_err}")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_balance(self, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
        return None

    def _standardize_catalog(self, raw_list: List[Any]) -> List[Dict[str, Any]]:
        formatted = []
        for p in raw_list:
            if not isinstance(p, dict):
                continue
            p_id = p.get("id") or p.get("product_id") or p.get("productId") or p.get("item_id") or p.get("service") or p.get("code")
            if p_id is None:
                continue
            
            p_name = (
                p.get("name") or p.get("title") or p.get("name_en") or p.get("name_ar") or
                p.get("service_name") or p.get("item_name") or f"Product {p_id}"
            )
            name_ar = p.get("name_ar") or p_name
            name_en = p.get("name_en") or p_name
            name_ru = p.get("name_ru") or p_name
            desc_ar = p.get("description_ar") or p.get("description") or f"Imported Product: {p_name}"
            desc_en = p.get("description_en") or p.get("description") or f"Imported Product: {p_name}"
            desc_ru = p.get("description_ru") or p.get("description") or f"Imported Product: {p_name}"
            
            try:
                price_val = float(p.get("price") or p.get("unit_price") or p.get("price_usd") or p.get("rate") or 0.0)
            except Exception:
                price_val = 0.0
                
            stock_val = extract_stock_from_dict(p, allow_boolean=False)
            if stock_val is None:
                stock_val = extract_stock_from_dict(p, allow_boolean=True) or 0
                
            formatted.append({
                "id": str(p_id),
                "name": p_name,
                "name_ar": name_ar,
                "name_en": name_en,
                "name_ru": name_ru,
                "description": desc_en,
                "description_ar": desc_ar,
                "description_en": desc_en,
                "description_ru": desc_ru,
                "price": price_val,
                "stock": stock_val,
                "custom_emoji_id": p.get("custom_emoji_id")
            })
        return formatted

    def _parse_delivery_data(self, buy_data: Dict[str, Any], ext_order_id: str) -> List[str]:
        if not isinstance(buy_data, dict):
            return [str(buy_data)]
            
        deliv = buy_data.get('delivery')
        if isinstance(deliv, dict) and deliv.get('items'):
            raw_creds = deliv['items']
        elif isinstance(deliv, list):
            raw_creds = deliv
        else:
            raw_creds = (
                buy_data.get('deliveredKeys') if buy_data.get('deliveredKeys') is not None
                else (buy_data.get('deliveredKey') if buy_data.get('deliveredKey') is not None
                else (buy_data.get('credentials') if buy_data.get('credentials') is not None
                else (buy_data.get('data') if buy_data.get('data') is not None
                else buy_data.get('items'))))
            )

        if raw_creds is not None:
            if isinstance(raw_creds, str):
                if "\n" in raw_creds:
                    return [item.strip() for item in raw_creds.split("\n") if item.strip()]
                elif "," in raw_creds:
                    return [item.strip() for item in raw_creds.split(",") if item.strip()]
                else:
                    return [raw_creds.strip()]
            elif isinstance(raw_creds, list):
                return [str(it['code']) if isinstance(it, dict) and 'code' in it else str(it) for it in raw_creds]
            else:
                return [str(raw_creds)]
        elif buy_data.get('success') or buy_data.get('ok') or buy_data.get('status') in ['completed', 'delivered']:
            ord_id = buy_data.get('order_id') or buy_data.get('id') or ext_order_id
            return [f"Order #{ord_id} Completed Successfully"]
            
        raise Exception("Provider returned empty delivery data")

    async def _parse_error_response(self, resp: aiohttp.ClientResponse) -> str:
        try:
            err_json = await resp.json()
            last_err = (
                err_json.get('error') or err_json.get('errorMessage') or
                err_json.get('message') or err_json.get('detail') or f"HTTP {resp.status}"
            )
            if isinstance(last_err, dict):
                last_err = last_err.get('message') or last_err.get('code') or str(last_err)
            return str(last_err)
        except Exception:
            err_txt = await resp.text()
            if "<!DOCTYPE html>" in err_txt or "<html" in err_txt or "Cannot POST" in err_txt:
                return f"Provider service error (HTTP {resp.status})"
            return err_txt[:200] if err_txt else f"HTTP {resp.status}"


# -------------------------------------------------------------------------
# 1. Pandora Digital Adapter (https://api.pandoradigital.shop)
# -------------------------------------------------------------------------
class PandoraProviderAdapter(BaseProviderAdapter):
    def __init__(self, base_url: str, api_key: str):
        super().__init__(base_url, api_key)
        self.provider_type = "pandora"

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/api/v1/products",
            f"{self.base_url}/v1/products"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw_list = extract_products_list_from_json(data)
                            if raw_list:
                                return self._standardize_catalog(raw_list)
                except Exception as e:
                    logger.debug(f"Pandora catalog probe {url} failed: {e}")
            return []

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def execute_order(
        self,
        provider_product_id: Any,
        quantity: int,
        expected_price: Optional[float] = None,
        client_order_ref: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        headers = self.get_headers({"Idempotency-Key": order_ref})

        async def _req(s):
            # Step 1: Quote
            unit_price = expected_price
            price_version = None
            try:
                async with s.post(
                    f"{self.base_url}/api/v1/quotes",
                    headers=headers,
                    json={"product_id": prov_pid, "quantity": int(quantity)},
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as q_resp:
                    if q_resp.status in [200, 201]:
                        q_data = await q_resp.json()
                        if isinstance(q_data, dict):
                            unit_price = q_data.get("unit_price")
                            price_version = q_data.get("price_version")
            except Exception as q_err:
                logger.warning(f"Pandora quote error: {q_err}")

            if not unit_price:
                try:
                    async with s.get(f"{self.base_url}/api/v1/products/{prov_pid}", headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as p_resp:
                        if p_resp.status == 200:
                            p_data = await p_resp.json()
                            if isinstance(p_data, dict):
                                unit_price = p_data.get("unit_price")
                except Exception:
                    pass

            buy_payload = {
                "product_id": prov_pid,
                "quantity": int(quantity),
                "expected_unit_price": str(unit_price) if unit_price is not None else "1.00"
            }
            if price_version:
                buy_payload["price_version"] = str(price_version)
            if order_ref:
                buy_payload["client_order_reference"] = order_ref[:100]

            logger.info(f"Executing Pandora order on {self.base_url}/api/v1/orders with payload: {buy_payload}")
            async with s.post(f"{self.base_url}/api/v1/orders", headers=headers, json=buy_payload, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                if resp.status in [200, 201]:
                    buy_data = await resp.json()
                    # Handle async processing
                    if buy_data.get('status') in ['processing', 'pending']:
                        ord_id = buy_data.get('order_id') or buy_data.get('id')
                        if ord_id:
                            for _ in range(4):
                                await asyncio.sleep(2)
                                try:
                                    async with s.get(f"{self.base_url}/api/v1/orders/{ord_id}", headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as o_resp:
                                        if o_resp.status == 200:
                                            o_data = await o_resp.json()
                                            if o_data.get('delivery') or o_data.get('deliveredKeys'):
                                                buy_data = o_data
                                                break
                                except Exception:
                                    pass
                    return self._parse_delivery_data(buy_data, order_ref)
                else:
                    last_err = await self._parse_error_response(resp)
                    raise Exception(f"Provider error: {last_err}")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 2. Aethel Seller API Adapter (https://mail-api.hvmforum.space/api)
# -------------------------------------------------------------------------
class AethelProviderAdapter(BaseProviderAdapter):
    """
    Aethel Seller API Adapter (https://mail-api.hvmforum.space/api/docs)
    Catalog: GET /v1/catalog
    Balance: GET /v1/balance
    Purchase: POST /v1/purchases {"item_id": 2, "quantity": 1} with Idempotency-Key
    """
    def __init__(self, base_url: str, api_key: str):
        super().__init__(base_url, api_key)
        self.provider_type = "aethel"

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/v1/catalog",
            f"{self.base_url}/api/v1/catalog",
            f"{self.base_url}/catalog"
        ]
        
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw_list = extract_products_list_from_json(data)
                            if raw_list:
                                return self._standardize_catalog(raw_list)
                except Exception as e:
                    logger.debug(f"Aethel catalog probe {url} failed: {e}")
            return []

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_balance(self, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/v1/balance",
            f"{self.base_url}/api/v1/balance"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            return await resp.json()
                except Exception:
                    pass
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def execute_order(
        self,
        provider_product_id: Any,
        quantity: int,
        expected_price: Optional[float] = None,
        client_order_ref: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        item_id = int(prov_pid) if prov_pid.isdigit() else prov_pid
        order_ref = client_order_ref or str(uuid.uuid4())
        
        headers = self.get_headers({
            "Idempotency-Key": str(order_ref)
        })
        payload = {
            "item_id": item_id,
            "quantity": int(quantity)
        }
        
        endpoints = [
            f"{self.base_url}/v1/purchases",
            f"{self.base_url}/api/v1/purchases"
        ]

        async def _req(s):
            last_err = "No response from Aethel API"
            for ep in endpoints:
                try:
                    logger.info(f"Executing Aethel order on {ep} with payload: {payload}")
                    async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                        if resp.status in [200, 201]:
                            buy_data = await resp.json()
                            return self._parse_delivery_data(buy_data, order_ref)
                        else:
                            last_err = await self._parse_error_response(resp)
                            if resp.status == 409 or "insufficient" in str(last_err).lower() or "stock" in str(last_err).lower():
                                raise Exception(f"Out of stock ({last_err})")
                            elif resp.status == 402:
                                raise Exception(f"Provider balance insufficient: {last_err}")
                            break
                except Exception as ep_err:
                    if "Out of stock" in str(ep_err):
                        raise ep_err
                    logger.warning(f"Aethel purchase error on {ep}: {ep_err}")
                    last_err = str(ep_err)
                    
            raise Exception(f"Provider error: {last_err}")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 3. ProdSeller Adapter (https://prodseller.com)
# -------------------------------------------------------------------------
class ProdSellerProviderAdapter(BaseProviderAdapter):
    def __init__(self, base_url: str, api_key: str):
        super().__init__(base_url, api_key)
        self.provider_type = "prodseller"

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/v1/products",
            f"{self.base_url}/api/products",
            f"{self.base_url}/products"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw_list = extract_products_list_from_json(data)
                            if raw_list:
                                return self._standardize_catalog(raw_list)
                except Exception:
                    pass
            return []

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def execute_order(
        self,
        provider_product_id: Any,
        quantity: int,
        expected_price: Optional[float] = None,
        client_order_ref: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        payload = {
            "productId": prov_pid,
            "product_id": prov_pid,
            "quantity": int(quantity),
            "external_order_id": order_ref,
            "client_order_reference": order_ref
        }
        headers = self.get_headers({"Idempotency-Key": order_ref})

        async def _req(s):
            ep = f"{self.base_url}/v1/orders"
            logger.info(f"Executing ProdSeller order on {ep} with payload: {payload}")
            async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                if resp.status in [200, 201]:
                    buy_data = await resp.json()
                    return self._parse_delivery_data(buy_data, order_ref)
                else:
                    last_err = await self._parse_error_response(resp)
                    if "$slice" in str(last_err) or "must be positive: 0" in str(last_err) or "no items in stock" in str(last_err).lower():
                        raise Exception(f"Out of stock (Product depleted at provider)")
                    raise Exception(f"Provider error: {last_err}")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 4. ShopDigital Adapter (https://shopdigital...)
# -------------------------------------------------------------------------
class ShopDigitalProviderAdapter(BaseProviderAdapter):
    def __init__(self, base_url: str, api_key: str):
        super().__init__(base_url, api_key)
        self.provider_type = "shopdigital"

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/api/products",
            f"{self.base_url}/products"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw_list = extract_products_list_from_json(data)
                            if raw_list:
                                return self._standardize_catalog(raw_list)
                except Exception:
                    pass
            return []

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def execute_order(
        self,
        provider_product_id: Any,
        quantity: int,
        expected_price: Optional[float] = None,
        client_order_ref: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        headers = self.get_headers({"Idempotency-Key": order_ref})
        ep = f"{self.base_url}/api/purchase"

        async def _req(s):
            collected_items = []
            for _ in range(int(quantity)):
                payload = {
                    "product_id": prov_pid,
                    "quantity": 1,
                    "external_order_id": f"{order_ref}_{len(collected_items)}"
                }
                async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status in [200, 201]:
                        buy_data = await resp.json()
                        delivered = self._parse_delivery_data(buy_data, order_ref)
                        collected_items.extend(delivered)
                    else:
                        last_err = await self._parse_error_response(resp)
                        if not collected_items:
                            raise Exception(f"Provider error: {last_err}")
                        break
            if not collected_items:
                raise Exception("Provider returned empty delivery data")
            return collected_items

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 5. Supabase Adapter (https://*.supabase.co)
# -------------------------------------------------------------------------
class SupabaseProviderAdapter(BaseProviderAdapter):
    def __init__(self, base_url: str, api_key: str):
        super().__init__(base_url, api_key)
        self.provider_type = "supabase"

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        url = f"{self.base_url}?action=products"
        async def _req(s):
            try:
                async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw_list = extract_products_list_from_json(data)
                        if raw_list:
                            return self._standardize_catalog(raw_list)
            except Exception as e:
                logger.warning(f"Supabase catalog error: {e}")
            return []

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def execute_order(
        self,
        provider_product_id: Any,
        quantity: int,
        expected_price: Optional[float] = None,
        client_order_ref: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        payload = {
            "productId": prov_pid,
            "product_id": prov_pid,
            "quantity": int(quantity),
            "external_order_id": order_ref
        }
        url = f"{self.base_url}?action=order"

        async def _req(s):
            async with s.post(url, headers=self.get_headers(), json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status in [200, 201]:
                    buy_data = await resp.json()
                    return self._parse_delivery_data(buy_data, order_ref)
                else:
                    last_err = await self._parse_error_response(resp)
                    raise Exception(f"Provider error: {last_err}")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# Provider Factory Function
# -------------------------------------------------------------------------
def get_provider_adapter(base_url: str, api_key: str) -> BaseProviderAdapter:
    """
    Factory function: Returns the specialized provider adapter based on base_url.
    """
    clean_url = str(base_url).lower().strip()
    
    if "pandoradigital" in clean_url:
        return PandoraProviderAdapter(base_url, api_key)
    elif "hvmforum" in clean_url or "aethel" in clean_url or "mail-api" in clean_url:
        return AethelProviderAdapter(base_url, api_key)
    elif "prodseller" in clean_url:
        return ProdSellerProviderAdapter(base_url, api_key)
    elif "shopdigital" in clean_url:
        return ShopDigitalProviderAdapter(base_url, api_key)
    elif "supabase.co" in clean_url:
        return SupabaseProviderAdapter(base_url, api_key)
    else:
        return BaseProviderAdapter(base_url, api_key)

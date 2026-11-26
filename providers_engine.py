import logging
import asyncio
import aiohttp
import uuid
import time
import json
from typing import List, Dict, Any, Optional, Tuple

from utils import (
    normalize_provider_url,
    extract_stock_from_dict,
    extract_price_from_dict,
    extract_products_list_from_json,
    matches_product_id
)

logger = logging.getLogger(__name__)

_PROVIDER_QUOTE_ENDPOINT_CACHE: Dict[str, Tuple[Optional[str], float]] = {}  # {base_url: (working_quote_url_or_None, ts)}
_QUOTE_CACHE_TTL = 600.0


def parse_customer_emails(customer_email: Optional[Any]) -> List[str]:
    """Normalize customer_email (list/tuple or comma/newline-separated string) into clean stripped entries."""
    if not customer_email:
        return []
    raw_items: List[str] = []
    if isinstance(customer_email, (list, tuple)):
        for entry in customer_email:
            raw_items.extend(str(entry).replace(',', '\n').split('\n'))
    else:
        raw_items.extend(str(customer_email).replace(',', '\n').split('\n'))
    return [e.strip() for e in raw_items if e and e.strip()]


class BaseProviderAdapter:
    """
    Abstract base class defining standardized methods for all API providers.
    """
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        self.raw_base_url = base_url.strip()
        self.base_url = normalize_provider_url(base_url)
        self.api_key = api_key.strip()
        self.provider_type = "generic"
        if isinstance(field_mapping, str) and field_mapping.strip():
            try:
                parsed = json.loads(field_mapping)
                self.field_mapping = parsed if isinstance(parsed, dict) else {}
            except Exception:
                self.field_mapping = {}
        elif isinstance(field_mapping, dict):
            self.field_mapping = dict(field_mapping)
        else:
            self.field_mapping = {}

    def _apply_order_mapping(self, payload: Dict[str, Any], item_id: Any, prov_pid: str, quantity: int) -> Dict[str, Any]:
        """
        Ensures both standard ('quantity', 'qty', 'product_id', 'productId', 'item_id')
        and any custom user-defined field mappings are present in the order payload.
        """
        payload["quantity"] = int(quantity)
        payload["qty"] = int(quantity)
        custom_qty = (self.field_mapping.get("buy_qty_field") or "").strip()
        if custom_qty:
            payload[custom_qty] = int(quantity)
        custom_pid = (self.field_mapping.get("buy_pid_field") or "").strip()
        if custom_pid:
            payload[custom_pid] = item_id
        return payload

    def _get_custom_buy_endpoints(self, default_endpoints: List[str]) -> List[str]:
        custom_ep = (self.field_mapping.get("buy_endpoint") or "").strip()
        if not custom_ep:
            return default_endpoints
        if custom_ep.startswith("http://") or custom_ep.startswith("https://"):
            full_custom = custom_ep
        else:
            full_custom = f"{self.base_url}/{custom_ep.lstrip('/')}"
        return [full_custom] + [ep for ep in default_endpoints if ep != full_custom]

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Reseller-Key": self.api_key,
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
            f"{self.base_url}/api/products",
            f"{self.base_url}/api/v1/products",
            f"{self.base_url}/v1/products",
            f"{self.base_url}/products",
            f"{self.base_url}/api/reseller/products",
            f"{self.base_url}/reseller/products",
            f"{self.base_url}/api/reseller/v1/products",
            f"{self.base_url}/api/v1/catalog",
            f"{self.base_url}/v1/catalog",
            f"{self.base_url}/api/catalog",
            f"{self.base_url}/catalog"
        ]
        
        async def _req(s):
            saw_empty_valid = False
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=15, connect=6)) as resp:
                        if resp.status == 200:
                            try:
                                data = await resp.json(content_type=None)
                            except Exception:
                                continue
                            raw_list = extract_products_list_from_json(data)
                            if raw_list:
                                standardized = self._standardize_catalog(raw_list)
                                if standardized:
                                    return standardized
                            if isinstance(data, dict) and (data.get('ok') is True or data.get('status') == 'success' or 'products' in data):
                                saw_empty_valid = True
                                return []
                            elif isinstance(data, list) and len(data) == 0:
                                saw_empty_valid = True
                                return []
                        elif resp.status in (401, 403):
                            logger.warning(f"Auth failed ({resp.status}) on {url}")
                            return None
                except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as ce:
                    logger.warning(f"Connection/timeout error on {url}: {ce}. Aborting remaining probes.")
                    break
                except Exception as e:
                    logger.debug(f"Catalog probe {url} failed: {e}")
            return [] if saw_empty_valid else None

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
        custom_stock_field = (self.field_mapping.get("stock_field") or "").strip() or None
        endpoints = [
            f"{self.base_url}/api/v1/products/{prov_pid}",
            f"{self.base_url}/v1/products/{prov_pid}",
            f"{self.base_url}/api/products/{prov_pid}",
            f"{self.base_url}/products/{prov_pid}",
            f"{self.base_url}/api/reseller/products/{prov_pid}",
            f"{self.base_url}/reseller/products/{prov_pid}",
            f"{self.base_url}/api/v1/catalog/{prov_pid}",
            f"{self.base_url}/v1/catalog/{prov_pid}"
        ]

        async def _req(s):
            fallback_stock = None
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                single_p = data.get('product') or data.get('data') or data
                                if isinstance(single_p, dict) and (matches_product_id(single_p, prov_pid) or ('stock' in single_p or 'quantity' in single_p or 'inStock' in single_p or (custom_stock_field and custom_stock_field in single_p))):
                                    num_s = extract_stock_from_dict(single_p, allow_boolean=False, custom_field=custom_stock_field)
                                    if num_s is not None:
                                        return num_s
                                    if fallback_stock is None:
                                        fallback_stock = extract_stock_from_dict(single_p, allow_boolean=True, custom_field=custom_stock_field)
                            
                            raw_list = extract_products_list_from_json(data)
                            for p in raw_list:
                                if matches_product_id(p, prov_pid):
                                    num_s = extract_stock_from_dict(p, allow_boolean=False, custom_field=custom_stock_field)
                                    if num_s is not None:
                                        return num_s
                                    if fallback_stock is None:
                                        fallback_stock = extract_stock_from_dict(p, allow_boolean=True, custom_field=custom_stock_field)
                except Exception:
                    pass
            if fallback_stock is not None:
                return fallback_stock
            
            # Fallback: fetch full catalog and search
            catalog = await self.fetch_catalog(s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, prov_pid):
                        return int(p.get('stock', 0))
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_live_product_price(self, provider_product_id: Any, quantity: int = 1, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        """
        Fetches the live wholesale cost per unit directly from provider before purchase.
        Supports quote endpoints (/api/reseller/quote, /api/v1/quotes) and product detail endpoints.
        """
        prov_pid = str(provider_product_id).strip()
        item_id = int(prov_pid) if prov_pid.isdigit() else prov_pid
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None
        pid_field = (self.field_mapping.get("buy_pid_field") or "").strip() or "product_id"
        qty_field = (self.field_mapping.get("buy_qty_field") or "").strip() or "quantity"

        endpoints = [
            f"{self.base_url}/api/reseller/products/{prov_pid}",
            f"{self.base_url}/reseller/products/{prov_pid}",
            f"{self.base_url}/api/v1/products/{prov_pid}",
            f"{self.base_url}/v1/products/{prov_pid}",
            f"{self.base_url}/api/products/{prov_pid}",
            f"{self.base_url}/products/{prov_pid}",
            f"{self.base_url}/api/v1/catalog/{prov_pid}",
            f"{self.base_url}/v1/catalog/{prov_pid}"
        ]
        quote_endpoints = [
            f"{self.base_url}/api/reseller/quote",
            f"{self.base_url}/reseller/quote",
            f"{self.base_url}/api/v1/quotes",
            f"{self.base_url}/v1/quotes",
            f"{self.base_url}/api/quote",
            f"{self.base_url}/quote"
        ]

        async def _try_quote(s: aiohttp.ClientSession, q_url: str) -> Optional[float]:
            q_payload: Dict[str, Any] = {
                "product_id": item_id,
                "quantity": int(quantity),
                "qty": int(quantity),
                pid_field: item_id,
                qty_field: int(quantity)
            }
            try:
                async with s.post(q_url, headers=self.get_headers(), json=q_payload, timeout=aiohttp.ClientTimeout(total=6, connect=3)) as q_resp:
                    if q_resp.status in [200, 201]:
                        q_data = await q_resp.json(content_type=None)
                        if isinstance(q_data, dict):
                            inner = q_data.get('data') if isinstance(q_data.get('data'), dict) else q_data
                            u_price = extract_price_from_dict(inner, custom_field=custom_price_field)
                            if u_price is not None and float(u_price) > 0:
                                return float(u_price)
                            tot_p = inner.get('total_price') or inner.get('total')
                            if tot_p is not None and int(quantity) > 0:
                                try:
                                    t_val = float(tot_p)
                                    if t_val > 0:
                                        return round(t_val / int(quantity), 4)
                                except Exception:
                                    pass
            except Exception:
                pass
            return None

        async def _req(s):
            now_ts = time.time()
            cached_q = _PROVIDER_QUOTE_ENDPOINT_CACHE.get(self.base_url)

            # 1. If we know this provider supports a quote endpoint, try it FIRST (gives live API/reseller price)
            if cached_q and cached_q[0] and (now_ts - cached_q[1]) < _QUOTE_CACHE_TTL:
                q_price = await _try_quote(s, cached_q[0])
                if q_price is not None and q_price > 0:
                    return q_price

            # 2. Probe quote endpoints automatically if not yet cached as unsupported
            if not cached_q or (now_ts - cached_q[1]) >= _QUOTE_CACHE_TTL:
                found_q_ep = None
                for q_ep in quote_endpoints:
                    q_price = await _try_quote(s, q_ep)
                    if q_price is not None and q_price > 0:
                        _PROVIDER_QUOTE_ENDPOINT_CACHE[self.base_url] = (q_ep, now_ts)
                        return q_price
                _PROVIDER_QUOTE_ENDPOINT_CACHE[self.base_url] = (found_q_ep, now_ts)

            # 3. Try single-product detail endpoints
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                single_p = data.get('product') or data.get('data') or data
                                price_val = extract_price_from_dict(single_p, custom_field=custom_price_field)
                                if price_val is not None and float(price_val) > 0:
                                    return float(price_val)
                except Exception:
                    pass

            # 4. Fallback to catalog search
            catalog = await self.fetch_catalog(s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, prov_pid):
                        return float(p.get('price', 0.0))
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        """
        Executes order and returns delivered keys/items as list of strings.
        Raises Exception if order failed or provider returned error.
        """
        prov_pid = str(provider_product_id).strip()
        item_id = int(prov_pid) if prov_pid.isdigit() else prov_pid
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "productId": prov_pid,
            "product_id": item_id,
            "item_id": item_id,
            "quantity": int(quantity),
            "qty": int(quantity),
            "external_order_id": order_ref,
            "client_order_reference": order_ref,
            "client_order_id": order_ref,
            "idempotency_key": order_ref
        }
        self._apply_order_mapping(payload, item_id, prov_pid, quantity)
        if customer_email:
            email_list = parse_customer_emails(customer_email)
            if email_list:
                if int(quantity) == 1:
                    payload["email"] = email_list[0]
                    payload["customer_email"] = email_list[0]
                else:
                    if len(email_list) < int(quantity):
                        email_list = email_list + [email_list[-1]] * (int(quantity) - len(email_list))
                    payload["emails"] = email_list[:int(quantity)]
                    payload["email"] = email_list[0]
                    payload["customer_email"] = ",".join(email_list[:int(quantity)])
        
        default_endpoints = [
            f"{self.base_url}/api/v1/orders",
            f"{self.base_url}/api/buy",
            f"{self.base_url}/buy",
            f"{self.base_url}/v1/orders",
            f"{self.base_url}/orders",
            f"{self.base_url}/api/reseller/v1/order",
            f"{self.base_url}/api/reseller/orders",
            f"{self.base_url}/reseller/orders",
            f"{self.base_url}/api/purchase",
            f"{self.base_url}/purchase",
            f"{self.base_url}/v1/purchases",
            f"{self.base_url}/api/v1/purchases"
        ]
        endpoints = self._get_custom_buy_endpoints(default_endpoints)

        async def _req(s):
            last_err = "No response from provider"
            headers = self.get_headers({"Idempotency-Key": str(order_ref)})
            
            for ep in endpoints:
                for ep_attempt in range(2):
                    try:
                        logger.info(f"Executing provider order on {ep} with payload: {payload}")
                        async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp:
                            if resp.status in [200, 201]:
                                try:
                                    buy_data = await resp.json(content_type=None)
                                except Exception:
                                    raw_txt = await resp.text()
                                    buy_data = {"credentials": raw_txt}
                                return self._parse_delivery_data(buy_data, order_ref)
                            elif resp.status == 422:
                                # Fallback minimal payload retry in case provider rejects extra fields or expects strict schema
                                custom_pid_k = (self.field_mapping.get("buy_pid_field") or "product_id").strip()
                                custom_qty_k = (self.field_mapping.get("buy_qty_field") or "qty").strip()
                                minimal_payload = {custom_pid_k: item_id, custom_qty_k: int(quantity)}
                                if "email" in payload:
                                    minimal_payload["email"] = payload["email"]
                                if "emails" in payload:
                                    minimal_payload["emails"] = payload["emails"]
                                async with s.post(ep, headers=headers, json=minimal_payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp2:
                                    if resp2.status in [200, 201]:
                                        try:
                                            buy_data = await resp2.json(content_type=None)
                                        except Exception:
                                            raw_txt = await resp2.text()
                                            buy_data = {"credentials": raw_txt}
                                        return self._parse_delivery_data(buy_data, order_ref)
                                    last_err = await self._parse_error_response(resp2)
                                    logger.warning(f"Provider {ep} 422 fallback returned status {resp2.status}: {last_err}")
                                break
                            else:
                                last_err = await self._parse_error_response(resp)
                                logger.warning(f"Provider {ep} returned status {resp.status}: {last_err}")
                                err_l = str(last_err).lower()
                                if resp.status == 402 or "balance" in err_l:
                                    raise Exception(f"Provider balance insufficient: {last_err}")
                                elif resp.status == 409 or "out of stock" in err_l or "stock" in err_l:
                                    raise Exception(f"Out of stock ({last_err})")
                                elif "email requis" in err_l or "email required" in err_l or "requires email" in err_l:
                                    raise Exception(f"Provider error: {last_err}")
                                elif resp.status in [401, 403] or "invalid api key" in err_l or "unauthorized" in err_l:
                                    break
                                break
                    except (aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as conn_err:
                        last_err = str(conn_err)
                        if ep_attempt == 0:
                            logger.warning(f"Connection error on {ep} (attempt 1/2): {conn_err}. Retrying in 1.5s...")
                            await asyncio.sleep(1.5)
                            continue
                        logger.warning(f"Provider request connection error on {ep}: {conn_err}")
                        break
                    except Exception as ep_err:
                        if "Out of stock" in str(ep_err) or "Provider balance insufficient" in str(ep_err) or "email" in str(ep_err).lower():
                            raise ep_err
                        logger.warning(f"Provider request error on {ep}: {ep_err}")
                        last_err = str(ep_err)
                        break
            
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
        endpoints = [
            f"{self.base_url}/api/v1/me",
            f"{self.base_url}/v1/me",
            f"{self.base_url}/api/me",
            f"{self.base_url}/me",
            f"{self.base_url}/api/reseller/me",
            f"{self.base_url}/reseller/me",
            f"{self.base_url}/v1/balance",
            f"{self.base_url}/api/v1/balance",
            f"{self.base_url}/api/balance",
            f"{self.base_url}/balance"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                return data
                except Exception:
                    pass
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    def _standardize_catalog(self, raw_list: List[Any]) -> List[Dict[str, Any]]:
        formatted = []
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None
        custom_stock_field = (self.field_mapping.get("stock_field") or "").strip() or None
        custom_id_field = (self.field_mapping.get("id_field") or "").strip() or None

        for p in raw_list:
            if not isinstance(p, dict):
                continue
            p_id = None
            if custom_id_field and p.get(custom_id_field) is not None:
                p_id = p.get(custom_id_field)
            if p_id is None:
                for id_k in ["id", "_id", "product_id", "productId", "item_id", "service", "code", "sku", "slug"]:
                    if p.get(id_k) is not None:
                        p_id = p.get(id_k)
                        break
            if p_id is None:
                continue
            
            p_name = (
                p.get("name") or p.get("title") or p.get("name_en") or p.get("name_ar") or
                p.get("service_name") or p.get("item_name") or f"Product {p_id}"
            )
            name_ar = p.get("name_ar") or p_name
            name_en = p.get("name_en") or p_name
            name_ru = p.get("name_ru") or p_name
            extracted_price = extract_price_from_dict(p, custom_field=custom_price_field)
            price_val = float(extracted_price) if extracted_price is not None else 0.0
            if price_val <= 0 and p.get("original_price") is not None:
                try:
                    orig_p = float(p.get("original_price") or 0.0)
                    if orig_p > 0:
                        price_val = orig_p
                except (ValueError, TypeError):
                    pass
                
            stock_val = extract_stock_from_dict(p, allow_boolean=False, custom_field=custom_stock_field)
            if stock_val is None:
                stock_val = extract_stock_from_dict(p, allow_boolean=True, custom_field=custom_stock_field) or 0
                
            req_email = bool(
                p.get("requiresEmailActivation")
                or p.get("requires_email")
                or (isinstance(p.get("delivery"), dict) and p["delivery"].get("requiresEmailActivation"))
            )
            desc_default = str(p.get("description") or p.get("description_en") or p.get("description_ar") or "")

            formatted.append({
                "id": str(p_id),
                "name": p_name,
                "name_ar": name_ar,
                "name_en": name_en,
                "name_ru": name_ru,
                "description": desc_default,
                "description_ar": str(p.get("description_ar") or desc_default),
                "description_en": str(p.get("description_en") or desc_default),
                "description_ru": str(p.get("description_ru") or desc_default),
                "price": price_val,
                "original_price": float(p.get("original_price") or price_val),
                "stock": stock_val,
                "custom_emoji_id": p.get("custom_emoji_id"),
                "requires_email": req_email,
                "requiresEmailActivation": req_email
            })
        return formatted

    def _parse_delivery_data(self, buy_data: Dict[str, Any], ext_order_id: str) -> List[str]:
        if not isinstance(buy_data, dict):
            return [str(buy_data)]
            
        deliv = buy_data.get('delivery')
        order = buy_data.get('order')
        
        raw_creds = None
        if isinstance(deliv, dict) and deliv.get('items'):
            raw_creds = deliv['items']
        elif isinstance(deliv, list) and len(deliv) > 0:
            raw_creds = deliv
        elif isinstance(order, dict) and order.get('items'):
            raw_creds = order['items']
        elif isinstance(order, list) and len(order) > 0:
            raw_creds = order
        elif buy_data.get('delivered'):
            raw_creds = buy_data.get('delivered')
        else:
            raw_creds = (
                buy_data.get('deliveredKeys') if buy_data.get('deliveredKeys') is not None
                else (buy_data.get('deliveredKey') if buy_data.get('deliveredKey') is not None
                else (buy_data.get('credentials') if buy_data.get('credentials') is not None
                else (buy_data.get('data') if buy_data.get('data') is not None
                else buy_data.get('items'))))
            )

        if raw_creds is not None and not (isinstance(raw_creds, list) and len(raw_creds) == 0):
            if isinstance(raw_creds, str):
                if "\n" in raw_creds:
                    return [item.strip() for item in raw_creds.split("\n") if item.strip()]
                elif "," in raw_creds:
                    return [item.strip() for item in raw_creds.split(",") if item.strip()]
                else:
                    return [raw_creds.strip()]
            elif isinstance(raw_creds, list):
                res = []
                for it in raw_creds:
                    if isinstance(it, dict):
                        val = it.get('account_data') or it.get('code') or it.get('credentials') or it.get('item') or it.get('key') or it.get('data')
                        if val is not None:
                            res.append(str(val).strip())
                        else:
                            res.append(str(it))
                    else:
                        res.append(str(it).strip())
                if res:
                    return [r for r in res if r]
            else:
                return [str(raw_creds)]
        if isinstance(buy_data.get('activation'), dict) or buy_data.get('status') in ['paid', 'pending_invite', 'pending', 'processing']:
            act = buy_data.get('activation') if isinstance(buy_data.get('activation'), dict) else {}
            emails = act.get('emails') or ([act['email']] if act.get('email') else [])
            eta = act.get('eta', 'ASAP')
            ord_id = buy_data.get('order_ref') or buy_data.get('orderId') or buy_data.get('order_id') or (order.get('id') if isinstance(order, dict) else None) or buy_data.get('id') or ext_order_id
            status_str = str(buy_data.get('status') or 'paid').upper()
            if emails:
                return [f"✅ Activation Order #{ord_id} ({status_str}) — Email: {em} | ETA: {eta}" for em in emails]
            return [f"✅ Activation Order #{ord_id} ({status_str}) | ETA: {eta}"]
        elif buy_data.get('success') or buy_data.get('ok') or buy_data.get('status') in ['completed', 'delivered']:
            ord_id = buy_data.get('order_ref') or buy_data.get('orderId') or buy_data.get('order_id') or (order.get('id') if isinstance(order, dict) else None) or buy_data.get('id') or ext_order_id
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
                msg = str(last_err.get('message') or last_err.get('code') or "")
                details = last_err.get('details')
                if details:
                    if isinstance(details, list):
                        parts = []
                        for item in details:
                            if isinstance(item, dict):
                                loc = ".".join(str(x) for x in item.get("loc", []) if x not in ("body", ""))
                                d_msg = item.get("msg") or str(item)
                                parts.append(f"{loc}: {d_msg}" if loc else str(d_msg))
                            else:
                                parts.append(str(item))
                        d_str = "; ".join(parts)
                        last_err = f"{msg} ({d_str})" if msg and d_str else (msg or d_str)
                    elif isinstance(details, dict):
                        d_parts = [f"{k}: {v}" for k, v in details.items()]
                        d_str = "; ".join(d_parts)
                        last_err = f"{msg} ({d_str})" if msg and d_str else (msg or d_str)
                    else:
                        last_err = f"{msg} ({details})" if msg else str(details)
                else:
                    last_err = msg or str(last_err)
            elif isinstance(last_err, list):
                parts = []
                for item in last_err:
                    if isinstance(item, dict):
                        loc = ".".join(str(x) for x in item.get("loc", []) if x not in ("body", ""))
                        msg = item.get("msg") or str(item)
                        parts.append(f"{loc}: {msg}" if loc else str(msg))
                    else:
                        parts.append(str(item))
                last_err = "; ".join(parts) if parts else f"HTTP {resp.status}"
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
    """
    Pandora Digital Reseller API Adapter (https://api.pandoradigital.shop/docs)
    Strict OpenAPI 3.1 schema compliance (additionalProperties: false on Quotes & Orders).
    """
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        self.provider_type = "pandora"

    @staticmethod
    def _parse_pid_and_variant(provider_product_id: Any) -> Tuple[str, Optional[str]]:
        prov_pid_str = str(provider_product_id).strip()
        for sep in [":", "#", "__variant__", "__"]:
            if sep in prov_pid_str:
                parts = prov_pid_str.split(sep, 1)
                p_id = parts[0].strip()
                v_id = parts[1].strip() or None
                return p_id, v_id
        return prov_pid_str, None

    def _standardize_pandora_catalog(self, raw_list: List[Any]) -> List[Dict[str, Any]]:
        formatted = []
        for p in raw_list:
            if not isinstance(p, dict):
                continue
            base_id = p.get("id")
            if not base_id:
                continue
            var_id = p.get("variant_id")
            var_name = p.get("variant_name")
            p_id = f"{base_id}:{var_id}" if var_id else str(base_id)

            p_name = p.get("name") or f"Product {p_id}"
            if var_name:
                p_name = f"{p_name} ({var_name})"

            unit_p = p.get("unit_price")
            price_val = float(unit_p) if unit_p is not None else 0.0

            stock_val = p.get("available_stock")
            stock_int = int(stock_val) if stock_val is not None else 0

            desc = str(p.get("description") or "")
            formatted.append({
                "id": str(p_id),
                "name": p_name,
                "name_ar": p_name,
                "name_en": p_name,
                "name_ru": p_name,
                "description": desc,
                "description_ar": desc,
                "description_en": desc,
                "description_ru": desc,
                "price": price_val,
                "original_price": price_val,
                "stock": stock_int,
                "custom_emoji_id": None,
                "requires_email": False,
                "requiresEmailActivation": False
            })
        return formatted

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/api/v1/products?limit=100",
            f"{self.base_url}/v1/products?limit=100",
            f"{self.base_url}/api/v1/products",
            f"{self.base_url}/v1/products"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=35, connect=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw_list = extract_products_list_from_json(data)
                            if raw_list:
                                return self._standardize_pandora_catalog(raw_list)
                except Exception as e:
                    logger.debug(f"Pandora catalog probe {url} failed: {e}")
            return []

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_stock(self, provider_product_id: Any, session: Optional[aiohttp.ClientSession] = None) -> Optional[int]:
        pid, var_id = self._parse_pid_and_variant(provider_product_id)
        headers = self.get_headers()

        async def _req(s):
            try:
                q_payload: Dict[str, Any] = {"product_id": pid, "quantity": 1}
                if var_id:
                    q_payload["variant_id"] = var_id
                async with s.post(
                    f"{self.base_url}/api/v1/quotes",
                    headers=headers,
                    json=q_payload,
                    timeout=aiohttp.ClientTimeout(total=8, connect=4)
                ) as q_resp:
                    if q_resp.status in [200, 201]:
                        q_data = await q_resp.json()
                        if isinstance(q_data, dict) and "available_stock" in q_data:
                            stk = q_data.get("available_stock")
                            return int(stk) if stk is not None else None
            except Exception:
                pass

            try:
                async with s.get(f"{self.base_url}/api/v1/products/{pid}", headers=headers, timeout=aiohttp.ClientTimeout(total=8, connect=4)) as p_resp:
                    if p_resp.status == 200:
                        p_data = await p_resp.json()
                        if isinstance(p_data, dict) and "available_stock" in p_data:
                            stk = p_data.get("available_stock")
                            return int(stk) if stk is not None else None
            except Exception:
                pass
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_live_product_price(self, provider_product_id: Any, quantity: int = 1, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        pid, var_id = self._parse_pid_and_variant(provider_product_id)
        headers = self.get_headers()

        async def _req(s):
            try:
                q_payload: Dict[str, Any] = {"product_id": pid, "quantity": int(quantity)}
                if var_id:
                    q_payload["variant_id"] = var_id
                async with s.post(
                    f"{self.base_url}/api/v1/quotes",
                    headers=headers,
                    json=q_payload,
                    timeout=aiohttp.ClientTimeout(total=8, connect=4)
                ) as q_resp:
                    if q_resp.status in [200, 201]:
                        q_data = await q_resp.json()
                        if isinstance(q_data, dict):
                            u_price = q_data.get("unit_price")
                            if u_price is not None:
                                return float(u_price)
            except Exception:
                pass

            try:
                async with s.get(f"{self.base_url}/api/v1/products/{pid}", headers=headers, timeout=aiohttp.ClientTimeout(total=8, connect=4)) as p_resp:
                    if p_resp.status == 200:
                        p_data = await p_resp.json()
                        if isinstance(p_data, dict):
                            u_price = p_data.get("unit_price")
                            if u_price is not None:
                                return float(u_price)
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        pid, var_id = self._parse_pid_and_variant(provider_product_id)
        order_ref = str(client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}")[:100]
        headers = self.get_headers({"Idempotency-Key": order_ref})

        async def _req(s):
            # Step 1: Quote to obtain live unit_price, price_version, and verify can_purchase
            unit_price = None
            price_version = None
            try:
                q_payload: Dict[str, Any] = {"product_id": pid, "quantity": int(quantity)}
                if var_id:
                    q_payload["variant_id"] = var_id
                async with s.post(
                    f"{self.base_url}/api/v1/quotes",
                    headers=headers,
                    json=q_payload,
                    timeout=aiohttp.ClientTimeout(total=10, connect=5)
                ) as q_resp:
                    if q_resp.status in [200, 201]:
                        q_data = await q_resp.json()
                        if isinstance(q_data, dict):
                            if q_data.get("can_purchase") is False:
                                avail_stk = q_data.get("available_stock", 0)
                                raise Exception(f"Product is unavailable or out of stock at provider (stock: {avail_stk})")
                            unit_price = q_data.get("unit_price")
                            price_version = q_data.get("price_version")
                    elif q_resp.status == 409:
                        last_err = await self._parse_error_response(q_resp)
                        raise Exception(f"Provider product unavailable: {last_err}")
                    elif q_resp.status == 404:
                        raise Exception("Provider product not found or not API-enabled")
            except Exception as q_err:
                if "Provider product unavailable:" in str(q_err) or "Product is unavailable" in str(q_err) or "Provider product not found" in str(q_err):
                    raise q_err
                logger.warning(f"Pandora quote check failed: {q_err}")

            # Step 2: Fallback price from product info if quote didn't provide unit_price
            if not unit_price or float(unit_price or 0.0) <= 0:
                try:
                    async with s.get(
                        f"{self.base_url}/api/v1/products/{pid}",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=8, connect=5)
                    ) as p_resp:
                        if p_resp.status == 200:
                            p_data = await p_resp.json()
                            if isinstance(p_data, dict):
                                unit_price = p_data.get("unit_price")
                except Exception:
                    pass

            # Step 3: Fallback to expected_price if valid positive number
            if not unit_price or float(unit_price or 0.0) <= 0:
                if expected_price is not None and float(expected_price) > 0:
                    unit_price = f"{float(expected_price):.4f}".rstrip('0').rstrip('.')

            if not unit_price or float(unit_price or 0.0) <= 0:
                raise Exception("Provider error: Could not determine valid unit price for product")

            # Step 4: Construct STRICT ApiOrderCreate payload (additionalProperties: false)
            buy_payload: Dict[str, Any] = {
                "product_id": pid,
                "quantity": int(quantity),
                "expected_unit_price": str(unit_price)
            }
            if var_id:
                buy_payload["variant_id"] = var_id
            if price_version:
                buy_payload["price_version"] = str(price_version)
            if order_ref:
                buy_payload["client_order_reference"] = order_ref[:160]

            ep = f"{self.base_url}/api/v1/orders"
            logger.info(f"Executing Pandora order on {ep} with payload: {buy_payload}")

            async with s.post(ep, headers=headers, json=buy_payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp:
                buy_data = None
                if resp.status in [200, 201]:
                    buy_data = await resp.json()
                elif resp.status == 409:
                    # Check if PRICE_CHANGED, retry once with updated price and version
                    try:
                        err_json = await resp.json()
                        err_obj = err_json.get("error", {}) if isinstance(err_json, dict) else {}
                        if isinstance(err_obj, dict) and err_obj.get("code") == "PRICE_CHANGED":
                            details = err_obj.get("details", {})
                            new_price = details.get("current_unit_price") if isinstance(details, dict) else None
                            new_ver = details.get("price_version") if isinstance(details, dict) else None
                            if new_price and float(new_price) > 0:
                                if expected_price is not None and float(new_price) > float(expected_price) + 0.005:
                                    logger.warning(f"Pandora cost increased from {expected_price} to {new_price}, halting order to update price first.")
                                    raise Exception(f"PRICE_CHANGED:{float(expected_price):.2f}:{float(new_price):.2f}")
                                logger.info(f"Pandora price changed to {new_price} (version: {new_ver}), retrying order...")
                                buy_payload["expected_unit_price"] = str(new_price)
                                if new_ver:
                                    buy_payload["price_version"] = str(new_ver)
                                async with s.post(ep, headers=headers, json=buy_payload, timeout=aiohttp.ClientTimeout(total=45, connect=10)) as retry_resp:
                                    if retry_resp.status in [200, 201]:
                                        buy_data = await retry_resp.json()
                                    else:
                                        last_err = await self._parse_error_response(retry_resp)
                                        raise Exception(f"Provider error: {last_err}")
                    except Exception as retry_e:
                        if "PRICE_CHANGED:" in str(retry_e) or "Provider error:" in str(retry_e):
                            raise retry_e
                    if not buy_data:
                        last_err = await self._parse_error_response(resp)
                        raise Exception(f"Provider error: {last_err}")
                else:
                    last_err = await self._parse_error_response(resp)
                    raise Exception(f"Provider error: {last_err}")

                if not isinstance(buy_data, dict):
                    raise Exception("Provider returned empty or invalid response")

                # Check if order failed
                if buy_data.get("status") == "failed":
                    fail_msg = buy_data.get("failure_message") or buy_data.get("failure_code") or "Order failed at provider"
                    raise Exception(f"Provider error: {fail_msg}")

                # Handle pending/processing
                if buy_data.get("status") in ["processing", "pending"]:
                    ord_id = buy_data.get("id") or buy_data.get("order_id")
                    if ord_id:
                        for _ in range(6):
                            await asyncio.sleep(2)
                            try:
                                async with s.get(f"{self.base_url}/api/v1/orders/{ord_id}", headers=headers, timeout=aiohttp.ClientTimeout(total=10, connect=5)) as o_resp:
                                    if o_resp.status == 200:
                                        o_data = await o_resp.json()
                                        if isinstance(o_data, dict):
                                            if o_data.get("status") == "failed":
                                                fail_msg = o_data.get("failure_message") or o_data.get("failure_code") or "Order failed at provider"
                                                raise Exception(f"Provider error: {fail_msg}")
                                            if (o_data.get("delivery") and o_data["delivery"].get("items")) or o_data.get("status") == "delivered":
                                                buy_data = o_data
                                                break
                            except Exception as pe:
                                if "Provider error:" in str(pe):
                                    raise pe

                return self._parse_delivery_data(buy_data, order_ref)

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
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        self.provider_type = "aethel"

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
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
            f"{self.base_url}/catalog",
            f"{self.base_url}/api/catalog"
        ]
        
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=35, connect=10)) as resp:
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
            f"{self.base_url}/api/v1/balance",
            f"{self.base_url}/api/balance",
            f"{self.base_url}/balance"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        item_id = int(prov_pid) if prov_pid.isdigit() else prov_pid
        order_ref = client_order_ref or str(uuid.uuid4())
        
        headers = self.get_headers({
            "Idempotency-Key": str(order_ref)
        })
        payload = {
            "item_id": item_id,
            "quantity": int(quantity),
            "qty": int(quantity)
        }
        self._apply_order_mapping(payload, item_id, prov_pid, quantity)
        
        default_endpoints = [
            f"{self.base_url}/v1/purchases",
            f"{self.base_url}/api/v1/purchases",
            f"{self.base_url}/v1/orders",
            f"{self.base_url}/api/v1/orders"
        ]
        endpoints = self._get_custom_buy_endpoints(default_endpoints)

        async def _req(s):
            last_err = "No response from Aethel API"
            for ep in endpoints:
                try:
                    logger.info(f"Executing Aethel order on {ep} with payload: {payload}")
                    async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp:
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
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
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
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=35, connect=10)) as resp:
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

    async def fetch_live_product_price(self, provider_product_id: Any, quantity: int = 1, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        prov_pid = str(provider_product_id).strip()
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None
        url = f"{self.base_url}/v1/products/{prov_pid}"
        async def _req(s):
            for attempt in range(2):
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                single_p = data.get('product') or data.get('data') or data
                                price_val = extract_price_from_dict(single_p, custom_field=custom_price_field)
                                if price_val is not None and float(price_val) > 0:
                                    return float(price_val)
                except Exception as e:
                    logger.debug(f"ProdSeller price fetch {url} attempt {attempt+1} failed: {e}")
                    if attempt == 0:
                        await asyncio.sleep(0.5)
            # Fallback to catalog search
            catalog = await self.fetch_catalog(s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, prov_pid):
                        return float(p.get('price', 0.0))
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        payload = {
            "productId": prov_pid,
            "quantity": int(quantity)
        }
        self._apply_order_mapping(payload, prov_pid, prov_pid, quantity)
        if customer_email:
            email_list = parse_customer_emails(customer_email)
            if email_list:
                if int(quantity) == 1:
                    payload["email"] = email_list[0]
                else:
                    if len(email_list) < int(quantity):
                        email_list = email_list + [email_list[-1]] * (int(quantity) - len(email_list))
                    payload["emails"] = email_list[:int(quantity)]

        headers = self.get_headers({"Idempotency-Key": str(order_ref)[:100]})

        async def _req(s):
            ep_list = self._get_custom_buy_endpoints([f"{self.base_url}/v1/orders"])
            ep = ep_list[0]
            logger.info(f"Executing ProdSeller order on {ep} with payload: {payload}")
            last_err = "No response from ProdSeller"
            
            # Auto-retry up to 3 times on transient connection errors with 1.5s delay
            for attempt in range(3):
                try:
                    async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp:
                        if resp.status in [200, 201]:
                            buy_data = await resp.json(content_type=None)
                            return self._parse_delivery_data(buy_data, order_ref)
                        else:
                            last_err = await self._parse_error_response(resp)
                            err_l = str(last_err).lower()
                            if resp.status == 402 or "balance" in err_l or "solde" in err_l:
                                raise Exception(f"Provider balance insufficient: {last_err}")
                            elif resp.status == 409 or "out of stock" in err_l or "$slice" in err_l or "must be positive: 0" in err_l or "no items in stock" in err_l:
                                raise Exception(f"Out of stock (Product depleted at provider)")
                            elif resp.status == 401:
                                raise Exception(f"Invalid API Key: {last_err}")
                            elif "email" in err_l:
                                raise Exception(f"Provider requires email: {last_err}")
                            raise Exception(f"Provider error ({resp.status}): {last_err}")
                except (aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as conn_err:
                    last_err = str(conn_err)
                    if attempt < 2:
                        logger.warning(f"Connection to ProdSeller ({ep}) failed on attempt {attempt+1}/3: {conn_err}. Retrying in 1.5s...")
                        await asyncio.sleep(1.5)
                        continue
                    raise Exception(f"Cannot connect to ProdSeller ({conn_err})")
                except Exception as ex:
                    # Non-transient errors (like balance, stock, email) should be re-raised immediately without wasteful retry
                    raise ex
            raise Exception(f"ProdSeller order failed: {last_err}")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 4. ShopDigital Adapter (https://shopdigital...)
# -------------------------------------------------------------------------
class ShopDigitalProviderAdapter(BaseProviderAdapter):
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        self.provider_type = "shopdigital"

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/api/products",
            f"{self.base_url}/products"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=35, connect=10)) as resp:
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        headers = self.get_headers({"Idempotency-Key": order_ref})
        ep_list = self._get_custom_buy_endpoints([f"{self.base_url}/api/purchase"])
        ep = ep_list[0]

        async def _req(s):
            collected_items = []
            for _ in range(int(quantity)):
                payload = {
                    "product_id": prov_pid,
                    "quantity": 1,
                    "qty": 1,
                    "external_order_id": f"{order_ref}_{len(collected_items)}"
                }
                self._apply_order_mapping(payload, prov_pid, prov_pid, 1)
                async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=35, connect=10)) as resp:
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
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        self.provider_type = "supabase"

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        url = f"{self.base_url}?action=products"
        async def _req(s):
            try:
                async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=35, connect=10)) as resp:
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        payload = {
            "productId": prov_pid,
            "product_id": prov_pid,
            "quantity": int(quantity),
            "qty": int(quantity),
            "external_order_id": order_ref
        }
        self._apply_order_mapping(payload, prov_pid, prov_pid, quantity)
        if customer_email:
            email_list = parse_customer_emails(customer_email)
            if email_list:
                payload["email"] = email_list[0]
                if int(quantity) > 1:
                    payload["emails"] = email_list[:int(quantity)]
        url = f"{self.base_url}?action=order"

        async def _req(s):
            async with s.post(url, headers=self.get_headers(), json=payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp:
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
# 6. VenteBot Reseller API Adapter (FastAPI / OpenAPI 3.0.3)
# -------------------------------------------------------------------------
class VenteBotProviderAdapter(BaseProviderAdapter):
    """
    VenteBot Reseller API Adapter (OpenAPI 3.0.3)
    Base URL: https://ventetelegrambotrailway-production.up.railway.app
    Catalog: GET /api/reseller/products
    Balance/Me: GET /api/reseller/me
    Quote: POST /api/reseller/quote {"product_id": int, "quantity": int}
    Order: POST /api/reseller/orders {"product_id": int, "quantity": int, "idempotency_key": str}
    """
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        self.provider_type = "ventebot"

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "X-Reseller-Key": self.api_key,
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/api/reseller/products",
            f"{self.base_url}/reseller/products",
            f"{self.base_url}/api/v1/products",
            f"{self.base_url}/v1/products",
            f"{self.base_url}/api/products",
            f"{self.base_url}/products"
        ]
        
        async def _req(s):
            saw_empty_valid = False
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=35, connect=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            raw_list = extract_products_list_from_json(data)
                            if raw_list:
                                standardized = self._standardize_catalog(raw_list)
                                if standardized:
                                    return standardized
                            if isinstance(data, dict) and (data.get('success') is True or data.get('ok') is True or 'products' in data):
                                saw_empty_valid = True
                            elif isinstance(data, list) and len(data) == 0:
                                saw_empty_valid = True
                except Exception as e:
                    logger.debug(f"VenteBot catalog probe {url} failed: {e}")
            return [] if saw_empty_valid else None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_stock(self, provider_product_id: Any, session: Optional[aiohttp.ClientSession] = None) -> Optional[int]:
        prov_pid = str(provider_product_id).strip()
        item_id = int(prov_pid) if prov_pid.isdigit() else prov_pid
        custom_stock_field = (self.field_mapping.get("stock_field") or "").strip() or None
        
        async def _req(s):
            # 1. Try single product detail endpoints first
            for url in [
                f"{self.base_url}/api/reseller/products/{prov_pid}",
                f"{self.base_url}/reseller/products/{prov_pid}",
                f"{self.base_url}/api/v1/products/{prov_pid}",
                f"{self.base_url}/api/products/{prov_pid}",
                f"{self.base_url}/products/{prov_pid}"
            ]:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                single_p = data.get('product') or data.get('data') or data
                                if isinstance(single_p, dict):
                                    stk = extract_stock_from_dict(single_p, allow_boolean=True, custom_field=custom_stock_field)
                                    if stk is not None:
                                        return stk
                except Exception:
                    pass

            # 2. Try quote endpoint
            try:
                quote_url = f"{self.base_url}/api/reseller/quote"
                async with s.post(quote_url, headers=self.get_headers(), json={"product_id": item_id, "quantity": 1, "qty": 1}, timeout=aiohttp.ClientTimeout(total=10, connect=5)) as q_resp:
                    if q_resp.status == 200:
                        q_data = await q_resp.json(content_type=None)
                        if isinstance(q_data, dict):
                            stk = extract_stock_from_dict(q_data, allow_boolean=True, custom_field=custom_stock_field)
                            if stk is not None:
                                return stk
                            if q_data.get('success') is True or 'unit_price' in q_data:
                                return 999
                    elif q_resp.status in [400, 404, 409, 422]:
                        q_err = await self._parse_error_response(q_resp)
                        if "stock" in q_err.lower() or "not available" in q_err.lower() or "insufficient" in q_err.lower():
                            return 0
            except Exception:
                pass
            
            # 3. Fallback: search products catalog
            catalog = await self.fetch_catalog(s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, prov_pid):
                        return int(p.get('stock', 0))
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_balance(self, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
        endpoints = [
            f"{self.base_url}/api/reseller/me",
            f"{self.base_url}/reseller/me",
            f"{self.base_url}/api/me",
            f"{self.base_url}/me",
            f"{self.base_url}/api/v1/me",
            f"{self.base_url}/v1/me"
        ]
        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                return data
                except Exception:
                    pass
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_live_product_price(self, provider_product_id: Any, quantity: int = 1, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        prov_pid = str(provider_product_id).strip()
        item_id = int(prov_pid) if prov_pid.isdigit() else prov_pid
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None

        async def _req(s):
            # 1. Try quote endpoints FIRST (returns real live/tiered API cost charged at checkout)
            for quote_url in [f"{self.base_url}/api/reseller/quote", f"{self.base_url}/reseller/quote", f"{self.base_url}/api/v1/quotes"]:
                try:
                    async with s.post(quote_url, headers=self.get_headers(), json={"product_id": item_id, "quantity": int(quantity), "qty": int(quantity)}, timeout=aiohttp.ClientTimeout(total=6, connect=3)) as q_resp:
                        if q_resp.status in [200, 201]:
                            q_data = await q_resp.json(content_type=None)
                            if isinstance(q_data, dict):
                                inner = q_data.get('data') if isinstance(q_data.get('data'), dict) else q_data
                                u_price = extract_price_from_dict(inner, custom_field=custom_price_field)
                                if u_price is not None and float(u_price) > 0:
                                    return float(u_price)
                except Exception:
                    pass

            # 2. Try single product detail endpoints
            for url in [
                f"{self.base_url}/api/reseller/products/{prov_pid}",
                f"{self.base_url}/reseller/products/{prov_pid}",
                f"{self.base_url}/api/v1/products/{prov_pid}",
                f"{self.base_url}/api/products/{prov_pid}",
                f"{self.base_url}/products/{prov_pid}"
            ]:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                single_p = data.get('product') or data.get('data') or data
                                u_price = extract_price_from_dict(single_p, custom_field=custom_price_field)
                                if u_price is not None and float(u_price) > 0:
                                    return float(u_price)
                except Exception:
                    pass

            # 3. Fallback to catalog
            catalog = await self.fetch_catalog(s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, prov_pid):
                        return float(p.get('price', 0.0))
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        prov_pid = str(provider_product_id).strip()
        item_id = int(prov_pid) if prov_pid.isdigit() else prov_pid
        order_ref = client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        headers = self.get_headers({
            "Idempotency-Key": str(order_ref)
        })
        payload = {
            "product_id": item_id,
            "quantity": int(quantity),
            "qty": int(quantity),
            "idempotency_key": str(order_ref)
        }
        self._apply_order_mapping(payload, item_id, prov_pid, quantity)
        if customer_email:
            email_list = parse_customer_emails(customer_email)
            if email_list:
                payload["email"] = email_list[0]
                if int(quantity) > 1:
                    if len(email_list) < int(quantity):
                        email_list = email_list + [email_list[-1]] * (int(quantity) - len(email_list))
                    payload["emails"] = email_list[:int(quantity)]
        
        default_endpoints = [
            f"{self.base_url}/api/reseller/orders",
            f"{self.base_url}/reseller/orders",
            f"{self.base_url}/api/v1/orders",
            f"{self.base_url}/v1/orders",
            f"{self.base_url}/api/buy",
            f"{self.base_url}/buy",
            f"{self.base_url}/orders",
            f"{self.base_url}/api/purchase",
            f"{self.base_url}/purchase",
            f"{self.base_url}/api/v1/purchases"
        ]
        endpoints = self._get_custom_buy_endpoints(default_endpoints)

        async def _req(s):
            last_err = "No response from VenteBot API"
            for ep in endpoints:
                try:
                    logger.info(f"Executing VenteBot order on {ep} with payload: {payload}")
                    async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp:
                        if resp.status in [200, 201]:
                            buy_data = await resp.json(content_type=None)
                            return self._parse_delivery_data(buy_data, order_ref)
                        elif resp.status == 422:
                            custom_pid_k = (self.field_mapping.get("buy_pid_field") or "product_id").strip()
                            custom_qty_k = (self.field_mapping.get("buy_qty_field") or "qty").strip()
                            minimal_payload = {custom_pid_k: item_id, custom_qty_k: int(quantity)}
                            if "email" in payload:
                                minimal_payload["email"] = payload["email"]
                            if "emails" in payload:
                                minimal_payload["emails"] = payload["emails"]
                            async with s.post(ep, headers=headers, json=minimal_payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp2:
                                if resp2.status in [200, 201]:
                                    buy_data = await resp2.json(content_type=None)
                                    return self._parse_delivery_data(buy_data, order_ref)
                                last_err = await self._parse_error_response(resp2)
                                logger.warning(f"VenteBot {ep} 422 fallback returned status {resp2.status}: {last_err}")
                            continue
                        else:
                            last_err = await self._parse_error_response(resp)
                            logger.warning(f"VenteBot order error on {ep}: HTTP {resp.status} - {last_err}")
                            err_l = str(last_err).lower()
                            if resp.status == 402 or "balance" in err_l:
                                raise Exception(f"Provider balance insufficient: {last_err}")
                            elif resp.status == 409 or "stock" in err_l or "insufficient" in err_l:
                                raise Exception(f"Out of stock ({last_err})")
                            elif "email requis" in err_l or "email required" in err_l or "requires email" in err_l:
                                raise Exception(f"Provider error: {last_err}")
                            elif resp.status in [401, 403] or "invalid api key" in err_l or "unauthorized" in err_l:
                                break
                            continue
                except Exception as ep_err:
                    if "Out of stock" in str(ep_err) or "Provider balance insufficient" in str(ep_err) or "email" in str(ep_err).lower():
                        raise ep_err
                    logger.warning(f"VenteBot purchase error on {ep}: {ep_err}")
                    last_err = str(ep_err)
                    
            raise Exception(f"Provider error: {last_err}")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 7. Roboticvn Customer API v2 Adapter (https://api.roboticvn.com/api/v2/docs)
# -------------------------------------------------------------------------
_ROBOTICVN_CATALOG_CACHE: Dict[str, Tuple[List[Dict[str, Any]], float]] = {}
_ROBOTICVN_CATALOG_LOCKS: Dict[str, asyncio.Lock] = {}
_ROBOTICVN_QUOTE_CACHE: Dict[Tuple[str, str, Optional[str], int], Tuple[float, float]] = {}
_ROBOTICVN_CACHE_TTL = 180.0  # 3 minutes catalog TTL with per-key Lock and polite concurrency
_ROBOTICVN_QUOTE_TTL = 15.0   # 15 seconds live quote TTL per product/variant

class RoboticvnProviderAdapter(BaseProviderAdapter):
    """
    Roboticvn Customer API v2 Adapter.
    Official Docs: https://api.roboticvn.com/api/v2/docs
    
    Structure:
    - Master Products (Categories): GET /api/v2/products (returns {data: [{id, title}, ...]})
    - Purchasable Sub-products (Variants): GET /api/v2/products/{master_id} (returns variants with prices & stock)
    - Realtime Quote: POST /api/v2/products/{master_id}/quote
    - Wallet Orders: POST /api/v2/orders
    - Delivered Credentials: GET /api/v2/orders/{id}/delivery
    """
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        self.provider_type = "roboticvn"
        clean = self.base_url.rstrip("/")
        if clean.endswith("/api/v2"):
            self.api_v2_url = clean
        elif "/api/v2" in clean:
            self.api_v2_url = clean.split("/api/v2")[0] + "/api/v2"
        else:
            self.api_v2_url = f"{clean}/api/v2"

    @staticmethod
    def _parse_pid_and_variant(provider_product_id: Any) -> Tuple[str, Optional[str]]:
        prov_pid_str = str(provider_product_id).strip()
        for sep in [":", "#", "__variant__", "__"]:
            if sep in prov_pid_str:
                parts = prov_pid_str.split(sep, 1)
                p_id = parts[0].strip()
                v_id = parts[1].strip() or None
                return p_id, v_id
        return prov_pid_str, None

    @staticmethod
    def _extract_variant_usd_price(v: Dict[str, Any]) -> float:
        prices = v.get("prices") or {}
        price_val = 0.0
        if isinstance(prices, dict):
            for k in ("reseller_usd", "sale_usd", "discounted_usd", "final_usd", "usd", "USD"):
                raw = prices.get(k)
                if raw is not None:
                    try:
                        val = float(raw)
                        if val > 0:
                            price_val = val
                            break
                    except Exception:
                        pass
            if price_val <= 0 and "vnd" in prices and prices["vnd"] is not None:
                try:
                    price_val = round(float(prices["vnd"]) / 25400.0, 2)
                except Exception:
                    pass
        elif isinstance(prices, (int, float, str)):
            try:
                price_val = float(prices)
            except Exception:
                pass
        if price_val <= 0:
            fallback = extract_price_from_dict(v)
            if fallback is not None and float(fallback) > 0:
                price_val = float(fallback)
        return max(0.0, float(price_val))

    def _update_cached_variant(self, cache_key: str, provider_product_id: Any, var_id: Optional[str], price: Optional[float] = None, stock: Optional[int] = None):
        if cache_key not in _ROBOTICVN_CATALOG_CACHE:
            return
        cached_list, _ = _ROBOTICVN_CATALOG_CACHE[cache_key]
        for p in cached_list:
            if matches_product_id(p, provider_product_id) or (var_id and p.get("variant_id") == var_id):
                if price is not None and price > 0:
                    p["price"] = float(price)
                    p["original_price"] = float(price)
                if stock is not None:
                    p["stock"] = int(stock)
                break

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "x-api-key": self.api_key,
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches master products from /api/v2/products and variants for each product.
        Uses in-memory caching (3 min), per-provider asyncio.Lock (prevents duplicate concurrent bursts),
        and polite rate-limiting (max 2 concurrent requests, 0.25s pause) to prevent rate limits.
        """
        cache_key = f"{self.base_url}:{self.api_key}"
        now_ts = time.time()

        # 1. Fast check before acquiring lock
        if not force_refresh and cache_key in _ROBOTICVN_CATALOG_CACHE:
            cached_list, cached_time = _ROBOTICVN_CATALOG_CACHE[cache_key]
            if (now_ts - cached_time) < _ROBOTICVN_CACHE_TTL and cached_list:
                logger.info(f"Serving Roboticvn catalog from memory cache ({len(cached_list)} products)")
                return cached_list

        lock = _ROBOTICVN_CATALOG_LOCKS.setdefault(cache_key, asyncio.Lock())
        async with lock:
            now_ts = time.time()
            if not force_refresh and cache_key in _ROBOTICVN_CATALOG_CACHE:
                cached_list, cached_time = _ROBOTICVN_CATALOG_CACHE[cache_key]
                if (now_ts - cached_time) < _ROBOTICVN_CACHE_TTL and cached_list:
                    logger.info(f"Serving Roboticvn catalog from memory cache ({len(cached_list)} products)")
                    return cached_list

            async def _fetch_master_products(s: aiohttp.ClientSession) -> List[Dict[str, Any]]:
                all_masters = []
                limit = 100
                offset = 0
                while True:
                    url = f"{self.api_v2_url}/products?limit={limit}&offset={offset}&locale=en-US"
                    try:
                        async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=20, connect=8)) as resp:
                            if resp.status == 200:
                                data = await resp.json(content_type=None)
                                items = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                                if not items:
                                    break
                                all_masters.extend(items)
                                meta = data.get("meta", {}) if isinstance(data, dict) else {}
                                total = meta.get("count") or meta.get("total")
                                if total and len(all_masters) >= total:
                                    break
                                if len(items) < limit:
                                    break
                                offset += limit
                            elif resp.status == 429:
                                logger.warning(f"Roboticvn rate limit (429) on products list. Sleeping 2.5s...")
                                await asyncio.sleep(2.5)
                                async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=20, connect=8)) as retry_resp:
                                    if retry_resp.status == 200:
                                        data = await retry_resp.json(content_type=None)
                                        items = data.get("data", []) if isinstance(data, dict) else []
                                        all_masters.extend(items)
                                break
                            else:
                                logger.warning(f"Roboticvn products list returned status {resp.status}")
                                break
                    except Exception as e:
                        logger.warning(f"Roboticvn master products fetch error on offset {offset}: {e}")
                        break
                return all_masters

            async def _fetch_single_product_variants(s: aiohttp.ClientSession, sem: asyncio.Semaphore, master_p: Dict[str, Any]) -> List[Dict[str, Any]]:
                m_id = str(master_p.get("id") or "").strip()
                if not m_id:
                    return []
                m_title = (master_p.get("title") or master_p.get("name") or "Product").strip()
                
                async with sem:
                    await asyncio.sleep(0.25)  # Polite pause between requests to prevent rate limit
                    url = f"{self.api_v2_url}/products/{m_id}?locale=en-US"
                    try:
                        async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=15, connect=6)) as resp:
                            if resp.status == 429:
                                logger.warning(f"Roboticvn rate limit (429) on product {m_id}. Pausing 2.5s...")
                                await asyncio.sleep(2.5)
                                async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=15, connect=6)) as retry_resp:
                                    resp = retry_resp

                            if resp.status == 200:
                                p_json = await resp.json(content_type=None)
                                p_data = p_json.get("data", {}) if isinstance(p_json, dict) else {}
                                if not isinstance(p_data, dict):
                                    return []
                                
                                p_title = (p_data.get("title") or m_title).strip()
                                p_desc = str(p_data.get("description") or "")
                                variants = p_data.get("variants") or []
                                
                                if not variants or not isinstance(variants, list):
                                    return [{
                                        "id": str(m_id),
                                        "name": p_title,
                                        "name_ar": p_title,
                                        "name_en": p_title,
                                        "name_ru": p_title,
                                        "description": p_desc,
                                        "description_ar": p_desc,
                                        "description_en": p_desc,
                                        "description_ru": p_desc,
                                        "price": self._extract_variant_usd_price(p_data),
                                        "original_price": self._extract_variant_usd_price(p_data),
                                        "stock": 0,
                                        "custom_emoji_id": None,
                                        "requires_email": False,
                                        "requiresEmailActivation": False
                                    }]
                                    
                                var_products = []
                                for v in variants:
                                    if not isinstance(v, dict):
                                        continue
                                    v_id = str(v.get("id") or "").strip()
                                    if not v_id:
                                        continue
                                    v_title = (v.get("title") or "").strip()
                                    
                                    if not v_title or v_title.lower() == p_title.lower():
                                        display_name = p_title
                                    elif p_title.lower() in v_title.lower():
                                        display_name = v_title
                                    else:
                                        display_name = f"{p_title} - {v_title}"
                                        
                                    price_val = self._extract_variant_usd_price(v)
                                        
                                    in_stock = bool(v.get("in_stock", True))
                                    avail_qty = v.get("available_quantity")
                                    stock_val = int(avail_qty) if in_stock and avail_qty is not None else (100 if in_stock else 0)
                                    
                                    v_desc = str(v.get("description") or p_desc or "")
                                    if v.get("delivery_instructions"):
                                        v_desc = (v_desc + "\n\nInstructions: " + str(v["delivery_instructions"])).strip()
                                    
                                    req_email = bool(v.get("manual_upgrade", False))
                                    composite_id = f"{m_id}:{v_id}"
                                    
                                    var_products.append({
                                        "id": composite_id,
                                        "variant_id": v_id,
                                        "master_id": m_id,
                                        "name": display_name,
                                        "name_ar": display_name,
                                        "name_en": display_name,
                                        "name_ru": display_name,
                                        "description": v_desc,
                                        "description_ar": v_desc,
                                        "description_en": v_desc,
                                        "description_ru": v_desc,
                                        "price": price_val,
                                        "original_price": price_val,
                                        "stock": stock_val,
                                        "custom_emoji_id": None,
                                        "requires_email": req_email,
                                        "requiresEmailActivation": req_email
                                    })
                                return var_products
                            else:
                                logger.warning(f"Failed to fetch Roboticvn product {m_id}: HTTP {resp.status}")
                    except Exception as e:
                        logger.warning(f"Error fetching Roboticvn detail for {m_id}: {e}")
                    return []

            async def _run(s: aiohttp.ClientSession) -> List[Dict[str, Any]]:
                masters = await _fetch_master_products(s)
                if not masters:
                    if cache_key in _ROBOTICVN_CATALOG_CACHE and _ROBOTICVN_CATALOG_CACHE[cache_key][0]:
                        logger.warning("Serving Roboticvn catalog from previous cache due to empty response")
                        return _ROBOTICVN_CATALOG_CACHE[cache_key][0]
                    return []
                
                # Use Semaphore(2) to prevent triggering Roboticvn rate limit
                sem = asyncio.Semaphore(2)
                tasks = [_fetch_single_product_variants(s, sem, m) for m in masters]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                final_catalog = []
                for r in results:
                    if isinstance(r, list):
                        final_catalog.extend(r)
                
                # Save to memory cache
                if final_catalog:
                    _ROBOTICVN_CATALOG_CACHE[cache_key] = (final_catalog, time.time())
                elif cache_key in _ROBOTICVN_CATALOG_CACHE and _ROBOTICVN_CATALOG_CACHE[cache_key][0]:
                    return _ROBOTICVN_CATALOG_CACHE[cache_key][0]

                return final_catalog

            if session:
                return await _run(session)
            else:
                async with aiohttp.ClientSession() as s:
                    return await _run(s)

    async def fetch_stock(self, provider_product_id: Any, session: Optional[aiohttp.ClientSession] = None) -> Optional[int]:
        """
        Fetches live stock using unexpired catalog cache (<= 60s), or live Quote / Product detail endpoint.
        """
        pid, var_id = self._parse_pid_and_variant(provider_product_id)
        cache_key = f"{self.base_url}:{self.api_key}"
        now_ts = time.time()
        
        # 1. Check in-memory catalog cache ONLY if fresh (<= 60s)
        if cache_key in _ROBOTICVN_CATALOG_CACHE:
            cached_list, cached_time = _ROBOTICVN_CATALOG_CACHE[cache_key]
            if (now_ts - cached_time) < min(_ROBOTICVN_CACHE_TTL, 60.0):
                for p in cached_list:
                    if matches_product_id(p, provider_product_id) or (var_id and p.get("variant_id") == var_id):
                        return int(p.get("stock", 0))

        async def _req(s: aiohttp.ClientSession):
            if pid and var_id:
                try:
                    q_url = f"{self.api_v2_url}/products/{pid}/quote"
                    q_payload = {
                        "variant_id": var_id,
                        "quantity": 1,
                        "currency_code": "usd"
                    }
                    async with s.post(q_url, headers=self.get_headers(), json=q_payload, timeout=aiohttp.ClientTimeout(total=8, connect=4)) as q_resp:
                        if q_resp.status == 200:
                            q_json = await q_resp.json(content_type=None)
                            q_data = q_json.get("data", {}) if isinstance(q_json, dict) else {}
                            u_price = q_data.get("unit_price")
                            live_p = float(u_price) if u_price is not None and float(u_price) > 0 else None
                            if q_data.get("can_purchase") is False:
                                self._update_cached_variant(cache_key, provider_product_id, var_id, price=live_p, stock=0)
                                return 0
                            avail = q_data.get("available_quantity")
                            if avail is not None:
                                self._update_cached_variant(cache_key, provider_product_id, var_id, price=live_p, stock=int(avail))
                                return int(avail)
                except Exception as e:
                    logger.debug(f"Roboticvn quote for stock failed: {e}")
                    
                try:
                    d_url = f"{self.api_v2_url}/products/{pid}?locale=en-US"
                    async with s.get(d_url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as d_resp:
                        if d_resp.status == 200:
                            d_json = await d_resp.json(content_type=None)
                            p_data = d_json.get("data", {}) if isinstance(d_json, dict) else {}
                            variants = p_data.get("variants") or []
                            for v in variants:
                                if str(v.get("id")) == str(var_id):
                                    in_stock = bool(v.get("in_stock", True))
                                    avail = v.get("available_quantity")
                                    stk = int(avail) if in_stock and avail is not None else (0 if not in_stock else 100)
                                    live_p = self._extract_variant_usd_price(v)
                                    self._update_cached_variant(cache_key, provider_product_id, var_id, price=(live_p if live_p > 0 else None), stock=stk)
                                    return stk
                except Exception as e:
                    logger.debug(f"Roboticvn product detail for stock failed: {e}")

            catalog = await self.fetch_catalog(s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, provider_product_id) or (var_id and p.get("variant_id") == var_id):
                        return int(p.get("stock", 0))
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_live_product_price(self, provider_product_id: Any, quantity: int = 1, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        """
        Fetches LIVE wholesale price in USD directly from Roboticvn Quote / Product Detail endpoint
        with a short 15-second per-item quote cache so price updates reflect immediately.
        """
        pid, var_id = self._parse_pid_and_variant(provider_product_id)
        cache_key = f"{self.base_url}:{self.api_key}"
        quote_key = (cache_key, pid, var_id, int(quantity))
        now_ts = time.time()

        # 1. Check short 15-second live quote cache (never return stale 15-min catalog price!)
        if quote_key in _ROBOTICVN_QUOTE_CACHE:
            q_price, q_ts = _ROBOTICVN_QUOTE_CACHE[quote_key]
            if (now_ts - q_ts) < _ROBOTICVN_QUOTE_TTL and q_price > 0:
                return q_price

        async def _req(s: aiohttp.ClientSession):
            if pid and var_id:
                try:
                    q_url = f"{self.api_v2_url}/products/{pid}/quote"
                    q_payload = {
                        "variant_id": var_id,
                        "quantity": int(quantity),
                        "currency_code": "usd"
                    }
                    async with s.post(q_url, headers=self.get_headers(), json=q_payload, timeout=aiohttp.ClientTimeout(total=8, connect=4)) as q_resp:
                        if q_resp.status == 200:
                            q_json = await q_resp.json(content_type=None)
                            q_data = q_json.get("data", {}) if isinstance(q_json, dict) else {}
                            u_price = q_data.get("unit_price")
                            if u_price is not None and float(u_price) > 0:
                                val = float(u_price)
                                _ROBOTICVN_QUOTE_CACHE[quote_key] = (val, time.time())
                                self._update_cached_variant(cache_key, provider_product_id, var_id, price=val)
                                return val
                            tot_p = q_data.get("total_price") or q_data.get("total")
                            if tot_p is not None and int(quantity) > 0:
                                t_val = float(tot_p)
                                if t_val > 0:
                                    val = round(t_val / int(quantity), 4)
                                    _ROBOTICVN_QUOTE_CACHE[quote_key] = (val, time.time())
                                    self._update_cached_variant(cache_key, provider_product_id, var_id, price=val)
                                    return val
                except Exception as e:
                    logger.debug(f"Roboticvn quote for price failed: {e}")
                    
                try:
                    d_url = f"{self.api_v2_url}/products/{pid}?locale=en-US"
                    async with s.get(d_url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as d_resp:
                        if d_resp.status == 200:
                            d_json = await d_resp.json(content_type=None)
                            p_data = d_json.get("data", {}) if isinstance(d_json, dict) else {}
                            variants = p_data.get("variants") or []
                            for v in variants:
                                if str(v.get("id")) == str(var_id):
                                    p_usd = self._extract_variant_usd_price(v)
                                    if p_usd > 0:
                                        _ROBOTICVN_QUOTE_CACHE[quote_key] = (p_usd, time.time())
                                        self._update_cached_variant(cache_key, provider_product_id, var_id, price=p_usd)
                                        return p_usd
                except Exception as e:
                    logger.debug(f"Roboticvn detail for price failed: {e}")

            catalog = await self.fetch_catalog(s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, provider_product_id) or (var_id and p.get("variant_id") == var_id):
                        return float(p.get("price", 0.0))
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        """
        Creates an order on Roboticvn paid from wallet balance and polls for delivery.
        POST /api/v2/orders
        GET /api/v2/orders/{id}/delivery
        """
        pid, var_id = self._parse_pid_and_variant(provider_product_id)
        
        async def _req(s: aiohttp.ClientSession):
            target_var_id = var_id
            
            if not target_var_id:
                try:
                    d_url = f"{self.api_v2_url}/products/{pid}?locale=en-US"
                    async with s.get(d_url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as d_resp:
                        if d_resp.status == 200:
                            d_json = await d_resp.json(content_type=None)
                            p_data = d_json.get("data", {}) if isinstance(d_json, dict) else {}
                            vars_list = p_data.get("variants") or []
                            if vars_list:
                                target_var_id = str(vars_list[0].get("id"))
                except Exception as e:
                    logger.warning(f"Failed to resolve variant for {pid}: {e}")
                    
            if not target_var_id:
                target_var_id = str(pid)

            item_payload: Dict[str, Any] = {
                "variant_id": target_var_id,
                "quantity": int(quantity)
            }
            if customer_email:
                email_list = parse_customer_emails(customer_email)
                if email_list:
                    if len(email_list) < int(quantity):
                        email_list = email_list + [email_list[-1]] * (int(quantity) - len(email_list))
                    item_payload["accounts"] = email_list[:int(quantity)]

            order_payload = {
                "items": [item_payload],
                "currency_code": "usd",
                "payment_method": "wallet"
            }

            order_url = f"{self.api_v2_url}/orders?locale=en-US"
            logger.info(f"Executing Roboticvn order on {order_url} with payload: {order_payload}")
            
            order_id = None
            async with s.post(order_url, headers=self.get_headers(), json=order_payload, timeout=aiohttp.ClientTimeout(total=30, connect=10)) as resp:
                if resp.status in [200, 201]:
                    res_json = await resp.json(content_type=None)
                    c_data = res_json.get("data", {}) if isinstance(res_json, dict) else {}
                    order_id = c_data.get("order_id") or c_data.get("checkout_id") or c_data.get("id")
                    logger.info(f"Roboticvn order created successfully: order_id={order_id}")
                else:
                    err_text = ""
                    try:
                        err_json = await resp.json(content_type=None)
                        if isinstance(err_json, dict):
                            err_text = err_json.get("error", {}).get("message") or err_json.get("message") or str(err_json)
                    except Exception:
                        err_text = await resp.text()
                    
                    err_l = str(err_text).lower()
                    if resp.status == 400 and ("wallet" in err_l or "balance" in err_l or "insufficient" in err_l):
                        raise Exception(f"Provider balance insufficient: {err_text}")
                    elif resp.status in [400, 409] and ("out of stock" in err_l or "stock" in err_l or "available" in err_l):
                        raise Exception(f"Out of stock ({err_text})")
                    else:
                        raise Exception(f"Provider error: {err_text or f'HTTP {resp.status}'}")

            if not order_id:
                raise Exception("Provider returned empty order ID")

            # Poll for delivery credentials
            delivery_url = f"{self.api_v2_url}/orders/{order_id}/delivery?locale=en-US"
            delivered_lines = []
            
            for attempt in range(8):
                await asyncio.sleep(2.5)
                try:
                    async with s.get(delivery_url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=10, connect=5)) as d_resp:
                        if d_resp.status == 200:
                            d_json = await d_resp.json(content_type=None)
                            accounts = d_json.get("deliveredAccount") or d_json.get("delivered_accounts") or []
                            if accounts and isinstance(accounts, list):
                                for acc_item in accounts:
                                    if isinstance(acc_item, dict):
                                        acc = (acc_item.get("account") or "").strip()
                                        pwd = (acc_item.get("password") or "").strip()
                                        info = (acc_item.get("additional_info") or "").strip()
                                        if acc and pwd:
                                            line = f"{acc}:{pwd}"
                                            if info:
                                                line += f" | {info}"
                                            delivered_lines.append(line)
                                        elif acc:
                                            line = acc
                                            if info:
                                                line += f" | {info}"
                                            delivered_lines.append(line)
                                        elif info:
                                            delivered_lines.append(info)
                                        else:
                                            delivered_lines.append(json.dumps(acc_item))
                                    elif isinstance(acc_item, str) and acc_item.strip():
                                        delivered_lines.append(acc_item.strip())
                                if delivered_lines:
                                    break
                except Exception as de:
                    logger.debug(f"Polling delivery for order {order_id} failed on attempt {attempt+1}: {de}")

            if delivered_lines:
                return delivered_lines

            try:
                stat_url = f"{self.api_v2_url}/orders/{order_id}?locale=en-US"
                async with s.get(stat_url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as s_resp:
                    if s_resp.status == 200:
                        s_json = await s_resp.json(content_type=None)
                        s_data = s_json.get("data", {}) if isinstance(s_json, dict) else {}
                        upg_stat = s_data.get("upgrade_status")
                        if upg_stat in ["pending", "processing"]:
                            return [f"Roboticvn Order #{order_id} (Manual Upgrade in progress)"]
            except Exception:
                pass

            return [f"Roboticvn Order #{order_id} Completed Successfully"]

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 8. Aitoolify / Reseller API v1 Adapter (https://noman304044.aitoolifystudio.io/docs)
# -------------------------------------------------------------------------
_AITOOLIFY_CATALOG_CACHE: Dict[str, Tuple[List[Dict[str, Any]], float]] = {}
_AITOOLIFY_CATALOG_LOCKS: Dict[str, asyncio.Lock] = {}
_AITOOLIFY_CACHE_TTL = 20.0  # 20s TTL (well within 120 req/min limit)


class AitoolifyProviderAdapter(BaseProviderAdapter):
    """
    Reseller API v1 Adapter (Aitoolify Studio / @netflixslotssellbot compatible).
    Docs: https://noman304044.aitoolifystudio.io/docs
    Endpoints:
    - GET  /api/reseller/v1/balance
    - GET  /api/reseller/v1/products
    - POST /api/reseller/v1/order
    - GET  /api/reseller/v1/orders?limit=50
    - GET  /api/reseller/v1/order/{order_ref}
    """
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        self.provider_type = "aitoolify"
        clean = self.base_url.rstrip("/")
        if clean.endswith("/api/reseller/v1"):
            self.api_v1_url = clean
        elif "/api/reseller/v1" in clean:
            self.api_v1_url = clean.split("/api/reseller/v1")[0] + "/api/reseller/v1"
        else:
            self.api_v1_url = f"{clean}/api/reseller/v1"

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _standardize_aitoolify_catalog(self, raw_list: List[Any]) -> List[Dict[str, Any]]:
        formatted = []
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None
        custom_stock_field = (self.field_mapping.get("stock_field") or "").strip() or None

        for p in raw_list:
            if not isinstance(p, dict):
                continue
            p_id = p.get("id")
            if p_id is None:
                continue

            p_name = (p.get("name") or p.get("title") or f"Product #{p_id}").strip()
            p_desc = str(p.get("description") or "")
            if p.get("duration") and str(p.get("duration")).strip():
                p_desc = f"{p_desc}\n⏱️ Duration: {p['duration']}".strip()

            # Prefer your_cost (what wallet is actually charged), then cost, price_usdt, price
            price_val = None
            if custom_price_field and p.get(custom_price_field) is not None:
                price_val = extract_price_from_dict(p, custom_field=custom_price_field)
            if price_val is None or float(price_val) <= 0:
                for pk in ("your_cost", "cost", "price_usdt", "price"):
                    raw_pv = p.get(pk)
                    if raw_pv is not None:
                        try:
                            fv = float(raw_pv)
                            if fv > 0:
                                price_val = fv
                                break
                        except Exception:
                            pass
            if price_val is None:
                price_val = float(extract_price_from_dict(p) or 0.0)
            price_val = float(price_val or 0.0)

            orig_p = float(p.get("price_usdt") or p.get("price") or price_val or 0.0)

            # Unlimited slot/manual products return is_unlimited=True and stock=None
            if custom_stock_field and p.get(custom_stock_field) is not None:
                stock_val = extract_stock_from_dict(p, allow_boolean=True, custom_field=custom_stock_field) or 0
            elif p.get("is_unlimited") is True:
                stock_val = 999
            else:
                raw_stk = p.get("stock_quantity") if p.get("stock_quantity") is not None else (
                    p.get("stock") if p.get("stock") is not None else p.get("quantity")
                )
                try:
                    stock_val = max(0, int(raw_stk)) if raw_stk is not None else 0
                except Exception:
                    stock_val = 0

            req_email = bool(p.get("requires_email", False))

            formatted.append({
                "id": str(p_id),
                "name": p_name,
                "name_ar": p.get("name_ar") or p_name,
                "name_en": p.get("name_en") or p_name,
                "name_ru": p.get("name_ru") or p_name,
                "description": p_desc,
                "description_ar": str(p.get("description_ar") or p_desc),
                "description_en": str(p.get("description_en") or p_desc),
                "description_ru": str(p.get("description_ru") or p_desc),
                "price": price_val,
                "original_price": orig_p if orig_p > 0 else price_val,
                "stock": stock_val,
                "is_unlimited": bool(p.get("is_unlimited", False)),
                "custom_emoji_id": p.get("custom_emoji_id"),
                "requires_email": req_email,
                "requiresEmailActivation": req_email
            })
        return formatted

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        cache_key = f"{self.api_v1_url}:{self.api_key}"
        now_ts = time.time()

        if not force_refresh and cache_key in _AITOOLIFY_CATALOG_CACHE:
            cached_list, cached_time = _AITOOLIFY_CATALOG_CACHE[cache_key]
            if (now_ts - cached_time) < _AITOOLIFY_CACHE_TTL and cached_list is not None:
                return cached_list

        lock = _AITOOLIFY_CATALOG_LOCKS.setdefault(cache_key, asyncio.Lock())
        async with lock:
            now_ts = time.time()
            if not force_refresh and cache_key in _AITOOLIFY_CATALOG_CACHE:
                cached_list, cached_time = _AITOOLIFY_CATALOG_CACHE[cache_key]
                if (now_ts - cached_time) < _AITOOLIFY_CACHE_TTL and cached_list is not None:
                    return cached_list

            url = f"{self.api_v1_url}/products"

            async def _req(s: aiohttp.ClientSession):
                for attempt in range(2):
                    try:
                        async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=20, connect=8)) as resp:
                            if resp.status == 200:
                                data = await resp.json(content_type=None)
                                raw_list = extract_products_list_from_json(data)
                                standardized = self._standardize_aitoolify_catalog(raw_list or [])
                                _AITOOLIFY_CATALOG_CACHE[cache_key] = (standardized, time.time())
                                return standardized
                            elif resp.status == 429 and attempt == 0:
                                logger.warning("Aitoolify rate limit (429) on /products. Retrying after 2.5s...")
                                await asyncio.sleep(2.5)
                                continue
                            else:
                                logger.warning(f"Aitoolify catalog {url} returned HTTP {resp.status}")
                                break
                    except Exception as e:
                        logger.warning(f"Aitoolify catalog fetch error: {e}")
                        if attempt == 0:
                            await asyncio.sleep(0.5)
                if cache_key in _AITOOLIFY_CATALOG_CACHE:
                    return _AITOOLIFY_CATALOG_CACHE[cache_key][0]
                return None

            if session:
                return await _req(session)
            else:
                async with aiohttp.ClientSession() as s:
                    return await _req(s)

    async def fetch_stock(self, provider_product_id: Any, session: Optional[aiohttp.ClientSession] = None) -> Optional[int]:
        prov_pid = str(provider_product_id).strip()
        catalog = await self.fetch_catalog(session=session)
        if catalog:
            for p in catalog:
                if matches_product_id(p, prov_pid):
                    return int(p.get("stock", 0))
        return None

    async def fetch_live_product_price(self, provider_product_id: Any, quantity: int = 1, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        prov_pid = str(provider_product_id).strip()
        cache_key = f"{self.api_v1_url}:{self.api_key}"
        now_ts = time.time()
        # Use fresh catalog (refresh if older than 5s so live your_cost changes reflect immediately)
        use_force = True
        if cache_key in _AITOOLIFY_CATALOG_CACHE:
            _, cached_time = _AITOOLIFY_CATALOG_CACHE[cache_key]
            if (now_ts - cached_time) < 5.0:
                use_force = False

        catalog = await self.fetch_catalog(session=session, force_refresh=use_force)
        if catalog:
            for p in catalog:
                if matches_product_id(p, prov_pid):
                    return float(p.get("price", 0.0))
        return None

    async def fetch_balance(self, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.api_v1_url}/balance"

        async def _req(s: aiohttp.ClientSession):
            try:
                async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if isinstance(data, dict):
                            return data
            except Exception as e:
                logger.debug(f"Aitoolify balance fetch failed: {e}")
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
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        """
        Places an order via POST /api/reseller/v1/order using idempotency_key.
        Handles comma-separated customer_email strings and pending_invite deliveries cleanly.
        """
        prov_pid = str(provider_product_id).strip()
        item_id = int(prov_pid) if prov_pid.isdigit() else prov_pid
        order_ref = str(client_order_ref or f"BOT_{int(time.time())}_{uuid.uuid4().hex[:8]}")[:120]

        payload: Dict[str, Any] = {
            "product_id": item_id,
            "quantity": int(quantity),
            "idempotency_key": order_ref
        }
        custom_qty = (self.field_mapping.get("buy_qty_field") or "").strip()
        if custom_qty:
            payload[custom_qty] = int(quantity)
        custom_pid = (self.field_mapping.get("buy_pid_field") or "").strip()
        if custom_pid:
            payload[custom_pid] = item_id

        if customer_email:
            email_list = parse_customer_emails(customer_email)
            if email_list:
                if len(email_list) < int(quantity):
                    email_list = email_list + [email_list[-1]] * (int(quantity) - len(email_list))
                payload["customer_email"] = ",".join(email_list[:int(quantity)])

        ep_list = self._get_custom_buy_endpoints([f"{self.api_v1_url}/order"])
        ep = ep_list[0]
        headers = self.get_headers({"Idempotency-Key": order_ref})

        async def _req(s: aiohttp.ClientSession):
            last_err = "No response from provider"
            for attempt in range(2):
                try:
                    logger.info(f"Executing Aitoolify Reseller v1 order on {ep} with payload: {payload}")
                    async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60, connect=10)) as resp:
                        if resp.status in [200, 201]:
                            data = await resp.json(content_type=None)
                            if not isinstance(data, dict):
                                return [str(data)]

                            delivered = data.get("delivered")
                            if isinstance(delivered, list) and delivered:
                                items = [str(it).strip() for it in delivered if str(it).strip()]
                                if items:
                                    return items

                            status_str = str(data.get("status") or "").lower()
                            remote_ref = data.get("order_ref") or order_ref

                            # If pending_invite / pending delivery, briefly poll GET /order/{order_ref}
                            if status_str in ["pending_invite", "pending", "processing"] and remote_ref:
                                poll_url = f"{self.api_v1_url}/order/{remote_ref}"
                                for _ in range(2):
                                    await asyncio.sleep(2.0)
                                    try:
                                        async with s.get(poll_url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=10, connect=5)) as p_resp:
                                            if p_resp.status == 200:
                                                p_data = await p_resp.json(content_type=None)
                                                if isinstance(p_data, dict):
                                                    p_deliv = p_data.get("delivered")
                                                    if isinstance(p_deliv, list) and p_deliv:
                                                        items = [str(it).strip() for it in p_deliv if str(it).strip()]
                                                        if items:
                                                            return items
                                                    p_stat = str(p_data.get("status") or "").lower()
                                                    if p_stat:
                                                        status_str = p_stat
                                    except Exception:
                                        pass
                                email_note = f" — Email: {payload['customer_email']}" if payload.get("customer_email") else ""
                                return [f"✅ Order #{remote_ref} Queued ({status_str.upper()}){email_note} | Seller will deliver shortly"]

                            if data.get("success"):
                                return [f"Order #{remote_ref} Completed Successfully"]
                            raise Exception("Provider returned empty delivery data")

                        # Parse structured error JSON
                        err_code = ""
                        err_msg = ""
                        try:
                            err_json = await resp.json(content_type=None)
                            if isinstance(err_json, dict):
                                err_code = str(err_json.get("error_code") or "").upper()
                                err_msg = str(err_json.get("error") or err_json.get("message") or "")
                        except Exception:
                            err_msg = (await resp.text())[:200]

                        last_err = f"{err_code}: {err_msg}".strip(": ") or f"HTTP {resp.status}"
                        err_lower = last_err.lower()

                        if resp.status == 402 or err_code == "INSUFFICIENT_BALANCE":
                            raise Exception(f"Provider balance insufficient: {err_msg or last_err}")
                        elif resp.status == 409 or err_code == "OUT_OF_STOCK":
                            raise Exception(f"Out of stock ({err_msg or last_err})")
                        elif err_code in ["CUSTOMER_EMAIL_REQUIRED", "INVALID_CUSTOMER_EMAIL"] or "email" in err_lower:
                            raise Exception(f"Provider requires email: {err_msg or last_err}")
                        elif resp.status in [401, 403, 404, 503] or err_code in ["AUTH_HEADER_REQUIRED", "INVALID_API_KEY", "KEY_BLOCKED", "ACCOUNT_BLOCKED", "PRODUCT_NOT_FOUND", "API_DISABLED"]:
                            raise Exception(f"Provider error: {last_err}")
                        elif (resp.status == 429 or err_code == "RATE_LIMITED" or resp.status >= 500) and attempt == 0:
                            # Safe retry using the EXACT same idempotency_key
                            logger.warning(f"Aitoolify order returned {resp.status} ({err_code}), safely retrying with same idempotency_key...")
                            await asyncio.sleep(2.5)
                            continue
                        else:
                            raise Exception(f"Provider error: {last_err}")
                except (aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as conn_err:
                    last_err = str(conn_err)
                    if attempt == 0:
                        logger.warning(f"Aitoolify connection error on {ep}, retrying safely with same idempotency_key: {conn_err}")
                        await asyncio.sleep(1.5)
                        continue
                    raise Exception(f"Cannot connect to provider: {last_err}")
                except Exception as ex:
                    raise ex
            raise Exception(f"Provider error: {last_err}")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 9. Canboso Telegram Buyer API v2 Adapter (https://canboso.com/api/swagger)
# -------------------------------------------------------------------------
_CANBOSO_CATALOG_CACHE: Dict[str, Tuple[List[Dict[str, Any]], float]] = {}
_CANBOSO_CATALOG_LOCKS: Dict[str, asyncio.Lock] = {}
_CANBOSO_RATE_UNTIL: Dict[str, float] = {}
_CANBOSO_USD_RATE_CACHE: Dict[str, Tuple[float, float]] = {}
_CANBOSO_CACHE_TTL = 90.0  # 90s TTL (well under 30 req/60s quota to prevent escalating 429 penalties)
_CANBOSO_USD_RATE_TTL = 600.0

class CanbosoProviderAdapter(BaseProviderAdapter):
    """
    Canboso Buyer API v2.2.0 Adapter.
    Docs: https://canboso.com/api/swagger
    Supports /api/v2/telegram-buyer/{products, balance, orders, purchase}.
    """
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        clean_base = self.base_url.rstrip('/')
        if clean_base.lower().endswith('/api/v2/telegram-buyer'):
            self.api_v2_url = clean_base
        else:
            self.api_v2_url = f"{clean_base}/api/v2/telegram-buyer"
        self.provider_type = "canboso"

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "x-buyer-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _handle_rate_limit(self, cache_key: str, resp: aiohttp.ClientResponse, err_json: Optional[dict] = None) -> int:
        retry_after = 15
        try:
            ra_hdr = resp.headers.get("Retry-After")
            if ra_hdr and str(ra_hdr).isdigit():
                retry_after = max(1, int(ra_hdr))
            elif isinstance(err_json, dict):
                rl = err_json.get("rateLimit") or {}
                if isinstance(rl, dict) and rl.get("retryAfter"):
                    retry_after = max(1, int(rl["retryAfter"]))
        except Exception:
            pass
        _CANBOSO_RATE_UNTIL[cache_key] = time.time() + min(retry_after, 3600)
        logger.warning(f"Canboso rate limited (429). Cooling down for {retry_after}s.")
        return retry_after

    async def _get_vnd_to_usd_rate(self, session: aiohttp.ClientSession) -> float:
        cache_key = f"{self.api_v2_url}:{self.api_key}"
        now_ts = time.time()
        if cache_key in _CANBOSO_USD_RATE_CACHE:
            rate_val, ts = _CANBOSO_USD_RATE_CACHE[cache_key]
            if (now_ts - ts) < _CANBOSO_USD_RATE_TTL and rate_val > 0:
                return rate_val
        bal = await self.fetch_balance(session=session)
        if isinstance(bal, dict):
            try:
                rate = float(bal.get("usdRate") or 0)
                if rate > 0:
                    _CANBOSO_USD_RATE_CACHE[cache_key] = (rate, time.time())
                    return rate
            except Exception:
                pass
        return 25400.0

    def _standardize_canboso_catalog(self, raw_products: List[Any], wallet_currency: str = "USD", usd_rate: float = 25400.0) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None
        custom_stock_field = (self.field_mapping.get("stock_field") or "").strip() or None

        for p in raw_products:
            if not isinstance(p, dict):
                continue
            p_id = str(p.get("productId") or p.get("id") or "").strip()
            if not p_id:
                continue

            p_name = str(p.get("name") or f"Product #{p_id}").strip()
            p_desc = str(p.get("description") or "").strip()
            prod_type = str(p.get("productType") or "account").strip().lower()
            reqs = p.get("purchaseRequirements") if isinstance(p.get("purchaseRequirements"), dict) else {}

            if reqs.get("allowedMonths"):
                months_str = ", ".join(str(m) for m in reqs["allowedMonths"])
                note = f"Allowed durations (months): {months_str}"
                p_desc = f"{p_desc}\n⏱️ {note}".strip() if p_desc else f"⏱️ {note}"

            # Extract price & normalize VND -> USD if wallet/price is VND
            price_usd = None
            if custom_price_field and p.get(custom_price_field) is not None:
                price_usd = extract_price_from_dict(p, custom_field=custom_price_field)
            if price_usd is None:
                price_obj = p.get("price")
                if isinstance(price_obj, dict):
                    raw_amt = float(price_obj.get("amount") or 0.0)
                    p_curr = str(price_obj.get("currency") or wallet_currency or "USD").upper()
                    if raw_amt > 0:
                        if p_curr == "VND":
                            div_rate = usd_rate if usd_rate > 0 else 25400.0
                            price_usd = round(raw_amt / div_rate, 2)
                            if price_usd <= 0:
                                price_usd = 0.01
                        else:
                            price_usd = round(raw_amt, 4)
                    else:
                        price_usd = 0.0
                else:
                    price_usd = float(extract_price_from_dict(p) or 0.0)
            price_usd = float(price_usd or 0.0)

            # Extract availability/stock
            avail_obj = p.get("availability") if isinstance(p.get("availability"), dict) else {}
            raw_avail = avail_obj.get("available")
            is_unlimited = False
            if custom_stock_field and p.get(custom_stock_field) is not None:
                stock_val = extract_stock_from_dict(p, allow_boolean=True, custom_field=custom_stock_field) or 0
            elif raw_avail is None:
                if prod_type in ("slot", "upgrade_account") or p_id == "slot_chatgpt_business":
                    stock_val = 999
                    is_unlimited = True
                else:
                    stock_val = 0
            else:
                try:
                    stock_val = max(0, int(raw_avail))
                except Exception:
                    stock_val = 0

            req_email = bool(
                reqs.get("customerEmail")
                or reqs.get("customerAccounts")
                or prod_type in ("slot", "upgrade_account")
                or p_id == "slot_chatgpt_business"
            )

            formatted.append({
                "id": p_id,
                "productId": p_id,
                "name": p_name,
                "name_ar": p_name,
                "name_en": p_name,
                "name_ru": p_name,
                "description": p_desc,
                "description_ar": p_desc,
                "description_en": p_desc,
                "description_ru": p_desc,
                "price": price_usd,
                "stock": stock_val,
                "is_unlimited": is_unlimited,
                "product_type": prod_type,
                "purchase_requirements": reqs,
                "requires_email": req_email,
                "requiresEmailActivation": req_email
            })
        return formatted

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        cache_key = f"{self.api_v2_url}:{self.api_key}"
        now_ts = time.time()

        # Respect active 429 cooldown
        if now_ts < _CANBOSO_RATE_UNTIL.get(cache_key, 0):
            if cache_key in _CANBOSO_CATALOG_CACHE:
                return _CANBOSO_CATALOG_CACHE[cache_key][0]
            return None

        if not force_refresh and cache_key in _CANBOSO_CATALOG_CACHE:
            cached_list, cached_time = _CANBOSO_CATALOG_CACHE[cache_key]
            if (now_ts - cached_time) < _CANBOSO_CACHE_TTL and cached_list is not None:
                return cached_list

        lock = _CANBOSO_CATALOG_LOCKS.setdefault(cache_key, asyncio.Lock())
        async with lock:
            now_ts = time.time()
            if now_ts < _CANBOSO_RATE_UNTIL.get(cache_key, 0):
                if cache_key in _CANBOSO_CATALOG_CACHE:
                    return _CANBOSO_CATALOG_CACHE[cache_key][0]
                return None

            if not force_refresh and cache_key in _CANBOSO_CATALOG_CACHE:
                cached_list, cached_time = _CANBOSO_CATALOG_CACHE[cache_key]
                if (now_ts - cached_time) < _CANBOSO_CACHE_TTL and cached_list is not None:
                    return cached_list

            url = f"{self.api_v2_url}/products"
            params = {"key": self.api_key}

            async def _req(s: aiohttp.ClientSession):
                try:
                    async with s.get(url, headers=self.get_headers(), params=params, timeout=aiohttp.ClientTimeout(total=15, connect=6)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if not isinstance(data, dict):
                                return None
                            raw_list = data.get("products") if isinstance(data.get("products"), list) else extract_products_list_from_json(data)
                            wallet_curr = str(data.get("walletCurrency") or "USD").upper()
                            usd_rate = 25400.0
                            needs_vnd = wallet_curr == "VND" or any(
                                isinstance(it, dict) and isinstance(it.get("price"), dict) and str(it["price"].get("currency") or "").upper() == "VND"
                                for it in (raw_list or [])
                            )
                            if needs_vnd:
                                usd_rate = await self._get_vnd_to_usd_rate(s)
                            standardized = self._standardize_canboso_catalog(raw_list or [], wallet_currency=wallet_curr, usd_rate=usd_rate)
                            _CANBOSO_CATALOG_CACHE[cache_key] = (standardized, time.time())
                            return standardized
                        elif resp.status == 429:
                            err_json = None
                            try:
                                err_json = await resp.json(content_type=None)
                            except Exception:
                                pass
                            self._handle_rate_limit(cache_key, resp, err_json)
                            if cache_key in _CANBOSO_CATALOG_CACHE:
                                return _CANBOSO_CATALOG_CACHE[cache_key][0]
                            return None
                        elif resp.status in (401, 403):
                            logger.warning(f"Canboso auth failed ({resp.status}) on {url}")
                            return None
                        else:
                            logger.warning(f"Canboso catalog {url} returned HTTP {resp.status}")
                except Exception as e:
                    logger.warning(f"Canboso catalog fetch error: {e}")

                if cache_key in _CANBOSO_CATALOG_CACHE:
                    return _CANBOSO_CATALOG_CACHE[cache_key][0]
                return None

            if session:
                return await _req(session)
            else:
                async with aiohttp.ClientSession() as s:
                    return await _req(s)

    def _get_cached_product_meta(self, provider_product_id: Any) -> Optional[Dict[str, Any]]:
        cache_key = f"{self.api_v2_url}:{self.api_key}"
        if cache_key not in _CANBOSO_CATALOG_CACHE:
            return None
        cached_list, _ = _CANBOSO_CATALOG_CACHE[cache_key]
        for p in (cached_list or []):
            if matches_product_id(p, provider_product_id):
                return p
        return None

    async def fetch_stock(self, provider_product_id: Any, session: Optional[aiohttp.ClientSession] = None) -> Optional[int]:
        prov_pid = str(provider_product_id).strip()
        catalog = await self.fetch_catalog(session=session)
        if catalog:
            for p in catalog:
                if matches_product_id(p, prov_pid):
                    return int(p.get("stock", 0))
        return None

    async def fetch_live_product_price(self, provider_product_id: Any, quantity: int = 1, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        prov_pid = str(provider_product_id).strip()
        cache_key = f"{self.api_v2_url}:{self.api_key}"
        now_ts = time.time()
        use_force = False
        # Only refresh if cache is missing or > 15s old (respect 30 req/60s quota)
        if cache_key not in _CANBOSO_CATALOG_CACHE or (now_ts - _CANBOSO_CATALOG_CACHE[cache_key][1]) > 15.0:
            use_force = now_ts >= _CANBOSO_RATE_UNTIL.get(cache_key, 0)
        catalog = await self.fetch_catalog(session=session, force_refresh=use_force)
        if catalog:
            for p in catalog:
                if matches_product_id(p, prov_pid):
                    return float(p.get("price", 0.0))
        return None

    async def fetch_balance(self, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
        cache_key = f"{self.api_v2_url}:{self.api_key}"
        if time.time() < _CANBOSO_RATE_UNTIL.get(cache_key, 0):
            return None
        url = f"{self.api_v2_url}/balance"
        params = {"key": self.api_key}

        async def _req(s: aiohttp.ClientSession):
            try:
                async with s.get(url, headers=self.get_headers(), params=params, timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if isinstance(data, dict):
                            return data
                    elif resp.status == 429:
                        try:
                            err_json = await resp.json(content_type=None)
                        except Exception:
                            err_json = None
                        self._handle_rate_limit(cache_key, resp, err_json)
            except Exception as e:
                logger.debug(f"Canboso balance fetch failed: {e}")
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    def _format_delivered_accounts(self, accounts: List[Any]) -> List[str]:
        delivered_lines: List[str] = []
        for acc_item in accounts:
            if isinstance(acc_item, dict):
                user_val = str(acc_item.get("user") or "").strip()
                pwd_val = str(acc_item.get("password") or "").strip()
                verify_email = str(acc_item.get("verifyEmail") or "").strip()
                expiry_text = str(acc_item.get("expiryText") or "").strip()
                other_info = str(acc_item.get("otherInfo") or "").strip()

                if user_val and pwd_val:
                    line = f"{user_val}:{pwd_val}"
                elif user_val:
                    line = user_val
                else:
                    line = ""

                extras = []
                if verify_email:
                    extras.append(f"Verify: {verify_email}")
                if expiry_text:
                    extras.append(f"Exp: {expiry_text}")
                if other_info:
                    extras.append(other_info)

                if extras:
                    line = f"{line} | {' | '.join(extras)}" if line else " | ".join(extras)
                if line:
                    delivered_lines.append(line)
                else:
                    delivered_lines.append(json.dumps(acc_item, ensure_ascii=False))
            elif isinstance(acc_item, str) and acc_item.strip():
                delivered_lines.append(acc_item.strip())
        return delivered_lines

    async def execute_order(
        self,
        provider_product_id: Any,
        quantity: int,
        expected_price: Optional[float] = None,
        client_order_ref: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        """
        Places an order via POST /api/v2/telegram-buyer/purchase using Idempotency-Key.
        Supports account, slot_chatgpt_business, catalog slot, and upgrade_account flows.
        """
        prov_pid = str(provider_product_id).strip()
        qty = max(1, int(quantity))
        cache_key = f"{self.api_v2_url}:{self.api_key}"

        raw_ref = str(client_order_ref or f"canboso-{int(time.time())}-{uuid.uuid4().hex[:8]}").strip()
        if len(raw_ref) < 8:
            raw_ref = f"canboso-{raw_ref}-{uuid.uuid4().hex[:6]}"
        idempotency_key = raw_ref[:128]

        meta = self._get_cached_product_meta(prov_pid)
        if not meta:
            try:
                await self.fetch_catalog(session=session)
                meta = self._get_cached_product_meta(prov_pid)
            except Exception:
                meta = None

        prod_type = str((meta or {}).get("product_type") or "account").lower()
        reqs = (meta or {}).get("purchase_requirements") or {}
        if not isinstance(reqs, dict):
            reqs = {}

        is_slot_flow = (
            prov_pid == "slot_chatgpt_business"
            or prod_type == "slot"
            or (reqs.get("customerEmail") and not reqs.get("customerAccounts"))
        )
        is_upgrade_flow = (prod_type == "upgrade_account" or bool(reqs.get("customerAccounts")))
        email_list = parse_customer_emails(customer_email)

        ep = f"{self.api_v2_url}/purchase"

        async def _send_single_purchase(s: aiohttp.ClientSession, req_payload: Dict[str, Any], idem_key: str) -> List[str]:
            headers = self.get_headers({"Idempotency-Key": idem_key})
            last_err = "No response from Canboso"
            for attempt in range(2):
                try:
                    safe_log_payload = {k: ("***" if k == "key" else v) for k, v in req_payload.items()}
                    logger.info(f"Executing Canboso order on {ep} with payload: {safe_log_payload}")
                    async with s.post(ep, headers=headers, json=req_payload, timeout=aiohttp.ClientTimeout(total=45, connect=10)) as resp:
                        if resp.status in [200, 201]:
                            data = await resp.json(content_type=None)
                            if not isinstance(data, dict):
                                return [str(data)]

                            delivery = data.get("delivery") or {}
                            accounts = delivery.get("accounts") if isinstance(delivery, dict) else None
                            if isinstance(accounts, list) and accounts:
                                formatted = self._format_delivered_accounts(accounts)
                                if formatted:
                                    return formatted

                            order = data.get("order") or {}
                            order_code = order.get("orderCode") or idem_key
                            fulfillment = str(order.get("fulfillmentStatus") or order.get("status") or "completed").strip()
                            target = req_payload.get("customer_email") or (", ".join(req_payload.get("customer_accounts") or []))
                            if target:
                                return [f"✅ Canboso Order #{order_code} ({fulfillment}) | Account: {target}"]
                            return [f"✅ Canboso Order #{order_code} ({fulfillment})"]

                        err_json = None
                        err_code = ""
                        err_msg = ""
                        try:
                            err_json = await resp.json(content_type=None)
                            if isinstance(err_json, dict):
                                err_code = str(err_json.get("code") or "").upper()
                                err_msg = str(err_json.get("message") or "")
                        except Exception:
                            err_msg = (await resp.text())[:200]

                        last_err = f"{err_code}: {err_msg}".strip(": ") or f"HTTP {resp.status}"
                        err_l = last_err.lower()

                        if resp.status == 429:
                            retry_after = self._handle_rate_limit(cache_key, resp, err_json)
                            if attempt == 0 and retry_after <= 5:
                                await asyncio.sleep(retry_after)
                                continue
                            raise Exception(f"Canboso rate limit exceeded (retry after {retry_after}s): {err_msg}")
                        elif resp.status == 400 and ("balance" in err_l or "enough" in err_l):
                            raise Exception(f"Provider balance insufficient: {err_msg or last_err}")
                        elif resp.status == 400 and ("customer_email" in err_l or "customer_accounts" in err_l or "email" in err_l):
                            raise Exception(f"Provider requires email: {err_msg or last_err}")
                        elif resp.status == 409:
                            if "inventory" in err_l or "stock" in err_l or "enough" in err_l:
                                raise Exception(f"Out of stock ({err_msg or last_err})")
                            raise Exception(f"Provider conflict: {err_msg or last_err}")
                        elif resp.status in (401, 403, 404):
                            raise Exception(f"Provider error: {last_err}")
                        elif resp.status >= 500 and attempt == 0:
                            logger.warning(f"Canboso order returned HTTP {resp.status}, retrying once with same Idempotency-Key...")
                            await asyncio.sleep(2.0)
                            continue
                        else:
                            raise Exception(f"Provider error: {last_err}")
                except (aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as conn_err:
                    last_err = str(conn_err)
                    if attempt == 0:
                        logger.warning(f"Canboso connection error on {ep}, retrying safely with same Idempotency-Key: {conn_err}")
                        await asyncio.sleep(1.5)
                        continue
                    raise Exception(f"Cannot connect to provider: {last_err}")
                except Exception as ex:
                    raise ex
            raise Exception(f"Provider error: {last_err}")

        async def _req(s: aiohttp.ClientSession):
            if is_slot_flow:
                if not email_list:
                    raise Exception("Provider requires email: customer_email is required for slot product")

                allowed_months = reqs.get("allowedMonths") or [1, 3, 6, 12]
                slot_months = None
                if prov_pid == "slot_chatgpt_business":
                    cfg_months = self.field_mapping.get("slot_months")
                    try:
                        slot_months = int(cfg_months) if cfg_months else (1 if 1 in allowed_months else int(allowed_months[0]))
                    except Exception:
                        slot_months = int(allowed_months[0]) if allowed_months else 1
                    if allowed_months and slot_months not in allowed_months:
                        slot_months = int(allowed_months[0])

                all_delivered: List[str] = []
                for idx in range(qty):
                    target_email = email_list[idx] if idx < len(email_list) else email_list[-1]
                    req_payload: Dict[str, Any] = {
                        "key": self.api_key,
                        "product_id": prov_pid,
                        "quantity": 1,
                        "customer_email": target_email,
                    }
                    if slot_months is not None:
                        req_payload["slot_months"] = slot_months
                    sub_idem = idempotency_key if qty == 1 else f"{idempotency_key[:115]}-{idx + 1}"
                    try:
                        items = await _send_single_purchase(s, req_payload, sub_idem)
                        all_delivered.extend(items)
                    except Exception as slot_err:
                        if all_delivered:
                            logger.warning(f"Canboso partial slot loop stopped at {idx + 1}/{qty}: {slot_err}")
                            break
                        raise slot_err
                return all_delivered

            payload: Dict[str, Any] = {
                "key": self.api_key,
                "product_id": prov_pid,
                "quantity": qty
            }
            if is_upgrade_flow:
                if not email_list:
                    raise Exception("Provider requires email: customer_accounts is required for upgrade product")
                if len(email_list) < qty:
                    raise Exception(f"Provider requires email: Please provide {qty} unique account emails (got {len(email_list)})")
                payload["customer_accounts"] = email_list[:qty]
            elif email_list:
                payload["customer_email"] = email_list[0]

            return await _send_single_purchase(s, payload, idempotency_key)

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# 10. DigitalCore API Adapter (https://digitalcore.top/docs)
# -------------------------------------------------------------------------
_DIGITALCORE_CATALOG_CACHE: Dict[str, Tuple[List[Dict[str, Any]], float]] = {}
_DIGITALCORE_CATALOG_LOCKS: Dict[str, asyncio.Lock] = {}
_DIGITALCORE_CACHE_TTL = 60.0


class DigitalCoreProviderAdapter(BaseProviderAdapter):
    """
    DigitalCore Wholesale REST API Adapter.
    Docs: https://digitalcore.top/docs
    Supports /api/user/{products, product, me, buy, history, order} using Api-Key header.
    """
    def __init__(self, base_url: str, api_key: str, field_mapping: Optional[Any] = None):
        super().__init__(base_url, api_key, field_mapping=field_mapping)
        clean_base = self.base_url.rstrip('/')
        if clean_base.lower().endswith('/api/user'):
            self.api_user_url = clean_base
        else:
            self.api_user_url = f"{clean_base}/api/user"
        self.provider_type = "digitalcore"

    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Api-Key": self.api_key,
            "X-Api-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _resolve_tier_unit_price(
        self,
        p: Dict[str, Any],
        quantity: int = 1,
        custom_price_field: Optional[str] = None
    ) -> Optional[float]:
        if custom_price_field and p.get(custom_price_field) is not None:
            custom_val = extract_price_from_dict(p, custom_field=custom_price_field)
            if custom_val is not None:
                return float(custom_val)

        qty = max(1, int(quantity or 1))
        tiers = p.get("tiers")
        if isinstance(tiers, list) and tiers:
            matched_tier_price = None
            best_fallback_min = -1
            best_fallback_price = None
            for tier in tiers:
                if not isinstance(tier, dict):
                    continue
                try:
                    min_q = int(tier.get("minQty") if tier.get("minQty") is not None else (tier.get("min_qty") or 0))
                    raw_max = tier.get("maxQty") if "maxQty" in tier else tier.get("max_qty")
                    max_q = int(raw_max) if raw_max is not None else None
                    t_price = float(tier.get("price") or 0.0)
                except (TypeError, ValueError):
                    continue
                if t_price <= 0:
                    continue
                if min_q <= qty and (max_q is None or qty <= max_q):
                    matched_tier_price = t_price
                    break
                if min_q <= qty and min_q >= best_fallback_min:
                    best_fallback_min = min_q
                    best_fallback_price = t_price
            if matched_tier_price is not None:
                return matched_tier_price
            if best_fallback_price is not None:
                return best_fallback_price

        base_price = extract_price_from_dict(p)
        if base_price is not None and float(base_price) > 0:
            return float(base_price)
        if p.get("priceFrom") is not None:
            try:
                pf = float(p.get("priceFrom") or 0.0)
                if pf > 0:
                    return pf
            except (TypeError, ValueError):
                pass
        return float(base_price) if base_price is not None else None

    def _standardize_digitalcore_catalog(self, raw_products: List[Any]) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None
        custom_stock_field = (self.field_mapping.get("stock_field") or "").strip() or None
        custom_id_field = (self.field_mapping.get("id_field") or "").strip() or None

        for p in raw_products:
            if not isinstance(p, dict):
                continue
            p_id = p.get(custom_id_field) if (custom_id_field and p.get(custom_id_field) is not None) else (p.get("id") or p.get("slug"))
            if p_id is None or not str(p_id).strip():
                continue
            p_id_str = str(p_id).strip()

            p_name = str(p.get("name") or f"Product #{p_id_str}").strip()
            p_desc = str(p.get("description") or "").strip()
            price_val = self._resolve_tier_unit_price(p, quantity=1, custom_price_field=custom_price_field)
            price_usd = float(price_val) if price_val is not None else 0.0

            stock_val = extract_stock_from_dict(p, allow_boolean=False, custom_field=custom_stock_field)
            if stock_val is None:
                stock_val = 0

            req_email = bool(p.get("requiresEmailActivation") or p.get("requires_email"))

            formatted.append({
                "id": p_id_str,
                "name": p_name,
                "name_ar": p_name,
                "name_en": p_name,
                "name_ru": p_name,
                "description": p_desc,
                "description_ar": p_desc,
                "description_en": p_desc,
                "description_ru": p_desc,
                "price": price_usd,
                "stock": max(0, int(stock_val)),
                "tiers": p.get("tiers") if isinstance(p.get("tiers"), list) else [],
                "requires_email": req_email,
                "requiresEmailActivation": req_email
            })
        return formatted

    async def fetch_catalog(self, session: Optional[aiohttp.ClientSession] = None, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        cache_key = f"{self.api_user_url}:{self.api_key}"
        now_ts = time.time()

        if not force_refresh and cache_key in _DIGITALCORE_CATALOG_CACHE:
            cached_list, cached_time = _DIGITALCORE_CATALOG_CACHE[cache_key]
            if (now_ts - cached_time) < _DIGITALCORE_CACHE_TTL and cached_list is not None:
                return cached_list

        lock = _DIGITALCORE_CATALOG_LOCKS.setdefault(cache_key, asyncio.Lock())
        async with lock:
            now_ts = time.time()
            if not force_refresh and cache_key in _DIGITALCORE_CATALOG_CACHE:
                cached_list, cached_time = _DIGITALCORE_CATALOG_CACHE[cache_key]
                if (now_ts - cached_time) < _DIGITALCORE_CACHE_TTL and cached_list is not None:
                    return cached_list

            url = f"{self.api_user_url}/products"

            async def _req(s: aiohttp.ClientSession):
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=15, connect=6)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            raw_list = data if isinstance(data, list) else extract_products_list_from_json(data)
                            standardized = self._standardize_digitalcore_catalog(raw_list or [])
                            _DIGITALCORE_CATALOG_CACHE[cache_key] = (standardized, time.time())
                            return standardized
                        elif resp.status in (401, 403):
                            logger.warning(f"DigitalCore auth failed ({resp.status}) on {url}")
                            return None
                        else:
                            logger.warning(f"DigitalCore catalog {url} returned HTTP {resp.status}")
                except Exception as e:
                    logger.warning(f"DigitalCore catalog fetch error: {e}")

                if cache_key in _DIGITALCORE_CATALOG_CACHE:
                    return _DIGITALCORE_CATALOG_CACHE[cache_key][0]
                return None

            if session:
                return await _req(session)
            else:
                async with aiohttp.ClientSession() as s:
                    return await _req(s)

    async def _fetch_single_product(self, provider_product_id: Any, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
        prov_pid = str(provider_product_id).strip()
        url = f"{self.api_user_url}/product"

        async def _req(s: aiohttp.ClientSession):
            try:
                async with s.get(url, headers=self.get_headers(), params={"id": prov_pid}, timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if isinstance(data, dict):
                            if data.get("success") is False:
                                return None
                            inner = data.get("product") or data.get("data") or data
                            if isinstance(inner, dict) and (matches_product_id(inner, prov_pid) or "stock" in inner or "price" in inner):
                                return inner
            except Exception as e:
                logger.debug(f"DigitalCore single product fetch failed for {prov_pid}: {e}")
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_stock(self, provider_product_id: Any, session: Optional[aiohttp.ClientSession] = None) -> Optional[int]:
        prov_pid = str(provider_product_id).strip()
        custom_stock_field = (self.field_mapping.get("stock_field") or "").strip() or None

        async def _req(s: aiohttp.ClientSession):
            single = await self._fetch_single_product(prov_pid, session=s)
            if isinstance(single, dict):
                num_s = extract_stock_from_dict(single, allow_boolean=False, custom_field=custom_stock_field)
                if num_s is not None:
                    return int(num_s)

            catalog = await self.fetch_catalog(session=s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, prov_pid):
                        return int(p.get("stock", 0))
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_live_product_price(self, provider_product_id: Any, quantity: int = 1, session: Optional[aiohttp.ClientSession] = None) -> Optional[float]:
        prov_pid = str(provider_product_id).strip()
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None

        async def _req(s: aiohttp.ClientSession):
            single = await self._fetch_single_product(prov_pid, session=s)
            if isinstance(single, dict):
                u_price = self._resolve_tier_unit_price(single, quantity=quantity, custom_price_field=custom_price_field)
                if u_price is not None and u_price > 0:
                    return float(u_price)

            catalog = await self.fetch_catalog(session=s)
            if catalog:
                for p in catalog:
                    if matches_product_id(p, prov_pid):
                        u_price = self._resolve_tier_unit_price(p, quantity=quantity, custom_price_field=custom_price_field)
                        if u_price is not None and u_price > 0:
                            return float(u_price)
                        return float(p.get("price", 0.0))
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def fetch_balance(self, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.api_user_url}/me"

        async def _req(s: aiohttp.ClientSession):
            try:
                async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=10, connect=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if isinstance(data, dict):
                            return data
            except Exception as e:
                logger.debug(f"DigitalCore balance fetch failed: {e}")
            return None

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)

    async def _parse_dc_error(self, resp: aiohttp.ClientResponse) -> str:
        try:
            err_json = await resp.json(content_type=None)
            if isinstance(err_json, dict):
                msg = err_json.get("msg") or err_json.get("message") or err_json.get("error") or err_json.get("detail")
                if msg:
                    return str(msg)
        except Exception:
            pass
        try:
            err_txt = await resp.text()
            if "<!DOCTYPE html>" in err_txt or "<html" in err_txt:
                return f"Provider service error (HTTP {resp.status})"
            if err_txt:
                return err_txt[:200]
        except Exception:
            pass
        return f"HTTP {resp.status}"

    async def execute_order(
        self,
        provider_product_id: Any,
        quantity: int,
        expected_price: Optional[float] = None,
        client_order_ref: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        customer_email: Optional[Any] = None
    ) -> List[str]:
        """
        Executes order via POST /api/user/buy with JSON payload {"id": <slug_or_id>, "count": <qty>}.
        """
        prov_pid = str(provider_product_id).strip()
        qty = max(1, int(quantity))
        pid_field = (self.field_mapping.get("buy_pid_field") or "").strip() or "id"
        qty_field = (self.field_mapping.get("buy_qty_field") or "").strip() or "count"
        payload: Dict[str, Any] = {pid_field: prov_pid, qty_field: qty}

        default_ep = f"{self.api_user_url}/buy"
        endpoints = self._get_custom_buy_endpoints([default_ep])
        ep = endpoints[0]

        def _raise_mapped_error(status: int, err_msg: str):
            err_l = err_msg.lower()
            if "insufficient_balance" in err_l or "balance" in err_l:
                raise Exception(f"Provider balance insufficient: {err_msg}")
            elif "out_of_stock" in err_l or "stock" in err_l:
                raise Exception(f"Out of stock ({err_msg})")
            elif "email" in err_l:
                raise Exception(f"Provider requires email: {err_msg}")
            elif status in (401, 403) or "api_key" in err_l or "unauthorized" in err_l:
                raise Exception(f"Provider authentication error ({err_msg})")
            raise Exception(f"Provider error: {err_msg}")

        async def _req(s: aiohttp.ClientSession) -> List[str]:
            for attempt in range(2):
                try:
                    logger.info(f"Executing DigitalCore order on {ep} with payload: {payload}")
                    async with s.post(ep, headers=self.get_headers(), json=payload, timeout=aiohttp.ClientTimeout(total=45, connect=10)) as resp:
                        if resp.status in (200, 201):
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                if data.get("success") is False:
                                    err_m = str(data.get("msg") or data.get("error") or "Order failed")
                                    _raise_mapped_error(resp.status, err_m)

                                items = data.get("items")
                                if isinstance(items, list) and items:
                                    cleaned = []
                                    for it in items:
                                        if isinstance(it, dict):
                                            val = it.get("key") or it.get("code") or it.get("credentials") or it.get("data") or it.get("item")
                                            cleaned.append(str(val).strip() if val is not None else json.dumps(it, ensure_ascii=False))
                                        else:
                                            s_it = str(it).strip()
                                            if s_it:
                                                cleaned.append(s_it)
                                    if cleaned:
                                        return cleaned
                                elif isinstance(items, str) and items.strip():
                                    return [ln.strip() for ln in items.splitlines() if ln.strip()]

                                if data.get("success") is True:
                                    ord_id = data.get("order_id") or client_order_ref or "OK"
                                    view_url = data.get("view_url") or ""
                                    if view_url:
                                        return [f"Order #{ord_id} | {view_url}"]
                                    return [f"Order #{ord_id} Completed Successfully"]

                            raise Exception("Provider returned empty delivery data")

                        err_msg = await self._parse_dc_error(resp)
                        logger.warning(f"DigitalCore order on {ep} returned HTTP {resp.status}: {err_msg}")
                        _raise_mapped_error(resp.status, err_msg)
                except aiohttp.ClientConnectorError as conn_err:
                    # Safe to retry once because TCP connection was not established
                    if attempt == 0:
                        logger.warning(f"DigitalCore connection error on {ep}, retrying once: {conn_err}")
                        await asyncio.sleep(1.5)
                        continue
                    raise Exception(f"Cannot connect to provider: {conn_err}")
                except (aiohttp.ServerTimeoutError, asyncio.TimeoutError) as to_err:
                    raise Exception(f"Provider request timed out: {to_err}")

            raise Exception("Provider error: Unable to complete DigitalCore order")

        if session:
            return await _req(session)
        else:
            async with aiohttp.ClientSession() as s:
                return await _req(s)


# -------------------------------------------------------------------------
# Provider Factory Function
# -------------------------------------------------------------------------
def get_provider_adapter(base_url: str, api_key: str, field_mapping: Optional[Any] = None) -> BaseProviderAdapter:
    """
    Factory function: Returns the specialized provider adapter based on base_url.
    """
    clean_url = str(base_url).lower().strip()
    
    if "pandoradigital" in clean_url:
        return PandoraProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "hvmforum" in clean_url or "aethel" in clean_url or "mail-api" in clean_url:
        return AethelProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "prodseller" in clean_url:
        return ProdSellerProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "shopdigital" in clean_url:
        return ShopDigitalProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "supabase.co" in clean_url:
        return SupabaseProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "aitoolifystudio" in clean_url or "/api/reseller/v1" in clean_url:
        return AitoolifyProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "ventetelegrambot" in clean_url or "ventebot" in clean_url or "/api/reseller" in clean_url or "/reseller" in clean_url:
        return VenteBotProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "canboso" in clean_url or "/api/v2/telegram-buyer" in clean_url:
        return CanbosoProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "digitalcore" in clean_url or "/api/user" in clean_url:
        return DigitalCoreProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    elif "roboticvn" in clean_url:
        return RoboticvnProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    else:
        return BaseProviderAdapter(base_url, api_key, field_mapping=field_mapping)


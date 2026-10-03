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
            f"{self.base_url}/api/v1/products",
            f"{self.base_url}/v1/products",
            f"{self.base_url}/api/products",
            f"{self.base_url}/products",
            f"{self.base_url}/api/reseller/products",
            f"{self.base_url}/reseller/products",
            f"{self.base_url}/api/v1/catalog",
            f"{self.base_url}/v1/catalog",
            f"{self.base_url}/api/catalog",
            f"{self.base_url}/catalog"
        ]
        
        async def _req(s):
            saw_empty_valid = False
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=35, connect=10)) as resp:
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
                            elif isinstance(data, list) and len(data) == 0:
                                saw_empty_valid = True
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
            f"{self.base_url}/products/{prov_pid}"
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
        """
        prov_pid = str(provider_product_id).strip()
        custom_price_field = (self.field_mapping.get("price_field") or "").strip() or None
        endpoints = [
            f"{self.base_url}/api/v1/products/{prov_pid}",
            f"{self.base_url}/v1/products/{prov_pid}",
            f"{self.base_url}/api/products/{prov_pid}",
            f"{self.base_url}/products/{prov_pid}"
        ]

        async def _req(s):
            for url in endpoints:
                try:
                    async with s.get(url, headers=self.get_headers(), timeout=aiohttp.ClientTimeout(total=8, connect=4)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                single_p = data.get('product') or data.get('data') or data
                                price_val = extract_price_from_dict(single_p, custom_field=custom_price_field)
                                if price_val is not None:
                                    return float(price_val)
                except Exception:
                    pass
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
            email_list = [e.strip() for e in (customer_email if isinstance(customer_email, list) else str(customer_email).replace(',', '\n').split('\n')) if e.strip()]
            if email_list:
                if int(quantity) == 1:
                    payload["email"] = email_list[0]
                else:
                    if len(email_list) < int(quantity):
                        email_list = email_list + [email_list[-1]] * (int(quantity) - len(email_list))
                    payload["emails"] = email_list[:int(quantity)]
                    payload["email"] = email_list[0]
        
        default_endpoints = [
            f"{self.base_url}/api/v1/orders",
            f"{self.base_url}/api/buy",
            f"{self.base_url}/buy",
            f"{self.base_url}/v1/orders",
            f"{self.base_url}/orders",
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
                            continue
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
                            continue
                except Exception as ep_err:
                    if "Out of stock" in str(ep_err) or "Provider balance insufficient" in str(ep_err) or "email" in str(ep_err).lower():
                        raise ep_err
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
        elif isinstance(deliv, list):
            raw_creds = deliv
        elif isinstance(order, dict) and order.get('items'):
            raw_creds = order['items']
        elif isinstance(order, list):
            raw_creds = order
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
                return [r for r in res if r]
            else:
                return [str(raw_creds)]
        elif isinstance(buy_data.get('activation'), dict) or buy_data.get('status') == 'paid':
            act = buy_data.get('activation') if isinstance(buy_data.get('activation'), dict) else {}
            emails = act.get('emails') or ([act['email']] if act.get('email') else [])
            eta = act.get('eta', 'ASAP')
            ord_id = buy_data.get('orderId') or buy_data.get('order_id') or (order.get('id') if isinstance(order, dict) else None) or buy_data.get('id') or ext_order_id
            status_str = str(buy_data.get('status') or 'paid').upper()
            if emails:
                return [f"✅ Activation Order #{ord_id} ({status_str}) — Email: {em} | ETA: {eta}" for em in emails]
            return [f"✅ Activation Order #{ord_id} ({status_str}) | ETA: {eta}"]
        elif buy_data.get('success') or buy_data.get('ok') or buy_data.get('status') in ['completed', 'delivered']:
            ord_id = buy_data.get('orderId') or buy_data.get('order_id') or (order.get('id') if isinstance(order, dict) else None) or buy_data.get('id') or ext_order_id
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
                        if "Provider error:" in str(retry_e):
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
            "external_order_id": order_ref,
            "client_order_reference": order_ref
        }
        self._apply_order_mapping(payload, prov_pid, prov_pid, quantity)
        if customer_email:
            email_list = [e.strip() for e in (customer_email if isinstance(customer_email, list) else str(customer_email).replace(',', '\n').split('\n')) if e.strip()]
            if email_list:
                if int(quantity) == 1:
                    payload["email"] = email_list[0]
                else:
                    if len(email_list) < int(quantity):
                        email_list = email_list + [email_list[-1]] * (int(quantity) - len(email_list))
                    payload["emails"] = email_list[:int(quantity)]

        headers = self.get_headers({"Idempotency-Key": order_ref})

        async def _req(s):
            ep_list = self._get_custom_buy_endpoints([f"{self.base_url}/v1/orders"])
            ep = ep_list[0]
            logger.info(f"Executing ProdSeller order on {ep} with payload: {payload}")
            async with s.post(ep, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=50, connect=10)) as resp:
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
            email_list = [e.strip() for e in (customer_email if isinstance(customer_email, list) else str(customer_email).replace(',', '\n').split('\n')) if e.strip()]
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
            # 1. Try single product detail endpoints first
            for url in [
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
                                if u_price is not None:
                                    return float(u_price)
                except Exception:
                    pass

            # 2. Try /api/reseller/quote
            try:
                quote_url = f"{self.base_url}/api/reseller/quote"
                async with s.post(quote_url, headers=self.get_headers(), json={"product_id": item_id, "quantity": int(quantity), "qty": int(quantity)}, timeout=aiohttp.ClientTimeout(total=8, connect=4)) as q_resp:
                    if q_resp.status == 200:
                        q_data = await q_resp.json(content_type=None)
                        if isinstance(q_data, dict):
                            u_price = extract_price_from_dict(q_data, custom_field=custom_price_field)
                            if u_price is not None:
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
            email_list = [e.strip() for e in (customer_email if isinstance(customer_email, list) else str(customer_email).replace(',', '\n').split('\n')) if e.strip()]
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
    elif "ventetelegrambot" in clean_url or "ventebot" in clean_url or "/api/reseller" in clean_url or "/reseller" in clean_url:
        return VenteBotProviderAdapter(base_url, api_key, field_mapping=field_mapping)
    else:
        return BaseProviderAdapter(base_url, api_key, field_mapping=field_mapping)


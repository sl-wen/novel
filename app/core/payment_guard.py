"""
支付中间件 — 支付宝 AI 收（A402 智能收）协议

402 响应带 Payment-Needed 头（Base64URL 编码的 JSON），
包含 protocol + method 两层结构 + seller_signature 签名。
"""

import base64
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

SHANGHAI_TZ = timezone(timedelta(hours=8))


class PaymentTokenStore:
    """一次性 paymentProof token 存储"""
    def __init__(self):
        self._tokens: dict = {}

    def create(self, action: str, amount: float, **extra) -> str:
        proof = f"pay_{int(time.time())}_{uuid.uuid4().hex[:12]}"
        self._tokens[proof] = {"action": action, "amount": amount, "created_at": time.time(), **extra}
        self._cleanup()
        return proof

    def verify(self, proof: str, action: str) -> Optional[dict]:
        order = self._tokens.get(proof)
        if not order:
            return None
        if time.time() - order["created_at"] > 1800:
            del self._tokens[proof]
            return None
        if order["action"] != action:
            return None
        del self._tokens[proof]
        return order

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._tokens.items() if now - v["created_at"] > 1800]
        for k in expired:
            del self._tokens[k]


token_store = PaymentTokenStore()


def _b64url_encode(data: bytes) -> str:
    """Base64URL 编码（无填充）"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    """Base64URL 解码"""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _ensure_pem(raw_key: str, marker: str) -> str:
    """确保密钥有 PEM 标记"""
    raw_key = raw_key.strip()
    if f"-----BEGIN {marker}-----" in raw_key:
        return raw_key
    import textwrap
    wrapped = textwrap.fill(raw_key, width=64)
    return f"-----BEGIN {marker}-----\n{wrapped}\n-----END {marker}-----"


def _format_private_key(raw_key: str) -> str:
    """格式化私钥：PKCS#8 → PKCS#1"""
    pem = _ensure_pem(raw_key, "PRIVATE KEY")
    if "BEGIN PRIVATE KEY" in pem and "BEGIN RSA PRIVATE KEY" not in pem:
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PrivateFormat, NoEncryption
            key = load_pem_private_key(pem.encode(), password=None)
            pem = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()).decode()
        except Exception as e:
            logger.warning(f"PKCS#8→PKCS#1 失败: {e}")
    return pem


def _sign_with_rsa2(private_key_pem: str, content: str) -> str:
    """RSA2 签名（SHA256WithRSA）"""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    key = load_pem_private_key(private_key_pem.encode(), password=None)
    signature = key.sign(content.encode(), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode()


def _get_sign_content(params: dict) -> str:
    """按 key 字典序排序拼成 key=value&key=value"""
    sorted_items = sorted(params.items())
    return "&".join(f"{k}={v}" for k, v in sorted_items)


def _build_payment_needed(action: str, amount: float, resource_id: str) -> str:
    """
    构造支付宝 A402 协议的 Payment-Needed 头
    """
    out_trade_no = f"novel{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    amount_fen = str(int(amount * 100))  # 转为分
    goods_name = "小说搜索" if action == "search" else "小说下载"
    pay_before = (datetime.now(SHANGHAI_TZ) + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    seller_id = getattr(settings, "ALIPAY_SELLER_ID", "2088000000000000")
    seller_name = getattr(settings, "ALIPAY_SELLER_NAME", "小说API")
    service_id = getattr(settings, "ALIPAY_SERVICE_ID", "default")

    # 签名参数（按字典序）
    sign_params = {
        "amount": amount_fen,
        "currency": "CNY",
        "goods_name": goods_name,
        "out_trade_no": out_trade_no,
        "pay_before": pay_before,
        "resource_id": resource_id,
        "seller_id": seller_id,
        "service_id": service_id,
    }
    sign_content = _get_sign_content(sign_params)

    # 签名
    try:
        formatted_key = _format_private_key(settings.ALIPAY_APP_PRIVATE_KEY)
        seller_signature = _sign_with_rsa2(formatted_key, sign_content)
    except Exception as e:
        logger.error(f"签名失败: {e}")
        seller_signature = ""

    payload = {
        "protocol": {
            "out_trade_no": out_trade_no,
            "amount": amount_fen,
            "currency": "CNY",
            "resource_id": resource_id,
            "pay_before": pay_before,
            "seller_signature": seller_signature,
            "seller_sign_type": "RSA2",
            "seller_unique_id": seller_id,
        },
        "method": {
            "seller_name": seller_name,
            "seller_id": seller_id,
            "seller_app_id": settings.ALIPAY_APP_ID,
            "goods_name": goods_name,
            "seller_unique_id_key": "seller_id",
            "service_id": service_id,
        },
    }

    return _b64url_encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())


def _find_request(args, kwargs) -> Optional[Request]:
    if "request" in kwargs:
        return kwargs["request"]
    for arg in args:
        if isinstance(arg, Request):
            return arg
    return None


def require_payment(action: str, amount: float = 0.01):
    """402 付费拦截装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not settings.ENABLE_PAYMENT:
                return await func(*args, **kwargs)

            req = _find_request(args, kwargs)
            proof = None

            if req:
                proof = (
                    req.headers.get("x-payment-proof")
                    or req.headers.get("paymentproof")
                    or req.query_params.get("paymentProof")
                )
                auth = req.headers.get("authorization", "")
                if auth.startswith("Bearer pay_"):
                    proof = auth[7:]

            if proof:
                order = token_store.verify(proof, action)
                if order:
                    logger.info(f"402 验证通过 | action={action} | proof={proof[:20]}...")
                    return await func(*args, **kwargs)

            # 构造 resource_id
            resource_id = f"/api/optimized/{action}"
            if req:
                qs = str(req.url.query)
                if qs:
                    resource_id = f"{req.url.path}?{qs}"

            amount_str = f"{amount:.2f}"
            description = "小说搜索" if action == "search" else "小说下载"
            payment_needed = _build_payment_needed(action, amount, resource_id)

            body = {
                "code": 402,
                "message": f"此接口需要付费 ¥{amount_str}",
                "payment": {
                    "action": action,
                    "amount": amount_str,
                    "currency": "CNY",
                    "description": description,
                    "accepts": ["alipay"],
                },
            }

            response = JSONResponse(status_code=402, content=body)
            response.headers["Payment-Needed"] = payment_needed
            return response

        return wrapper
    return decorator

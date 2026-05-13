"""
支付中间件 — HTTP 402 (AI Pay) 方案

流程：
1. AI Agent 调用搜索/下载 API
2. 未付费时返回 HTTP 402 + 价格信息
3. AI Agent 通过支付宝 AI 付技能完成支付，获取 paymentProof
4. 携带 paymentProof 重试请求 → 验证通过后放行

当 ENABLE_PAYMENT=false 时，所有请求直接放行。
"""

import logging
import time
import uuid
from functools import wraps
from typing import Optional

from fastapi import HTTPException, Request

from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentTokenStore:
    """
    存储 paymentProof → 订单信息
    proof 有效期 30 分钟，验证通过后一次性消耗
    """
    def __init__(self):
        self._tokens: dict = {}

    def create(self, action: str, amount: float, **extra) -> str:
        proof = f"pay_{int(time.time())}_{uuid.uuid4().hex[:12]}"
        self._tokens[proof] = {
            "action": action,
            "amount": amount,
            "created_at": time.time(),
            **extra,
        }
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


def _find_request(args, kwargs) -> Optional[Request]:
    """从函数参数中找到 FastAPI Request 对象"""
    # 先看 kwargs
    if "request" in kwargs:
        return kwargs["request"]
    # 再看 args
    for arg in args:
        if isinstance(arg, Request):
            return arg
    return None


def require_payment(action: str, amount: float = 0.01):
    """
    402 付费拦截装饰器。
    """
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
                # Authorization: Bearer pay_xxx
                auth = req.headers.get("authorization", "")
                if auth.startswith("Bearer pay_"):
                    proof = auth[7:]

            if proof:
                order = token_store.verify(proof, action)
                if order:
                    logger.info(f"402 验证通过 | action={action} | proof={proof[:20]}...")
                    return await func(*args, **kwargs)
                else:
                    logger.warning(f"proof 无效 | action={action} | proof={proof[:20] if proof else 'None'}...")

            # 返回 402
            amount_str = f"{amount:.2f}"
            description = f"小说搜索" if action == "search" else "小说下载"

            raise HTTPException(
                status_code=402,
                detail={
                    "code": 402,
                    "message": f"此接口需要付费 ¥{amount_str}，请获取 paymentProof 后重试",
                    "payment": {
                        "action": action,
                        "amount": amount_str,
                        "currency": "CNY",
                        "description": description,
                        "getProofUrl": "/api/payment/proof",
                        "accepts": ["alipay"],
                        "x402": {
                            "version": "1",
                            "maxAmountRequired": amount_str,
                            "payTo": settings.ALIPAY_APP_ID,
                            "description": description,
                        },
                    },
                },
            )

        return wrapper
    return decorator

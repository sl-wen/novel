"""
支付 API — 402 AI Pay 方案

GET  /api/payment/price      — 查询价格
POST /api/payment/proof      — AI Agent 获取 paymentProof（创建预付费 token）
GET  /api/payment/verify     — 验证 proof 是否有效
POST /api/payment/callback   — 支付宝回调（保留兼容，402 方案下实际不需要）
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.payment_guard import token_store
from app.models.payment import (
    PaymentAction,
    PaymentProofRequest,
    PaymentProofResponse,
    PRICE_TABLE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])


@router.get("/price")
async def get_price(action: Optional[str] = None):
    """查询接口价格"""
    prices = {a.value: p for a, p in PRICE_TABLE.items()}
    if action:
        amount = PRICE_TABLE.get(PaymentAction(action))
        if amount is None:
            return JSONResponse(status_code=400, content={"code": 400, "message": f"未知 action: {action}"})
        return {"code": 200, "data": {"action": action, "amount": amount, "currency": "CNY"}}
    return {"code": 200, "data": prices}


@router.post("/proof", response_model=PaymentProofResponse)
async def create_proof(req: PaymentProofRequest):
    """
    AI Agent 调用此接口获取 paymentProof。

    流程：
    1. AI Agent 搜索/下载时收到 402
    2. 调此接口创建 proof token
    3. 带着proof重试原请求
    """
    if not settings.ENABLE_PAYMENT:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "付费功能未启用"},
        )

    amount = PRICE_TABLE.get(req.action, 0.01)
    description = f"小说搜索：{req.keyword}" if req.action == PaymentAction.SEARCH else "小说下载"

    proof = token_store.create(
        action=req.action.value,
        amount=amount,
        keyword=req.keyword,
        url=req.url,
    )

    logger.info(f"创建 proof | action={req.action} | amount={amount} | proof={proof}")

    return PaymentProofResponse(
        paymentProof=proof,
        action=req.action,
        amount=amount,
        description=description,
    )


@router.get("/verify")
async def verify_proof(proof: str, action: str):
    """验证 proof 是否有效（调试用）"""
    order = token_store._tokens.get(proof)
    if not order:
        return {"code": 200, "data": {"valid": False, "reason": "not found"}}
    if order["action"] != action:
        return {"code": 200, "data": {"valid": False, "reason": "action mismatch"}}
    return {"code": 200, "data": {"valid": True, "order": order}}


@router.post("/callback")
async def alipay_callback(request: Request):
    """
    支付宝异步回调（保留兼容）
    402 方案下 AI Agent 自己处理支付，不需要服务端回调。
    """
    return "success"


@router.get("/callback")
async def alipay_callback_get(request: Request):
    """回调 GET（支付宝同步跳转保留）"""
    return "success"

"""
支付 API 路由

POST /api/payment/create      — 创建订单，返回支付链接
GET  /api/payment/status       — 查询订单状态
POST /api/payment/callback     — 支付宝异步回调（支付宝服务器调用）
GET  /api/payment/return       — 支付宝同步跳转（用户浏览器跳回）
GET  /api/payment/paid-content — 支付成功后获取实际内容（搜索结果/下载链接）
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.config import settings
from app.models.payment import (
    OrderCreateRequest,
    OrderResponse,
    OrderStatusResponse,
    PaymentAction,
    PaymentStatus,
)
from app.services.payment_service import PaymentService, order_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])

payment_service = PaymentService()


# ── 创建订单 ──────────────────────────────────────────────────

@router.post("/create", response_model=OrderResponse)
async def create_order(req: OrderCreateRequest):
    """
    创建支付订单

    - action=search 时 keyword 必填
    - action=download 时 url 必填
    - 返回 pay_url 供前端跳转支付宝
    """
    # 参数校验
    if req.action == PaymentAction.SEARCH and not req.keyword:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "搜索需要 keyword 参数", "data": None},
        )
    if req.action == PaymentAction.DOWNLOAD and not req.url:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "下载需要 url 参数", "data": None},
        )

    try:
        order = payment_service.create_order(
            action=req.action,
            keyword=req.keyword,
            url=req.url,
            source_id=req.source_id,
            format=req.format,
        )
        return order
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"创建订单失败: {str(e)}", "data": None},
        )


# ── 查询订单状态 ──────────────────────────────────────────────

@router.get("/status")
async def get_order_status(order_id: str = Query(..., description="订单号")):
    """
    查询订单支付状态

    前端轮询此接口判断是否支付成功
    """
    result = payment_service.query_order(order_id)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "订单不存在", "data": None},
        )
    return {"code": 200, "message": "success", "data": result}


# ── 支付宝异步回调 ────────────────────────────────────────────

@router.post("/callback")
async def alipay_callback(request: Request):
    """
    支付宝异步通知回调

    支付宝服务器 POST 表单数据到这里
    必须验签 + 返回 "success" 字符串（支付宝约定）
    """
    form_data = await request.form()
    params = dict(form_data)

    logger.info(f"收到支付宝回调 | out_trade_no={params.get('out_trade_no')}")

    success = payment_service.handle_callback(params)

    if success:
        # 支付宝要求成功返回纯文本 "success"，否则会持续重试
        return HTMLResponse(content="success", status_code=200)
    else:
        return HTMLResponse(content="fail", status_code=200)


# ── 支付宝同步跳转 ────────────────────────────────────────────

@router.get("/return")
async def alipay_return(request: Request):
    """
    支付宝同步跳转（用户在支付宝付完款后跳回来的页面）

    这里简单展示支付结果，前端可以接管做更漂亮的 UI
    """
    params = dict(request.query_params)
    order_id = params.get("out_trade_no", "")

    # 验签
    sign = params.get("sign")
    if sign:
        try:
            from alipay.aop.api.util.SignatureUtils import verify_with_rsa
            params_for_verify = {
                k: v for k, v in params.items()
                if k not in ("sign", "sign_type") and v
            }
            sorted_params = sorted(params_for_verify.items())
            query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
            is_valid = verify_with_rsa(
                settings.ALIPAY_PUBLIC_KEY, query_string, sign
            )
            if not is_valid:
                return HTMLResponse(content="<h1>验签失败</h1>", status_code=400)
        except Exception as e:
            logger.warning(f"同步跳转验签异常: {e}")

    # 同步查询一下真实状态
    if order_id:
        payment_service._sync_alipay_status(order_id)

    order = order_store.get(order_id) if order_id else None
    status_text = "支付成功 ✅" if order and order["status"] == PaymentStatus.PAID else "支付处理中..."

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>支付结果</title></head>
    <body style="font-family:sans-serif;text-align:center;padding-top:100px;">
        <h1>{status_text}</h1>
        <p>订单号：{order_id}</p>
        <p><a href="javascript:window.close()">关闭页面</a></p>
        <script>
            // 如果有 opener，尝试通知父窗口
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'alipay_result',
                    order_id: '{order_id}',
                    status: '{order["status"] if order else "unknown"}'
                }}, '*');
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# ── 获取已付费内容 ────────────────────────────────────────────

@router.get("/paid-content")
async def get_paid_content(
    order_id: str = Query(..., description="订单号"),
):
    """
    支付成功后，用 order_id 换取实际内容

    对于 search：返回搜索结果（再次调用搜索 API）
    对于 download：返回下载链接
    """
    order = order_store.get(order_id)
    if not order:
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "订单不存在", "data": None},
        )

    if order["status"] != PaymentStatus.PAID:
        return JSONResponse(
            status_code=402,
            content={
                "code": 402,
                "message": f"订单未支付，当前状态：{order['status']}",
                "data": None,
            },
        )

    # 根据 action 返回对应内容
    if order["action"] == PaymentAction.SEARCH:
        # 返回搜索参数，前端拿去调搜索 API（或这里直接调）
        return {
            "code": 200,
            "message": "success",
            "data": {
                "action": "search",
                "keyword": order["keyword"],
                "order_id": order_id,
            },
        }
    elif order["action"] == PaymentAction.DOWNLOAD:
        return {
            "code": 200,
            "message": "success",
            "data": {
                "action": "download",
                "url": order["url"],
                "source_id": order.get("source_id"),
                "format": order.get("format", "txt"),
                "order_id": order_id,
            },
        }

    return JSONResponse(
        status_code=400,
        content={"code": 400, "message": "未知的 action 类型", "data": None},
    )

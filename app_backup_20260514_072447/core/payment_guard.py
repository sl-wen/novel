"""
支付中间件 — 对搜索/下载接口加付费校验

使用方式：
1. 前端先 POST /api/payment/create 创建订单 → 拿到 pay_url
2. 用户完成支付后，前端拿 order_id 调搜索/下载接口
3. 中间件校验 order_id 已支付才放行

当 ENABLE_PAYMENT=false 时，所有请求直接放行（开发模式）。
"""

import logging
from functools import wraps
from typing import Optional

from fastapi import HTTPException

from app.core.config import settings
from app.models.payment import PaymentAction, PaymentStatus
from app.services.payment_service import order_store

logger = logging.getLogger(__name__)


def require_payment(action: PaymentAction):
    """
    依赖注入式校验装饰器。
    在路由参数中加 order_id: Optional[str] = Query(None)，
    如果 order_id 存在且已支付则放行，否则返回 402。
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, order_id: Optional[str] = None, **kwargs):
            # 支付功能关闭时直接放行
            if not settings.ENABLE_PAYMENT:
                return await func(*args, order_id=order_id, **kwargs)

            # 没传 order_id → 需要付费
            if not order_id:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": 402,
                        "message": "此接口需要付费，请先创建支付订单",
                        "action": action,
                        "create_order_url": "/api/payment/create",
                    },
                )

            # 校验订单
            order = order_store.get(order_id)
            if not order:
                raise HTTPException(
                    status_code=404,
                    detail={"code": 404, "message": f"订单不存在: {order_id}"},
                )

            if order["action"] != action:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": 400,
                        "message": f"订单动作不匹配，期望 {action}，实际 {order['action']}",
                    },
                )

            if order["status"] != PaymentStatus.PAID:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": 402,
                        "message": f"订单未支付，状态: {order['status']}",
                        "order_id": order_id,
                        "status": order["status"],
                    },
                )

            # 支付成功，放行
            logger.info(f"付费校验通过 | order_id={order_id} | action={action}")
            return await func(*args, order_id=order_id, **kwargs)

        return wrapper

    return decorator

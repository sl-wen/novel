"""
支付服务 — 下单、查询、回调验签、订单生命周期管理

使用内存字典存储订单（轻量方案，单实例够用）。
后续可切 Redis / SQLite / MySQL。
"""

import logging
import time
from typing import Dict, Optional

from alipay.aop.api.domain.AlipayTradeWapPayModel import AlipayTradeWapPayModel
from alipay.aop.api.request.AlipayTradeWapPayRequest import AlipayTradeWapPayRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.response.AlipayTradeQueryResponse import AlipayTradeQueryResponse

from app.core.alipay_client import get_alipay_client
from app.core.config import settings
from app.models.payment import (
    PaymentAction,
    PaymentStatus,
    OrderResponse,
    OrderStatusResponse,
    PRICE_TABLE,
    generate_order_id,
)

logger = logging.getLogger(__name__)


class OrderStore:
    """
    内存订单存储（单进程）
    key = order_id, value = dict
    """

    def __init__(self):
        self._orders: Dict[str, dict] = {}

    def save(self, order: dict) -> None:
        self._orders[order["order_id"]] = order

    def get(self, order_id: str) -> Optional[dict]:
        return self._orders.get(order_id)

    def update_status(
        self,
        order_id: str,
        status: PaymentStatus,
        trade_no: Optional[str] = None,
    ) -> Optional[dict]:
        order = self._orders.get(order_id)
        if not order:
            return None
        order["status"] = status
        if trade_no:
            order["trade_no"] = trade_no
        if status == PaymentStatus.PAID:
            order["paid_at"] = time.time()
        return order

    def cleanup_expired(self, expire_seconds: int = 1800) -> int:
        """清理超时未支付的订单"""
        now = time.time()
        expired = [
            oid
            for oid, o in self._orders.items()
            if o["status"] == PaymentStatus.PENDING
            and now - o["created_at"] > expire_seconds
        ]
        for oid in expired:
            self._orders[oid]["status"] = PaymentStatus.CLOSED
        return len(expired)


# 全局单例
order_store = OrderStore()


class PaymentService:
    """支付服务"""

    def __init__(self):
        self.client = get_alipay_client()

    # ── 创建订单 ──────────────────────────────────────────────

    def create_order(
        self,
        action: PaymentAction,
        keyword: Optional[str] = None,
        url: Optional[str] = None,
        source_id: Optional[int] = None,
        format: Optional[str] = None,
    ) -> OrderResponse:
        """创建支付订单，返回支付宝 H5 支付链接"""
        order_id = generate_order_id()
        amount = PRICE_TABLE.get(action, 0.01)

        # 构造订单数据
        order_data = {
            "order_id": order_id,
            "action": action,
            "amount": amount,
            "status": PaymentStatus.PENDING,
            "keyword": keyword,
            "url": url,
            "source_id": source_id,
            "format": format,
            "trade_no": None,
            "created_at": time.time(),
            "paid_at": None,
        }
        order_store.save(order_data)

        # 构造支付描述
        if action == PaymentAction.SEARCH:
            subject = f"小说搜索：{keyword}"
            body = f"搜索关键词：{keyword}"
        else:
            subject = "小说下载"
            body = f"下载格式：{format or 'txt'}"

        # 调用支付宝 H5 手机网站支付
        pay_url = self._create_wap_pay(
            out_trade_no=order_id,
            total_amount=str(amount),
            subject=subject,
            body=body,
        )

        logger.info(f"订单创建 | order_id={order_id} | action={action} | amount={amount}")

        return OrderResponse(
            order_id=order_id,
            action=action,
            amount=amount,
            pay_url=pay_url,
            status=PaymentStatus.PENDING,
            created_at=order_data["created_at"],
        )

    def _create_wap_pay(
        self,
        out_trade_no: str,
        total_amount: str,
        subject: str,
        body: str,
    ) -> str:
        """
        调用 alipay.trade.wap.pay（手机网站支付）
        返回支付宝收银台 URL
        """
        model = AlipayTradeWapPayModel()
        model.out_trade_no = out_trade_no
        model.total_amount = total_amount
        model.subject = subject
        model.body = body
        model.product_code = "QUICK_WAP_WAY"
        # 支付超时：15 分钟
        model.timeout_express = "15m"

        request = AlipayTradeWapPayRequest(biz_model=model)
        # 设置回调地址
        request.notify_url = settings.ALIPAY_NOTIFY_URL
        request.return_url = settings.ALIPAY_RETURN_URL

        try:
            # page_execute 返回的是跳转 URL (GET 方式)
            pay_url = self.client.page_execute(request, http_method="GET")
            return pay_url
        except Exception as e:
            logger.error(f"创建支付链接失败: {e}")
            raise

    # ── 查询订单状态 ──────────────────────────────────────────

    def query_order(self, order_id: str) -> Optional[OrderStatusResponse]:
        """查询本地订单 + 主动向支付宝查询"""
        order = order_store.get(order_id)
        if not order:
            return None

        # 如果本地还是 PENDING，主动去支付宝查一下
        if order["status"] == PaymentStatus.PENDING:
            self._sync_alipay_status(order_id)

        # 重新获取（可能被 sync 更新了）
        order = order_store.get(order_id)

        return OrderStatusResponse(
            order_id=order["order_id"],
            status=order["status"],
            action=order["action"],
            amount=order["amount"],
            trade_no=order.get("trade_no"),
            created_at=order["created_at"],
            paid_at=order.get("paid_at"),
            keyword=order.get("keyword"),
            url=order.get("url"),
        )

    def _sync_alipay_status(self, out_trade_no: str) -> None:
        """主动查询支付宝订单状态"""
        from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
        model = AlipayTradeQueryModel()
        model.out_trade_no = out_trade_no

        request = AlipayTradeQueryRequest(biz_model=model)
        try:
            response_content = self.client.execute(request)
            if response_content:
                response = AlipayTradeQueryResponse()
                response.parse_response_content(response_content)
                if response.is_success():
                    trade_status = response.trade_status
                    if trade_status == "TRADE_SUCCESS":
                        order_store.update_status(
                            out_trade_no,
                            PaymentStatus.PAID,
                            trade_no=response.trade_no,
                        )
                        logger.info(
                            f"支付宝同步 | {out_trade_no} => PAID | "
                            f"trade_no={response.trade_no}"
                        )
                    elif trade_status == "TRADE_CLOSED":
                        order_store.update_status(out_trade_no, PaymentStatus.CLOSED)
        except Exception as e:
            logger.warning(f"支付宝状态同步失败 | {out_trade_no}: {e}")

    # ── 处理回调 ──────────────────────────────────────────────

    def handle_callback(self, params: dict) -> bool:
        """
        处理支付宝异步回调通知
        1. 验签
        2. 更新订单状态
        返回是否处理成功
        """
        # 1. 验签
        from alipay.aop.api.util.SignatureUtils import verify_with_rsa

        sign = params.get("sign")
        sign_type = params.get("sign_type", "RSA2")
        if not sign:
            logger.warning("回调缺少 sign 参数")
            return False

        # 构造待验签字符串：去 sign 和 sign_type，按 key 排序
        params_for_verify = {
            k: v for k, v in params.items()
            if k not in ("sign", "sign_type") and v
        }
        sorted_params = sorted(params_for_verify.items())
        query_string = "&".join(f"{k}={v}" for k, v in sorted_params)

        # 用支付宝公钥验签
        is_valid = verify_with_rsa(
            settings.ALIPAY_PUBLIC_KEY,
            query_string,
            sign,
        )

        if not is_valid:
            logger.warning(f"回调验签失败 | out_trade_no={params.get('out_trade_no')}")
            return False

        # 2. 处理业务
        out_trade_no = params.get("out_trade_no")
        trade_status = params.get("trade_status")
        trade_no = params.get("trade_no")

        if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            order = order_store.update_status(
                out_trade_no, PaymentStatus.PAID, trade_no=trade_no
            )
            if order:
                logger.info(
                    f"支付成功 | order={out_trade_no} | "
                    f"trade_no={trade_no} | action={order.get('action')}"
                )
                return True
            else:
                logger.warning(f"回调订单不存在: {out_trade_no}")
        elif trade_status == "TRADE_CLOSED":
            order_store.update_status(out_trade_no, PaymentStatus.CLOSED)
            logger.info(f"交易关闭 | order={out_trade_no}")

        return False

    # ── 判断是否已支付 ────────────────────────────────────────

    def is_paid(self, order_id: str) -> bool:
        """快速判断订单是否已支付"""
        order = order_store.get(order_id)
        return order is not None and order["status"] == PaymentStatus.PAID

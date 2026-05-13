"""
支付订单数据模型
"""

import enum
import time
import uuid
from typing import Optional

from pydantic import BaseModel, Field


class PaymentStatus(str, enum.Enum):
    """订单状态"""
    PENDING = "PENDING"          # 待支付
    PAID = "PAID"                # 已支付
    CLOSED = "CLOSED"            # 已关闭（超时/取消）
    REFUNDED = "REFUNDED"        # 已退款


class PaymentAction(str, enum.Enum):
    """支付的业务动作"""
    SEARCH = "search"            # 搜索
    DOWNLOAD = "download"        # 下载


class OrderCreateRequest(BaseModel):
    """创建订单请求"""
    action: PaymentAction = Field(..., description="业务动作：search / download")
    keyword: Optional[str] = Field(None, description="搜索关键词（search 时必填）")
    url: Optional[str] = Field(None, description="小说URL（download 时必填）")
    source_id: Optional[int] = Field(None, description="书源ID")
    format: Optional[str] = Field("txt", description="下载格式：txt / epub")


class OrderResponse(BaseModel):
    """创建订单响应"""
    order_id: str = Field(..., description="订单号")
    trade_no: Optional[str] = Field(None, description="支付宝交易号（支付后才有）")
    action: PaymentAction
    amount: float = Field(..., description="金额（元）")
    pay_url: Optional[str] = Field(None, description="支付跳转 URL")
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: float = Field(default_factory=time.time)


class OrderStatusResponse(BaseModel):
    """订单状态查询响应"""
    order_id: str
    status: PaymentStatus
    action: PaymentAction
    amount: float
    trade_no: Optional[str] = None
    created_at: float
    paid_at: Optional[float] = None
    keyword: Optional[str] = None
    url: Optional[str] = None


class PaymentCallbackData(BaseModel):
    """支付宝异步回调数据（只列关键字段）"""
    out_trade_no: str = Field(..., alias="out_trade_no")
    trade_no: str = Field(..., alias="trade_no")
    trade_status: str = Field(..., alias="trade_status")
    total_amount: str = Field(..., alias="total_amount")
    buyer_id: Optional[str] = Field(None, alias="buyer_id")
    gmt_payment: Optional[str] = Field(None, alias="gmt_payment")

    class Config:
        populate_by_name = True


# ── 价格配置（可后续移到 config / 数据库） ──────────────────────────

PRICE_TABLE = {
    PaymentAction.SEARCH: 0.01,    # 搜索 1 分钱（测试价，正式调高）
    PaymentAction.DOWNLOAD: 0.01,  # 下载 1 分钱
}


def generate_order_id() -> str:
    """生成唯一订单号：novel + 时间戳 + 8位随机"""
    ts = int(time.time() * 1000)
    short_uuid = uuid.uuid4().hex[:8]
    return f"novel{ts}{short_uuid}"

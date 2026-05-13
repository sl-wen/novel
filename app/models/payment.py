"""
支付数据模型 — 402 AI Pay 方案（精简版）
"""

import enum
import time
import uuid
from typing import Optional

from pydantic import BaseModel, Field


class PaymentAction(str, enum.Enum):
    """支付的业务动作"""
    SEARCH = "search"
    DOWNLOAD = "download"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CLOSED = "CLOSED"


class PaymentProofRequest(BaseModel):
    """AI Agent 请求 paymentProof"""
    action: PaymentAction = Field(..., description="search / download")
    keyword: Optional[str] = Field(None, description="搜索关键词")
    url: Optional[str] = Field(None, description="小说URL")
    format: Optional[str] = Field("txt", description="下载格式")


class PaymentProofResponse(BaseModel):
    """返回 paymentProof 给 AI Agent"""
    paymentProof: str = Field(..., description="付费凭证，重试请求时带上")
    action: PaymentAction
    amount: float
    description: str
    usage: str = Field(
        "在请求头 X-Payment-Proof 或参数 paymentProof 中携带此凭证重试请求",
        description="使用说明",
    )


# ── 价格 ──────────────────────────────────────────────
PRICE_TABLE = {
    PaymentAction.SEARCH: 0.01,
    PaymentAction.DOWNLOAD: 0.01,
}

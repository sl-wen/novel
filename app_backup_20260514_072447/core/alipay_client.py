"""
支付宝客户端初始化 — RSA2 公钥模式

密钥自动处理：
- 支持带/不带 BEGIN/END 标记
- 自动将 PKCS#8 格式转为 PKCS#1（rsa 库需要）
"""

import logging
import textwrap
from functools import lru_cache

from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient

from app.core.config import settings

logger = logging.getLogger(__name__)


def _ensure_pem(raw_key: str, marker: str) -> str:
    """确保密钥有 PEM 标记"""
    raw_key = raw_key.strip()
    if f"-----BEGIN {marker}-----" in raw_key:
        return raw_key
    wrapped = textwrap.fill(raw_key, width=64)
    return f"-----BEGIN {marker}-----\n{wrapped}\n-----END {marker}-----"


def _pkcs8_to_pkcs1(private_key_pem: str) -> str:
    """
    将 PKCS#8 格式私钥转换为 PKCS#1 格式
    rsa 库的 load_pkcs1 需要 PKCS#1 格式
    """
    try:
        from cryptography.hazmat.primitives.serialization import (
            load_pem_private_key,
            Encoding,
            PrivateFormat,
            NoEncryption,
        )
        key = load_pem_private_key(private_key_pem.encode(), password=None)
        return key.private_bytes(
            Encoding.PEM,
            PrivateFormat.TraditionalOpenSSL,  # PKCS#1
            NoEncryption(),
        ).decode()
    except Exception as e:
        logger.warning(f"PKCS#8 转 PKCS#1 失败，使用原始密钥: {e}")
        return private_key_pem


def _format_private_key(raw_key: str) -> str:
    """格式化应用私钥：加 PEM 标记 + PKCS#8→PKCS#1 转换"""
    # 先确保有 PEM 标记
    pem = _ensure_pem(raw_key, "PRIVATE KEY")
    # 如果是 PKCS#8（以 BEGIN PRIVATE KEY 开头，不含 RSA），转为 PKCS#1
    if "BEGIN PRIVATE KEY" in pem and "BEGIN RSA PRIVATE KEY" not in pem:
        pem = _pkcs8_to_pkcs1(pem)
    return pem


@lru_cache(maxsize=1)
def get_alipay_client() -> DefaultAlipayClient:
    """
    获取支付宝客户端单例。
    自动处理密钥格式兼容性。
    """
    formatted_private_key = _format_private_key(settings.ALIPAY_APP_PRIVATE_KEY)
    formatted_public_key = _ensure_pem(settings.ALIPAY_PUBLIC_KEY, "PUBLIC KEY")

    config = AlipayClientConfig()
    config.server_url = settings.ALIPAY_SERVER_URL
    config.app_id = settings.ALIPAY_APP_ID
    config.app_private_key = formatted_private_key
    config.alipay_public_key = formatted_public_key
    config.sign_type = "RSA2"

    client = DefaultAlipayClient(alipay_client_config=config, logger=logger)
    logger.info(
        f"支付宝客户端初始化完成 | app_id={settings.ALIPAY_APP_ID} | "
        f"sandbox={settings.ALIPAY_SANDBOX}"
    )
    return client

import base64
import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from settings.config import settings


class AlipayConfigError(RuntimeError):
    pass


def _normalize_key(key: str, key_type: str) -> str:
    key = (key or "").strip().replace("\\n", "\n")
    if not key:
        raise AlipayConfigError("支付宝沙箱密钥未配置")
    if "BEGIN" in key:
        return key
    header = "PRIVATE KEY" if key_type == "private" else "PUBLIC KEY"
    lines = [key[i:i + 64] for i in range(0, len(key), 64)]
    return f"-----BEGIN {header}-----\n" + "\n".join(lines) + f"\n-----END {header}-----"


def ensure_alipay_enabled() -> None:
    if not settings.ALIPAY_SANDBOX_ENABLED:
        raise AlipayConfigError("支付宝沙箱支付未启用")
    if not settings.ALIPAY_APP_ID:
        raise AlipayConfigError("ALIPAY_APP_ID 未配置")
    if not settings.ALIPAY_NOTIFY_URL:
        raise AlipayConfigError("ALIPAY_NOTIFY_URL 未配置")


def _ordered_content(
        params: dict[str, Any],
        *,
        include_sign_type: bool = True,
) -> str:
    filtered = {
        key: str(value)
        for key, value in params.items()
        if value not in (None, "")
        and key != "sign"
        and (include_sign_type or key != "sign_type")
    }
    return "&".join(f"{key}={filtered[key]}" for key in sorted(filtered))


def sign_params(params: dict[str, Any]) -> str:
    private_key = serialization.load_pem_private_key(
        _normalize_key(settings.ALIPAY_PRIVATE_KEY, "private").encode("utf-8"),
        password=None,
    )
    signature = private_key.sign(
        _ordered_content(params).encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def verify_params(params: dict[str, Any]) -> bool:
    sign = params.get("sign")
    if not sign:
        return False
    public_key = serialization.load_pem_public_key(
        _normalize_key(settings.ALIPAY_PUBLIC_KEY, "public").encode("utf-8")
    )
    try:
        public_key.verify(
            base64.b64decode(sign),
            _ordered_content(params, include_sign_type=False).encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except (InvalidSignature, ValueError):
        return False


def build_page_pay_url(out_trade_no: str, subject: str, total_amount: Decimal) -> str:
    ensure_alipay_enabled()
    biz_content = {
        "out_trade_no": out_trade_no,
        "product_code": "FAST_INSTANT_TRADE_PAY",
        "total_amount": f"{total_amount:.2f}",
        "subject": subject,
    }
    params = {
        "app_id": settings.ALIPAY_APP_ID,
        "method": "alipay.trade.page.pay",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": settings.ALIPAY_NOTIFY_URL,
        "return_url": settings.ALIPAY_RETURN_URL or None,
        "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
    }
    params["sign"] = sign_params(params)
    return f"{settings.ALIPAY_GATEWAY}?{urlencode(params)}"


def request_trade_query(out_trade_no: str) -> dict[str, Any]:
    ensure_alipay_enabled()
    params = {
        "app_id": settings.ALIPAY_APP_ID,
        "method": "alipay.trade.query",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": json.dumps(
            {"out_trade_no": out_trade_no},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    params["sign"] = sign_params(params)
    body = urlencode(params).encode("utf-8")
    request = Request(
        settings.ALIPAY_GATEWAY,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("alipay_trade_query_response") or {}

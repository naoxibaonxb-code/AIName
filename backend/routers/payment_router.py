import asyncio
import html
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import AuthHandler
from dependencies import get_session
from models.payment import PaymentOrder
from repository.usage_repo import UsageRepository
from schemas.payment import (
    AlipayReturnOut,
    AlipaySandboxCreateIn,
    AlipaySandboxCreateOut,
    PaymentOrderOut,
)
from services.alipay_sandbox import (
    AlipayConfigError,
    build_page_pay_url,
    ensure_alipay_enabled,
    request_trade_query,
    verify_params,
)
from settings.config import settings

router = APIRouter(prefix="/payments", tags=["payments"])
auth_handler = AuthHandler()
logger = logging.getLogger(__name__)
GENERATION_CREDIT_AMOUNT = 1
GENERATION_CREDIT_PRICE = Decimal("0.01")
GENERATION_CREDIT_SUBJECT = "AIName 生成机会 x1"


def _trade_status(raw_status: str | None) -> str:
    return {
        "WAIT_BUYER_PAY": "waiting",
        "TRADE_SUCCESS": "paid",
        "TRADE_FINISHED": "finished",
        "TRADE_CLOSED": "closed",
    }.get(raw_status or "", "unknown")


def _parse_alipay_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


async def _get_user_order(
        session: AsyncSession, out_trade_no: str, user_id: int
) -> PaymentOrder:
    order = await session.scalar(
        select(PaymentOrder).where(
            PaymentOrder.out_trade_no == out_trade_no,
            PaymentOrder.user_id == user_id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="支付订单不存在")
    return order


def _apply_alipay_trade_result(order: PaymentOrder, data: dict) -> bool:
    if not data or data.get("code") != "10000":
        return False
    total_amount = data.get("total_amount")
    if total_amount and Decimal(total_amount).quantize(Decimal("0.01")) != order.total_amount:
        logger.warning(
            "支付宝查询金额不一致: out_trade_no=%s, local=%s, remote=%s",
            order.out_trade_no, order.total_amount, total_amount,
        )
        return False
    order.trade_no = data.get("trade_no") or order.trade_no
    order.status = _trade_status(data.get("trade_status"))
    order.buyer_id = data.get("buyer_user_id") or data.get("buyer_logon_id") or order.buyer_id
    order.paid_at = _parse_alipay_time(data.get("send_pay_date")) or order.paid_at
    return True


async def _grant_generation_credit(order: PaymentOrder, session: AsyncSession) -> None:
    if order.status not in {"paid", "finished"}:
        return
    if order.product_code != "generation_credit":
        return
    if order.benefit_granted_at:
        return
    await UsageRepository(session).grant_paid_credit(
        user_id=order.user_id,
        source_id=order.out_trade_no,
        credits=order.credit_amount or GENERATION_CREDIT_AMOUNT,
    )
    order.benefit_granted_at = datetime.now()
    await session.commit()
    await session.refresh(order)


async def _sync_order_from_alipay(order: PaymentOrder, session: AsyncSession) -> None:
    if order.status not in {"created", "waiting", "unknown"}:
        return
    try:
        data = await asyncio.to_thread(request_trade_query, order.out_trade_no)
    except Exception:
        logger.exception("支付宝交易查询失败: %s", order.out_trade_no)
        return
    if _apply_alipay_trade_result(order, data):
        await _grant_generation_credit(order, session)
        if not order.benefit_granted_at:
            await session.commit()
            await session.refresh(order)
    else:
        logger.warning(
            "支付宝交易查询未更新订单: out_trade_no=%s, response=%s",
            order.out_trade_no, data,
        )


@router.post("/alipay/sandbox/orders", response_model=AlipaySandboxCreateOut)
async def create_alipay_sandbox_order(
        data: AlipaySandboxCreateIn,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    try:
        ensure_alipay_enabled()
        subject = data.subject or settings.ALIPAY_TEST_SUBJECT or GENERATION_CREDIT_SUBJECT
        out_trade_no = f"AINAME{datetime.now():%Y%m%d%H%M%S}{uuid.uuid4().hex[:10]}"
        order = PaymentOrder(
            user_id=user_id,
            out_trade_no=out_trade_no,
            subject=subject,
            total_amount=GENERATION_CREDIT_PRICE,
            status="created",
            product_code="generation_credit",
            credit_amount=GENERATION_CREDIT_AMOUNT,
        )
        session.add(order)
        await session.flush()
        pay_url = build_page_pay_url(order.out_trade_no, order.subject, order.total_amount)
        await session.commit()
        await session.refresh(order)
        return AlipaySandboxCreateOut(order=PaymentOrderOut.model_validate(order), pay_url=pay_url)
    except AlipayConfigError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/alipay/sandbox/orders", response_model=list[PaymentOrderOut])
async def list_alipay_sandbox_orders(
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(
        select(PaymentOrder)
        .where(PaymentOrder.user_id == user_id)
        .order_by(PaymentOrder.created_at.desc())
        .limit(limit)
    )
    return [PaymentOrderOut.model_validate(item) for item in rows]


@router.get("/alipay/sandbox/orders/{out_trade_no}", response_model=PaymentOrderOut)
async def get_alipay_sandbox_order(
        out_trade_no: str,
        user_id: int = Depends(auth_handler.auth_access_dependency),
        session: AsyncSession = Depends(get_session)):
    order = await _get_user_order(session, out_trade_no, user_id)
    await _sync_order_from_alipay(order, session)
    return PaymentOrderOut.model_validate(order)


@router.post("/alipay/notify", response_class=PlainTextResponse)
async def alipay_notify(
        request: Request,
        session: AsyncSession = Depends(get_session)):
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    try:
        ensure_alipay_enabled()
    except AlipayConfigError as exc:
        logger.warning("支付宝通知配置错误: %s", exc)
        return PlainTextResponse("fail", status_code=400)
    if not verify_params(params):
        logger.warning(
            "支付宝通知验签失败: out_trade_no=%s, app_id=%s, trade_status=%s",
            params.get("out_trade_no"), params.get("app_id"), params.get("trade_status"),
        )
        return PlainTextResponse("fail", status_code=400)
    if params.get("app_id") != settings.ALIPAY_APP_ID:
        logger.warning("支付宝通知 app_id 不匹配: %s", params.get("app_id"))
        return PlainTextResponse("fail", status_code=400)

    out_trade_no = params.get("out_trade_no", "")
    order = await session.scalar(
        select(PaymentOrder).where(PaymentOrder.out_trade_no == out_trade_no)
    )
    if not order:
        logger.warning("支付宝通知订单不存在: %s", out_trade_no)
        return PlainTextResponse("fail", status_code=404)
    if Decimal(params.get("total_amount", "0")).quantize(Decimal("0.01")) != order.total_amount:
        logger.warning(
            "支付宝通知金额不一致: out_trade_no=%s, local=%s, remote=%s",
            out_trade_no, order.total_amount, params.get("total_amount"),
        )
        return PlainTextResponse("fail", status_code=400)

    order.trade_no = params.get("trade_no") or order.trade_no
    order.status = _trade_status(params.get("trade_status"))
    order.buyer_id = params.get("buyer_id") or order.buyer_id
    order.paid_at = _parse_alipay_time(params.get("gmt_payment")) or order.paid_at
    order.raw_notify = json.dumps(params, ensure_ascii=False)[:4000]
    await _grant_generation_credit(order, session)
    if not order.benefit_granted_at:
        await session.commit()
    return PlainTextResponse("success")


@router.get("/alipay/return", response_model=AlipayReturnOut)
async def alipay_return(request: Request):
    params = dict(request.query_params)
    try:
        ensure_alipay_enabled()
        verified = verify_params(params)
    except AlipayConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AlipayReturnOut(
        out_trade_no=params.get("out_trade_no", ""),
        trade_no=params.get("trade_no"),
        verified=verified,
        message="支付宝同步返回已验签" if verified else "支付宝同步返回验签失败",
    )


@router.get("/alipay/return-page", response_class=HTMLResponse)
async def alipay_return_page(request: Request):
    params = dict(request.query_params)
    verified = False
    if settings.ALIPAY_SANDBOX_ENABLED:
        verified = verify_params(params)
    title = "支付返回"
    status = "验签通过" if verified else "验签失败或未启用沙箱"
    out_trade_no = html.escape(params.get("out_trade_no", ""))
    frontend_url = settings.ALIPAY_FRONTEND_RETURN_URL or ""
    frontend_url_html = html.escape(frontend_url)
    frontend_url_js = json.dumps(frontend_url, ensure_ascii=False)
    action_text = "自动返回个人中心" if frontend_url else "自动关闭当前页面"
    script = (
        f"window.location.href = {frontend_url_js};"
        if frontend_url else
        "window.close();"
    )
    return HTMLResponse(f"""
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <title>{title}</title>
      <style>
        body {{ font-family: sans-serif; padding: 32px; color: #29312d; }}
        .count {{ color: #315c4c; font-weight: 700; }}
        a {{ color: #315c4c; }}
      </style>
    </head>
    <body>
      <h2>{title}</h2>
      <p>{status}</p>
      <p>订单号：{out_trade_no}</p>
      <p><span class="count" id="count">3</span> 秒后{action_text}。</p>
      <p>回到 AIName 后请刷新订单状态。</p>
      {f'<p><a href="{frontend_url_html}">立即返回个人中心</a></p>' if frontend_url else ''}
      <script>
        let count = 3;
        const node = document.getElementById('count');
        const timer = setInterval(() => {{
          count -= 1;
          node.textContent = count;
          if (count <= 0) {{
            clearInterval(timer);
            {script}
          }}
        }}, 1000);
      </script>
    </body>
    </html>
    """)

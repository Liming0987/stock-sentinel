"""App settings CRUD — phone number and notification toggles."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.settings import AppSetting
from app.services.notification_service import (
    SETTING_PHONE, SETTING_SIGNALS, SETTING_TRADE_OPEN, SETTING_TRADE_CLOSE,
)

router = APIRouter()

ALL_KEYS = [SETTING_PHONE, SETTING_SIGNALS, SETTING_TRADE_OPEN, SETTING_TRADE_CLOSE]


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSetting).where(AppSetting.key.in_(ALL_KEYS)))
    rows = {r.key: r.value for r in result.scalars().all()}
    return {
        "notification_phone": rows.get(SETTING_PHONE, ""),
        "notify_signals": rows.get(SETTING_SIGNALS, "true") != "false",
        "notify_trade_open": rows.get(SETTING_TRADE_OPEN, "true") != "false",
        "notify_trade_close": rows.get(SETTING_TRADE_CLOSE, "true") != "false",
    }


@router.post("")
async def save_settings(body: dict, db: AsyncSession = Depends(get_db)):
    mapping = {
        "notification_phone": SETTING_PHONE,
        "notify_signals": SETTING_SIGNALS,
        "notify_trade_open": SETTING_TRADE_OPEN,
        "notify_trade_close": SETTING_TRADE_CLOSE,
    }
    for field, key in mapping.items():
        if field not in body:
            continue
        raw = body[field]
        value = str(raw).lower() if isinstance(raw, bool) else str(raw)

        existing = await db.execute(select(AppSetting).where(AppSetting.key == key))
        row = existing.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(AppSetting(key=key, value=value))

    await db.commit()
    return {"ok": True}


@router.post("/test-sms")
async def test_sms(db: AsyncSession = Depends(get_db)):
    """Send a test SMS to the configured phone number."""
    import asyncio
    from app.config import settings as app_settings
    from app.services.notification_service import NotificationService

    sync_url = app_settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")

    def _send():
        svc = NotificationService(sync_url)
        return svc.notify("Stock Sentinel: test message — notifications are working!")

    loop = asyncio.get_event_loop()
    sent = await loop.run_in_executor(None, _send)
    if sent:
        return {"ok": True, "message": "Test SMS sent"}
    return {"ok": False, "message": "SMS not sent — check phone number is saved and EC2 role has sns:Publish"}

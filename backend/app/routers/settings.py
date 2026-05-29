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
async def test_sms(body: dict = None, db: AsyncSession = Depends(get_db)):
    """Send a test SMS. Accepts {phone} in body or falls back to the saved number."""
    import asyncio
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    from app.config import settings as app_settings
    from app.services.notification_service import NotificationService

    # Phone from request body takes priority so the user can test before saving
    phone = ""
    if body:
        phone = (body.get("phone") or "").strip()

    # Fall back to saved DB value
    if not phone:
        sync_url = app_settings.database_url.replace("+asyncpg", "").replace("+aiopg", "")

        def _load_phone():
            return NotificationService(sync_url)._load_all().get("notification_phone", "")

        phone = await asyncio.to_thread(_load_phone)
        phone = (phone or "").strip()

    if not phone:
        return {"ok": False, "message": "No phone number found — enter your number and click Save first."}

    # Format the number
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        e164 = f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        e164 = f"+{digits}"
    else:
        e164 = f"+{digits}"

    def _send():
        try:
            client = boto3.client("sns", region_name=app_settings.aws_region)
            client.publish(
                PhoneNumber=e164,
                Message="Stock Sentinel: test message — SMS notifications are working!",
                MessageAttributes={
                    "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
                },
            )
            return True, f"SMS sent to {e164}"
        except (BotoCoreError, ClientError) as exc:
            return False, f"AWS SNS error: {exc}"
        except Exception as exc:
            return False, f"Unexpected error: {exc}"

    ok, message = await asyncio.to_thread(_send)
    return {"ok": ok, "message": message}

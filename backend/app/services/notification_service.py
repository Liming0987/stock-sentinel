"""SMS notification service via AWS SNS.

Reads the destination phone and per-event toggles from app_settings (DB).
Uses boto3 / the EC2 instance role — no extra credentials needed.
Failures are always logged and swallowed; notifications must never break
the main trading/scraping flow.
"""
import logging
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings as app_settings

logger = logging.getLogger(__name__)

SETTING_PHONE = "notification_phone"
SETTING_SIGNALS = "notify_signals"
SETTING_TRADE_OPEN = "notify_trade_open"
SETTING_TRADE_CLOSE = "notify_trade_close"


class NotificationService:
    def __init__(self, db_url: str):
        self.db_url = db_url

    def _load_all(self) -> dict:
        try:
            from sqlalchemy import create_engine, select
            from sqlalchemy.orm import Session
            from app.models.settings import AppSetting
            engine = create_engine(self.db_url)
            with Session(engine) as s:
                rows = s.execute(select(AppSetting)).scalars().all()
            engine.dispose()
            return {r.key: r.value for r in rows}
        except Exception as e:
            logger.warning(f"NotificationService: could not load settings: {e}")
            return {}

    def _is_enabled(self, cfg: dict, key: str) -> bool:
        return cfg.get(key, "true").lower() != "false"

    def _format_phone(self, phone: str) -> str:
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        return f"+{digits}"

    def _send_sms(self, message: str, phone: str) -> bool:
        try:
            client = boto3.client("sns", region_name=app_settings.aws_region)
            client.publish(
                PhoneNumber=self._format_phone(phone),
                Message=message,
                MessageAttributes={
                    "AWS.SNS.SMS.SMSType": {
                        "DataType": "String",
                        "StringValue": "Transactional",
                    }
                },
            )
            logger.info(f"SMS sent to {phone[:6]}**** : {message[:60]}")
            return True
        except (BotoCoreError, ClientError) as e:
            logger.warning(f"SMS send failed: {e}")
            return False

    def notify(self, message: str, setting_key: Optional[str] = None) -> bool:
        """Send an SMS if a phone is configured and the toggle is on."""
        cfg = self._load_all()
        phone = cfg.get(SETTING_PHONE, "").strip()
        if not phone:
            return False
        if setting_key and not self._is_enabled(cfg, setting_key):
            return False
        return self._send_sms(message, phone)

    # ── Convenience helpers ──────────────────────────────────────────────

    def notify_signal(self, ticker: str, action: str, confidence: float,
                      reasoning: str) -> bool:
        msg = (
            f"Stock Sentinel: {action.upper()} signal for ${ticker} "
            f"(confidence {confidence*100:.0f}%). {reasoning}"
        )
        return self.notify(msg, SETTING_SIGNALS)

    def notify_trade_open(self, strategy: str, ticker: str, price: float,
                          stop: Optional[float], target: Optional[float]) -> bool:
        parts = [f"Stock Sentinel: [{strategy}] opened ${ticker} @ ${price:.2f}"]
        if stop:
            parts.append(f"Stop ${stop:.2f}")
        if target:
            parts.append(f"Target ${target:.2f}")
        return self.notify(" | ".join(parts), SETTING_TRADE_OPEN)

    def notify_error(self, context: str, error: str) -> bool:
        msg = f"Stock Sentinel ERROR [{context}]: {error[:200]}"
        return self.notify(msg)

    def notify_trade_close(self, strategy: str, ticker: str, price: float,
                           pnl: float, return_pct: float, reason: str) -> bool:
        sign = "+" if pnl >= 0 else ""
        msg = (
            f"Stock Sentinel: [{strategy}] closed ${ticker} @ ${price:.2f} | "
            f"P&L {sign}${pnl:.2f} ({sign}{return_pct*100:.2f}%) | {reason}"
        )
        return self.notify(msg, SETTING_TRADE_CLOSE)

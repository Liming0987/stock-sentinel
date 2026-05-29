"""Centralized secret loader for AWS Secrets Manager.

All third-party API credentials live in a single secret:
  stock-sentinel/credentials

Keys in that secret are prefixed by service (e.g. reddit_client_id, alpaca_api_key).
There is NO environment variable fallback — credentials must come from AWS.

For local development, run with valid AWS credentials (e.g. `aws sso login`)
that can read the secret above.
"""
import json
import logging
from functools import lru_cache
from typing import Dict

from app.config import settings

logger = logging.getLogger(__name__)

SECRET_NAME = "stock-sentinel/credentials"


class SecretNotConfiguredError(RuntimeError):
    """Raised when a required secret is missing or contains placeholder values."""


@lru_cache(maxsize=1)
def _load_credentials() -> Dict:
    """
    Fetch stock-sentinel/credentials from AWS Secrets Manager (cached for process lifetime).
    Raises SecretNotConfiguredError if missing or still contains placeholder values.
    """
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    try:
        client = boto3.client("secretsmanager", region_name=settings.aws_region)
        response = client.get_secret_value(SecretId=SECRET_NAME)
    except (BotoCoreError, ClientError) as e:
        raise SecretNotConfiguredError(f"Cannot read secret '{SECRET_NAME}': {e}") from e

    try:
        data = json.loads(response["SecretString"])
    except (KeyError, json.JSONDecodeError) as e:
        raise SecretNotConfiguredError(f"Secret '{SECRET_NAME}' is not valid JSON: {e}") from e

    if any(str(v) == "PLACEHOLDER" for v in data.values()):
        raise SecretNotConfiguredError(
            f"Secret '{SECRET_NAME}' contains placeholder values. "
            f"Populate it in the AWS Console."
        )

    logger.info(f"Loaded secret '{SECRET_NAME}' from AWS Secrets Manager")
    return data


def get_reddit_credentials() -> Dict:
    """Returns dict with keys: client_id, client_secret, user_agent."""
    data = _load_credentials()
    return {
        "client_id": data["reddit_client_id"],
        "client_secret": data["reddit_client_secret"],
        "user_agent": data.get("reddit_user_agent", "stock-sentinel/1.0"),
    }


def get_alpaca_credentials() -> Dict:
    """Returns dict with keys: api_key, api_secret, paper.

    When alpaca_paper is True, uses alpaca_paper_api_key / alpaca_paper_api_secret.
    Falls back to alpaca_api_key / alpaca_api_secret for live trading.
    """
    data = _load_credentials()
    paper = bool(data.get("alpaca_paper", True))
    if paper:
        api_key = data.get("alpaca_paper_api_key", "")
        api_secret = data.get("alpaca_paper_api_secret", "")
        if not api_key or not api_secret:
            raise SecretNotConfiguredError(
                "alpaca_paper is True but alpaca_paper_api_key / alpaca_paper_api_secret are empty"
            )
    else:
        api_key = data.get("alpaca_api_key", "")
        api_secret = data.get("alpaca_api_secret", "")
        if not api_key or not api_secret:
            raise SecretNotConfiguredError(
                "alpaca_paper is False but alpaca_api_key / alpaca_api_secret are empty"
            )

    return {"api_key": api_key, "api_secret": api_secret, "paper": paper}

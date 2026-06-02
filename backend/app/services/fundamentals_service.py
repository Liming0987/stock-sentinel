import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import Stock
from app.models.fundamentals import StockFundamentals

logger = logging.getLogger(__name__)

_EMPTY = {"score": None, "grade": "N/A", "pillars": {}, "flags": [], "metrics": {}, "reasoning": []}

PILLAR_WEIGHTS = {
    "valuation": 0.25,
    "profitability": 0.25,
    "growth": 0.20,
    "health": 0.15,
    "analyst": 0.15,
}


def _safe(val, default=None):
    if val is None or (isinstance(val, float) and val != val):
        return default
    return val


def _score_valuation(m: dict) -> tuple[float, list[str]]:
    scores = []
    reasoning = []

    pe = _safe(m.get("trailingPE"))
    if pe is not None:
        if pe < 15:
            scores.append(1.0)
        elif pe < 25:
            scores.append(0.75)
        elif pe < 40:
            scores.append(0.5)
        elif pe < 80:
            scores.append(0.25)
        else:
            scores.append(0.0)
        reasoning.append(f"P/E {pe:.1f}")

    fpe = _safe(m.get("forwardPE"))
    if fpe is not None:
        if fpe < 15:
            scores.append(1.0)
        elif fpe < 25:
            scores.append(0.75)
        elif fpe < 40:
            scores.append(0.5)
        else:
            scores.append(0.0)

    peg = _safe(m.get("pegRatio"))
    if peg is not None:
        if peg < 1:
            scores.append(1.0)
        elif peg < 2:
            scores.append(0.6)
        else:
            scores.append(0.2)
        reasoning.append(f"PEG {peg:.2f}")

    pb = _safe(m.get("priceToBook"))
    if pb is not None:
        if pb < 1.5:
            scores.append(1.0)
        elif pb < 3:
            scores.append(0.75)
        elif pb < 6:
            scores.append(0.4)
        else:
            scores.append(0.1)

    ps = _safe(m.get("priceToSalesTrailing12Months"))
    if ps is not None:
        if ps < 1:
            scores.append(1.0)
        elif ps < 3:
            scores.append(0.75)
        elif ps < 6:
            scores.append(0.4)
        else:
            scores.append(0.2)

    ev_ebitda = _safe(m.get("enterpriseToEbitda"))
    if ev_ebitda is not None and ev_ebitda > 0:
        if ev_ebitda < 10:
            scores.append(1.0)
        elif ev_ebitda < 20:
            scores.append(0.75)
        elif ev_ebitda < 30:
            scores.append(0.4)
        else:
            scores.append(0.1)

    return (sum(scores) / len(scores)) if scores else 0.5, reasoning


def _score_profitability(m: dict) -> tuple[float, list[str]]:
    scores = []
    reasoning = []

    net_margin = _safe(m.get("profitMargins"))
    if net_margin is not None:
        if net_margin > 0.20:
            scores.append(1.0)
        elif net_margin > 0.10:
            scores.append(0.75)
        elif net_margin > 0.05:
            scores.append(0.5)
        elif net_margin >= 0:
            scores.append(0.25)
        else:
            scores.append(0.0)
        reasoning.append(f"Net margin {net_margin:.1%}")

    op_margin = _safe(m.get("operatingMargins"))
    if op_margin is not None:
        if op_margin > 0.20:
            scores.append(1.0)
        elif op_margin > 0.10:
            scores.append(0.75)
        elif op_margin > 0.05:
            scores.append(0.5)
        else:
            scores.append(0.2)

    roe = _safe(m.get("returnOnEquity"))
    if roe is not None:
        if roe > 0.20:
            scores.append(1.0)
        elif roe > 0.10:
            scores.append(0.75)
        elif roe > 0.05:
            scores.append(0.4)
        else:
            scores.append(0.1)
        reasoning.append(f"ROE {roe:.1%}")

    roa = _safe(m.get("returnOnAssets"))
    if roa is not None:
        if roa > 0.10:
            scores.append(1.0)
        elif roa > 0.05:
            scores.append(0.75)
        elif roa > 0.02:
            scores.append(0.5)
        else:
            scores.append(0.2)

    return (sum(scores) / len(scores)) if scores else 0.5, reasoning


def _score_growth(m: dict) -> tuple[float, list[str]]:
    scores = []
    reasoning = []

    rev_growth = _safe(m.get("revenueGrowth"))
    if rev_growth is not None:
        if rev_growth > 0.20:
            scores.append(1.0)
        elif rev_growth > 0.10:
            scores.append(0.75)
        elif rev_growth > 0.05:
            scores.append(0.5)
        elif rev_growth >= 0:
            scores.append(0.25)
        else:
            scores.append(0.0)
        reasoning.append(f"Rev growth {rev_growth:.1%}")

    earn_growth = _safe(m.get("earningsGrowth"))
    if earn_growth is not None:
        if earn_growth > 0.20:
            scores.append(1.0)
        elif earn_growth > 0.10:
            scores.append(0.75)
        elif earn_growth > 0.05:
            scores.append(0.5)
        elif earn_growth >= 0:
            scores.append(0.25)
        else:
            scores.append(0.0)

    qtr_growth = _safe(m.get("earningsQuarterlyGrowth"))
    if qtr_growth is not None:
        if qtr_growth > 0.20:
            scores.append(1.0)
        elif qtr_growth > 0.10:
            scores.append(0.75)
        elif qtr_growth >= 0:
            scores.append(0.4)
        else:
            scores.append(0.1)

    return (sum(scores) / len(scores)) if scores else 0.5, reasoning


def _score_health(m: dict) -> tuple[float, list[str]]:
    scores = []
    reasoning = []

    de = _safe(m.get("debtToEquity"))
    if de is not None:
        de_ratio = de / 100.0 if de > 10 else de
        if de_ratio < 0.3:
            scores.append(1.0)
        elif de_ratio < 1.0:
            scores.append(0.75)
        elif de_ratio < 2.0:
            scores.append(0.5)
        elif de_ratio < 3.0:
            scores.append(0.25)
        else:
            scores.append(0.0)
        reasoning.append(f"D/E {de:.1f}")

    cr = _safe(m.get("currentRatio"))
    if cr is not None:
        if cr > 2:
            scores.append(1.0)
        elif cr >= 1.5:
            scores.append(0.75)
        elif cr >= 1.0:
            scores.append(0.5)
        else:
            scores.append(0.1)

    fcf = _safe(m.get("freeCashflow"))
    if fcf is not None:
        scores.append(1.0 if fcf > 0 else 0.0)
        reasoning.append("Positive FCF" if fcf > 0 else "Negative FCF")

    return (sum(scores) / len(scores)) if scores else 0.5, reasoning


def _score_analyst(m: dict) -> tuple[float, list[str]]:
    scores = []
    reasoning = []

    mean = _safe(m.get("recommendationMean"))
    if mean is not None:
        analyst_score = (5.0 - mean) / 4.0
        scores.append(max(0.0, min(1.0, analyst_score)))
        reasoning.append(f"Analyst rating {mean:.1f}/5")

    n_analysts = _safe(m.get("numberOfAnalystOpinions"), 0)
    if n_analysts and n_analysts > 0:
        scores.append(min(1.0, n_analysts / 20.0))

    target = _safe(m.get("targetMeanPrice"))
    current = _safe(m.get("currentPrice")) or _safe(m.get("regularMarketPrice"))
    if target and current and current > 0:
        upside = (target - current) / current
        if upside > 0.20:
            scores.append(1.0)
        elif upside > 0.10:
            scores.append(0.75)
        elif upside >= 0:
            scores.append(0.5)
        elif upside >= -0.10:
            scores.append(0.25)
        else:
            scores.append(0.0)
        reasoning.append(f"Upside {upside:.1%}")

    return (sum(scores) / len(scores)) if scores else 0.5, reasoning


def _compute_flags(m: dict) -> list[str]:
    flags = []

    pe = _safe(m.get("trailingPE"))
    if pe is not None and pe > 80:
        flags.append("High PE (>80)")

    fcf = _safe(m.get("freeCashflow"))
    if fcf is not None and fcf < 0:
        flags.append("Negative FCF")

    de = _safe(m.get("debtToEquity"))
    if de is not None:
        de_ratio = de / 100.0 if de > 10 else de
        if de_ratio > 3:
            flags.append("High Leverage (D/E>3)")

    rev_growth = _safe(m.get("revenueGrowth"))
    if rev_growth is not None and rev_growth < 0:
        flags.append("Negative Revenue Growth")

    target = _safe(m.get("targetMeanPrice"))
    current = _safe(m.get("currentPrice")) or _safe(m.get("regularMarketPrice"))
    if target and current and current > 0:
        upside = (target - current) / current
        if upside < -0.10:
            flags.append("Below Analyst Target (<-10%)")

    return flags


class FundamentalsService:
    def fetch_raw(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        info = t.info or {}

        next_earnings: Optional[str] = None
        try:
            cal = t.calendar
            if isinstance(cal, dict):
                dates = cal.get("Earnings Date")
                if dates and len(dates) > 0:
                    next_earnings = str(dates[0])
        except Exception:
            pass

        metrics = {
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "pegRatio": info.get("pegRatio") or info.get("trailingPegRatio"),
            "priceToBook": info.get("priceToBook"),
            "priceToSalesTrailing12Months": info.get("priceToSalesTrailing12Months"),
            "enterpriseToEbitda": info.get("enterpriseToEbitda"),
            "profitMargins": info.get("profitMargins"),
            "operatingMargins": info.get("operatingMargins"),
            "returnOnEquity": info.get("returnOnEquity"),
            "returnOnAssets": info.get("returnOnAssets"),
            "revenueGrowth": info.get("revenueGrowth"),
            "earningsGrowth": info.get("earningsGrowth"),
            "earningsQuarterlyGrowth": info.get("earningsQuarterlyGrowth"),
            "debtToEquity": info.get("debtToEquity"),
            "currentRatio": info.get("currentRatio"),
            "freeCashflow": info.get("freeCashflow"),
            "recommendationMean": info.get("recommendationMean"),
            "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
            "targetMeanPrice": info.get("targetMeanPrice"),
            "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
        }
        metrics["_next_earnings"] = next_earnings
        return metrics

    def score(self, metrics: dict) -> dict:
        has_any = any(
            _safe(metrics.get(k)) is not None
            for k in ("trailingPE", "profitMargins", "revenueGrowth", "debtToEquity", "recommendationMean")
        )
        if not has_any:
            return {**_EMPTY, "metrics": metrics}

        val_score, val_r = _score_valuation(metrics)
        prof_score, prof_r = _score_profitability(metrics)
        grow_score, grow_r = _score_growth(metrics)
        health_score, health_r = _score_health(metrics)
        analyst_score, analyst_r = _score_analyst(metrics)

        pillar_scores = {
            "valuation": round(val_score, 4),
            "profitability": round(prof_score, 4),
            "growth": round(grow_score, 4),
            "health": round(health_score, 4),
            "analyst": round(analyst_score, 4),
        }

        composite = sum(pillar_scores[k] * w for k, w in PILLAR_WEIGHTS.items())
        composite = round(composite, 4)

        if composite >= 0.80:
            grade = "A"
        elif composite >= 0.65:
            grade = "B"
        elif composite >= 0.50:
            grade = "C"
        elif composite >= 0.35:
            grade = "D"
        else:
            grade = "F"

        reasoning = val_r + prof_r + grow_r + health_r + analyst_r
        flags = _compute_flags(metrics)

        return {
            "score": composite,
            "grade": grade,
            "pillars": pillar_scores,
            "flags": flags,
            "metrics": {k: v for k, v in metrics.items() if not k.startswith("_")},
            "reasoning": reasoning,
        }

    def get(self, ticker: str, session: Session, allow_fetch: bool = True) -> dict:
        try:
            stock = session.execute(
                select(Stock).where(Stock.ticker == ticker)
            ).scalar_one_or_none()
            if stock is None:
                return {**_EMPTY}

            row = session.execute(
                select(StockFundamentals).where(StockFundamentals.stock_id == stock.id)
            ).scalar_one_or_none()

            stale = row is None or (
                datetime.now(timezone.utc) - row.fetched_at.replace(tzinfo=timezone.utc)
                > timedelta(hours=24)
            )

            if stale and not allow_fetch:
                if row is None:
                    return {**_EMPTY}
                # Return cached stale data — nightly task will refresh

            if stale and allow_fetch:
                raw = self.fetch_raw(ticker)
                result = self.score(raw)
                next_earnings_str = raw.get("_next_earnings")
                next_earnings_dt: Optional[datetime] = None
                if next_earnings_str:
                    try:
                        next_earnings_dt = datetime.fromisoformat(str(next_earnings_str))
                        if next_earnings_dt.tzinfo is None:
                            next_earnings_dt = next_earnings_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                if row is None:
                    row = StockFundamentals(stock_id=stock.id)
                    session.add(row)

                row.raw_metrics = result["metrics"]
                row.score = result["score"]
                row.grade = result["grade"]
                row.pillars = result["pillars"]
                row.flags = result["flags"]
                row.next_earnings = next_earnings_dt
                row.fetched_at = datetime.now(timezone.utc)
                session.commit()

            return {
                "ticker": ticker,
                "score": float(row.score) if row.score is not None else None,
                "grade": row.grade or "N/A",
                "pillars": row.pillars or {},
                "flags": row.flags or [],
                "metrics": row.raw_metrics or {},
                "next_earnings": row.next_earnings.isoformat() if row.next_earnings else None,
                "reasoning": [],
            }
        except Exception as e:
            logger.warning(f"FundamentalsService.get({ticker}) failed: {e}")
            return {**_EMPTY}

    def refresh_all(self, tickers: list[str], session: Session) -> None:
        for ticker in tickers:
            try:
                stock = session.execute(
                    select(Stock).where(Stock.ticker == ticker)
                ).scalar_one_or_none()
                if stock is None:
                    continue
                raw = self.fetch_raw(ticker)
                result = self.score(raw)

                next_earnings_str = raw.get("_next_earnings")
                next_earnings_dt: Optional[datetime] = None
                if next_earnings_str:
                    try:
                        next_earnings_dt = datetime.fromisoformat(str(next_earnings_str))
                        if next_earnings_dt.tzinfo is None:
                            next_earnings_dt = next_earnings_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                row = session.execute(
                    select(StockFundamentals).where(StockFundamentals.stock_id == stock.id)
                ).scalar_one_or_none()
                if row is None:
                    row = StockFundamentals(stock_id=stock.id)
                    session.add(row)

                row.raw_metrics = result["metrics"]
                row.score = result["score"]
                row.grade = result["grade"]
                row.pillars = result["pillars"]
                row.flags = result["flags"]
                row.next_earnings = next_earnings_dt
                row.fetched_at = datetime.now(timezone.utc)
                session.flush()
            except Exception as e:
                logger.warning(f"refresh_all({ticker}) failed: {e}")

        session.commit()

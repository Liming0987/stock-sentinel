import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from app.services.price_service import PriceService


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return None if (f != f) else f  # NaN check
    except Exception:
        return None


def _safe_int(val) -> Optional[int]:
    f = _safe_float(val)
    return None if f is None else int(f)


class VolumeService:
    _price_service = PriceService()

    def analyze(self, ticker: str, period: str = "90d") -> Dict[str, Any]:
        empty = {
            "ticker": ticker,
            "period": period,
            "name": ticker,
            "current_price": None,
            "avg_vol_30d": None,
            "current_vol_ratio": None,
            "history": [],
            "events": [],
            "checklist": {
                "selling_climax": False,
                "high_vol_breakout": False,
                "low_vol_retest": False,
                "higher_low_pivot": False,
                "vwap_reclaim": False,
                "overall": "No reversal signal",
                "score": 0,
                "details": {},
            },
        }

        try:
            df = self._price_service.get_price_data(ticker, period=period, interval="1d")
        except Exception:
            return empty

        if df is None or df.empty:
            return empty

        df = df.copy()

        avg_vol_30 = df["Volume"].rolling(30, min_periods=1).mean()
        vol_ratio = df["Volume"] / avg_vol_30.replace(0, np.nan)

        obv_sign = np.sign(df["Close"].diff()).fillna(0)
        obv = (obv_sign * df["Volume"]).cumsum()

        typical = (df["High"] + df["Low"] + df["Close"]) / 3
        cum_tp_vol = (typical * df["Volume"]).cumsum()
        cum_vol = df["Volume"].cumsum()
        vwap = cum_tp_vol / cum_vol.replace(0, np.nan)

        price_change_pct = df["Close"].pct_change() * 100

        # Interpretation — vectorised via np.select
        cond_reversal = (vol_ratio >= 2.5) & (df["Close"] > df["Open"])
        cond_distribution = (vol_ratio >= 2.5) & (df["Close"] <= df["Open"])
        cond_acc = (vol_ratio >= 1.5) & (price_change_pct > 0)
        cond_dist = (vol_ratio >= 1.5) & (price_change_pct <= 0)
        cond_low = vol_ratio < 0.8

        interpretation = np.select(
            [cond_reversal, cond_distribution, cond_acc, cond_dist, cond_low],
            [
                "Selling climax — possible reversal",
                "Selling climax — heavy distribution",
                "High-volume up day — accumulation",
                "High-volume down day — distribution",
                "Low-volume drift — buyers exhausted",
            ],
            default="Normal trading activity",
        )

        is_spike = (vol_ratio >= 1.5).values

        history: List[Dict] = []
        for i in range(len(df)):
            idx = df.index[i]
            date_str = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
            history.append({
                "date": date_str,
                "open": _safe_float(df["Open"].iat[i]),
                "high": _safe_float(df["High"].iat[i]),
                "low": _safe_float(df["Low"].iat[i]),
                "close": _safe_float(df["Close"].iat[i]),
                "volume": _safe_int(df["Volume"].iat[i]),
                "avg_vol_30": _safe_float(avg_vol_30.iat[i]),
                "vol_ratio": _safe_float(vol_ratio.iat[i]),
                "obv": _safe_float(obv.iat[i]),
                "vwap": _safe_float(vwap.iat[i]),
                "price_change_pct": _safe_float(price_change_pct.iat[i]),
                "interpretation": str(interpretation[i]),
                "is_spike": bool(is_spike[i]),
            })

        events = [
            {
                "date": h["date"],
                "vol_ratio": h["vol_ratio"],
                "price_change_pct": h["price_change_pct"],
                "interpretation": h["interpretation"],
            }
            for h in history
            if h["is_spike"]
        ]

        # Checklist
        prev_close = df["Close"].shift(1)
        gap_down = df["Open"] < prev_close

        selling_climax = bool(((vol_ratio >= 2.5) & gap_down & (df["Close"] > df["Open"])).any())
        high_vol_breakout = bool(((price_change_pct >= 3) & (vol_ratio >= 1.5)).any())

        spike_mask = is_spike
        spike_indices = np.where(spike_mask)[0]
        if len(spike_indices) > 0:
            last_spike_idx = int(spike_indices[-1])
            post_spike = df["Volume"].iloc[last_spike_idx + 1:] if last_spike_idx + 1 < len(df) else pd.Series(dtype=float)
            post_avg = avg_vol_30.iloc[last_spike_idx + 1:] if last_spike_idx + 1 < len(df) else pd.Series(dtype=float)
            if len(post_spike) >= 3:
                below = (post_spike.values < post_avg.values)
                low_vol_retest = bool(np.all(below[:3]))
            else:
                low_vol_retest = False
        else:
            low_vol_retest = False

        if len(df) >= 20:
            lows = df["Low"].iloc[-20:]
            half1 = lows.iloc[:10]
            half2 = lows.iloc[10:]
            higher_low_pivot = bool(float(half2.min()) > float(half1.min()))
        else:
            higher_low_pivot = False

        last_close = _safe_float(df["Close"].iloc[-1])
        last_vwap = _safe_float(vwap.iloc[-1])
        vwap_reclaim = bool(
            last_close is not None and last_vwap is not None and last_close > last_vwap
        )

        score = sum([selling_climax, high_vol_breakout, low_vol_retest, higher_low_pivot, vwap_reclaim])
        if score >= 4:
            overall = "Bullish reversal forming"
        elif score >= 2:
            overall = "Early signs of reversal"
        else:
            overall = "No reversal signal"

        checklist = {
            "selling_climax": selling_climax,
            "high_vol_breakout": high_vol_breakout,
            "low_vol_retest": low_vol_retest,
            "higher_low_pivot": higher_low_pivot,
            "vwap_reclaim": vwap_reclaim,
            "overall": overall,
            "score": score,
            "details": {
                "selling_climax": "Vol spike 2.5x+ with intraday recovery after gap down",
                "high_vol_breakout": "Price +3%+ on 1.5x+ volume",
                "low_vol_retest": "3+ consecutive bars below avg vol after last spike",
                "higher_low_pivot": "Trailing 20-bar second half low > first half low",
                "vwap_reclaim": "Current close above period VWAP",
            },
        }

        try:
            info = self._price_service.get_stock_info(ticker)
            name = info.get("name", ticker) or ticker
        except Exception:
            name = ticker

        current_price = _safe_float(df["Close"].iloc[-1])
        avg_vol_30d = _safe_float(avg_vol_30.iloc[-1])
        current_vol_ratio = _safe_float(vol_ratio.iloc[-1])

        return {
            "ticker": ticker,
            "period": period,
            "name": name,
            "current_price": current_price,
            "avg_vol_30d": avg_vol_30d,
            "current_vol_ratio": current_vol_ratio,
            "history": history,
            "events": events,
            "checklist": checklist,
        }

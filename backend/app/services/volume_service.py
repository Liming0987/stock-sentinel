import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from app.services.price_service import PriceService
from app.services.vcp_service import detect_vcp


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

    def _compute_wyckoff(self, df, vol_ratio, avg_vol_30, gap_down, price_change_pct):
        win = df.tail(min(60, len(df)))
        support = float(np.nanpercentile(win["Low"].values, 5))
        resistance = float(np.nanpercentile(win["High"].values, 95))
        midpoint = (support + resistance) / 2.0

        def _first_date(mask, df):
            idx = mask[mask].index
            if len(idx) == 0:
                return None
            i = idx[0]
            return str(i.date()) if hasattr(i, "date") else str(i)[:10]

        def _last_date(mask, df):
            idx = mask[mask].index
            if len(idx) == 0:
                return None
            i = idx[-1]
            return str(i.date()) if hasattr(i, "date") else str(i)[:10]

        # --- Accumulation ---

        # 1. Selling Climax
        sc_mask = (vol_ratio >= 2.5) & gap_down & (df["Close"] > df["Open"])
        sc_det = bool(sc_mask.any())
        sc_date = _last_date(sc_mask, df)
        sc_detail = (
            "Vol spike 2.5x+ with gap-down open and intraday recovery"
            if sc_det
            else "No selling climax detected"
        )

        # 2. Automatic Rally
        ar_abs_idx: Optional[int] = None
        if sc_det:
            sc_idx = int(np.where(sc_mask.values)[0][-1])
            sc_low = float(df["Low"].iat[sc_idx])
            ar_window_end = min(sc_idx + 6, len(df))
            if sc_idx + 1 < len(df):
                ar_pct = price_change_pct.iloc[sc_idx + 1 : ar_window_end]
                ar_vr = vol_ratio.iloc[sc_idx + 1 : ar_window_end]
                ar_found = (ar_pct >= 3) & (ar_vr >= 1.0)
                ar_det = bool(ar_found.any())
                if ar_det:
                    ar_idx_local = int(np.where(ar_found.values)[0][0])
                    ar_abs_idx = sc_idx + 1 + ar_idx_local
                    ar_ts = df.index[ar_abs_idx]
                    ar_date = str(ar_ts.date()) if hasattr(ar_ts, "date") else str(ar_ts)[:10]
                    ar_detail = "3%+ bounce on volume within 5 bars of selling climax"
                else:
                    ar_date = None
                    ar_detail = "No 3%+ bounce within 5 bars of selling climax"
            else:
                ar_det = False
                ar_date = None
                ar_detail = "No 3%+ bounce within 5 bars of selling climax"
        else:
            sc_low = None
            ar_det = False
            ar_date = None
            ar_detail = "No prior selling climax to follow"

        # 3. Secondary Test
        if sc_det and sc_low is not None:
            start_idx = ar_abs_idx + 1 if ar_abs_idx is not None else (int(np.where(sc_mask.values)[0][-1]) + 1)
            if start_idx < len(df):
                st_vol = vol_ratio.iloc[start_idx:]
                st_close = df["Close"].iloc[start_idx:]
                st_cond = (st_vol < 0.8) & (st_close > sc_low)
                consec = st_cond.astype(int)
                rolling_3 = consec.rolling(3).sum()
                st_det = bool((rolling_3 >= 3).any())
                if st_det:
                    first_end = int(np.where((rolling_3 >= 3).values)[0][0])
                    st_ts = st_vol.index[first_end - 2]
                    st_date = str(st_ts.date()) if hasattr(st_ts, "date") else str(st_ts)[:10]
                    st_detail = "3+ consecutive low-vol bars above SC low"
                else:
                    st_date = None
                    st_detail = "No secondary test pattern found"
            else:
                st_det = False
                st_date = None
                st_detail = "No secondary test pattern found"
        else:
            st_det = False
            st_date = None
            st_detail = "No prior selling climax to anchor secondary test"

        # 4. Sign of Strength
        sos_mask = (price_change_pct >= 4) & (vol_ratio >= 2.0) & (df["Close"] > midpoint)
        sos_det = bool(sos_mask.any())
        sos_date = _last_date(sos_mask, df)
        sos_detail = "Strong up day 4%+ on 2x+ volume above range midpoint" if sos_det else "No sign of strength detected"

        # 5. Last Point of Support
        if len(df) >= 20:
            lows = df["Low"].iloc[-20:]
            half1_min = float(lows.iloc[:10].min())
            half2_min = float(lows.iloc[10:].min())
            last_close_val = float(df["Close"].iloc[-1])
            lps_higher_low = half2_min > half1_min
            lps_near_support = (last_close_val <= support * 1.03) and (last_close_val >= support * 0.97)
            lps_det = lps_higher_low and lps_near_support
        else:
            lps_det = False
        lps_date = str(df.index[-1].date()) if lps_det and hasattr(df.index[-1], "date") else (str(df.index[-1])[:10] if lps_det else None)
        lps_detail = "Higher low pivot with price near support zone" if lps_det else "No last point of support confirmed"

        # --- Distribution ---

        # 1. Buying Climax
        window_high = float(df["High"].max())
        bc_mask = (df["High"] >= window_high * 0.999) & (vol_ratio >= 2.0) & (df["Close"] < df["Open"])
        bc_det = bool(bc_mask.any())
        bc_date = _last_date(bc_mask, df)
        bc_detail = (
            "New period high on 2x+ volume with bearish close (in-window high — may not be true 52w high for periods < 1y)"
            if bc_det
            else "No buying climax detected"
        )

        # 2. Automatic Reaction
        if bc_det:
            bc_idx = int(np.where(bc_mask.values)[0][-1])
            ar2_window_end = min(bc_idx + 11, len(df))
            if bc_idx + 1 < len(df):
                ar2_pct = price_change_pct.iloc[bc_idx + 1 : ar2_window_end]
                ar2_vr = vol_ratio.iloc[bc_idx + 1 : ar2_window_end]
                ar2_found = (ar2_pct <= -3) & (ar2_vr >= 1.5)
                ar2_det = bool(ar2_found.any())
                if ar2_det:
                    ar2_idx_local = int(np.where(ar2_found.values)[0][0])
                    ar2_abs_idx = bc_idx + 1 + ar2_idx_local
                    ar2_ts = df.index[ar2_abs_idx]
                    ar2_date = str(ar2_ts.date()) if hasattr(ar2_ts, "date") else str(ar2_ts)[:10]
                    ar2_detail = "3%+ drop on 1.5x+ volume within 10 bars of buying climax"
                else:
                    ar2_date = None
                    ar2_detail = "No sharp reaction within 10 bars of buying climax"
            else:
                ar2_det = False
                ar2_date = None
                ar2_detail = "No sharp reaction within 10 bars of buying climax"
        else:
            ar2_det = False
            ar2_date = None
            ar2_detail = "No prior buying climax to follow"

        # 3. Upthrust
        ut_mask = (df["High"] > resistance * 1.005) & (df["Close"] < resistance)
        ut_det = bool(ut_mask.any())
        ut_date = _last_date(ut_mask, df)
        ut_detail = "Price pierced resistance intraday but closed below it" if ut_det else "No upthrust detected"

        # 4. Sign of Weakness
        sow_mask = (price_change_pct <= -3) & (vol_ratio >= 1.5) & (df["Close"] < (df["High"] + df["Low"]) / 2)
        sow_det = bool(sow_mask.any())
        sow_date = _last_date(sow_mask, df)
        sow_detail = "Sharp decline 3%+ on 1.5x+ volume closing near lows" if sow_det else "No sign of weakness detected"

        # 5. Last Point of Supply
        if sow_det:
            sow_idx = int(np.where(sow_mask.values)[0][-1])
            if sow_idx + 1 < len(df):
                lps2_pct = price_change_pct.iloc[sow_idx + 1:]
                lps2_vr = vol_ratio.iloc[sow_idx + 1:]
                lps2_close = df["Close"].iloc[sow_idx + 1:]
                lps2_avg = avg_vol_30.iloc[sow_idx + 1:]
                lps2_cond = (lps2_pct > 0) & (lps2_close < resistance) & (df["Volume"].iloc[sow_idx + 1:] < lps2_avg)
                consec2 = lps2_cond.astype(int)
                rolling2_3 = consec2.rolling(3).sum()
                lps2_det = bool((rolling2_3 >= 3).any())
                if lps2_det:
                    first2_end = int(np.where((rolling2_3 >= 3).values)[0][0])
                    lps2_ts = lps2_vr.index[first2_end - 2]
                    lps2_date = str(lps2_ts.date()) if hasattr(lps2_ts, "date") else str(lps2_ts)[:10]
                    lps2_detail = "3+ low-vol up-days below resistance after SOW"
                else:
                    lps2_date = None
                    lps2_detail = "No last point of supply pattern found"
            else:
                lps2_det = False
                lps2_date = None
                lps2_detail = "No last point of supply pattern found"
        else:
            lps2_det = False
            lps2_date = None
            lps2_detail = "No prior sign of weakness to anchor LPSY"

        # Scoring
        acc_score = sum([sc_det, ar_det, st_det, sos_det, lps_det])
        dist_score = sum([bc_det, ar2_det, ut_det, sow_det, lps2_det])

        bias = "bullish" if acc_score > dist_score else ("bearish" if dist_score > acc_score else "neutral")

        def phase_label(score, side):
            mapping = {0: "No Signal", 1: "Phase A", 2: "Phase B", 3: "Phase B", 4: "Phase C-D", 5: "Phase E (Complete)"}
            return f"{side} {mapping.get(score, 'Phase B')}"

        if bias == "bullish":
            phase = phase_label(acc_score, "Accumulation")
        elif bias == "bearish":
            phase = phase_label(dist_score, "Distribution")
        else:
            phase = "Consolidation / No Clear Phase"

        def acc_overall(s):
            if s >= 4:
                return "Strong Accumulation (Phase C-D)"
            if s >= 2:
                return "Early Accumulation (Phase A-B)"
            return "No Accumulation Signal"

        def dist_overall(s):
            if s >= 4:
                return "Distribution Warning (Phase C-D)"
            if s >= 2:
                return "Distribution Warning (Phase B)"
            return "No Distribution Signal"

        return {
            "phase": phase,
            "bias": bias,
            "trading_range": {"support": _safe_float(support), "resistance": _safe_float(resistance)},
            "accumulation": {
                "selling_climax": {"detected": sc_det, "date": sc_date, "detail": sc_detail},
                "automatic_rally": {"detected": ar_det, "date": ar_date, "detail": ar_detail},
                "secondary_test": {"detected": st_det, "date": st_date, "detail": st_detail},
                "sign_of_strength": {"detected": sos_det, "date": sos_date, "detail": sos_detail},
                "last_point_support": {"detected": lps_det, "date": lps_date, "detail": lps_detail},
                "score": acc_score,
                "overall": acc_overall(acc_score),
            },
            "distribution": {
                "buying_climax": {"detected": bc_det, "date": bc_date, "detail": bc_detail},
                "automatic_reaction": {"detected": ar2_det, "date": ar2_date, "detail": ar2_detail},
                "upthrust": {"detected": ut_det, "date": ut_date, "detail": ut_detail},
                "sign_of_weakness": {"detected": sow_det, "date": sow_date, "detail": sow_detail},
                "last_point_supply": {"detected": lps2_det, "date": lps2_date, "detail": lps2_detail},
                "score": dist_score,
                "overall": dist_overall(dist_score),
            },
        }

    def _compute_pnf(self, df: pd.DataFrame, atr_14: float) -> Dict[str, Any]:
        """Compute Point & Figure price targets using ATR-based box sizing."""
        empty_pnf = {
            "box_size": None,
            "reversal_boxes": 3,
            "current_price": None,
            "bullish_vertical_target": None,
            "bearish_vertical_target": None,
            "horizontal_target": None,
            "column_count": None,
            "bias": None,
            "note": "Insufficient data — need at least 20 bars for P&F analysis.",
        }

        if len(df) < 20:
            return empty_pnf

        box_size = max(round(atr_14 * 0.1, 2), 0.01)
        reversal_boxes = 3
        reversal_amount = reversal_boxes * box_size

        closes = df["Close"].values
        current_price = float(closes[-1])

        # Build P&F columns iteratively
        # Each column is represented as (direction, high, low, num_boxes)
        direction = 1  # 1=X (up), -1=O (down)
        col_high = closes[0]
        col_low = closes[0]
        columns: List[Dict] = []

        for price in closes[1:]:
            if direction == 1:
                # In an X column — check for continuation or reversal
                if price >= col_high + box_size:
                    col_high = price
                elif price <= col_high - reversal_amount:
                    # Reversal to O column
                    num_boxes = max(1, int((col_high - col_low) / box_size))
                    columns.append({"direction": 1, "high": col_high, "low": col_low, "boxes": num_boxes})
                    direction = -1
                    col_high = col_high - box_size  # new O column starts one box below prior X high
                    col_low = price
            else:
                # In an O column — check for continuation or reversal
                if price <= col_low - box_size:
                    col_low = price
                elif price >= col_low + reversal_amount:
                    # Reversal to X column
                    num_boxes = max(1, int((col_high - col_low) / box_size))
                    columns.append({"direction": -1, "high": col_high, "low": col_low, "boxes": num_boxes})
                    direction = 1
                    col_low = col_low + box_size  # new X column starts one box above prior O low
                    col_high = price

        # Finalize last column
        num_boxes = max(1, int((col_high - col_low) / box_size)) if col_high > col_low else 1
        columns.append({"direction": direction, "high": col_high, "low": col_low, "boxes": num_boxes})

        column_count = len(columns)
        bias = "bullish" if direction == 1 else "bearish"

        # Vertical Count: tallest X column → bullish target; tallest O column → bearish target
        x_cols = [c for c in columns if c["direction"] == 1]
        o_cols = [c for c in columns if c["direction"] == -1]

        if x_cols:
            tallest_x = max(x_cols, key=lambda c: c["boxes"])
            bullish_vertical_target = _safe_float(tallest_x["high"] + tallest_x["boxes"] * box_size * 3)
        else:
            bullish_vertical_target = None

        if o_cols:
            tallest_o = max(o_cols, key=lambda c: c["boxes"])
            bearish_vertical_target = _safe_float(tallest_o["low"] - tallest_o["boxes"] * box_size * 3)
        else:
            bearish_vertical_target = None

        # Horizontal Count: count columns in most recent congestion zone
        # Congestion = contiguous run of alternating columns with small overall range
        horizontal_target = None
        if column_count >= 4:
            # Use last min(12, column_count) columns as congestion zone
            congestion_cols = columns[-min(12, column_count):]
            cong_count = len(congestion_cols)
            cong_high = max(c["high"] for c in congestion_cols)
            cong_low = min(c["low"] for c in congestion_cols)
            cong_range = cong_high - cong_low

            # Only apply horizontal count if range is reasonably tight (< 10 * box_size)
            if cong_range < box_size * 10:
                h_target_val = cong_high + cong_count * box_size * reversal_boxes
                horizontal_target = _safe_float(h_target_val)

        return {
            "box_size": _safe_float(box_size),
            "reversal_boxes": reversal_boxes,
            "current_price": _safe_float(current_price),
            "bullish_vertical_target": bullish_vertical_target,
            "bearish_vertical_target": bearish_vertical_target,
            "horizontal_target": horizontal_target,
            "column_count": column_count,
            "bias": bias,
            "note": "Targets computed via 3-box reversal ATR-based P&F. Use 1y period for most accurate targets.",
        }

    def _compute_swing_entry(self, wyckoff: Dict, current_price: Optional[float], atr_14: float) -> Dict[str, Any]:
        """Compute swing trade entry zone based on Wyckoff bias, support/resistance, and ATR."""
        bias = wyckoff.get("bias", "neutral")
        support = wyckoff.get("trading_range", {}).get("support")
        resistance = wyckoff.get("trading_range", {}).get("resistance")

        if support is None or resistance is None or current_price is None:
            return {
                "bias": bias,
                "entry_zone_low": None,
                "entry_zone_high": None,
                "stop_loss": None,
                "target": None,
                "risk_reward": None,
                "time_horizon": "1–5 days (short-term swing)",
                "note": "Insufficient data to compute swing entry.",
            }

        if bias == "bullish":
            entry_zone_low = support
            entry_zone_high = support + atr_14
            stop_loss = support - atr_14
            target = resistance
            note = "Long at support with stop below. R/R based on trading range width."
        else:
            # bearish or neutral — use short setup
            entry_zone_low = resistance - atr_14
            entry_zone_high = resistance
            stop_loss = resistance + atr_14
            target = support
            note = "Short at resistance with stop above. R/R based on trading range width."

        entry_mid = (entry_zone_low + entry_zone_high) / 2.0
        price_diff = abs(target - entry_mid)
        stop_diff = abs(entry_mid - stop_loss)
        risk_reward = _safe_float(price_diff / stop_diff) if stop_diff > 0 else None

        return {
            "bias": bias,
            "entry_zone_low": _safe_float(entry_zone_low),
            "entry_zone_high": _safe_float(entry_zone_high),
            "stop_loss": _safe_float(stop_loss),
            "target": _safe_float(target),
            "risk_reward": risk_reward,
            "time_horizon": "1–5 days (short-term swing)",
            "note": note,
        }

    def _compute_edgar_dca(self, edgar_quarters: List[dict], wyckoff: Dict) -> Optional[Dict[str, Any]]:
        """
        Fundamental DCA zone derived from SEC EDGAR quarterly EPS.
        Returns None if there isn't enough data, so the caller can fall back.
        """
        # Need 4 quarters with non-null EPS
        eps_vals = [q.get("eps_diluted") for q in edgar_quarters[:4]]
        if len(eps_vals) < 4 or any(v is None for v in eps_vals):
            return None

        ttm_eps = sum(eps_vals)
        if ttm_eps <= 0:
            # Loss-making company — price-based DCA is more appropriate
            return None

        # Annualised EPS growth: compare newest quarter vs oldest over 3 intervals
        newest, oldest = eps_vals[0], eps_vals[3]
        if oldest > 0:
            total_growth = (newest - oldest) / oldest
            # 3 quarter span → annualise to 4 quarters
            annual_growth_pct = total_growth * (4 / 3) * 100
        else:
            annual_growth_pct = 0.0

        # Fair P/E via PEG ≈ 1.2, bounded [10, 35]
        if annual_growth_pct > 0:
            fair_pe = min(35.0, max(10.0, annual_growth_pct * 1.2))
        else:
            fair_pe = 12.0  # low/no-growth baseline multiple

        fair_value = ttm_eps * fair_pe

        # DCA zone: 5–20% below fair value (margin of safety)
        entry_low = fair_value * 0.80
        entry_high = fair_value * 0.95
        entry_mid = (entry_low + entry_high) / 2.0
        # Stop: 35% below fair value — fundamental thesis is broken
        stop_loss = fair_value * 0.65

        # Target: whichever is higher — fair value or Wyckoff resistance
        resistance = wyckoff.get("trading_range", {}).get("resistance")
        target = max(fair_value, resistance) if resistance else fair_value

        r_diff = abs(target - entry_mid)
        s_diff = abs(entry_mid - stop_loss)
        risk_reward = _safe_float(r_diff / s_diff) if s_diff > 0 else None

        growth_str = f"{annual_growth_pct:+.1f}%" if annual_growth_pct != 0 else "flat"
        note = (
            f"Fair value ${fair_value:.2f} = TTM EPS ${ttm_eps:.2f} × P/E {fair_pe:.1f} "
            f"(EPS growth {growth_str} annualised). "
            f"DCA 5–20% below fair value. Stop 35% below fair value."
        )

        return {
            "entry_zone_low": _safe_float(entry_low),
            "entry_zone_high": _safe_float(entry_high),
            "stop_loss": _safe_float(stop_loss),
            "target": _safe_float(target),
            "risk_reward": risk_reward,
            "time_horizon": "6–18 months (long-term position)",
            "note": note,
        }

    def _compute_longterm_entry(self, df: pd.DataFrame, wyckoff: Dict, edgar_quarters: Optional[List[dict]] = None) -> Dict[str, Any]:
        """Fundamental DCA when EDGAR EPS data is available; price-based fallback otherwise."""
        if edgar_quarters:
            result = self._compute_edgar_dca(edgar_quarters, wyckoff)
            if result:
                return result

        # ── price-based fallback ─────────────────────────────────────────────
        resistance = wyckoff.get("trading_range", {}).get("resistance")
        lt_support = float(df["Close"].min())
        lt_resistance = resistance if resistance is not None else float(df["Close"].max())

        entry_zone_low = lt_support * 0.98
        entry_zone_high = lt_support * 1.02
        entry_mid = (entry_zone_low + entry_zone_high) / 2.0
        stop_loss = entry_mid * 0.85
        target = lt_resistance

        price_diff = abs(target - entry_mid)
        stop_diff = abs(entry_mid - stop_loss)
        risk_reward = _safe_float(price_diff / stop_diff) if stop_diff > 0 else None

        return {
            "entry_zone_low": _safe_float(entry_zone_low),
            "entry_zone_high": _safe_float(entry_zone_high),
            "stop_loss": _safe_float(stop_loss),
            "target": _safe_float(target),
            "risk_reward": risk_reward,
            "time_horizon": "6–18 months (long-term position)",
            "note": "DCA into 52w support zone. Stop 15% below entry. Target prior resistance.",
        }

    def analyze(self, ticker: str, period: str = "90d", edgar_quarters: Optional[List[dict]] = None) -> Dict[str, Any]:
        _empty_pnf = {
            "box_size": None,
            "reversal_boxes": 3,
            "current_price": None,
            "bullish_vertical_target": None,
            "bearish_vertical_target": None,
            "horizontal_target": None,
            "column_count": None,
            "bias": None,
            "note": "No data available.",
        }
        _empty_swing = {
            "bias": "neutral",
            "entry_zone_low": None,
            "entry_zone_high": None,
            "stop_loss": None,
            "target": None,
            "risk_reward": None,
            "time_horizon": "1–5 days (short-term swing)",
            "note": "No data available.",
        }
        _empty_longterm = {
            "entry_zone_low": None,
            "entry_zone_high": None,
            "stop_loss": None,
            "target": None,
            "risk_reward": None,
            "time_horizon": "6–18 months (long-term position)",
            "note": "No data available.",
        }

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
            "wyckoff": {
                "phase": "Consolidation / No Clear Phase",
                "bias": "neutral",
                "trading_range": {"support": None, "resistance": None},
                "accumulation": {
                    "selling_climax": {"detected": False, "date": None, "detail": ""},
                    "automatic_rally": {"detected": False, "date": None, "detail": ""},
                    "secondary_test": {"detected": False, "date": None, "detail": ""},
                    "sign_of_strength": {"detected": False, "date": None, "detail": ""},
                    "last_point_support": {"detected": False, "date": None, "detail": ""},
                    "score": 0,
                    "overall": "No Accumulation Signal",
                },
                "distribution": {
                    "buying_climax": {"detected": False, "date": None, "detail": ""},
                    "automatic_reaction": {"detected": False, "date": None, "detail": ""},
                    "upthrust": {"detected": False, "date": None, "detail": ""},
                    "sign_of_weakness": {"detected": False, "date": None, "detail": ""},
                    "last_point_supply": {"detected": False, "date": None, "detail": ""},
                    "score": 0,
                    "overall": "No Distribution Signal",
                },
            },
            "pnf": _empty_pnf,
            "swing_entry": _empty_swing,
            "longterm_entry": _empty_longterm,
            "vcp": {
                "detected": False,
                "stage2": False,
                "pivot": None,
                "contractions": [],
                "base_start_date": None,
                "status": "not_detected",
                "note": "No data available.",
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

        # ATR-14 over last 30 bars
        df_atr = df.tail(30)
        tr = pd.concat(
            [
                df_atr["High"] - df_atr["Low"],
                (df_atr["High"] - df_atr["Close"].shift(1)).abs(),
                (df_atr["Low"] - df_atr["Close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr_series = tr.rolling(14).mean()
        atr_14 = float(atr_series.iloc[-1]) if not atr_series.empty and not np.isnan(atr_series.iloc[-1]) else 1.0

        wyckoff = self._compute_wyckoff(df, vol_ratio, avg_vol_30, gap_down, price_change_pct)

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
            "wyckoff": wyckoff,
            "pnf": self._compute_pnf(df, atr_14),
            "swing_entry": self._compute_swing_entry(wyckoff, current_price, atr_14),
            "longterm_entry": self._compute_longterm_entry(df, wyckoff, edgar_quarters),
            "vcp": detect_vcp(df),
        }

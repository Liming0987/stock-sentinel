"""
Discounted Cash Flow (DCF) valuation service.

Methodology:
  1. Estimate FCF growth rate from historical annual cashflow statements (3-4yr CAGR).
     Falls back to analyst revenue-growth proxy if history is insufficient.
  2. Compute discount rate via CAPM: r = Rf + beta * ERP
     (Rf = 4.5% 10y treasury, ERP = 5.5% historical equity risk premium).
     Clamped to [8%, 15%].
  3. Project FCF forward for 10 years, then apply Gordon Growth terminal value.
  4. Subtract net debt and divide by shares outstanding for per-share intrinsic value.
  5. Return bear / base / bull scenarios and a 3×3 sensitivity table.
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

FORECAST_YEARS = 10
TERMINAL_GROWTH = 0.025   # 2.5% — long-run nominal GDP
RISK_FREE = 0.045          # 4.5% — approximate 10y US treasury
EQUITY_RISK_PREMIUM = 0.055  # 5.5% — historical US ERP


class DCFService:

    def analyze(self, ticker: str) -> Dict:
        empty = {"feasible": False, "reason": "Insufficient data", "ticker": ticker}
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.info or {}

            # ── Raw inputs ───────────────────────────────────────────────────
            fcf_ttm: Optional[float] = info.get("freeCashflow")
            total_debt: float = float(info.get("totalDebt") or 0)
            total_cash: float = float(info.get("totalCash") or 0)
            shares: Optional[float] = (
                info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
            )
            beta: float = float(info.get("beta") or 1.0)
            current_price: Optional[float] = (
                info.get("currentPrice") or info.get("regularMarketPrice")
            )

            if not fcf_ttm or not shares or not current_price:
                return {**empty, "reason": "Missing FCF, shares outstanding, or current price"}
            if fcf_ttm <= 0:
                return {**empty, "reason": "Negative or zero free cash flow — DCF not meaningful"}

            net_debt = total_debt - total_cash

            # ── Discount rate (CAPM) ─────────────────────────────────────────
            beta = max(0.5, min(beta, 2.5))
            discount_rate = RISK_FREE + beta * EQUITY_RISK_PREMIUM
            discount_rate = round(max(0.08, min(discount_rate, 0.15)), 4)

            # ── FCF growth rate from history ─────────────────────────────────
            growth_rate, growth_source = self._estimate_growth(t, info)

            # ── Build scenarios ──────────────────────────────────────────────
            # Bear: growth -5pp, discount +2pp
            # Base: base growth, base discount
            # Bull: growth +5pp, discount -1pp
            scenarios = {}
            for name, g_adj, r_adj in [
                ("bear", -0.05, +0.02),
                ("base",  0.00,  0.00),
                ("bull", +0.05, -0.01),
            ]:
                g = max(0.0, growth_rate + g_adj)
                r = max(0.08, min(discount_rate + r_adj, 0.20))
                iv = self._dcf(fcf_ttm, g, r, TERMINAL_GROWTH, FORECAST_YEARS, net_debt, shares)
                if iv is None:
                    scenarios[name] = None
                    continue
                upside = (iv - current_price) / current_price if current_price else None
                scenarios[name] = {
                    "growth_rate": round(g, 4),
                    "discount_rate": round(r, 4),
                    "intrinsic_value": round(iv, 2),
                    "upside_pct": round(upside * 100, 1) if upside is not None else None,
                }

            # ── Sensitivity table (discount rate × terminal growth) ───────────
            sensitivity: List[Dict] = []
            for r in [0.08, 0.10, 0.12]:
                for g_t in [0.015, 0.025, 0.035]:
                    if r <= g_t:
                        iv_s = None
                    else:
                        iv_s = self._dcf(
                            fcf_ttm, growth_rate, r, g_t, FORECAST_YEARS, net_debt, shares
                        )
                    sensitivity.append({
                        "discount_rate": r,
                        "terminal_growth": g_t,
                        "intrinsic_value": round(iv_s, 2) if iv_s is not None else None,
                    })

            # ── Projected cashflows (base scenario) ──────────────────────────
            projected = self._project_cashflows(
                fcf_ttm, growth_rate, discount_rate, TERMINAL_GROWTH, FORECAST_YEARS
            )

            base_iv = (scenarios.get("base") or {}).get("intrinsic_value")
            margin_of_safety = (
                (base_iv - current_price) / base_iv if base_iv and base_iv > 0 else None
            )

            return {
                "feasible": True,
                "ticker": ticker,
                "current_price": round(current_price, 2),
                "base_intrinsic_value": round(base_iv, 2) if base_iv else None,
                "margin_of_safety_pct": round(margin_of_safety * 100, 1) if margin_of_safety is not None else None,
                "inputs": {
                    "fcf_ttm": round(fcf_ttm),
                    "net_debt": round(net_debt),
                    "shares_outstanding": round(shares),
                    "growth_rate": round(growth_rate, 4),
                    "growth_rate_source": growth_source,
                    "discount_rate": discount_rate,
                    "discount_rate_note": f"CAPM: {RISK_FREE*100:.1f}% + {beta:.2f}×{EQUITY_RISK_PREMIUM*100:.1f}%",
                    "terminal_growth_rate": TERMINAL_GROWTH,
                    "forecast_years": FORECAST_YEARS,
                },
                "scenarios": scenarios,
                "sensitivity": sensitivity,
                "projected_cashflows": projected,
            }

        except Exception as e:
            logger.warning("DCF failed for %s: %s", ticker, e)
            return {**empty, "reason": str(e)}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _dcf(
        self,
        fcf: float,
        growth: float,
        discount: float,
        terminal_growth: float,
        years: int,
        net_debt: float,
        shares: float,
    ) -> Optional[float]:
        """Return per-share intrinsic value or None if math breaks down."""
        if discount <= terminal_growth:
            return None
        pv_sum = 0.0
        fcf_t = fcf
        for t in range(1, years + 1):
            fcf_t *= 1 + growth
            pv_sum += fcf_t / (1 + discount) ** t
        terminal_value = fcf_t * (1 + terminal_growth) / (discount - terminal_growth)
        pv_terminal = terminal_value / (1 + discount) ** years
        equity_value = pv_sum + pv_terminal - net_debt
        if equity_value <= 0 or shares <= 0:
            return None
        return equity_value / shares

    def _project_cashflows(
        self,
        fcf: float,
        growth: float,
        discount: float,
        terminal_growth: float,
        years: int,
    ) -> List[Dict]:
        rows = []
        fcf_t = fcf
        for t in range(1, years + 1):
            fcf_t *= 1 + growth
            pv = fcf_t / (1 + discount) ** t
            rows.append({"year": t, "fcf": round(fcf_t), "pv": round(pv)})
        terminal_value = fcf_t * (1 + terminal_growth) / (discount - terminal_growth)
        pv_terminal = terminal_value / (1 + discount) ** years
        rows.append({"year": "TV", "fcf": round(terminal_value), "pv": round(pv_terminal)})
        return rows

    def _estimate_growth(self, ticker_obj, info: dict):
        """Estimate FCF growth rate. Returns (rate, source_label)."""
        try:
            cf = ticker_obj.cashflow
            if cf is not None and not cf.empty and "Free Cash Flow" in cf.index:
                fcf_hist = (
                    cf.loc["Free Cash Flow"]
                    .dropna()
                    .sort_index()
                )
                # Keep only positive years
                pos = fcf_hist[fcf_hist > 0]
                if len(pos) >= 2:
                    first, last = float(pos.iloc[0]), float(pos.iloc[-1])
                    n = len(pos) - 1
                    cagr = (last / first) ** (1 / n) - 1
                    cagr = max(-0.20, min(cagr, 0.35))
                    return round(cagr, 4), f"{n}-year FCF CAGR"
        except Exception:
            pass

        # Fallback: use analyst revenue growth from yfinance info
        rev_growth = info.get("revenueGrowth") or info.get("earningsGrowth")
        if rev_growth and -0.20 < rev_growth < 0.50:
            return round(rev_growth, 4), "yfinance revenue/earnings growth estimate"

        # Last resort: 5% conservative default
        return 0.05, "default (5% conservative)"

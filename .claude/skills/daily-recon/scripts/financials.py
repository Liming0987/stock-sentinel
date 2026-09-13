"""
financials.py — Fetch and summarise quarterly financial statements for the Daily Recon skill.

Pulls the 4 most recent quarters of:
  - Income statement (revenue, gross profit, operating income, net income, EPS)
  - Balance sheet (total assets, total debt, cash, equity, current ratio)
  - Cash flow (operating CF, capex, FCF, dividends)

Flags red flags:
  - Margin deterioration (gross margin shrinking 2+ consecutive quarters)
  - Rising debt (debt/equity worsening quarter-over-quarter)
  - FCF/NI divergence (net income growing but FCF flat or declining)
  - Revenue deceleration (growth rate slowing significantly)

Usage:
    from financials import fetch_financials
    data = fetch_financials("NVDA")
    # data["summary"] — plain-English narrative for Claude
    # data["flags"]   — list of red flag strings
    # data["quarters"] — list of quarterly dicts
"""

from typing import Optional


def _safe(val):
    try:
        if val is None:
            return None
        f = float(val)
        return None if f != f else f  # NaN → None
    except Exception:
        return None


def _fmt_b(val) -> str:
    """Format a dollar value in billions."""
    if val is None:
        return "N/A"
    b = val / 1e9
    return f"${b:.2f}B"


def _fmt_pct(val) -> str:
    if val is None:
        return "N/A"
    return f"{val:.1f}%"


def _pct_change(new, old) -> Optional[float]:
    if new is None or old is None or old == 0:
        return None
    return (new - old) / abs(old) * 100


def fetch_financials(ticker: str) -> dict:
    """
    Returns a dict with:
      summary: str  — plain-English narrative (3-5 sentences)
      flags: list   — red flag strings
      quarters: list — list of quarterly metric dicts (most recent first)
      raw: dict     — raw DataFrames (income, balance, cashflow)
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)

        inc = t.quarterly_income_stmt
        bal = t.quarterly_balance_sheet
        cf  = t.quarterly_cashflow

        if inc is None or inc.empty:
            return {"summary": "Financial statements unavailable.", "flags": [], "quarters": []}

        # Limit to 4 most recent quarters (columns are dates, most recent first)
        inc = inc.iloc[:, :4]
        bal = bal.iloc[:, :4] if (bal is not None and not bal.empty) else None
        cf  = cf.iloc[:, :4]  if (cf  is not None and not cf.empty)  else None

        quarters = []
        for i, col in enumerate(inc.columns):
            q_label = col.strftime("Q%q %Y") if hasattr(col, "strftime") else str(col)[:7]

            def get_inc(row):
                try:
                    return _safe(inc.loc[row, col]) if row in inc.index else None
                except Exception:
                    return None

            def get_bal(row):
                if bal is None:
                    return None
                try:
                    return _safe(bal.loc[row, col]) if row in bal.index else None
                except Exception:
                    return None

            def get_cf(row):
                if cf is None:
                    return None
                try:
                    return _safe(cf.loc[row, col]) if row in cf.index else None
                except Exception:
                    return None

            revenue      = get_inc("Total Revenue")
            gross_profit = get_inc("Gross Profit")
            op_income    = get_inc("Operating Income")
            net_income   = get_inc("Net Income")
            ebitda       = get_inc("EBITDA")

            gross_margin = (gross_profit / revenue * 100) if revenue and gross_profit else None
            op_margin    = (op_income / revenue * 100) if revenue and op_income else None
            net_margin   = (net_income / revenue * 100) if revenue and net_income else None

            total_assets = get_bal("Total Assets")
            total_debt   = get_bal("Total Debt") or get_bal("Long Term Debt")
            cash         = get_bal("Cash And Cash Equivalents") or get_bal("Cash Cash Equivalents And Short Term Investments")
            equity       = get_bal("Stockholders Equity") or get_bal("Total Stockholder Equity")
            cur_assets   = get_bal("Current Assets")
            cur_liab     = get_bal("Current Liabilities")
            current_ratio = (cur_assets / cur_liab) if cur_assets and cur_liab and cur_liab != 0 else None
            debt_equity  = (total_debt / equity) if total_debt and equity and equity != 0 else None

            op_cf  = get_cf("Operating Cash Flow")
            capex  = get_cf("Capital Expenditure")
            fcf    = (op_cf + capex) if op_cf and capex else (op_cf if op_cf else None)  # capex is negative
            divs   = get_cf("Common Stock Dividends")

            quarters.append({
                "label":         q_label,
                "revenue":       revenue,
                "gross_profit":  gross_profit,
                "op_income":     op_income,
                "net_income":    net_income,
                "gross_margin":  gross_margin,
                "op_margin":     op_margin,
                "net_margin":    net_margin,
                "total_debt":    total_debt,
                "cash":          cash,
                "equity":        equity,
                "current_ratio": current_ratio,
                "debt_equity":   debt_equity,
                "op_cf":         op_cf,
                "capex":         capex,
                "fcf":           fcf,
            })

        # ── Flag detection ────────────────────────────────────────────────
        flags = []

        # Gross margin trend (need 3+ quarters)
        margins = [q["gross_margin"] for q in quarters if q["gross_margin"] is not None]
        if len(margins) >= 3:
            if margins[0] < margins[1] < margins[2]:
                flags.append(
                    f"Gross margin declining 3 consecutive quarters: "
                    f"{_fmt_pct(margins[2])} → {_fmt_pct(margins[1])} → {_fmt_pct(margins[0])}"
                )

        # Revenue deceleration
        revs = [q["revenue"] for q in quarters if q["revenue"] is not None]
        if len(revs) >= 3:
            g1 = _pct_change(revs[0], revs[1])  # most recent QoQ
            g2 = _pct_change(revs[1], revs[2])  # prior QoQ
            if g1 is not None and g2 is not None and g2 > 0 and g1 < g2 * 0.5:
                flags.append(
                    f"Revenue growth decelerating sharply: {_fmt_pct(g2)} QoQ → {_fmt_pct(g1)} QoQ"
                )

        # FCF/NI divergence (earnings growing, cash not keeping up)
        fcfs = [q["fcf"] for q in quarters if q["fcf"] is not None]
        nis  = [q["net_income"] for q in quarters if q["net_income"] is not None]
        if len(fcfs) >= 2 and len(nis) >= 2:
            ni_growth  = _pct_change(nis[0], nis[1])
            fcf_growth = _pct_change(fcfs[0], fcfs[1])
            if ni_growth is not None and fcf_growth is not None:
                if ni_growth > 20 and fcf_growth < 0:
                    flags.append(
                        f"FCF/NI divergence: net income +{_fmt_pct(ni_growth)} QoQ but FCF {_fmt_pct(fcf_growth)} — "
                        f"earnings quality concern"
                    )

        # Rising debt/equity
        des = [q["debt_equity"] for q in quarters if q["debt_equity"] is not None]
        if len(des) >= 2 and des[0] is not None and des[1] is not None:
            if des[0] > des[1] * 1.25:
                flags.append(
                    f"Debt/equity rising: {des[1]:.2f}x → {des[0]:.2f}x — leverage increasing"
                )

        # Current ratio below 1 (liquidity concern)
        if quarters and quarters[0]["current_ratio"] is not None:
            if quarters[0]["current_ratio"] < 1.0:
                flags.append(
                    f"Current ratio {quarters[0]['current_ratio']:.2f}x — current liabilities exceed current assets (liquidity risk)"
                )

        # ── Plain-English summary ─────────────────────────────────────────
        q0 = quarters[0] if quarters else {}
        q1 = quarters[1] if len(quarters) > 1 else {}

        rev_growth = _pct_change(q0.get("revenue"), q1.get("revenue"))
        fcf_str = _fmt_b(q0.get("fcf"))
        debt_str = _fmt_b(q0.get("total_debt"))
        cash_str = _fmt_b(q0.get("cash"))
        gm_str   = _fmt_pct(q0.get("gross_margin"))
        nm_str   = _fmt_pct(q0.get("net_margin"))

        summary_parts = []

        if q0.get("revenue"):
            rev_part = f"Most recent quarter revenue: {_fmt_b(q0['revenue'])}"
            if rev_growth is not None:
                trend = "up" if rev_growth > 0 else "down"
                rev_part += f" ({trend} {abs(rev_growth):.1f}% QoQ)"
            summary_parts.append(rev_part)

        if q0.get("gross_margin") and q0.get("net_margin"):
            summary_parts.append(
                f"Gross margin {gm_str}, net margin {nm_str} — "
                + ("healthy spread" if (q0["gross_margin"] - q0["net_margin"]) < 50 else "high operating costs")
            )

        if q0.get("fcf") is not None:
            fcf_quality = "FCF positive — earnings backed by real cash" if q0["fcf"] > 0 else "FCF negative — spending exceeds operating cash inflow"
            summary_parts.append(f"Free cash flow {fcf_str}. {fcf_quality}.")

        if q0.get("total_debt") and q0.get("cash"):
            net_debt = (q0["total_debt"] - q0["cash"]) / 1e9
            if net_debt < 0:
                summary_parts.append(f"Net cash position ${abs(net_debt):.1f}B (cash > debt) — strong balance sheet.")
            else:
                summary_parts.append(f"Net debt ${net_debt:.1f}B (debt {debt_str} vs cash {cash_str}).")

        if flags:
            summary_parts.append(f"Red flags: {'; '.join(flags)}.")

        summary = " ".join(summary_parts) if summary_parts else "Financial data not available."

        return {
            "summary":  summary,
            "flags":    flags,
            "quarters": quarters,
        }

    except Exception as e:
        return {"summary": f"Could not fetch financials: {e}", "flags": [], "quarters": []}

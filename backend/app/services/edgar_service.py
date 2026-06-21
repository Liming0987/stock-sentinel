import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_SEC_HEADERS = {
    "User-Agent": "StockSentinel limingsiu2016@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

_REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "RevenuesNetOfInterestExpense",
    "SalesRevenueGoodsNet",
    "InterestAndDividendIncomeOperating",
]
_NET_INCOME_TAGS = [
    "NetIncomeLoss",
    "ProfitLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
]
_EPS_TAGS = [
    "EarningsPerShareDiluted",
    "EarningsPerShareBasic",
]
_OP_INCOME_TAGS = [
    "OperatingIncomeLoss",
]

_VALID_FP = {"Q1", "Q2", "Q3", "FY"}


def _extract_quarters(entries: list[dict]) -> list[dict]:
    """
    Extract Q1/Q2/Q3 directly from 10-Q filings and derive Q4 = FY − Q1 − Q2 − Q3
    from the 10-K annual filing. Groups by (fy, fp), keeping the most recently filed
    entry per slot to handle amended filings.

    Returns list of dicts with keys:
        period_key, period, end, val, form, filed, q4_computed
    sorted newest-first by end date.
    """
    # Deduplicate by (fy, fp), keeping latest filing
    by_fy_fp: dict[tuple, dict] = {}
    for e in entries:
        fp = e.get("fp", "")
        fy = e.get("fy")
        form = e.get("form", "")
        if fp not in _VALID_FP or fy is None:
            continue
        if form not in ("10-Q", "10-K"):
            continue
        key = (fy, fp)
        filed = e.get("filed", "")
        if key not in by_fy_fp or filed > by_fy_fp[key]["filed"]:
            by_fy_fp[key] = e

    results: list[dict] = []

    # Q1 / Q2 / Q3 come directly from 10-Q entries
    for (fy, fp), e in by_fy_fp.items():
        if fp not in ("Q1", "Q2", "Q3"):
            continue
        qnum = fp[-1]
        results.append({
            "period_key": f"{fy}-{fp}",
            "period": f"Q{qnum} {fy}",
            "end": e.get("end", ""),
            "val": e.get("val"),
            "form": e.get("form"),
            "filed": e.get("filed", ""),
            "q4_computed": False,
        })

    # Q4 = FY − Q1 − Q2 − Q3 (requires all four slots for the same fiscal year)
    fiscal_years = {fy for (fy, _fp) in by_fy_fp}
    for fy in fiscal_years:
        fy_e = by_fy_fp.get((fy, "FY"))
        if not fy_e:
            continue
        fy_val = fy_e.get("val")
        q1_val = by_fy_fp.get((fy, "Q1"), {}).get("val")
        q2_val = by_fy_fp.get((fy, "Q2"), {}).get("val")
        q3_val = by_fy_fp.get((fy, "Q3"), {}).get("val")
        if None in (fy_val, q1_val, q2_val, q3_val):
            continue
        results.append({
            "period_key": f"{fy}-Q4",
            "period": f"Q4 {fy}",
            "end": fy_e.get("end", ""),
            "val": fy_val - q1_val - q2_val - q3_val,
            "form": "10-K",
            "filed": fy_e.get("filed", ""),
            "q4_computed": True,
        })

    return sorted(results, key=lambda x: x["end"], reverse=True)


def _find_units(us_gaap: dict, tags: list[str]) -> Optional[list]:
    for tag in tags:
        if tag not in us_gaap:
            continue
        units = us_gaap[tag].get("units", {})
        for key in ("USD", "USD/shares"):
            if key in units:
                return units[key]
        if units:
            return next(iter(units.values()))
    return None


class EdgarService:
    def _cik_for(self, ticker: str) -> Optional[str]:
        resp = httpx.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={**_SEC_HEADERS, "Host": "www.sec.gov"},
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
        for entry in resp.json().values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry["cik_str"]).zfill(10)
        return None

    def get_quarterly(self, ticker: str) -> dict:
        try:
            cik = self._cik_for(ticker)
            if not cik:
                return {"quarters": []}

            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            resp = httpx.get(
                url,
                headers={**_SEC_HEADERS, "Host": "data.sec.gov"},
                timeout=30,
                follow_redirects=True,
            )
            resp.raise_for_status()
            us_gaap = resp.json().get("facts", {}).get("us-gaap", {})

            rev_quarters = _extract_quarters(_find_units(us_gaap, _REVENUE_TAGS) or [])[:8]
            ni_quarters = _extract_quarters(_find_units(us_gaap, _NET_INCOME_TAGS) or [])[:8]
            eps_quarters = _extract_quarters(_find_units(us_gaap, _EPS_TAGS) or [])[:8]
            op_quarters = _extract_quarters(_find_units(us_gaap, _OP_INCOME_TAGS) or [])[:8]

            rev_by_key = {r["period_key"]: r for r in rev_quarters}
            ni_by_key = {r["period_key"]: r for r in ni_quarters}
            eps_by_key = {r["period_key"]: r for r in eps_quarters}
            op_by_key = {r["period_key"]: r for r in op_quarters}

            all_keys = sorted(
                set(rev_by_key) | set(ni_by_key),
                key=lambda k: (rev_by_key.get(k) or ni_by_key.get(k, {})).get("end", ""),
                reverse=True,
            )[:4]

            quarters = []
            for key in all_keys:
                ref = rev_by_key.get(key) or ni_by_key.get(key, {})
                quarters.append({
                    "period": ref.get("period", key),
                    "period_key": key,
                    "revenue": (rev_by_key.get(key) or {}).get("val"),
                    "net_income": (ni_by_key.get(key) or {}).get("val"),
                    "eps_diluted": (eps_by_key.get(key) or {}).get("val"),
                    "operating_income": (op_by_key.get(key) or {}).get("val"),
                    "q4_computed": ref.get("q4_computed", False),
                })

            return {"quarters": quarters}
        except Exception as e:
            logger.warning("EdgarService.get_quarterly(%s) failed: %s", ticker, e)
            return {"quarters": []}

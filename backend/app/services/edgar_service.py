import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_SEC_HEADERS = {
    "User-Agent": "StockSentinel limingsiu2016@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

_QUARTER_RE = re.compile(r"^CY(\d{4})Q([1-4])$")

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


def _extract_quarters(entries: list[dict]) -> list[dict]:
    """Return deduplicated quarterly entries sorted newest-first."""
    by_frame: dict[str, dict] = {}
    for e in entries:
        frame = e.get("frame", "")
        if not _QUARTER_RE.match(frame):
            continue
        if e.get("form") not in ("10-Q", "10-K"):
            continue
        filed = e.get("filed", "")
        if frame not in by_frame or filed > by_frame[frame]["filed"]:
            by_frame[frame] = {
                "end": e.get("end"),
                "val": e.get("val"),
                "frame": frame,
                "form": e.get("form"),
                "filed": filed,
            }
    return sorted(by_frame.values(), key=lambda x: x["end"], reverse=True)


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

            rev_raw = _find_units(us_gaap, _REVENUE_TAGS)
            ni_raw = _find_units(us_gaap, _NET_INCOME_TAGS)
            eps_raw = _find_units(us_gaap, _EPS_TAGS)
            op_raw = _find_units(us_gaap, _OP_INCOME_TAGS)

            rev_by_frame = {r["frame"]: r["val"] for r in _extract_quarters(rev_raw or [])[:8]}
            ni_by_frame = {r["frame"]: r["val"] for r in _extract_quarters(ni_raw or [])[:8]}
            eps_by_frame = {r["frame"]: r["val"] for r in _extract_quarters(eps_raw or [])[:8]}
            op_by_frame = {r["frame"]: r["val"] for r in _extract_quarters(op_raw or [])[:8]}

            all_frames = sorted(
                set(rev_by_frame) | set(ni_by_frame),
                reverse=True,
            )[:4]

            quarters = []
            for frame in all_frames:
                m = _QUARTER_RE.match(frame)
                if not m:
                    continue
                year, qnum = m.group(1), m.group(2)
                quarters.append({
                    "period": f"Q{qnum} {year}",
                    "frame": frame,
                    "revenue": rev_by_frame.get(frame),
                    "net_income": ni_by_frame.get(frame),
                    "eps_diluted": eps_by_frame.get(frame),
                    "operating_income": op_by_frame.get(frame),
                })

            return {"quarters": quarters}
        except Exception as e:
            logger.warning("EdgarService.get_quarterly(%s) failed: %s", ticker, e)
            return {"quarters": []}

"""SEC EDGAR XBRL facts analyst tool.

Ported from day-trader-skill `trader-analyst`:
Fetches reported quarterly facts directly from SEC EDGAR (XBRL company facts from
10-Qs and 10-Ks, plus recent 8-K filings) and computes YoY revenue growth,
gross/operating/net margins, and diluted EPS.
"""

from __future__ import annotations

import datetime as _dt
import logging
from typing import Any, Optional
import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

CONCEPTS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "RevenuesNetOfInterestExpense",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
    ],
    "cost_of_revenue": [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
    ],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ],
    "eps_diluted": [
        "EarningsPerShareDiluted",
        "EarningsPerShareBasicAndDiluted",
    ],
}

# In-memory CIK lookup cache
_TICKER_TO_CIK: dict[str, dict[str, Any]] = {}
_CACHE_TIMESTAMP: float = 0.0


async def _get_sec_headers() -> dict[str, str]:
    settings = get_settings()
    ua = getattr(settings, "sec_user_agent", None) or "EquitIQResearch research@equitiq.com"
    return {
        "User-Agent": ua,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json",
    }


async def get_company_cik(symbol: str) -> Optional[dict[str, Any]]:
    """Look up CIK and company name by stock ticker from SEC directory."""
    global _TICKER_TO_CIK, _CACHE_TIMESTAMP
    sym = symbol.strip().upper()
    now = _dt.datetime.now().timestamp()

    # Cache for 24 hours
    if not _TICKER_TO_CIK or (now - _CACHE_TIMESTAMP > 86400):
        try:
            headers = await _get_sec_headers()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(TICKERS_URL, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    mapping = {}
                    for item in data.values():
                        ticker = str(item.get("ticker", "")).upper()
                        mapping[ticker] = {
                            "cik": int(item.get("cik_str", 0)),
                            "title": item.get("title", ""),
                            "symbol": ticker,
                        }
                    _TICKER_TO_CIK = mapping
                    _CACHE_TIMESTAMP = now
        except Exception as e:
            logger.warning("Could not refresh SEC ticker directory: %s", e)

    return _TICKER_TO_CIK.get(sym)


def _facts_for(companyfacts: dict[str, Any], concept: str) -> list[dict[str, Any]]:
    node = companyfacts.get("facts", {}).get("us-gaap", {}).get(concept)
    if not node:
        return []
    units = node.get("units", {})
    unit = "USD" if "USD" in units else ("USD/shares" if "USD/shares" in units else next(iter(units), None))
    return units.get(unit, []) if unit else []


def _extract_quarterly_periods(facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for f in facts:
        if "start" not in f or f.get("form", "").split("/")[0] not in ("10-Q", "10-K", "20-F", "40-F"):
            continue
        key = (f["start"], f["end"])
        stamp = (f.get("filed", ""), f.get("accn", ""))
        if key not in latest or stamp > (latest[key].get("filed", ""), latest[key].get("accn", "")):
            latest[key] = f

    quarters: dict[str, dict[str, Any]] = {}
    for (start, end), f in latest.items():
        try:
            s_dt = _dt.date.fromisoformat(start)
            e_dt = _dt.date.fromisoformat(end)
            days = (e_dt - s_dt).days
            if 80 <= days <= 105:
                quarters[end] = {
                    "val": f.get("val"),
                    "start": start,
                    "end": end,
                    "fy": f.get("fy"),
                    "fp": f.get("fp"),
                    "form": f.get("form"),
                    "filed": f.get("filed"),
                }
        except Exception:
            continue
    return quarters


async def fetch_sec_financial_facts(symbol: str) -> dict[str, Any]:
    """Fetch and parse official SEC EDGAR quarterly financials for a ticker."""
    info = await get_company_cik(symbol)
    if not info or not info.get("cik"):
        return {
            "error": f"Ticker {symbol} not found in SEC EDGAR directory.",
            "symbol": symbol.upper(),
        }

    cik = info["cik"]
    company_name = info["title"]
    headers = await _get_sec_headers()

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(FACTS_URL.format(cik=cik), headers=headers)
            if resp.status_code != 200:
                return {
                    "error": f"SEC EDGAR returned status {resp.status_code} for CIK {cik}",
                    "symbol": symbol.upper(),
                    "company_name": company_name,
                }
            companyfacts = resp.json()
    except Exception as e:
        return {
            "error": f"Failed to connect to SEC EDGAR: {str(e)}",
            "symbol": symbol.upper(),
            "company_name": company_name,
        }

    # Extract metrics by concept priority
    extracted: dict[str, dict[str, dict[str, Any]]] = {}
    for metric_name, concept_list in CONCEPTS.items():
        for concept in concept_list:
            raw_facts = _facts_for(companyfacts, concept)
            if raw_facts:
                quarters = _extract_quarterly_periods(raw_facts)
                if quarters:
                    extracted[metric_name] = quarters
                    break

    # Build sorted quarter list by end date descending
    all_dates = set()
    for metric in extracted.values():
        all_dates.update(metric.keys())
    sorted_dates = sorted(list(all_dates), reverse=True)

    quarters_summary = []
    for i, date in enumerate(sorted_dates[:8]):
        rev_val = extracted.get("revenue", {}).get(date, {}).get("val")
        cost_val = extracted.get("cost_of_revenue", {}).get(date, {}).get("val")
        gp_val = extracted.get("gross_profit", {}).get(date, {}).get("val")
        if gp_val is None and rev_val is not None and cost_val is not None:
            gp_val = rev_val - cost_val

        op_inc = extracted.get("operating_income", {}).get(date, {}).get("val")
        net_inc = extracted.get("net_income", {}).get(date, {}).get("val")
        eps = extracted.get("eps_diluted", {}).get(date, {}).get("val")

        # YoY comparison: look 4 quarters back (approx ~365 days ago)
        yoy_rev_growth = None
        yoy_net_growth = None
        target_yoy_date = None
        try:
            curr_dt = _dt.date.fromisoformat(date)
            for prev_date in sorted_dates:
                prev_dt = _dt.date.fromisoformat(prev_date)
                delta_days = (curr_dt - prev_dt).days
                if 340 <= delta_days <= 390:
                    target_yoy_date = prev_date
                    break
        except Exception:
            pass

        if target_yoy_date:
            prev_rev = extracted.get("revenue", {}).get(target_yoy_date, {}).get("val")
            if rev_val is not None and prev_rev and prev_rev != 0:
                yoy_rev_growth = round(((rev_val - prev_rev) / abs(prev_rev)) * 100, 2)
            prev_net = extracted.get("net_income", {}).get(target_yoy_date, {}).get("val")
            if net_inc is not None and prev_net and prev_net != 0:
                yoy_net_growth = round(((net_inc - prev_net) / abs(prev_net)) * 100, 2)

        # Margins
        gross_margin = round((gp_val / rev_val) * 100, 2) if (gp_val is not None and rev_val and rev_val > 0) else None
        operating_margin = round((op_inc / rev_val) * 100, 2) if (op_inc is not None and rev_val and rev_val > 0) else None
        net_margin = round((net_inc / rev_val) * 100, 2) if (net_inc is not None and rev_val and rev_val > 0) else None

        flags = []
        if net_inc is not None and op_inc is not None and net_inc > op_inc:
            flags.append("Net income exceeds operating income (likely non-operating/one-off gains)")

        quarters_summary.append({
            "period_end": date,
            "revenue": rev_val,
            "revenue_yoy_pct": yoy_rev_growth,
            "gross_profit": gp_val,
            "gross_margin_pct": gross_margin,
            "operating_income": op_inc,
            "operating_margin_pct": operating_margin,
            "net_income": net_inc,
            "net_income_yoy_pct": yoy_net_growth,
            "eps_diluted": eps,
            "flags": flags,
        })

    latest = quarters_summary[0] if quarters_summary else None

    return {
        "symbol": symbol.upper(),
        "company_name": company_name,
        "cik": cik,
        "source": "SEC EDGAR XBRL (10-Q / 10-K)",
        "latest_quarter": latest,
        "quarters": quarters_summary,
    }

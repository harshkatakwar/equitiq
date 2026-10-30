"""Market data module — API routes for price history, live quotes, and market scanner.

Existing routes
---------------
  GET /companies/{company_id}/prices   – EOD price history (DB)
  GET /companies/{company_id}/price    – latest stored price snapshot (DB)

Day-trader-skill routes (trader-scanner + trader-alerts)
---------------------------------------------------------
  GET /market/scanner                  – pre-market setup scan (Yahoo daily spark)
  GET /market/status                   – NYSE open / closed status
  GET /market/quote/{symbol}           – live delayed quote for a ticker
  POST /market/alerts/{symbol}         – check price-alert rules against a live quote

Data is sourced from Yahoo Finance's free, unofficial API and is typically
15-minute delayed. All data is for information purposes only and does not
constitute financial advice or a recommendation to trade.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.database import get_db
from src.modules.market_data.service import get_latest_price, get_price_history
from src.modules.market_data.scanner import (
    run_daily_scan,
    DEFAULT_MIN_PRICE,
    DEFAULT_MIN_VOLUME,
)
from src.modules.market_data.alerts import get_quote, check_alerts, get_market_status

router = APIRouter()


# ---------------------------------------------------------------------------
# Existing DB-backed price routes (unchanged)
# ---------------------------------------------------------------------------

@router.get("/companies/{company_id}/prices")
async def price_history(
    company_id: UUID,
    days: int = Query(252, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Get EOD price history for a company's primary security."""
    prices = await get_price_history(db, company_id, days)
    return {"company_id": str(company_id), "prices": prices, "count": len(prices)}


@router.get("/companies/{company_id}/price")
async def latest_price(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get latest price snapshot."""
    data = await get_latest_price(db, company_id)
    return data or {"error": "No price data available"}


# ---------------------------------------------------------------------------
# Day-trader-skill: NYSE market status
# ---------------------------------------------------------------------------

@router.get(
    "/market/status",
    summary="NYSE market status",
    tags=["Market Data"],
)
async def market_status() -> dict:
    """
    Return whether the NYSE is currently open, the session hours, and the
    next scheduled open.  Uses the 2026-2027 NYSE holiday and early-close
    calendar from the day-trader-skill `trader-alerts` pack.
    """
    return get_market_status()


# ---------------------------------------------------------------------------
# Day-trader-skill: pre-market setup scanner (trader-scanner daily mode)
# ---------------------------------------------------------------------------

@router.get(
    "/market/scanner",
    summary="Pre-market daily setup scanner",
    tags=["Market Data"],
)
async def daily_scanner(
    symbols: str = Query(
        ...,
        description=(
            "Comma-separated list of US ticker symbols to scan, e.g. AAPL,MSFT,TSLA. "
            "Maximum 200 symbols per request."
        ),
        example="AAPL,MSFT,TSLA,GOOGL,AMZN",
    ),
    min_price: float = Query(
        DEFAULT_MIN_PRICE,
        ge=0.0,
        description="Minimum last-close price to include (default 5.0).",
    ),
    min_volume: int = Query(
        DEFAULT_MIN_VOLUME,
        ge=0,
        description="Minimum recent-volume to include (default 1,000,000).",
    ),
) -> dict:
    """
    Scan a list of US tickers for **day-trading technical setups** using
    3-month daily data from Yahoo Finance.

    Detected setups (from `trader-scanner` daily mode):
    - **breakout_20d** — last close above every close of the prior 20 sessions
    - **bull_flag** — >10 % run over 10 sessions, then 5-session consolidation ≤5 %
    - **reclaim_ma20** — price was below the 20-day MA yesterday, above it today
    - **oversold** — RSI-14 (Wilder) under 30
    - **oversold_bounce** — RSI-14 was under 30 yesterday, closed up today

    Results are sorted by dollar volume (most liquid movers first).

    > ⚠️ A scan result is a list of charts matching a rule — **not** a list of
    > stocks to buy. Free Yahoo data is unofficial and may lag. Education and
    > tooling only; not financial advice.
    """
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not sym_list:
        raise HTTPException(status_code=422, detail="No symbols provided.")
    if len(sym_list) > 200:
        raise HTTPException(status_code=422, detail="Maximum 200 symbols per request.")

    result = await run_daily_scan(sym_list, min_price=min_price, min_volume=min_volume)
    return result


# ---------------------------------------------------------------------------
# Day-trader-skill: live delayed quote (trader-alerts quote command)
# ---------------------------------------------------------------------------

@router.get(
    "/market/quote/{symbol}",
    summary="Live delayed quote for a ticker",
    tags=["Market Data"],
)
async def live_quote(symbol: str) -> dict:
    """
    Fetch a **live delayed quote** for a single US ticker from Yahoo Finance
    (v8 chart endpoint, typically ~15 minutes delayed).

    Returns: price, open, high, low, prev_close, change_pct, quote_time.

    > ⚠️ Delayed quote from Yahoo's free, unofficial API. Your broker's
    > price is the one that fills. Not financial advice.
    """
    sym = symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=422, detail="Symbol is required.")
    try:
        return await get_quote(sym)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Day-trader-skill: price-alert rule check (trader-alerts check command)
# ---------------------------------------------------------------------------

_ALERT_RULES_EXAMPLE: list[dict[str, Any]] = [
    {"type": "above",    "price": 185.0},
    {"type": "below",    "price": 170.0},
    {"type": "pct_move", "pct": 2.0, "direction": "up"},
]


@router.post(
    "/market/alerts/{symbol}",
    summary="Check price-alert rules against a live quote",
    tags=["Market Data"],
)
async def alert_check(
    symbol: str,
    rules: list[dict[str, Any]] = Body(
        ...,
        examples={"basic": {"value": _ALERT_RULES_EXAMPLE}},
    ),
) -> dict:
    """
    Fetch a live quote for `symbol` and evaluate one or more **price-alert
    rules** against it (ported from `trader-alerts` check command).

    **Rule types**:
    | type | required fields | fires when |
    |---|---|---|
    | `above` | `price` | quote ≥ threshold |
    | `below` | `price` | quote ≤ threshold |
    | `stop`  | `price` | quote ≤ threshold (alias for below) |
    | `target`| `price` | quote ≥ threshold (alias for above) |
    | `pct_move` | `pct`, optional `direction` (up/down) | abs(move) ≥ pct % |

    Returns: quote, list of triggered alerts, NYSE market status.

    > ⚠️ An alert is information, not an order. Delayed data. Not financial advice.
    """
    sym = symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=422, detail="Symbol is required.")
    if not rules:
        raise HTTPException(status_code=422, detail="Provide at least one alert rule.")

    valid_types = {"above", "below", "stop", "target", "pct_move"}
    for rule in rules:
        if rule.get("type") not in valid_types:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown rule type {rule.get('type')!r}. Use: {sorted(valid_types)}",
            )

    try:
        return await check_alerts(sym, rules)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

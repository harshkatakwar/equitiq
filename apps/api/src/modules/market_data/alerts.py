"""Market data module — Live quote and price-alert service.

Ported from the day-trader-skill `trader-alerts`:
https://github.com/Jakeschincariol/day-trader-skill

Capabilities:
  quote(symbol)         – live delayed quote from Yahoo Finance (v8 chart API)
  market_status()       – is the NYSE open right now?
  check_alerts(symbol,
               rules)   – evaluate above/below/pct_move rules against a live quote

Yahoo's quote API is free, unofficial, and typically 15-minute delayed.
Data is for information only and does not constitute financial advice.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (match trader-alerts)
# ---------------------------------------------------------------------------
YAHOO_HOSTS = (
    "query2.finance.yahoo.com",
    "query1.finance.yahoo.com",
)
UA = (
    "Mozilla/5.0 (compatible; day-trader-skill/2.0; "
    "+https://github.com/Jakeschincariol/day-trader-skill)"
)
HEADERS = {"User-Agent": UA}

NYSE_HOLIDAYS = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King, Jr. Day",
    "2026-02-16": "Washington's Birthday",
    "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King, Jr. Day",
    "2027-02-15": "Washington's Birthday",
    "2027-03-26": "Good Friday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-11-25": "Thanksgiving Day",
    "2027-12-24": "Christmas Day (observed)",
}
NYSE_EARLY_CLOSE = {
    "2026-11-27": "day after Thanksgiving",
    "2026-12-24": "Christmas Eve",
    "2027-11-26": "day after Thanksgiving",
}
CALENDAR_YEARS = (2026, 2027)
OPEN  = datetime.time(9, 30)
CLOSE = datetime.time(16, 0)
EARLY = datetime.time(13, 0)


# ---------------------------------------------------------------------------
# Time helpers — ported verbatim from trader-alerts (no pytz)
# ---------------------------------------------------------------------------
def _nth_sunday(year: int, month: int, n: int) -> datetime.date:
    d = datetime.date(year, month, 1)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)
    return d + datetime.timedelta(weeks=n - 1)


def _eastern_offset(utc: datetime.datetime) -> int:
    y = utc.year
    start = datetime.datetime.combine(_nth_sunday(y, 3, 2), datetime.time(7, 0))
    end   = datetime.datetime.combine(_nth_sunday(y, 11, 1), datetime.time(6, 0))
    naive = utc.replace(tzinfo=None)
    return -4 if start <= naive < end else -5


def _to_eastern(utc: datetime.datetime) -> datetime.datetime:
    return utc.replace(tzinfo=None) + datetime.timedelta(hours=_eastern_offset(utc))


def _trading_day(d: datetime.date) -> tuple[bool, str]:
    if d.weekday() >= 5:
        return False, "weekend"
    name = NYSE_HOLIDAYS.get(d.isoformat())
    if name:
        return False, "NYSE holiday: " + name
    return True, ""


def _session(d: datetime.date):
    ok, _ = _trading_day(d)
    if not ok:
        return None
    return OPEN, (EARLY if d.isoformat() in NYSE_EARLY_CLOSE else CLOSE)


# ---------------------------------------------------------------------------
# Market status (mirrors trader-alerts' market_status)
# ---------------------------------------------------------------------------
def get_market_status(now_utc: datetime.datetime | None = None) -> dict:
    """Return NYSE open/closed status, session hours, and next open."""
    if now_utc is None:
        now_utc = datetime.datetime.utcnow()

    local = _to_eastern(now_utc)
    d = local.date()
    ok, reason = _trading_day(d)

    st: dict[str, Any] = {
        "now_new_york":    local.strftime("%Y-%m-%d %H:%M"),
        "date":            d.isoformat(),
        "weekday":         local.strftime("%A"),
        "calendar_known":  d.year in CALENDAR_YEARS,
        "open":            False,
        "reason":          reason,
        "early_close":     NYSE_EARLY_CLOSE.get(d.isoformat()),
    }

    s = _session(d)
    if s:
        o, c = s
        st["opens"]  = o.strftime("%H:%M")
        st["closes"] = c.strftime("%H:%M")
        if o <= local.time() < c:
            st["open"]   = True
            st["reason"] = "regular session"
        elif local.time() < o:
            st["reason"] = "before the open"
        else:
            st["reason"] = "after the close"

    # next trading open
    nd = d if (s and local.time() < s[0]) else d + datetime.timedelta(days=1)
    for _ in range(15):
        if _session(nd):
            st["next_open"] = "%s 09:30" % nd.isoformat()
            break
        nd += datetime.timedelta(days=1)

    return st


# ---------------------------------------------------------------------------
# Yahoo quote fetch (async — mirrors trader-alerts' fetch_yahoo / parse_yahoo)
# ---------------------------------------------------------------------------
async def _fetch_yahoo_quote(client: httpx.AsyncClient, symbol: str) -> dict:
    """Fetch a single delayed quote from Yahoo's v8 chart endpoint."""
    ysym = symbol.upper().replace(".", "-")
    path = "/v8/finance/chart/{}?range=1d&interval=1d".format(ysym)
    last_err = "unknown error"

    for host in YAHOO_HOSTS:
        url = "https://" + host + path
        try:
            r = await client.get(url, headers=HEADERS, timeout=12.0)
            if r.status_code == 429 or r.status_code >= 500:
                last_err = "HTTP %d" % r.status_code
                continue
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            last_err = str(exc)
            continue

        try:
            res = data["chart"]["result"]
        except (KeyError, TypeError):
            last_err = "unexpected response shape"
            continue

        if not res:
            err = (data.get("chart") or {}).get("error") or {}
            raise ValueError(
                "Yahoo has no data for %s: %s"
                % (symbol, err.get("description", "unknown ticker"))
            )

        m = res[0].get("meta", {})
        price = m.get("regularMarketPrice")
        if price is None:
            raise ValueError("Yahoo has no price for %s" % symbol)

        t = m.get("regularMarketTime")
        when = (
            datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            if t
            else ""
        )

        q = (res[0].get("indicators", {}).get("quote") or [{}])[0]
        opens = [x for x in (q.get("open") or []) if x is not None]
        prev_close = m.get("previousClose") or m.get("chartPreviousClose")

        return {
            "symbol":     symbol.upper(),
            "price":      round(float(price), 2),
            "open":       round(float(opens[0]), 2) if opens else None,
            "high":       m.get("regularMarketDayHigh"),
            "low":        m.get("regularMarketDayLow"),
            "prev_close": round(float(prev_close), 2) if prev_close is not None else None,
            "change_pct": (
                round((price / prev_close - 1) * 100, 2)
                if prev_close
                else None
            ),
            "currency":   m.get("currency"),
            "quote_time": when,
            "source":     "yahoo",
            "note":       "Delayed quote — typically 15 minutes. Not financial advice.",
        }

    raise ValueError("Could not fetch quote for %s: %s" % (symbol, last_err))


# ---------------------------------------------------------------------------
# Alert rule evaluation (mirrors trader-alerts' evaluate — pure function)
# ---------------------------------------------------------------------------
def _evaluate_rules(
    rules: list[dict],
    quote: dict,
    market_status: dict,
) -> list[dict]:
    """
    Evaluate a list of alert rules against a live quote.

    Each rule must have:
      type   – "above" | "below" | "pct_move"
      price  – (above/below) the threshold price
      pct    – (pct_move) the % move threshold
      direction – optional "up" | "down" for pct_move

    Returns a list of triggered alert dicts.
    """
    sym   = quote["symbol"]
    price = quote["price"]
    prev  = quote.get("prev_close") or quote.get("open")
    rings: list[dict] = []

    for rule in rules:
        typ = rule.get("type", "")
        if typ == "stop":
            typ = "below"
        elif typ == "target":
            typ = "above"

        if typ == "above":
            threshold = float(rule.get("price", 0))
            if price >= threshold:
                word  = "at or above" if market_status.get("open") else "last"
                rings.append({
                    "rule_type": rule.get("type", "above"),
                    "symbol":    sym,
                    "price":     price,
                    "threshold": threshold,
                    "triggered": True,
                    "message": (
                        "{sym} is {word} ${price:.2f} — at or above your "
                        "level ${threshold:.2f}."
                    ).format(sym=sym, word=word, price=price, threshold=threshold),
                })

        elif typ == "below":
            threshold = float(rule.get("price", 0))
            if price <= threshold:
                rings.append({
                    "rule_type": rule.get("type", "below"),
                    "symbol":    sym,
                    "price":     price,
                    "threshold": threshold,
                    "triggered": True,
                    "message": (
                        "{sym} is at or below ${price:.2f} — "
                        "at or below your level ${threshold:.2f}."
                    ).format(sym=sym, price=price, threshold=threshold),
                })

        elif typ == "pct_move":
            if prev is None:
                continue
            pct_req   = float(rule.get("pct", 0))
            direction = rule.get("direction")
            move      = 100.0 * (price / float(prev) - 1)
            hit = abs(move) >= pct_req and (
                not direction
                or (direction == "up" and move > 0)
                or (direction == "down" and move < 0)
            )
            if hit:
                rings.append({
                    "rule_type": "pct_move",
                    "symbol":    sym,
                    "price":     price,
                    "pct_move":  round(move, 2),
                    "threshold_pct": pct_req,
                    "triggered": True,
                    "message": (
                        "{sym} moved {move:+.2f}% to ${price:.2f} "
                        "(from ${prev:.2f})."
                    ).format(sym=sym, move=move, price=price, prev=float(prev)),
                })

    return rings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def get_quote(symbol: str) -> dict:
    """
    Fetch a live (delayed) quote for a single ticker via Yahoo Finance.

    Returns price, open, high, low, prev_close, change_pct, quote_time.
    Raises ValueError when Yahoo has no data for the symbol.
    """
    async with httpx.AsyncClient() as client:
        return await _fetch_yahoo_quote(client, symbol)


async def check_alerts(symbol: str, rules: list[dict]) -> dict:
    """
    Fetch a live quote for `symbol` and evaluate `rules` against it.

    Rule schema (any subset):
      [{"type": "above",    "price": 185.0},
       {"type": "below",    "price": 175.0},
       {"type": "pct_move", "pct": 2.0, "direction": "up"}]

    Returns:
      quote       – the live quote dict
      alerts      – list of triggered alert dicts
      market      – NYSE market status
      checked_at  – UTC timestamp
    """
    now_utc = datetime.datetime.utcnow()
    market  = get_market_status(now_utc)

    async with httpx.AsyncClient() as client:
        quote = await _fetch_yahoo_quote(client, symbol)

    triggered = _evaluate_rules(rules, quote, market)

    return {
        "checked_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quote":      quote,
        "alerts":     triggered,
        "any_triggered": bool(triggered),
        "market":     market,
        "note": (
            "Delayed quote — typically 15 minutes. "
            "Alerts are information, not orders. Not financial advice."
        ),
    }

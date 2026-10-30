"""Market data module — Pre-market scanner service.

Ported from the day-trader-skill `trader-scanner` (daily mode):
https://github.com/Jakeschincariol/day-trader-skill

Fetches 3-month daily spark data from Yahoo Finance and detects:
  breakout_20d    – last close above every close of the prior 20 sessions
  bull_flag       – >10 % run over 10 sessions then 5-session flag ≤5 %
  reclaim_ma20    – was below the 20-day MA, now above it
  oversold        – RSI-14 (Wilder) under 30
  oversold_bounce – RSI-14 was under 30 yesterday; closed up today

Yahoo's spark API is free, unofficial, and may lag. Data is for information
only and does not constitute financial advice or a recommendation to trade.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (match trader-scanner defaults)
# ---------------------------------------------------------------------------
YAHOO_HOSTS = (
    "https://query2.finance.yahoo.com",
    "https://query1.finance.yahoo.com",
)
SPARK_BATCH = 20          # Yahoo's spark API caps at 20 symbols per request
MIN_DAILY_BARS = 30       # need at least 30 days of history
DEFAULT_MIN_PRICE = 5.0
DEFAULT_MIN_VOLUME = 1_000_000

SETUPS: list[tuple[str, str]] = [
    ("breakout_20d",    "20-day closing-high breakout"),
    ("bull_flag",       "bull flag"),
    ("reclaim_ma20",    "reclaimed the 20-day average"),
    ("oversold",        "oversold (RSI-14 under 30)"),
    ("oversold_bounce", "oversold bounce"),
]
SETUP_LABELS = dict(SETUPS)

NOTE = (
    "A scan is a list of charts that match a rule, not a list of stocks to buy. "
    "Free Yahoo data is unofficial and may lag. Education and tooling, not financial advice."
)

UA = (
    "Mozilla/5.0 (compatible; day-trader-skill/2.0; "
    "+https://github.com/Jakeschincariol/day-trader-skill)"
)
HEADERS = {"User-Agent": UA}


# ---------------------------------------------------------------------------
# Time utilities (no pytz — ported verbatim from trader-scanner)
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


def _ts_to_eastern(ts: int) -> datetime.datetime:
    return _to_eastern(datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts)))


# ---------------------------------------------------------------------------
# Yahoo spark fetch (async, mirrors trader-scanner's fetch_spark)
# ---------------------------------------------------------------------------
async def _fetch_spark(
    client: httpx.AsyncClient,
    symbols: list[str],
    rng: str = "3mo",
    interval: str = "1d",
) -> dict[str, Any]:
    yahoo_syms = [s.upper().replace(".", "-") for s in symbols]
    wanted = {y: s for y, s in zip(yahoo_syms, symbols)}

    path = "/v7/finance/spark?symbols={}&range={}&interval={}".format(
        ",".join(yahoo_syms), rng, interval
    )
    last_err = "unknown error"
    for host in YAHOO_HOSTS:
        try:
            r = await client.get(host + path, headers=HEADERS, timeout=15.0)
            if r.status_code == 429 or r.status_code >= 500:
                last_err = "HTTP %d" % r.status_code
                continue
            r.raise_for_status()
            doc = r.json()
        except Exception as exc:
            last_err = str(exc)
            continue

        sp = (doc or {}).get("spark") if isinstance(doc, dict) else None
        if not isinstance(sp, dict):
            continue

        out: dict[str, Any] = {}
        for item in sp.get("result") or []:
            resp = item.get("response") or []
            if not resp:
                continue
            ysym = item.get("symbol") or (resp[0].get("meta") or {}).get("symbol") or ""
            sym = wanted.get(ysym.upper(), ysym.upper().replace("-", "."))
            res0 = resp[0]
            q = ((res0.get("indicators") or {}).get("quote") or [{}])[0] or {}
            t = res0.get("timestamp") or []
            n = len(t)

            def _col(k: str) -> list:
                v = q.get(k)
                return list(v) + [None] * (n - len(v)) if isinstance(v, list) else [None] * n

            out[sym] = {"t": list(t), "c": _col("close"), "meta": res0.get("meta") or {}}
        return out

    log.warning("spark fetch failed for batch: %s", last_err)
    return {}


# ---------------------------------------------------------------------------
# Daily closes extraction
# ---------------------------------------------------------------------------
def _daily_closes(series: dict) -> list[tuple[datetime.date, float]]:
    now_utc = datetime.datetime.utcnow()
    today_et = _to_eastern(now_utc).date()

    by_date: dict[datetime.date, float] = {}
    for ts, c in zip(series["t"], series["c"]):
        if c is None:
            continue
        d = _ts_to_eastern(ts).date()
        if d >= today_et:
            continue
        by_date[d] = float(c)
    return sorted(by_date.items())


# ---------------------------------------------------------------------------
# RSI-14 (Wilder's smoothed EMA) — ported from trader-scanner
# ---------------------------------------------------------------------------
def _rsi14(closes: list[float]) -> tuple[float | None, float | None]:
    if len(closes) < 16:
        return None, None

    gains, losses = [], []
    for i in range(1, 15):
        d = closes[-15 + i] - closes[-15 + i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))

    ag, al = sum(gains) / 14, sum(losses) / 14
    last_d = closes[-1] - closes[-2]
    ag = (ag * 13 + max(last_d, 0.0)) / 14
    al = (al * 13 + max(-last_d, 0.0)) / 14
    rsi = 100.0 - 100.0 / (1.0 + ag / al) if al else 100.0

    prev = closes[:-1]
    if len(prev) < 16:
        return rsi, None
    g2, l2 = [], []
    for i in range(1, 15):
        d = prev[-15 + i] - prev[-15 + i - 1]
        g2.append(max(d, 0.0))
        l2.append(max(-d, 0.0))
    ag2, al2 = sum(g2) / 14, sum(l2) / 14
    prev_d = prev[-1] - prev[-2]
    ag2 = (ag2 * 13 + max(prev_d, 0.0)) / 14
    al2 = (al2 * 13 + max(-prev_d, 0.0)) / 14
    rsi_prev = 100.0 - 100.0 / (1.0 + ag2 / al2) if al2 else 100.0
    return rsi, rsi_prev


# ---------------------------------------------------------------------------
# Setup detection — ported verbatim from trader-scanner's find_setups
# ---------------------------------------------------------------------------
def _find_setups(closes: list[float]) -> tuple[list[str], dict]:
    if len(closes) < MIN_DAILY_BARS:
        return [], {}

    last = closes[-1]
    r, r_prev = _rsi14(closes)
    tags: list[str] = []

    hi20 = max(closes[-21:-1]) if len(closes) >= 21 else None
    if hi20 is not None and last > hi20:
        tags.append("breakout_20d")

    ma20      = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    ma20_prev = sum(closes[-21:-1]) / 20 if len(closes) >= 21 else None
    if ma20 is not None and ma20_prev is not None:
        if closes[-2] < ma20_prev and last > ma20:
            tags.append("reclaim_ma20")

    if len(closes) >= 16:
        run_start = closes[-16]
        run_end   = closes[-6]
        run = (run_end / run_start - 1) if run_start else 0.0
        flag_hi = max(closes[-5:])
        flag_lo = min(closes[-5:])
        rng5 = (flag_hi / flag_lo - 1) if flag_lo else 1.0
        if run >= 0.10 and rng5 <= 0.05:
            tags.append("bull_flag")

    if r is not None and r < 30:
        tags.append("oversold")
    if r_prev is not None and r_prev < 30 and len(closes) >= 2 and last > closes[-2]:
        tags.append("oversold_bounce")

    return tags, {
        "rsi":   round(r, 1) if r is not None else None,
        "ma20":  round(ma20, 2) if ma20 is not None else None,
        "high20": round(hi20, 2) if hi20 is not None else None,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def run_daily_scan(
    symbols: list[str],
    min_price: float = DEFAULT_MIN_PRICE,
    min_volume: int = DEFAULT_MIN_VOLUME,
) -> dict:
    """
    Scan a list of symbols for day-trading setups using Yahoo daily spark data.

    Returns:
      hits       – matching symbols with setup tags, price, RSI, volume
      counts     – statistics (fetched, scanned, illiquid, hits)
      as_of      – UTC timestamp of the scan
      note       – educational disclaimer
    """
    now_utc = datetime.datetime.utcnow()

    async with httpx.AsyncClient() as client:
        all_series: dict[str, Any] = {}
        for i in range(0, len(symbols), SPARK_BATCH):
            batch = symbols[i : i + SPARK_BATCH]
            all_series.update(await _fetch_spark(client, batch))

    hits: list[dict] = []
    counts = {
        "requested": len(symbols),
        "fetched": 0,
        "illiquid": 0,
        "short_history": 0,
        "scanned": 0,
        "hits": 0,
    }

    for sym in symbols:
        s = all_series.get(sym)
        if not s:
            continue
        counts["fetched"] += 1

        meta   = s.get("meta") or {}
        price  = meta.get("regularMarketPrice")
        volume = meta.get("regularMarketVolume")
        bars   = _daily_closes(s)

        if price is None and bars:
            price = bars[-1][1]

        if (
            price is None
            or price < min_price
            or (min_volume > 0 and (volume is None or volume < min_volume))
        ):
            counts["illiquid"] += 1
            continue

        closes = [c for _, c in bars]
        if len(closes) < MIN_DAILY_BARS:
            counts["short_history"] += 1
            continue

        counts["scanned"] += 1
        tags, nums = _find_setups(closes)

        if tags:
            hits.append({
                "symbol":       sym,
                "setups":       tags,
                "setup_labels": [SETUP_LABELS[t] for t in tags],
                "price":        round(float(price), 2),
                "close_date":   bars[-1][0].isoformat() if bars else None,
                "rsi":          nums.get("rsi"),
                "ma20":         nums.get("ma20"),
                "high20":       nums.get("high20"),
                "volume":       int(volume) if volume is not None else None,
            })

    hits.sort(key=lambda h: -(h["price"] * (h["volume"] or 0)))
    counts["hits"] = len(hits)

    return {
        "as_of":  now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hits":   hits,
        "counts": counts,
        "note":   NOTE,
    }

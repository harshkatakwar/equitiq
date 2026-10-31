"""Trade entry and exit planning tool.

Ported from day-trader-skill `trader-entry`, `trader-exit`, and `trader-budget`:
Calculates trade plans for long positions: entry triggers, stop-loss levels,
2R profit targets, and share sizing based on disciplined risk limits.
"""

from __future__ import annotations

import math
from typing import Any, Optional


def build_trade_plan(
    symbol: str,
    current_price: float,
    setup_name: str = "breakout",
    stop_pct: float = 1.5,
    budget_usd: Optional[float] = 5000.0,
    max_risk_usd: Optional[float] = 100.0,
    custom_entry: Optional[float] = None,
    custom_stop: Optional[float] = None,
) -> dict[str, Any]:
    """Calculate disciplined trade plan with entry, stop loss, and 2R/1R profit targets."""
    sym = symbol.strip().upper()
    entry = round(custom_entry if custom_entry and custom_entry > 0 else current_price, 2)

    # Calculate stop loss
    if custom_stop and custom_stop > 0:
        stop = round(custom_stop, 2)
    else:
        # Default stop rounded down to the cent
        stop = math.floor(entry * (1.0 - (stop_pct / 100.0)) * 100) / 100.0

    risk_per_share = round(entry - stop, 2)

    # Sanity checks
    if risk_per_share <= 0:
        return {
            "error": f"Invalid trade plan: Stop (${stop:.2f}) must be strictly below Entry (${entry:.2f}).",
            "symbol": sym,
        }

    if (risk_per_share / entry) < 0.0005:
        return {
            "error": "Stop is too tight to survive bid/ask spread (less than 0.05% of price).",
            "symbol": sym,
        }

    # Targets (round half-up to cent)
    target_1r = round(entry + risk_per_share, 2)
    target_2r = round(entry + (2.0 * risk_per_share), 2)
    reward_risk_ratio = 2.0

    # Sizing (if budget and max risk provided)
    shares = None
    position_cost = None
    actual_risk = None

    if max_risk_usd and max_risk_usd > 0 and risk_per_share > 0:
        shares_by_risk = math.floor(max_risk_usd / risk_per_share)
        if budget_usd and budget_usd > 0:
            shares_by_budget = math.floor(budget_usd / entry)
            shares = max(1, min(shares_by_risk, shares_by_budget))
        else:
            shares = max(1, shares_by_risk)

        position_cost = round(shares * entry, 2)
        actual_risk = round(shares * risk_per_share, 2)

    return {
        "symbol": sym,
        "setup": setup_name,
        "side": "buy",
        "entry_price": entry,
        "stop_loss": stop,
        "risk_per_share": risk_per_share,
        "risk_pct": round((risk_per_share / entry) * 100, 2),
        "target_1r": target_1r,
        "target_2r": target_2r,
        "reward_risk_ratio": reward_risk_ratio,
        "recommended_shares": shares,
        "position_cost_usd": position_cost,
        "total_max_risk_usd": actual_risk,
        "rules": {
            "mandatory_stop": True,
            "min_rr": "2:1",
            "close_by_eod": True,
        },
    }

"""Pre-trade risk validator tool.

Ported from day-trader-skill `trader-risk`:
Enforces strict day-trading risk rules: mandatory stop-loss, minimum 2:1 reward/risk,
maximum dollar loss per trade, and spread survivability.
"""

from __future__ import annotations

from typing import Any


def check_trade_risk(
    trade_plan: dict[str, Any],
    max_loss_limit_usd: float = 150.0,
    min_reward_risk: float = 2.0,
) -> dict[str, Any]:
    """Audit trade plan against disciplined risk controls."""
    if not trade_plan or "error" in trade_plan:
        return {
            "verdict": "BLOCK",
            "passed": False,
            "reasons": [trade_plan.get("error", "Invalid or missing trade plan.")],
        }

    reasons = []
    warnings = []
    entry = trade_plan.get("entry_price", 0.0)
    stop = trade_plan.get("stop_loss", 0.0)
    target = trade_plan.get("target_2r", 0.0)
    rr = trade_plan.get("reward_risk_ratio", 0.0)
    total_risk = trade_plan.get("total_max_risk_usd", 0.0)

    # 1. Stop loss check
    if stop <= 0 or stop >= entry:
        reasons.append(f"Invalid stop loss (${stop:.2f}) - long trade requires stop strictly below entry (${entry:.2f}).")

    # 2. Minimum Reward:Risk check
    if rr < min_reward_risk:
        reasons.append(f"Reward-to-risk ratio ({rr:.1f}:1) is below mandatory minimum of {min_reward_risk:.1f}:1.")

    # 3. Dollar risk limit check
    if total_risk and total_risk > max_loss_limit_usd:
        reasons.append(f"Max potential loss (${total_risk:.2f}) exceeds per-trade loss ceiling (${max_loss_limit_usd:.2f}).")

    # 4. Spread check
    risk_per_share = entry - stop
    if entry > 0 and (risk_per_share / entry) < 0.005:
        warnings.append("Tight stop: Risk is less than 0.5% of stock price; watch out for market noise/spread slippage.")

    passed = len(reasons) == 0
    verdict = "PASS" if passed and not warnings else ("CAUTION" if passed else "BLOCK")

    return {
        "verdict": verdict,
        "passed": passed,
        "reasons": reasons,
        "warnings": warnings,
        "checked_rules": {
            "mandatory_stop": "OK" if stop < entry else "FAILED",
            "min_reward_risk": "OK" if rr >= min_reward_risk else "FAILED",
            "loss_within_limit": "OK" if (not total_risk or total_risk <= max_loss_limit_usd) else "FAILED",
        },
    }

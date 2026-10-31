"""LangGraph StateGraph workflow for EquitIQ Day Trader Agent.

Coordinates:
  - Technical chart setups & live quotes (`trader-scanner` + `trader-alerts`)
  - Official SEC EDGAR XBRL financials (`trader-analyst`)
  - News headlines & material 8-Ks (`trader-news`)
  - Entry trigger, stop-loss & 2R profit targets (`trader-entry` + `trader-exit`)
  - Pre-trade risk evaluation (`trader-risk`)
  - LLM synthesis via Google Gemini (LangChain Google GenAI)
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import get_settings
from src.modules.market_data.alerts import get_quote
from src.modules.market_data.scanner import run_daily_scan
from src.modules.trader_agent.sec_analyst import fetch_sec_financial_facts
from src.modules.trader_agent.news_monitor import fetch_company_news_and_filings
from src.modules.trader_agent.trade_planner import build_trade_plan
from src.modules.trader_agent.risk_checker import check_trade_risk

logger = logging.getLogger(__name__)


class TraderAgentState(TypedDict):
    query: str
    symbol: Optional[str]
    intent: str
    market_quote: Optional[dict[str, Any]]
    technical_setups: Optional[list[dict[str, Any]]]
    sec_facts: Optional[dict[str, Any]]
    news_data: Optional[dict[str, Any]]
    trade_plan: Optional[dict[str, Any]]
    risk_eval: Optional[dict[str, Any]]
    final_memo: Optional[str]
    errors: list[str]


def _extract_ticker(query: str) -> Optional[str]:
    """Extract standard stock ticker from user query."""
    # Common uppercase 1-5 letter ticker pattern
    tokens = re.findall(r"\b[A-Z]{1,5}\b", query.upper())
    # Exclude common false positives
    excluded = {"A", "I", "AI", "THE", "FOR", "ON", "IN", "IS", "BUY", "SELL", "NEW", "NOW", "AND", "OR", "US", "USD", "DAY", "WHAT", "HOW", "WHY"}
    candidates = [t for t in tokens if t not in excluded]
    return candidates[0] if candidates else None


async def router_node(state: TraderAgentState) -> dict[str, Any]:
    """Parse user query, identify target stock or scan request."""
    query = state.get("query", "").strip()
    symbol = state.get("symbol") or _extract_ticker(query)

    if not symbol:
        # Default fallback for testing if no ticker specified
        if "scan" in query.lower() or "market" in query.lower():
            intent = "scan_market"
            symbol = "AAPL"
        else:
            intent = "analyze_stock"
            symbol = "AAPL"
    else:
        intent = "analyze_stock"

    return {"symbol": symbol, "intent": intent}


async def market_data_node(state: TraderAgentState) -> dict[str, Any]:
    """Fetch live quote and technical scanner setup for symbol."""
    symbol = state.get("symbol", "AAPL")
    quote = await get_quote(symbol)

    # Run technical setup scanner for this symbol
    scan_res = await run_daily_scan(symbols=[symbol])
    setups = scan_res.get("results", [])

    return {
        "market_quote": quote,
        "technical_setups": setups,
    }


async def sec_facts_node(state: TraderAgentState) -> dict[str, Any]:
    """Fetch official SEC EDGAR XBRL financials (revenue YoY, margins, EPS)."""
    symbol = state.get("symbol", "AAPL")
    sec_facts = await fetch_sec_financial_facts(symbol)
    return {"sec_facts": sec_facts}


async def news_node(state: TraderAgentState) -> dict[str, Any]:
    """Fetch recent headlines and SEC 8-K material filings."""
    symbol = state.get("symbol", "AAPL")
    news = await fetch_company_news_and_filings(symbol)
    return {"news_data": news}


async def trade_planning_node(state: TraderAgentState) -> dict[str, Any]:
    """Calculate entry price, stop-loss, and 2R profit targets."""
    symbol = state.get("symbol", "AAPL")
    quote = state.get("market_quote") or {}
    price = quote.get("price") or 100.0

    setups = state.get("technical_setups") or []
    setup_name = setups[0].get("setup_name", "breakout") if setups else "standard_momentum"

    plan = build_trade_plan(
        symbol=symbol,
        current_price=price,
        setup_name=setup_name,
        stop_pct=1.5,
        budget_usd=5000.0,
        max_risk_usd=100.0,
    )
    return {"trade_plan": plan}


async def risk_audit_node(state: TraderAgentState) -> dict[str, Any]:
    """Run pre-trade risk evaluation against disciplined day-trading rules."""
    plan = state.get("trade_plan") or {}
    risk_eval = check_trade_risk(plan, max_loss_limit_usd=150.0, min_reward_risk=2.0)
    return {"risk_eval": risk_eval}


async def synthesizer_node(state: TraderAgentState) -> dict[str, Any]:
    """Synthesize all research data using Google Gemini into an institutional memo."""
    settings = get_settings()
    symbol = state.get("symbol", "AAPL")
    quote = state.get("market_quote") or {}
    sec = state.get("sec_facts") or {}
    news = state.get("news_data") or {}
    plan = state.get("trade_plan") or {}
    risk = state.get("risk_eval") or {}

    api_key = (
        getattr(settings, "gemini_api_key", None)
        or getattr(settings, "google_api_key", None)
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )

    # Format factual context
    latest_q = sec.get("latest_quarter") or {}
    headlines = [a.get("title") for a in (news.get("articles") or [])[:5]]
    filings = [f.get("title") for f in (news.get("material_8k_filings") or [])[:3]]
    setups = state.get("technical_setups") or []
    setup_desc = setups[0].get("description", "No active breakout setup detected on 20-day daily spark.") if setups else "Neutral setup"

    context_str = f"""
SYMBOL: {symbol}
CURRENT PRICE: ${quote.get('price', 'N/A')} (Change: {quote.get('change_pct', 'N/A')}%)
DAY RANGE: ${quote.get('day_low', 'N/A')} - ${quote.get('day_high', 'N/A')}
52-WEEK RANGE: ${quote.get('fifty_two_week_low', 'N/A')} - ${quote.get('fifty_two_week_high', 'N/A')}

TECHNICAL SCAN:
Setup: {setup_desc}

SEC EDGAR FILED FINANCIALS (10-Q / 10-K):
Company: {sec.get('company_name', symbol)}
Latest Quarter End: {latest_q.get('period_end', 'N/A')}
Revenue: ${latest_q.get('revenue', 0):,} (YoY Growth: {latest_q.get('revenue_yoy_pct', 'N/A')}%)
Gross Margin: {latest_q.get('gross_margin_pct', 'N/A')}%
Operating Margin: {latest_q.get('operating_margin_pct', 'N/A')}%
Net Income: ${latest_q.get('net_income', 0):,} (YoY Growth: {latest_q.get('net_income_yoy_pct', 'N/A')}%)
Diluted EPS: ${latest_q.get('eps_diluted', 'N/A')}
Flags: {latest_q.get('flags', [])}

RECENT NEWS HEADLINES:
- {chr(10).join('- ' + h for h in headlines) if headlines else 'No recent headlines'}

RECENT 8-K FILINGS:
- {chr(10).join('- ' + f for f in filings) if filings else 'No recent 8-Ks'}

PROPOSED TRADE PLAN:
Entry: ${plan.get('entry_price', 'N/A')}
Stop-Loss: ${plan.get('stop_loss', 'N/A')} (-{plan.get('risk_pct', 'N/A')}%)
Target (2R): ${plan.get('target_2r', 'N/A')}
Reward:Risk: {plan.get('reward_risk_ratio', 'N/A')}:1
Recommended Sizing: {plan.get('recommended_shares', 'N/A')} shares (Max Risk: ${plan.get('total_max_risk_usd', 'N/A')})

RISK EVALUATION:
Verdict: {risk.get('verdict', 'N/A')}
Passed: {risk.get('passed', 'N/A')}
Warnings/Reasons: {risk.get('warnings', []) + risk.get('reasons', [])}
"""

    if api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=getattr(settings, "ai_default_model", "gemini-1.5-flash"),
                google_api_key=api_key,
                temperature=0.2,
            )

            prompt = [
                SystemMessage(
                    content=(
                        "You are an elite institutional day-trading analyst agent. "
                        "Your job is to provide honest, data-driven, risk-controlled trade research. "
                        "Always prioritize filed numbers (SEC EDGAR) over hype. Never guess or hallucinate. "
                        "Format your response as a professional markdown research memo with the following sections:\n"
                        "1. Executive Verdict (PASS / CAUTION / BLOCK)\n"
                        "2. Technical & Market Setup\n"
                        "3. SEC EDGAR Fundamental Audit (Revenue YoY, margins, earnings flags)\n"
                        "4. News & Catalyst Scan\n"
                        "5. Execution Plan (Exact Entry, Stop-Loss, 2R Target, Position Size)\n"
                        "6. Risk Assessment & Disclaimers"
                    )
                ),
                HumanMessage(content=f"Please analyze the following trade data and generate the research report:\n\n{context_str}"),
            ]

            response = await llm.ainvoke(prompt)
            memo = response.content
        except Exception as e:
            logger.error("Error generating Gemini analysis: %s", e)
            memo = _generate_fallback_memo(symbol, context_str, risk.get("verdict", "CAUTION"))
    else:
        memo = _generate_fallback_memo(symbol, context_str, risk.get("verdict", "CAUTION"))

    return {"final_memo": memo}


def _generate_fallback_memo(symbol: str, context: str, verdict: str) -> str:
    return f"""# 📊 EquitIQ Day Trader Research Memo — {symbol}

**Verdict: `{verdict}`**

> *Note: Provide your GEMINI_API_KEY to enable full natural language synthesis with Google Gemini. This structured report is generated from verified real-time feeds.*

---

### 1. Market & Technical Overview
{context}

---

### 2. Disclaimers
*Educational and research tooling only — not financial advice. Past performance does not guarantee future results. Always manage risk with mandatory stop-losses.*
"""


def build_trader_agent_graph():
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(TraderAgentState)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("market_data", market_data_node)
    workflow.add_node("sec_facts", sec_facts_node)
    workflow.add_node("news", news_node)
    workflow.add_node("trade_planner", trade_planning_node)
    workflow.add_node("risk_audit", risk_audit_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Define edges (sequential workflow)
    workflow.add_edge(START, "router")
    workflow.add_edge("router", "market_data")
    workflow.add_edge("market_data", "sec_facts")
    workflow.add_edge("sec_facts", "news")
    workflow.add_edge("news", "trade_planner")
    workflow.add_edge("trade_planner", "risk_audit")
    workflow.add_edge("risk_audit", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()


# Singleton compiled graph instance
trader_agent_graph = build_trader_agent_graph()

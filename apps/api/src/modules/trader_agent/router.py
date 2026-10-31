"""FastAPI router for the LangGraph-powered Day Trader Agent."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from src.modules.trader_agent.graph import trader_agent_graph
from src.modules.trader_agent.sec_analyst import fetch_sec_financial_facts
from src.modules.trader_agent.news_monitor import fetch_company_news_and_filings
from src.modules.trader_agent.trade_planner import build_trade_plan
from src.modules.trader_agent.risk_checker import check_trade_risk

router = APIRouter()


class AnalyzeRequest(BaseModel):
    symbol: Optional[str] = Field(None, description="Stock ticker symbol (e.g. AAPL, TSLA, NVDA)")
    query: Optional[str] = Field("Analyze this stock for a day trade setup with full SEC earnings and risk check", description="User question or analysis goal")


class TradePlanRequest(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol")
    current_price: float = Field(..., description="Current market price")
    stop_pct: float = Field(1.5, description="Stop loss percentage under entry")
    budget_usd: Optional[float] = Field(5000.0, description="Available budget")
    max_risk_usd: Optional[float] = Field(100.0, description="Max dollar loss at stop")


@router.post("/analyze")
async def analyze_stock_with_agent(req: AnalyzeRequest):
    """Run full LangGraph agent workflow:

    1. Gathers live quote & 20-day technical setups (breakout, bull flag, oversold)
    2. Reads official SEC EDGAR XBRL facts (revenue YoY, margins, diluted EPS)
    3. Scans breaking news headlines & material 8-K filings
    4. Formulates trade entry, stop-loss, and 2R profit targets
    5. Audits against pre-trade risk controls
    6. Generates institutional research memo with Google Gemini
    """
    initial_state = {
        "query": req.query or f"Analyze {req.symbol}",
        "symbol": req.symbol.upper() if req.symbol else None,
        "intent": "analyze_stock",
        "market_quote": None,
        "technical_setups": None,
        "sec_facts": None,
        "news_data": None,
        "trade_plan": None,
        "risk_eval": None,
        "final_memo": None,
        "errors": [],
    }

    try:
        result = await trader_agent_graph.ainvoke(initial_state)
        return {
            "symbol": result.get("symbol"),
            "intent": result.get("intent"),
            "market_quote": result.get("market_quote"),
            "technical_setups": result.get("technical_setups"),
            "sec_facts": result.get("sec_facts"),
            "news_data": result.get("news_data"),
            "trade_plan": result.get("trade_plan"),
            "risk_eval": result.get("risk_eval"),
            "memo": result.get("final_memo"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow execution failed: {str(e)}")


@router.get("/tools/sec-facts/{symbol}")
async def get_sec_facts(symbol: str):
    """Direct tool: Fetch official SEC EDGAR XBRL financials for a company."""
    return await fetch_sec_financial_facts(symbol)


@router.get("/tools/news/{symbol}")
async def get_news_and_filings(symbol: str):
    """Direct tool: Fetch Yahoo headlines and SEC 8-K material filings for a company."""
    return await fetch_company_news_and_filings(symbol)


@router.post("/tools/plan-trade")
async def calculate_trade_plan(req: TradePlanRequest):
    """Direct tool: Calculate entry price, stop-loss, 2R target and risk audit."""
    plan = build_trade_plan(
        symbol=req.symbol,
        current_price=req.current_price,
        stop_pct=req.stop_pct,
        budget_usd=req.budget_usd,
        max_risk_usd=req.max_risk_usd,
    )
    risk = check_trade_risk(plan)
    return {"plan": plan, "risk_audit": risk}

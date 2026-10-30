"""Seed script — Fetch and insert real market data using yfinance."""

import asyncio
import uuid
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import yfinance as yf
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import get_settings

settings = get_settings()

NIFTY_COMPANIES = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services Limited"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank Limited"},
    {"symbol": "INFY.NS", "name": "Infosys Limited"},
    {"symbol": "ITC.NS", "name": "ITC Limited"},
    {"symbol": "SBIN.NS", "name": "State Bank of India"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel Limited"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever Limited"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance Limited"}
]

async def seed_real_data():
    """Fetch real market data and seed it into the database."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as db:
        print("Clearing old synthetic market data...")
        tables_to_clear = [
            "transcript_segments", "transcripts", "concall_events",
            "document_sections", "document_versions", "documents", "filings",
            "financial_facts", "financial_statements", "financial_periods",
            "announcements", "market_prices", "securities", "companies"
        ]
        for table in tables_to_clear:
            await db.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
            
        await db.commit()
        
        # Ensure NSE exchange exists
        nse_id = uuid.uuid4()
        result = await db.execute(text("SELECT id FROM exchanges WHERE code = 'NSE'"))
        row = result.first()
        if row:
            nse_id = row[0]
        else:
            await db.execute(text("INSERT INTO exchanges (id, code, name) VALUES (:id, :code, :name)"), 
                             {"id": nse_id, "code": "NSE", "name": "National Stock Exchange"})
            await db.commit()

        print(f"Fetching data for {len(NIFTY_COMPANIES)} companies from Yahoo Finance...")

        for comp in NIFTY_COMPANIES:
            symbol = comp["symbol"]
            print(f"Processing {symbol}...")
            
            ticker = yf.Ticker(symbol)
            company_id = uuid.uuid4()
            slug = symbol.lower().replace(".ns", "")
            
            sector = "Equities"
            industry = "Market"
            description = f"Real market data for {comp['name']}."
            website = ""
            hq = "India"
            
            await db.execute(text("""
                INSERT INTO companies (id, name, slug, sector, industry, description, headquarters, website, created_at, updated_at)
                VALUES (:id, :name, :slug, :sector, :industry, :desc, :hq, :web, now(), now())
            """), {
                "id": company_id,
                "name": comp["name"],
                "slug": slug,
                "sector": sector,
                "industry": industry,
                "desc": description,
                "hq": hq,
                "web": website,
            })
            
            security_id = uuid.uuid4()
            db_symbol = symbol.replace(".NS", "")
            await db.execute(text("""
                INSERT INTO securities (id, company_id, exchange_id, symbol, is_primary)
                VALUES (:id, :cid, :eid, :sym, true)
            """), {
                "id": security_id,
                "cid": company_id,
                "eid": nse_id,
                "sym": db_symbol
            })
            
            hist = ticker.history(period="1y")
            if not hist.empty:
                print(f"  Found {len(hist)} days of historical data.")
                for index, row in hist.iterrows():
                    trade_date = index.date()
                    
                    if str(row['Open']) == "nan":
                        continue
                        
                    await db.execute(text("""
                        INSERT INTO market_prices (id, security_id, date, open, high, low, close, volume, source)
                        VALUES (:id, :sid, :d, :o, :h, :l, :c, :v, 'yfinance')
                        ON CONFLICT (security_id, date) DO NOTHING
                    """), {
                        "id": uuid.uuid4(),
                        "sid": security_id,
                        "d": trade_date,
                        "o": round(row['Open'], 2),
                        "h": round(row['High'], 2),
                        "l": round(row['Low'], 2),
                        "c": round(row['Close'], 2),
                        "v": int(row['Volume']) if not str(row['Volume']) == "nan" else 0,
                    })
            else:
                print(f"  No historical data found for {symbol}")

            await db.commit()
            print(f"Successfully processed {symbol}.")

    print("Seed process completed.")

if __name__ == "__main__":
    asyncio.run(seed_real_data())

"""Seed script — Create demo data for 10 companies across 10 sectors."""

import asyncio
import uuid
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import get_settings
from src.modules.identity.service import hash_password

settings = get_settings()

DEMO_COMPANIES = [
    {"name": "Bharat National Bank", "slug": "bharat-national-bank", "symbol": "BHARATBANK", "isin": "INE001D01010",
     "sector": "Banking", "industry": "Private Sector Banks", "description": "Demo content — not an exchange filing. A leading private sector bank offering retail, corporate, and treasury banking services across India.",
     "founded_year": 1994, "headquarters": "Mumbai, Maharashtra", "website": "https://demo.bharatbank.example"},
    {"name": "Pinnacle Financial Services", "slug": "pinnacle-financial", "symbol": "PINNFIN", "isin": "INE002D01020",
     "sector": "NBFC", "industry": "Housing Finance", "description": "Demo content — not an exchange filing. A non-banking financial company focused on affordable housing loans and micro-enterprise lending.",
     "founded_year": 2008, "headquarters": "Bengaluru, Karnataka", "website": "https://demo.pinnfin.example"},
    {"name": "Drishti Technologies", "slug": "drishti-technologies", "symbol": "DRISHTITECH", "isin": "INE003D01030",
     "sector": "IT Services", "industry": "IT Consulting & Software", "description": "Demo content — not an exchange filing. A global IT services and consulting company providing digital transformation and cloud solutions.",
     "founded_year": 1998, "headquarters": "Pune, Maharashtra", "website": "https://demo.drishtitech.example"},
    {"name": "Vajra Motors", "slug": "vajra-motors", "symbol": "VAJRAMOTORS", "isin": "INE004D01040",
     "sector": "Automobiles", "industry": "Passenger Vehicles", "description": "Demo content — not an exchange filing. A diversified automobile manufacturer producing passenger vehicles, commercial vehicles, and electric vehicles.",
     "founded_year": 1945, "headquarters": "Chennai, Tamil Nadu", "website": "https://demo.vajramotors.example"},
    {"name": "Arogya Pharmaceuticals", "slug": "arogya-pharma", "symbol": "AROGYAPHARMA", "isin": "INE005D01050",
     "sector": "Pharmaceuticals", "industry": "Formulations", "description": "Demo content — not an exchange filing. An integrated pharmaceutical company with strengths in complex generics and specialty medicines.",
     "founded_year": 1986, "headquarters": "Hyderabad, Telangana", "website": "https://demo.arogyapharma.example"},
    {"name": "Samriddhi Consumer Products", "slug": "samriddhi-consumer", "symbol": "SAMRIDDHI", "isin": "INE006D01060",
     "sector": "Consumer Goods", "industry": "FMCG", "description": "Demo content — not an exchange filing. A fast-moving consumer goods company with market-leading brands in home care, personal care, and food segments.",
     "founded_year": 1933, "headquarters": "Mumbai, Maharashtra", "website": "https://demo.samriddhi.example"},
    {"name": "Nirmaan Engineering", "slug": "nirmaan-engineering", "symbol": "NIRMAAN", "isin": "INE007D01070",
     "sector": "Capital Goods", "industry": "Heavy Electrical Equipment", "description": "Demo content — not an exchange filing. A capital goods company manufacturing power equipment, industrial machinery, and defence systems.",
     "founded_year": 1956, "headquarters": "New Delhi", "website": "https://demo.nirmaan.example"},
    {"name": "Rasayan Industries", "slug": "rasayan-industries", "symbol": "RASAYAN", "isin": "INE008D01080",
     "sector": "Chemicals", "industry": "Specialty Chemicals", "description": "Demo content — not an exchange filing. A leading specialty chemicals company producing agrochemicals, polymer additives, and pigments.",
     "founded_year": 1992, "headquarters": "Vadodara, Gujarat", "website": "https://demo.rasayan.example"},
    {"name": "Sanchar Telecom", "slug": "sanchar-telecom", "symbol": "SANCHARTELE", "isin": "INE009D01090",
     "sector": "Telecom", "industry": "Wireless Services", "description": "Demo content — not an exchange filing. A major telecommunications company providing 4G/5G wireless, broadband, and enterprise connectivity services.",
     "founded_year": 2002, "headquarters": "Mumbai, Maharashtra", "website": "https://demo.sanchartele.example"},
    {"name": "Urja Power Corporation", "slug": "urja-power", "symbol": "URJAPOWER", "isin": "INE010D01100",
     "sector": "Utilities", "industry": "Power Generation", "description": "Demo content — not an exchange filing. An integrated power utility operating thermal, solar, and wind energy generation assets.",
     "founded_year": 1975, "headquarters": "Ahmedabad, Gujarat", "website": "https://demo.urjapower.example"},
]

STANDARD_METRICS_PNL = [
    ("revenue", "Revenue from Operations", "income", "currency", "pnl", 1),
    ("other_income", "Other Income", "income", "currency", "pnl", 2),
    ("total_income", "Total Income", "income", "currency", "pnl", 3),
    ("raw_materials", "Cost of Materials", "expense", "currency", "pnl", 4),
    ("employee_cost", "Employee Benefits Expense", "expense", "currency", "pnl", 5),
    ("other_expenses", "Other Expenses", "expense", "currency", "pnl", 6),
    ("ebitda", "EBITDA", "income", "currency", "pnl", 7),
    ("depreciation", "Depreciation & Amortisation", "expense", "currency", "pnl", 8),
    ("ebit", "EBIT", "income", "currency", "pnl", 9),
    ("interest", "Finance Costs", "expense", "currency", "pnl", 10),
    ("pbt", "Profit Before Tax", "income", "currency", "pnl", 11),
    ("tax", "Tax Expense", "expense", "currency", "pnl", 12),
    ("pat", "Profit After Tax", "income", "currency", "pnl", 13),
    ("eps", "Earnings Per Share", "ratio", "ratio", "pnl", 14),
]

ANNOUNCEMENT_CATEGORIES = [
    ("board_meeting", "Board Meeting"),
    ("financial_results", "Financial Results"),
    ("dividend", "Dividend"),
    ("agm", "Annual General Meeting"),
    ("corporate_action", "Corporate Action"),
    ("acquisition", "Acquisition / Disposal"),
    ("order_win", "Order Win"),
    ("credit_rating", "Credit Rating"),
    ("management_change", "Management Change"),
    ("regulatory", "Regulatory"),
    ("general", "General Announcement"),
]


async def seed_all():
    """Run all seed functions."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as db:
        # Check if already seeded
        result = await db.execute(text("SELECT COUNT(*) FROM companies"))
        count = result.scalar()
        if count and count > 0:
            print("Database already seeded, skipping.")
            return

        print("Seeding database...")

        # Create demo user
        demo_user_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO users (id, email, password_hash, display_name, role, is_active, email_verified)
            VALUES (:id, :email, :password_hash, :display_name, :role, true, true)
        """), {
            "id": demo_user_id, "email": settings.demo_user_email,
            "password_hash": hash_password(settings.demo_user_password),
            "display_name": "Demo User", "role": "user",
        })

        # Create admin user
        admin_user_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO users (id, email, password_hash, display_name, role, is_active, email_verified)
            VALUES (:id, :email, :password_hash, :display_name, :role, true, true)
        """), {
            "id": admin_user_id, "email": "admin@researchos.dev",
            "password_hash": hash_password("admin123456"),
            "display_name": "Admin User", "role": "admin",
        })

        # Create exchanges
        nse_id, bse_id = uuid.uuid4(), uuid.uuid4()
        await db.execute(text("INSERT INTO exchanges (id, code, name) VALUES (:id, :code, :name)"), {"id": nse_id, "code": "NSE", "name": "National Stock Exchange"})
        await db.execute(text("INSERT INTO exchanges (id, code, name) VALUES (:id, :code, :name)"), {"id": bse_id, "code": "BSE", "name": "Bombay Stock Exchange"})

        # Create standard metrics
        metric_ids = {}
        for code, name, category, unit_type, stmt_type, order in STANDARD_METRICS_PNL:
            mid = uuid.uuid4()
            metric_ids[code] = mid
            await db.execute(text("""
                INSERT INTO standard_metrics (id, code, name, category, unit_type, statement_type, display_order)
                VALUES (:id, :code, :name, :category, :unit_type, :stmt_type, :order)
            """), {"id": mid, "code": code, "name": name, "category": category,
                   "unit_type": unit_type, "stmt_type": stmt_type, "order": order})

        # Create announcement categories
        cat_ids = {}
        for code, name in ANNOUNCEMENT_CATEGORIES:
            cid = uuid.uuid4()
            cat_ids[code] = cid
            await db.execute(text("INSERT INTO announcement_categories (id, code, name) VALUES (:id, :code, :name)"),
                             {"id": cid, "code": code, "name": name})

        # Create plans and entitlements
        starter_plan_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO plans (id, code, name, description, price_monthly, price_annual, display_order)
            VALUES (:id, :code, :name, :desc, :pm, :pa, :order)
        """), {"id": starter_plan_id, "code": "STARTER", "name": "Starter", "desc": "Free plan with basic features",
               "pm": 0, "pa": 0, "order": 0})

        pro_plan_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO plans (id, code, name, description, price_monthly, price_annual, display_order)
            VALUES (:id, :code, :name, :desc, :pm, :pa, :order)
        """), {"id": pro_plan_id, "code": "PROFESSIONAL", "name": "Professional", "desc": "For active investors",
               "pm": 999, "pa": 9999, "order": 1})

        research_m_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO plans (id, code, name, description, price_monthly, price_annual, display_order)
            VALUES (:id, :code, :name, :desc, :pm, :pa, :order)
        """), {"id": research_m_id, "code": "RESEARCH_MONTHLY", "name": "Research Monthly", "desc": "Full research access",
               "pm": 2999, "pa": None, "order": 2})

        # Starter entitlements
        starter_entitlements = [
            ("watchlists.count", 2, None), ("watchlists.companies_per_list", 50, None),
            ("filters.executions", 10, "month"), ("concall.summaries", 5, "month"),
            ("annual_report.summaries", 3, "month"), ("company.ai_overviews", 3, "month"),
            ("document_chat.questions", 3, "month"), ("idea_discovery.views", 10, "month"),
            ("tables.max_columns", 12, None), ("concall.ai_transcripts", 2, "month"),
        ]
        for fkey, limit, period in starter_entitlements:
            await db.execute(text("""
                INSERT INTO entitlements (id, plan_id, feature_key, limit_value, period)
                VALUES (:id, :plan_id, :fk, :lv, :p)
            """), {"id": uuid.uuid4(), "plan_id": starter_plan_id, "fk": fkey, "lv": limit, "p": period})

        # Assign demo user to Starter plan
        sub_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO subscriptions (id, user_id, plan_id, status, current_period_start, current_period_end)
            VALUES (:id, :uid, :pid, 'active', :ps, :pe)
        """), {"id": sub_id, "uid": demo_user_id, "pid": starter_plan_id,
               "ps": date.today().replace(day=1), "pe": (date.today().replace(day=1) + timedelta(days=31)).replace(day=1)})

        # Demo data licence
        demo_licence_id = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO data_licences (id, provider, dataset, licence_type, internal_use_allowed, display_allowed,
                derived_data_allowed, export_allowed, api_delivery_allowed, ai_processing_allowed, document_retention_allowed)
            VALUES (:id, 'demo', 'synthetic', 'internal', true, true, true, true, true, true, true)
        """), {"id": demo_licence_id})

        # Seed companies
        random.seed(42)  # Deterministic
        base_prices = [850, 1200, 3500, 2100, 950, 2800, 1600, 780, 450, 320]
        base_revenues = [85000, 12000, 120000, 95000, 18000, 55000, 28000, 8500, 65000, 42000]

        for i, comp_data in enumerate(DEMO_COMPANIES):
            company_id = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO companies (id, name, slug, isin, sector, industry, description, founded_year, headquarters, website)
                VALUES (:id, :name, :slug, :isin, :sector, :industry, :desc, :fy, :hq, :web)
            """), {
                "id": company_id, "name": comp_data["name"], "slug": comp_data["slug"],
                "isin": comp_data["isin"], "sector": comp_data["sector"], "industry": comp_data["industry"],
                "desc": comp_data["description"], "fy": comp_data["founded_year"],
                "hq": comp_data["headquarters"], "web": comp_data["website"],
            })

            # NSE security
            security_id = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO securities (id, company_id, exchange_id, symbol, is_primary)
                VALUES (:id, :cid, :eid, :sym, true)
            """), {"id": security_id, "cid": company_id, "eid": nse_id, "sym": comp_data["symbol"]})

            # Generate 2 years of EOD prices
            base_price = base_prices[i]
            today = date.today()
            for d in range(500):
                trade_date = today - timedelta(days=d)
                if trade_date.weekday() >= 5:
                    continue
                drift = (500 - d) * 0.0003
                noise = random.uniform(-0.02, 0.02)
                price = base_price * (1 + drift + noise)
                vol = random.randint(500000, 5000000)
                mcap = price * random.randint(50000000, 500000000)
                await db.execute(text("""
                    INSERT INTO market_prices (id, security_id, date, open, high, low, close, volume, market_cap, source)
                    VALUES (:id, :sid, :d, :o, :h, :l, :c, :v, :mc, 'demo')
                    ON CONFLICT (security_id, date) DO NOTHING
                """), {
                    "id": uuid.uuid4(), "sid": security_id, "d": trade_date,
                    "o": round(price * 0.995, 2), "h": round(price * 1.015, 2),
                    "l": round(price * 0.985, 2), "c": round(price, 2),
                    "v": vol, "mc": round(mcap, 2),
                })

            # Create financial periods (8 quarters + 2 annual)
            base_rev = base_revenues[i]
            for q in range(8):
                fy = 2026 if q < 4 else 2025
                quarter = (q % 4) + 1
                q_start_month = {1: 4, 2: 7, 3: 10, 4: 1}[quarter]
                q_start_year = fy if quarter != 4 else fy + 1
                if quarter == 4:
                    q_start_year = fy
                    q_start_month = 1

                period_start = date(fy - 1 if quarter == 4 else fy, q_start_month, 1) if quarter < 4 else date(fy, 1, 1)
                # Simplified quarter dates
                period_start = date(fy, {1:4, 2:7, 3:10, 4:1}[quarter], 1)
                period_end = date(fy, {1:6, 2:9, 3:12, 4:3}[quarter], {1:30, 2:30, 3:31, 4:31}[quarter])

                period_id = uuid.uuid4()
                await db.execute(text("""
                    INSERT INTO financial_periods (id, company_id, period_type, period_start, period_end, fiscal_year, fiscal_quarter, standalone_or_consolidated)
                    VALUES (:id, :cid, 'quarterly', :ps, :pe, :fy, :fq, 'standalone')
                """), {"id": period_id, "cid": company_id, "ps": period_start, "pe": period_end, "fy": fy, "fq": quarter})

                # Create P&L statement
                stmt_id = uuid.uuid4()
                pub_ts = datetime(fy, period_end.month, min(period_end.day + 15, 28), tzinfo=timezone.utc)
                await db.execute(text("""
                    INSERT INTO financial_statements (id, financial_period_id, statement_type, publication_timestamp)
                    VALUES (:id, :pid, 'pnl', :pts)
                """), {"id": stmt_id, "pid": period_id, "pts": pub_ts})

                # Create financial facts with growth trend
                growth = 1 + (8 - q) * 0.03 + random.uniform(-0.05, 0.05)
                rev = round(base_rev * growth / 4, 2)
                facts = [
                    ("revenue", rev), ("other_income", round(rev * 0.02, 2)),
                    ("total_income", round(rev * 1.02, 2)),
                    ("raw_materials", round(rev * 0.4, 2)), ("employee_cost", round(rev * 0.15, 2)),
                    ("other_expenses", round(rev * 0.12, 2)), ("ebitda", round(rev * 0.33, 2)),
                    ("depreciation", round(rev * 0.05, 2)), ("ebit", round(rev * 0.28, 2)),
                    ("interest", round(rev * 0.03, 2)), ("pbt", round(rev * 0.25, 2)),
                    ("tax", round(rev * 0.065, 2)), ("pat", round(rev * 0.185, 2)),
                    ("eps", round(rev * 0.185 / 100, 2)),
                ]
                for metric_code, value in facts:
                    await db.execute(text("""
                        INSERT INTO financial_facts (id, company_id, financial_statement_id, standard_metric_id,
                            value, unit, currency, period_start, period_end, period_type, standalone_or_consolidated)
                        VALUES (:id, :cid, :sid, :mid, :val, 'Cr', 'INR', :ps, :pe, 'quarterly', 'standalone')
                    """), {
                        "id": uuid.uuid4(), "cid": company_id, "sid": stmt_id,
                        "mid": metric_ids[metric_code], "val": value,
                        "ps": period_start, "pe": period_end,
                    })

            # Create filing, document, and document version for each quarter
            for q in range(4):
                filing_id = uuid.uuid4()
                doc_id = uuid.uuid4()
                dv_id = uuid.uuid4()
                filing_date = today - timedelta(days=q * 90 + 15)
                await db.execute(text("""
                    INSERT INTO filings (id, company_id, filing_type, filing_date, provider)
                    VALUES (:id, :cid, 'quarterly_result', :fd, 'demo')
                """), {"id": filing_id, "cid": company_id, "fd": filing_date})

                await db.execute(text("""
                    INSERT INTO documents (id, filing_id, company_id, title, document_type)
                    VALUES (:id, :fid, :cid, :title, 'quarterly_result')
                """), {"id": doc_id, "fid": filing_id, "cid": company_id,
                       "title": f"Demo content — Q{4-q} FY{2026} Results - {comp_data['name']}"})

                await db.execute(text("""
                    INSERT INTO document_versions (id, document_id, version_number, processing_status, mime_type, licence_id)
                    VALUES (:id, :did, 1, 'PUBLISHED', 'application/pdf', :lid)
                """), {"id": dv_id, "did": doc_id, "lid": demo_licence_id})

                # Document section
                await db.execute(text("""
                    INSERT INTO document_sections (id, document_version_id, section_type, title, content, sequence)
                    VALUES (:id, :dvid, 'financial_results', :title, :content, 0)
                """), {"id": uuid.uuid4(), "dvid": dv_id,
                       "title": f"Financial Results Q{4-q} FY2026",
                       "content": f"Demo content — not an exchange filing. {comp_data['name']} reported quarterly results with revenue growth and margin expansion."})

            # Create concall events with transcripts
            for q in range(4):
                concall_id = uuid.uuid4()
                scheduled = datetime(2026, {0:8, 1:5, 2:2, 3:11}[q], 15, 16, 0, tzinfo=timezone.utc)
                status = "completed" if q > 0 else "scheduled"

                await db.execute(text("""
                    INSERT INTO concall_events (id, company_id, title, event_type, scheduled_at, status, source)
                    VALUES (:id, :cid, :title, 'earnings_call', :sa, :status, 'demo')
                """), {"id": concall_id, "cid": company_id,
                       "title": f"Demo content — Q{4-q} FY2026 Earnings Call - {comp_data['name']}",
                       "sa": scheduled, "status": status})

                if status == "completed":
                    transcript_id = uuid.uuid4()
                    await db.execute(text("""
                        INSERT INTO transcripts (id, concall_event_id, source_type, language, is_verified)
                        VALUES (:id, :ceid, 'demo', 'en', true)
                    """), {"id": transcript_id, "ceid": concall_id})

                    # Transcript segments
                    segments = [
                        ("Moderator", "Operator", "prepared_remarks", "Demo content — not an exchange filing. Good afternoon and welcome to the earnings conference call. We have the management team present today."),
                        ("CEO", "Managing Director & CEO", "prepared_remarks", f"Demo content — not an exchange filing. Thank you. We are pleased to report strong performance this quarter. {comp_data['name']} achieved robust revenue growth driven by volume expansion and market share gains."),
                        ("CFO", "Chief Financial Officer", "prepared_remarks", "Demo content — not an exchange filing. Revenue for the quarter grew significantly year-over-year. EBITDA margins expanded by approximately 200 basis points due to operating leverage and cost optimization initiatives."),
                        ("Analyst 1", "Analyst, Demo Securities", "qa_question", "Demo content — not an exchange filing. Can you provide more color on the margin expansion drivers and sustainability?"),
                        ("CFO", "Chief Financial Officer", "qa_answer", "Demo content — not an exchange filing. The margin improvement is driven by better product mix, operating leverage, and ongoing cost optimization programs. We expect margins to remain stable."),
                        ("Analyst 2", "Analyst, Demo Capital", "qa_question", "Demo content — not an exchange filing. What is the guidance for next quarter in terms of revenue growth?"),
                        ("CEO", "Managing Director & CEO", "qa_answer", "Demo content — not an exchange filing. We are optimistic about sustained growth momentum. We expect continued strong performance driven by our strategic initiatives."),
                    ]
                    for seq, (speaker, role, seg_type, seg_text) in enumerate(segments):
                        await db.execute(text("""
                            INSERT INTO transcript_segments (id, transcript_id, speaker_name, speaker_role, sequence, segment_type, text, confidence)
                            VALUES (:id, :tid, :sn, :sr, :seq, :st, :txt, 0.95)
                        """), {"id": uuid.uuid4(), "tid": transcript_id, "sn": speaker, "sr": role,
                               "seq": seq, "st": seg_type, "txt": seg_text})

            # Create announcements
            ann_templates = [
                ("Board Meeting scheduled to consider quarterly results", "board_meeting", True),
                ("Declaration of interim dividend", "dividend", True),
                (f"Demo content — {comp_data['name']} wins major order worth ₹500 Cr", "order_win", True),
                ("Outcome of Board Meeting - Financial Results approved", "financial_results", True),
                ("Annual General Meeting notice", "agm", False),
                ("Change in key managerial personnel", "management_change", True),
            ]
            for j, (title_tmpl, cat_code, material) in enumerate(ann_templates):
                pub_date = datetime.now(timezone.utc) - timedelta(days=j * 15 + i * 3)
                await db.execute(text("""
                    INSERT INTO announcements (id, company_id, category_id, title, summary, exchange, published_at, discovered_at, is_material, provider)
                    VALUES (:id, :cid, :catid, :title, :summary, 'NSE', :pub, :disc, :mat, 'demo')
                """), {
                    "id": uuid.uuid4(), "cid": company_id, "catid": cat_ids.get(cat_code),
                    "title": f"Demo content — {title_tmpl}",
                    "summary": f"Demo content — not an exchange filing. {title_tmpl} for {comp_data['name']}.",
                    "pub": pub_date, "disc": pub_date, "mat": material,
                })

            # Create ingestion job (for admin view)
            await db.execute(text("""
                INSERT INTO ingestion_jobs (id, job_type, company_id, status, pipeline_stage, attempts)
                VALUES (:id, 'seed_data', :cid, 'completed', 'PUBLISHED', 1)
            """), {"id": uuid.uuid4(), "cid": company_id})

        await db.commit()
        print(f"Seeded {len(DEMO_COMPANIES)} companies with financials, documents, concalls, and announcements.")
        print(f"Demo user: {settings.demo_user_email} / {settings.demo_user_password}")
        print(f"Admin user: admin@researchos.dev / admin123456")


def run():
    asyncio.run(seed_all())


if __name__ == "__main__":
    run()

"""Seed script — Generate dummy financials, announcements, etc. for existing companies."""

import asyncio
import uuid
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import get_settings

settings = get_settings()

async def seed_fake_info():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as db:
        print("Fetching existing companies...")
        result = await db.execute(text("SELECT id, name FROM companies"))
        companies = result.fetchall()
        
        if not companies:
            print("No companies found. Please run real_data.py first.")
            return

        print("Fetching metrics and categories...")
        result = await db.execute(text("SELECT code, id FROM standard_metrics"))
        metric_ids = {row[0]: row[1] for row in result.fetchall()}
        
        result = await db.execute(text("SELECT code, id FROM announcement_categories"))
        cat_ids = {row[0]: row[1] for row in result.fetchall()}
        
        result = await db.execute(text("SELECT id FROM data_licences WHERE provider = 'demo'"))
        licence_id = result.scalar()
        if not licence_id:
            licence_id = uuid.uuid4()
            await db.execute(text("""
                INSERT INTO data_licences (id, provider, dataset, licence_type, internal_use_allowed, display_allowed,
                    derived_data_allowed, export_allowed, api_delivery_allowed, ai_processing_allowed, document_retention_allowed)
                VALUES (:id, 'demo', 'synthetic', 'internal', true, true, true, true, true, true, true)
            """), {"id": licence_id})

        random.seed(42)  # Deterministic
        today = date.today()

        for idx, comp in enumerate(companies):
            company_id = comp[0]
            comp_name = comp[1]
            print(f"Generating dummy info for {comp_name}...")
            
            base_rev = 50000 + random.randint(10000, 100000)

            # Create financial periods (8 quarters)
            for q in range(8):
                fy = 2026 if q < 4 else 2025
                quarter = (q % 4) + 1
                q_start_month = {1: 4, 2: 7, 3: 10, 4: 1}[quarter]
                q_start_year = fy if quarter != 4 else fy + 1
                if quarter == 4:
                    q_start_year = fy
                    q_start_month = 1

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
                    if metric_code in metric_ids:
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
                       "title": f"Demo content — Q{4-q} FY{2026} Results - {comp_name}"})

                await db.execute(text("""
                    INSERT INTO document_versions (id, document_id, version_number, processing_status, mime_type, licence_id)
                    VALUES (:id, :did, 1, 'PUBLISHED', 'application/pdf', :lid)
                """), {"id": dv_id, "did": doc_id, "lid": licence_id})

                # Document section
                await db.execute(text("""
                    INSERT INTO document_sections (id, document_version_id, section_type, title, content, sequence)
                    VALUES (:id, :dvid, 'financial_results', :title, :content, 0)
                """), {"id": uuid.uuid4(), "dvid": dv_id,
                       "title": f"Financial Results Q{4-q} FY2026",
                       "content": f"Demo content — not an exchange filing. {comp_name} reported quarterly results with revenue growth and margin expansion."})

            # Create concall events with transcripts
            for q in range(4):
                concall_id = uuid.uuid4()
                scheduled = datetime(2026, {0:8, 1:5, 2:2, 3:11}[q], 15, 16, 0, tzinfo=timezone.utc)
                status = "completed" if q > 0 else "scheduled"

                await db.execute(text("""
                    INSERT INTO concall_events (id, company_id, title, event_type, scheduled_at, status, source)
                    VALUES (:id, :cid, :title, 'earnings_call', :sa, :status, 'demo')
                """), {"id": concall_id, "cid": company_id,
                       "title": f"Demo content — Q{4-q} FY2026 Earnings Call - {comp_name}",
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
                        ("CEO", "Managing Director & CEO", "prepared_remarks", f"Demo content — not an exchange filing. Thank you. We are pleased to report strong performance this quarter. {comp_name} achieved robust revenue growth driven by volume expansion and market share gains."),
                        ("CFO", "Chief Financial Officer", "prepared_remarks", "Demo content — not an exchange filing. Revenue for the quarter grew significantly year-over-year. EBITDA margins expanded by approximately 200 basis points due to operating leverage and cost optimization initiatives."),
                        ("Analyst 1", "Analyst, Demo Securities", "qa_question", "Demo content — not an exchange filing. Can you provide more color on the margin expansion drivers and sustainability?"),
                        ("CFO", "Chief Financial Officer", "qa_answer", "Demo content — not an exchange filing. The margin improvement is driven by better product mix, operating leverage, and ongoing cost optimization programs. We expect margins to remain stable."),
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
                (f"Demo content — {comp_name} wins major order worth ₹500 Cr", "order_win", True),
                ("Outcome of Board Meeting - Financial Results approved", "financial_results", True),
                ("Annual General Meeting notice", "agm", False),
                ("Change in key managerial personnel", "management_change", True),
            ]
            for j, (title_tmpl, cat_code, material) in enumerate(ann_templates):
                if cat_code in cat_ids:
                    pub_date = datetime.now(timezone.utc) - timedelta(days=j * 15 + idx * 3)
                    await db.execute(text("""
                        INSERT INTO announcements (id, company_id, category_id, title, summary, exchange, published_at, discovered_at, is_material, provider)
                        VALUES (:id, :cid, :catid, :title, :summary, 'NSE', :pub, :disc, :mat, 'demo')
                    """), {
                        "id": uuid.uuid4(), "cid": company_id, "catid": cat_ids.get(cat_code),
                        "title": f"Demo content — {title_tmpl}",
                        "summary": f"Demo content — not an exchange filing. {title_tmpl} for {comp_name}.",
                        "pub": pub_date, "disc": pub_date, "mat": material,
                    })
            
            await db.commit()

    print("Dummy info seeded for existing companies.")

if __name__ == "__main__":
    asyncio.run(seed_fake_info())

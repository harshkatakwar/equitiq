# ResearchOS — Product Requirements Document

## 1. Product Vision

ResearchOS is an Indian-equity research platform enabling investors to search companies, view financials, track earnings and concalls, browse announcements, create watchlists, screen stocks, and leverage AI-generated summaries with verified citations.

## 2. Target Users

- Retail equity investors researching Indian-listed companies
- Independent research analysts
- Small advisory firms
- Investment clubs

## 3. Core Capabilities

### 3.1 Company Intelligence
- Search 6,000–8,000 NSE/BSE-listed companies by name, symbol, ISIN
- View quarterly and annual financial statements (P&L, Balance Sheet, Cash Flow)
- Examine ratios, growth, and valuation metrics
- Track earnings-result dates and conference calls
- Browse corporate announcements and filings

### 3.2 Research Tools
- Configurable watchlists with financial columns
- Financial screener with typed filter expressions
- Idea Discovery Board classifying material announcements
- Earnings calendar and concall calendar

### 3.3 AI Research
- AI-generated concall summaries with citations
- AI-generated annual-report summaries
- AI-generated company overviews
- Document chat (RAG) across transcripts and filings
- Every AI claim verified against source documents

### 3.4 Data Integrity
- Point-in-time versioning for all financial facts and documents
- Append-only data model — no silent overwrites
- Data-licensing registry enforcing display/export/redistribution rights
- Clear separation of reported facts, calculated values, and AI interpretations

### 3.5 Subscription Management
- Four tiers: Starter, Professional, Research Monthly, Research Annual
- Entitlement-based feature access with configurable limits
- Atomic usage tracking with idempotency

## 4. Data Modes

| Mode | Description |
|------|-------------|
| `demo` | Synthetic data for 10 companies, no external dependencies |
| `official` | Legally permitted access to NSE, BSE, company IR sites |
| `licensed` | Commercial data feeds via provider interfaces |

## 5. Capacity Requirements

- 6,000–8,000 listed companies
- 10,000 MAU initially
- 100–300 concurrent users
- 1M documents eventually
- 50,000 AI operations/month

## 6. Performance Targets

- 99.9% availability
- RPO: 15 minutes, RTO: 4 hours
- P95 read API: <400ms
- P95 search: <500ms
- Announcements within 15 min of discovery

## 7. Clean-Room Requirements

- Original UI design, terminology, and implementation
- No copied source code, APIs, HTML, CSS, or assets from competitors
- No scraping of Concall.in or Screener.in
- Synthetic demo data only
- Data provenance tracked throughout

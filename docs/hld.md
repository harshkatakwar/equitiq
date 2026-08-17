# ResearchOS — High-Level Design

## 1. Architecture Overview

ResearchOS is a **modular monolith** with asynchronous workers, designed for eventual service extraction.

```mermaid
graph TB
    subgraph "Client Layer"
        WEB["Next.js Web App"]
    end

    subgraph "API Layer"
        NGINX["Nginx Reverse Proxy"]
        API["FastAPI Application"]
    end

    subgraph "Worker Layer"
        CELERY["Celery Workers"]
        BEAT["Celery Beat Scheduler"]
    end

    subgraph "Data Layer"
        PG["PostgreSQL 16<br/>pgvector + pg_trgm"]
        REDIS["Redis<br/>Cache + Broker"]
        MINIO["MinIO / S3<br/>Object Storage"]
    end

    subgraph "External"
        AI["AI Providers<br/>OpenAI-compatible"]
        DATA["Data Providers<br/>NSE/BSE/Licensed"]
    end

    WEB --> NGINX
    NGINX --> API
    NGINX --> WEB
    API --> PG
    API --> REDIS
    API --> MINIO
    CELERY --> PG
    CELERY --> REDIS
    CELERY --> MINIO
    CELERY --> AI
    CELERY --> DATA
    BEAT --> REDIS
```

## 2. Module Architecture

```mermaid
graph LR
    subgraph "Core Modules"
        IDENTITY["identity"]
        COMPANIES["companies"]
        MARKET["market_data"]
        FIN["financials"]
    end

    subgraph "Content Modules"
        DOCS["documents"]
        CONCALLS["concalls"]
        ANN["announcements"]
    end

    subgraph "Research Modules"
        WATCH["watchlists"]
        SCREEN["screening"]
        AI_RES["ai_research"]
    end

    subgraph "Platform Modules"
        SUBS["subscriptions"]
        LIC["licensing"]
        INGEST["ingestion"]
        ADMIN["administration"]
        AUDIT["audit"]
    end

    COMPANIES --> IDENTITY
    MARKET --> COMPANIES
    FIN --> COMPANIES
    DOCS --> COMPANIES
    CONCALLS --> COMPANIES
    ANN --> COMPANIES
    WATCH --> COMPANIES
    WATCH --> IDENTITY
    WATCH --> SUBS
    SCREEN --> FIN
    AI_RES --> DOCS
    AI_RES --> CONCALLS
    AI_RES --> SUBS
    INGEST --> DOCS
    ADMIN --> INGEST
```

### Module Responsibilities

| Module | Owns | Key Operations |
|--------|------|----------------|
| `identity` | Users, Orgs, Roles, Sessions | Auth, RBAC |
| `companies` | Company, Security, Exchange, Identifiers | Search, company profiles |
| `market_data` | Prices, Corporate Actions | EOD price ingestion |
| `financials` | Periods, Statements, Facts, Metrics | Versioned financial data |
| `documents` | Documents, Versions, Sections, Filings | Document lifecycle |
| `concalls` | Events, Transcripts, Segments | Concall tracking |
| `announcements` | Announcements, Categories, Ideas | Feed and classification |
| `watchlists` | Watchlists, WatchlistCompanies | User watchlist management |
| `screening` | Filters, Executions | Financial screening |
| `ai_research` | AIArtifacts, Claims, Citations, Chat | AI generation and verification |
| `subscriptions` | Plans, Subscriptions, Entitlements, Usage | Billing and limits |
| `licensing` | DataLicences | Rights enforcement |
| `ingestion` | IngestionJobs | Pipeline orchestration |
| `administration` | — | Admin operations |
| `audit` | AuditEvents | Compliance logging |

## 3. Request Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant N as Nginx
    participant A as FastAPI
    participant DB as PostgreSQL
    participant R as Redis
    participant W as Celery Worker
    participant S3 as MinIO/S3
    participant AI as AI Provider

    U->>N: GET /api/v1/companies/search?q=reliance
    N->>A: Proxy request
    A->>DB: pg_trgm fuzzy search
    DB-->>A: Company results
    A-->>N: JSON response
    N-->>U: Search results

    U->>N: POST /api/v1/ai/concall-summary
    N->>A: Proxy request
    A->>DB: Check entitlements + usage
    A->>R: Enqueue AI job
    A-->>U: 202 Accepted {job_id}
    W->>R: Dequeue job
    W->>S3: Fetch transcript
    W->>AI: Generate summary
    W->>DB: Store AIArtifact + Claims
    W->>DB: Verify citations
    W->>DB: Update job status → PUBLISHED
```

## 4. Data Flow

```mermaid
graph TD
    subgraph "Ingestion"
        DISC["Discover"] --> DL["Download"]
        DL --> VAL["Validate + Checksum"]
        VAL --> DEDUP["Deduplicate"]
        DEDUP --> STORE["Store Original → S3"]
        STORE --> PARSE["Parse Text + Tables"]
        PARSE --> OCR{"OCR Needed?"}
        OCR -->|Yes| OCRP["OCR Processing"]
        OCR -->|No| NORM["Normalize Metadata"]
        OCRP --> NORM
        NORM --> SPLIT["Split Sections"]
        SPLIT --> EXTRACT["Extract Facts"]
        EXTRACT --> INDEX["Search Index"]
        INDEX --> EMBED["Create Embeddings"]
        EMBED --> AIGEN["AI Generation"]
        AIGEN --> CITE["Verify Citations"]
        CITE --> PUB["Publish"]
    end
```

## 5. Deployment Topology (Production)

```mermaid
graph TB
    subgraph "CDN / Edge"
        CF["CDN"]
    end

    subgraph "Compute"
        LB["Load Balancer"]
        API1["API Instance 1"]
        API2["API Instance 2"]
        W1["Worker Instance 1"]
        W2["Worker Instance 2"]
        WEB1["Next.js Instance"]
    end

    subgraph "Data"
        PG_PRIMARY["PostgreSQL Primary"]
        PG_REPLICA["PostgreSQL Replica"]
        REDIS_C["Redis Cluster"]
        S3_B["S3 Bucket"]
    end

    CF --> LB
    LB --> API1
    LB --> API2
    LB --> WEB1
    API1 --> PG_PRIMARY
    API2 --> PG_PRIMARY
    PG_PRIMARY --> PG_REPLICA
    W1 --> PG_PRIMARY
    W2 --> PG_PRIMARY
    API1 --> REDIS_C
    W1 --> REDIS_C
    W1 --> S3_B
```

## 6. Security Architecture

- Passwords: bcrypt hashing
- Sessions: JWT + HTTP-only cookies
- Authorization: Server-side RBAC on every request
- Tenant isolation: `user_id` / `organization_id` on private records
- API: Rate limiting, request IDs, parameterized SQL only
- Files: Upload validation, size limits, signed URLs
- Webhooks: Signature verification
- Logging: No PII, passwords, tokens, or payment data

## 7. Technology Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Radix UI |
| Data Fetching | TanStack Query, OpenAPI-generated client |
| Forms | React Hook Form + Zod |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 + pgvector + pg_trgm |
| Migrations | Alembic |
| Cache/Broker | Redis 7 |
| Workers | Celery 5 |
| Object Storage | MinIO (dev) / S3 (prod) |
| Testing | Pytest, Vitest, Playwright |
| Infrastructure | Docker Compose (dev), IaC stubs (prod) |

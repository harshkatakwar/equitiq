# ResearchOS

Indian-equity research platform for investors. Search companies, view financials, track earnings and concalls, create watchlists, screen stocks, and leverage AI-powered research with verified citations.

## Quick Start

```bash
# Clone and start all services
cp .env.example .env
docker compose up --build

# Access the application
# Web UI:    http://localhost:3000
# API:       http://localhost:8000
# API Docs:  http://localhost:8000/docs
# MinIO:     http://localhost:9001

# Demo credentials
# Email:    demo@researchos.dev
# Password: demo123456
```

## Architecture

- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend**: FastAPI + SQLAlchemy 2 + Pydantic v2
- **Workers**: Celery + Redis
- **Database**: PostgreSQL 16 (pgvector + pg_trgm)
- **Storage**: MinIO (S3-compatible)
- **Cache/Broker**: Redis 7

## Project Structure

```
apps/
  web/          # Next.js frontend
  api/          # FastAPI backend
  worker/       # Celery workers
packages/
  ui/           # Shared React components
  config/       # Shared configs
infra/          # Docker, nginx configs
docs/           # Architecture docs
```

## Development Commands

```bash
# Full stack
docker compose up --build

# Run migrations
docker compose exec api alembic upgrade head

# Seed demo data
docker compose exec api python -m seeds.run

# Run backend tests
docker compose exec api pytest

# Run frontend tests
docker compose exec web npm test

# Lint
docker compose exec api ruff check .
docker compose exec web npm run lint

# Type check
docker compose exec api mypy src/
docker compose exec web npm run typecheck
```

## Data Modes

| Mode | Env Value | Description |
|------|-----------|-------------|
| Demo | `DATA_MODE=demo` | Synthetic data, no external deps |
| Official | `DATA_MODE=official` | Public exchange data |
| Licensed | `DATA_MODE=licensed` | Commercial feeds |

## Documentation

- [Product Requirements](docs/product-requirements.md)
- [High-Level Design](docs/hld.md)
- [Low-Level Design](docs/lld.md)
- [Data Sources](docs/data-sources.md)
- [Data Licensing](docs/data-licensing.md)
- [AI Architecture](docs/ai-architecture.md)

## License

Proprietary. All rights reserved.

"""Alembic environment configuration."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import Base

# Import all models so they register with Base.metadata
from src.modules.identity.models import User, Organization, OrganizationMember, Session
from src.modules.companies.models import Exchange, Company, Security, IdentifierHistory
from src.modules.market_data.models import MarketPrice, CorporateAction
from src.modules.financials.models import StandardMetric, FinancialPeriod, FinancialStatement, FinancialFact
from src.modules.documents.models import Filing, Document, DocumentVersion, DocumentSection
from src.modules.concalls.models import ConcallEvent, Transcript, TranscriptSegment
from src.modules.announcements.models import AnnouncementCategory, Announcement, AnnouncementIdea
from src.modules.watchlists.router import Watchlist, WatchlistCompany
from src.modules.subscriptions.models import Plan, Entitlement, Subscription, UsageLedger
from src.modules.ai_research.models import AIArtifact, AIClaim, SourceCitation, ChatConversation, ChatMessage
from src.modules.licensing.models import DataLicence
from src.modules.ingestion.models import IngestionJob
from src.modules.audit.models import AuditEvent

config = context.config

# Override sqlalchemy.url from environment
database_url = os.environ.get("DATABASE_URL_SYNC") or os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    elif database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

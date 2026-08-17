"""Initial migration — Create all tables.

Revision ID: 001_initial
Revises: None
Create Date: 2026-08-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # Users
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(100)),
        sa.Column('role', sa.String(20), server_default='user'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('email_verified', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Organizations
    op.create_table('organizations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Organization Members
    op.create_table('organization_members',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(20), server_default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Sessions
    op.create_table('sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Exchanges
    op.create_table('exchanges',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(10), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('country', sa.String(2), server_default='IN'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Companies
    op.create_table('companies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('slug', sa.String(300), unique=True, nullable=False),
        sa.Column('isin', sa.String(12)),
        sa.Column('sector', sa.String(100)),
        sa.Column('industry', sa.String(100)),
        sa.Column('description', sa.Text()),
        sa.Column('founded_year', sa.Integer()),
        sa.Column('headquarters', sa.String(200)),
        sa.Column('website', sa.String(500)),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_companies_name_trgm', 'companies', ['name'], postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('ix_companies_sector', 'companies', ['sector'])
    op.create_index('ix_companies_isin', 'companies', ['isin'])

    # Securities
    op.create_table('securities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('exchange_id', UUID(as_uuid=True), sa.ForeignKey('exchanges.id'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('listing_date', sa.Date()),
        sa.Column('delisting_date', sa.Date()),
    )
    op.create_index('ix_securities_symbol', 'securities', ['symbol'])
    op.create_index('ix_securities_symbol_trgm', 'securities', ['symbol'], postgresql_using='gin', postgresql_ops={'symbol': 'gin_trgm_ops'})

    # Identifier History
    op.create_table('identifier_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('identifier_type', sa.String(20), nullable=False),
        sa.Column('old_value', sa.String(300)),
        sa.Column('new_value', sa.String(300)),
        sa.Column('effective_date', sa.Date()),
        sa.Column('source', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Market Prices
    op.create_table('market_prices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('security_id', UUID(as_uuid=True), sa.ForeignKey('securities.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(18, 4)),
        sa.Column('high', sa.Numeric(18, 4)),
        sa.Column('low', sa.Numeric(18, 4)),
        sa.Column('close', sa.Numeric(18, 4)),
        sa.Column('volume', sa.BigInteger()),
        sa.Column('market_cap', sa.Numeric(20, 2)),
        sa.Column('source', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_market_prices_security_date', 'market_prices', ['security_id', 'date'], unique=True)

    # Corporate Actions
    op.create_table('corporate_actions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('ex_date', sa.Date()),
        sa.Column('record_date', sa.Date()),
        sa.Column('details', JSONB()),
        sa.Column('source', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Standard Metrics
    op.create_table('standard_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('unit_type', sa.String(20), nullable=False),
        sa.Column('statement_type', sa.String(20), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Financial Periods
    op.create_table('financial_periods',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('period_type', sa.String(10), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('fiscal_quarter', sa.Integer()),
        sa.Column('standalone_or_consolidated', sa.String(15), server_default='standalone'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('company_id', 'period_type', 'period_start', 'period_end', 'standalone_or_consolidated', name='uq_financial_period'),
    )

    # Data Licences (needed for FK from document_versions)
    op.create_table('data_licences',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('dataset', sa.String(100), nullable=False),
        sa.Column('licence_type', sa.String(30), nullable=False),
        sa.Column('internal_use_allowed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('display_allowed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('derived_data_allowed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('redistribution_allowed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('export_allowed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('api_delivery_allowed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('ai_processing_allowed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('ai_training_allowed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('document_retention_allowed', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('allowed_channels', ARRAY(sa.String(50))),
        sa.Column('allowed_regions', ARRAY(sa.String(10))),
        sa.Column('contract_start', sa.Date()),
        sa.Column('contract_expiry', sa.Date()),
        sa.Column('attribution_required', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('terms_url', sa.String(2000)),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Filings
    op.create_table('filings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('filing_type', sa.String(50), nullable=False),
        sa.Column('filing_date', sa.Date()),
        sa.Column('source_url', sa.String(2000)),
        sa.Column('provider', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Documents
    op.create_table('documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('filing_id', UUID(as_uuid=True), sa.ForeignKey('filings.id')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Document Versions
    op.create_table('document_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('version_number', sa.Integer(), server_default='1'),
        sa.Column('supersedes_document_version_id', UUID(as_uuid=True), sa.ForeignKey('document_versions.id')),
        sa.Column('source_url', sa.String(2000)),
        sa.Column('provider', sa.String(100)),
        sa.Column('publication_timestamp', sa.DateTime(timezone=True)),
        sa.Column('retrieval_timestamp', sa.DateTime(timezone=True)),
        sa.Column('financial_period_id', UUID(as_uuid=True), sa.ForeignKey('financial_periods.id')),
        sa.Column('sha256_checksum', sa.String(64)),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('storage_key', sa.String(500)),
        sa.Column('file_size_bytes', sa.BigInteger()),
        sa.Column('processing_status', sa.String(30), server_default='DISCOVERED'),
        sa.Column('extraction_status', sa.String(30)),
        sa.Column('licence_id', UUID(as_uuid=True), sa.ForeignKey('data_licences.id')),
        sa.Column('page_count', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Financial Statements
    op.create_table('financial_statements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('financial_period_id', UUID(as_uuid=True), sa.ForeignKey('financial_periods.id'), nullable=False),
        sa.Column('statement_type', sa.String(20), nullable=False),
        sa.Column('source_document_version_id', UUID(as_uuid=True), sa.ForeignKey('document_versions.id')),
        sa.Column('publication_timestamp', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Financial Facts
    op.create_table('financial_facts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('financial_statement_id', UUID(as_uuid=True), sa.ForeignKey('financial_statements.id')),
        sa.Column('standard_metric_id', UUID(as_uuid=True), sa.ForeignKey('standard_metrics.id'), nullable=False),
        sa.Column('original_label', sa.String(500)),
        sa.Column('value', sa.Numeric(20, 4), nullable=False),
        sa.Column('unit', sa.String(20)),
        sa.Column('currency', sa.String(3), server_default='INR'),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('period_type', sa.String(10), nullable=False),
        sa.Column('standalone_or_consolidated', sa.String(15), server_default='standalone'),
        sa.Column('publication_timestamp', sa.DateTime(timezone=True)),
        sa.Column('known_from', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('known_until', sa.DateTime(timezone=True)),
        sa.Column('source_document_version_id', UUID(as_uuid=True), sa.ForeignKey('document_versions.id')),
        sa.Column('source_page', sa.Integer()),
        sa.Column('source_location', sa.String(200)),
        sa.Column('extraction_confidence', sa.Numeric(5, 4)),
        sa.Column('version_number', sa.Integer(), server_default='1'),
        sa.Column('supersedes_financial_fact_id', UUID(as_uuid=True), sa.ForeignKey('financial_facts.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_financial_facts_company_metric', 'financial_facts', ['company_id', 'standard_metric_id'])
    op.create_index('ix_financial_facts_period', 'financial_facts', ['period_start', 'period_end'])

    # Document Sections (with pgvector)
    op.create_table('document_sections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_version_id', UUID(as_uuid=True), sa.ForeignKey('document_versions.id'), nullable=False),
        sa.Column('section_type', sa.String(50)),
        sa.Column('title', sa.String(500)),
        sa.Column('content', sa.Text()),
        sa.Column('page_start', sa.Integer()),
        sa.Column('page_end', sa.Integer()),
        sa.Column('sequence', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.execute('ALTER TABLE document_sections ADD COLUMN embedding vector(1536)')

    # Concall Events
    op.create_table('concall_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('event_type', sa.String(30), server_default='earnings_call'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True)),
        sa.Column('actual_start', sa.DateTime(timezone=True)),
        sa.Column('actual_end', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(20), server_default='scheduled'),
        sa.Column('financial_period_id', UUID(as_uuid=True), sa.ForeignKey('financial_periods.id')),
        sa.Column('recording_url', sa.String(2000)),
        sa.Column('presentation_document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id')),
        sa.Column('source', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Transcripts
    op.create_table('transcripts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('concall_event_id', UUID(as_uuid=True), sa.ForeignKey('concall_events.id'), nullable=False),
        sa.Column('document_version_id', UUID(as_uuid=True), sa.ForeignKey('document_versions.id')),
        sa.Column('source_type', sa.String(30), server_default='official'),
        sa.Column('language', sa.String(10), server_default='en'),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Transcript Segments (with pgvector)
    op.create_table('transcript_segments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('transcript_id', UUID(as_uuid=True), sa.ForeignKey('transcripts.id'), nullable=False),
        sa.Column('speaker_name', sa.String(200)),
        sa.Column('speaker_role', sa.String(200)),
        sa.Column('sequence', sa.Integer(), server_default='0'),
        sa.Column('timestamp_start', sa.String(20)),
        sa.Column('timestamp_end', sa.String(20)),
        sa.Column('segment_type', sa.String(30), server_default='prepared_remarks'),
        sa.Column('text', sa.Text()),
        sa.Column('confidence', sa.Numeric(5, 4)),
        sa.Column('source_reference', sa.String(200)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.execute('ALTER TABLE transcript_segments ADD COLUMN embedding vector(1536)')

    # Announcement Categories
    op.create_table('announcement_categories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Announcements
    op.create_table('announcements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('announcement_categories.id')),
        sa.Column('title', sa.String(1000), nullable=False),
        sa.Column('content', sa.Text()),
        sa.Column('summary', sa.Text()),
        sa.Column('source_url', sa.String(2000)),
        sa.Column('exchange', sa.String(10)),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('discovered_at', sa.DateTime(timezone=True)),
        sa.Column('is_material', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('materiality_reason', sa.Text()),
        sa.Column('materiality_confidence', sa.Numeric(5, 4)),
        sa.Column('provider', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_announcements_company_date', 'announcements', ['company_id', 'published_at'])

    # Announcement Ideas
    op.create_table('announcement_ideas',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('announcement_id', UUID(as_uuid=True), sa.ForeignKey('announcements.id'), nullable=False),
        sa.Column('idea_type', sa.String(50), nullable=False),
        sa.Column('explanation', sa.Text()),
        sa.Column('evidence', sa.Text()),
        sa.Column('confidence', sa.Numeric(5, 4)),
        sa.Column('analyst_correction', sa.String(50)),
        sa.Column('corrected_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('corrected_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Watchlists
    op.create_table('watchlists',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Watchlist Companies
    op.create_table('watchlist_companies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('watchlist_id', UUID(as_uuid=True), sa.ForeignKey('watchlists.id'), nullable=False),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('notes', sa.Text()),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Plans
    op.create_table('plans',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('price_monthly', sa.Numeric(10, 2)),
        sa.Column('price_annual', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), server_default='INR'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Entitlements
    op.create_table('entitlements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plan_id', UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=False),
        sa.Column('feature_key', sa.String(100), nullable=False),
        sa.Column('limit_value', sa.Integer()),
        sa.Column('period', sa.String(10)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Subscriptions
    op.create_table('subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('plan_id', UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=False),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('payment_provider', sa.String(50)),
        sa.Column('external_subscription_id', sa.String(200)),
        sa.Column('current_period_start', sa.Date()),
        sa.Column('current_period_end', sa.Date()),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Usage Ledger
    op.create_table('usage_ledger',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('subscription_id', UUID(as_uuid=True), sa.ForeignKey('subscriptions.id')),
        sa.Column('feature_key', sa.String(100), nullable=False),
        sa.Column('delta', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(200), unique=True),
        sa.Column('operation_type', sa.String(20), server_default='use'),
        sa.Column('reference_id', UUID(as_uuid=True)),
        sa.Column('reference_type', sa.String(50)),
        sa.Column('period_start', sa.Date()),
        sa.Column('period_end', sa.Date()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # AI Artifacts
    op.create_table('ai_artifacts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), server_default='pending'),
        sa.Column('generation_timestamp', sa.DateTime(timezone=True)),
        sa.Column('data_cutoff_date', sa.Date()),
        sa.Column('model_name', sa.String(100)),
        sa.Column('prompt_version', sa.String(20)),
        sa.Column('input_tokens', sa.Integer()),
        sa.Column('output_tokens', sa.Integer()),
        sa.Column('estimated_cost_usd', sa.Numeric(10, 6)),
        sa.Column('latency_ms', sa.Integer()),
        sa.Column('content', JSONB()),
        sa.Column('source_document_version_ids', ARRAY(UUID(as_uuid=True))),
        sa.Column('regeneration_of', UUID(as_uuid=True), sa.ForeignKey('ai_artifacts.id')),
        sa.Column('unsupported_claim_count', sa.Integer()),
        sa.Column('total_claim_count', sa.Integer()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # AI Claims
    op.create_table('ai_claims',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('ai_artifact_id', UUID(as_uuid=True), sa.ForeignKey('ai_artifacts.id'), nullable=False),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('claim_type', sa.String(50), nullable=False),
        sa.Column('section', sa.String(100)),
        sa.Column('confidence', sa.Numeric(5, 4)),
        sa.Column('verification_status', sa.String(20), server_default='pending'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Source Citations
    op.create_table('source_citations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('ai_claim_id', UUID(as_uuid=True), sa.ForeignKey('ai_claims.id'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', UUID(as_uuid=True)),
        sa.Column('source_text', sa.Text()),
        sa.Column('page_or_sequence', sa.Integer()),
        sa.Column('location', sa.String(200)),
        sa.Column('confidence', sa.Numeric(5, 4)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Chat Conversations
    op.create_table('chat_conversations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('title', sa.String(500)),
        sa.Column('document_scope', ARRAY(UUID(as_uuid=True))),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Chat Messages
    op.create_table('chat_messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('chat_conversations.id'), nullable=False),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations', JSONB()),
        sa.Column('tokens_used', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Ingestion Jobs
    op.create_table('ingestion_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id')),
        sa.Column('document_version_id', UUID(as_uuid=True), sa.ForeignKey('document_versions.id')),
        sa.Column('status', sa.String(30), server_default='pending'),
        sa.Column('pipeline_stage', sa.String(30)),
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('attempts', sa.Integer(), server_default='0'),
        sa.Column('max_attempts', sa.Integer(), server_default='3'),
        sa.Column('unique_key', sa.String(500), unique=True),
        sa.Column('input_params', JSONB()),
        sa.Column('result', JSONB()),
        sa.Column('error_message', sa.Text()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('next_retry_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Audit Events
    op.create_table('audit_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50)),
        sa.Column('resource_id', UUID(as_uuid=True)),
        sa.Column('details', JSONB()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('request_id', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # Saved Filters
    op.create_table('saved_filters',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('filter_expression', JSONB(), nullable=False),
        sa.Column('result_columns', JSONB()),
        sa.Column('sort_config', JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # Filter Executions
    op.create_table('filter_executions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('saved_filter_id', UUID(as_uuid=True), sa.ForeignKey('saved_filters.id')),
        sa.Column('filter_expression', JSONB(), nullable=False),
        sa.Column('result_count', sa.Integer()),
        sa.Column('execution_time_ms', sa.Integer()),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )


def downgrade() -> None:
    tables = [
        'filter_executions', 'saved_filters', 'audit_events', 'ingestion_jobs',
        'chat_messages', 'chat_conversations', 'source_citations', 'ai_claims', 'ai_artifacts',
        'usage_ledger', 'subscriptions', 'entitlements', 'plans',
        'watchlist_companies', 'watchlists',
        'announcement_ideas', 'announcements', 'announcement_categories',
        'transcript_segments', 'transcripts', 'concall_events',
        'document_sections', 'financial_facts', 'financial_statements', 'document_versions',
        'documents', 'filings',
        'corporate_actions', 'market_prices', 'financial_periods', 'standard_metrics',
        'data_licences',
        'identifier_history', 'securities', 'companies', 'exchanges',
        'sessions', 'organization_members', 'organizations', 'users',
    ]
    for t in tables:
        op.drop_table(t)

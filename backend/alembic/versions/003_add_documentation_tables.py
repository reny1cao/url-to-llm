"""Add documentation hosting tables

Revision ID: 003_add_documentation_tables
Revises: 002_add_crawl_jobs
Create Date: 2025-06-12 03:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_documentation_tables'
down_revision = '002_add_crawl_jobs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add tables for hosting full documentation sites."""
    
    # Create sites table
    op.create_table(
        'sites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('host', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text()),
        sa.Column('favicon_url', sa.String(1024)),
        sa.Column('language', sa.String(10), server_default='en'),
        sa.Column('crawl_settings', postgresql.JSONB(), server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_crawled_at', sa.DateTime(timezone=True)),
        sa.Column('total_pages', sa.Integer(), server_default='0'),
        sa.Column('total_size_bytes', sa.BigInteger(), server_default='0')
    )
    
    # Create pages table with optimized indexing
    op.create_table(
        'pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('path', sa.String(1024), nullable=False),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text()),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('html_storage_key', sa.String(512)),  # S3 key for HTML
        sa.Column('markdown_storage_key', sa.String(512)),  # S3 key for markdown
        sa.Column('html_size_bytes', sa.Integer()),
        sa.Column('markdown_size_bytes', sa.Integer()),
        sa.Column('extracted_text', sa.Text()),  # First 10KB for search
        sa.Column('headers', postgresql.JSONB()),  # HTTP headers
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),  # Custom metadata
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('crawled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('search_vector', postgresql.TSVECTOR())  # Full-text search vector
    )
    
    # Create indexes for pages
    op.create_index('idx_pages_site_id', 'pages', ['site_id'])
    op.create_index('idx_pages_site_path', 'pages', ['site_id', 'path'], unique=True)
    op.create_index('idx_pages_content_hash', 'pages', ['content_hash'])
    op.create_index('idx_pages_search_vector', 'pages', ['search_vector'], postgresql_using='gin')
    
    # Create site navigation table
    op.create_table(
        'site_navigation',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('site_navigation.id', ondelete='CASCADE')),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('path', sa.String(1024), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_expanded', sa.Boolean(), server_default='true'),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}')
    )
    
    # Create indexes for navigation
    op.create_index('idx_navigation_site_id', 'site_navigation', ['site_id'])
    op.create_index('idx_navigation_parent', 'site_navigation', ['parent_id'])
    op.create_index('idx_navigation_order', 'site_navigation', ['site_id', 'parent_id', 'order_index'])
    
    # Create assets table
    op.create_table(
        'assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('path', sa.String(1024), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('storage_key', sa.String(512), nullable=False),  # S3 key
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Create indexes for assets
    op.create_index('idx_assets_site_id', 'assets', ['site_id'])
    op.create_index('idx_assets_site_path', 'assets', ['site_id', 'path'], unique=True)
    op.create_index('idx_assets_content_hash', 'assets', ['content_hash'])
    
    # Create page_links table for tracking internal links
    op.create_table(
        'page_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('from_page_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('to_page_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('link_text', sa.String(255)),
        sa.Column('link_context', sa.Text())
    )
    
    # Create indexes for page links
    op.create_index('idx_page_links_from', 'page_links', ['from_page_id'])
    op.create_index('idx_page_links_to', 'page_links', ['to_page_id'])
    
    # Create crawl_history table for tracking changes
    op.create_table(
        'crawl_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('crawl_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crawl_jobs.id'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('pages_added', sa.Integer(), server_default='0'),
        sa.Column('pages_updated', sa.Integer(), server_default='0'),
        sa.Column('pages_deleted', sa.Integer(), server_default='0'),
        sa.Column('errors', postgresql.JSONB(), server_default='[]'),
        sa.Column('stats', postgresql.JSONB(), server_default='{}')
    )
    
    # Create index for crawl history
    op.create_index('idx_crawl_history_site', 'crawl_history', ['site_id', 'started_at'])
    
    # Add trigger to update search vectors
    op.execute("""
        CREATE OR REPLACE FUNCTION update_page_search_vector()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.extracted_text, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER page_search_vector_update
        BEFORE INSERT OR UPDATE OF title, description, extracted_text
        ON pages
        FOR EACH ROW
        EXECUTE FUNCTION update_page_search_vector();
    """)
    
    # Add updated_at trigger for sites
    op.execute("""
        CREATE TRIGGER update_sites_updated_at
        BEFORE UPDATE ON sites
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Remove documentation hosting tables."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS page_search_vector_update ON pages")
    op.execute("DROP TRIGGER IF EXISTS update_sites_updated_at ON sites")
    op.execute("DROP FUNCTION IF EXISTS update_page_search_vector()")
    
    # Drop tables in reverse order due to foreign keys
    op.drop_table('crawl_history')
    op.drop_table('page_links')
    op.drop_table('assets')
    op.drop_table('site_navigation')
    op.drop_table('pages')
    op.drop_table('sites')
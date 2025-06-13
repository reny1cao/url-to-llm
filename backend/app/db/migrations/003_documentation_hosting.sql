-- Documentation hosting schema
-- Adds tables for storing and serving complete documentation sites
-- PostgreSQL 14+

-- Create sites table for documentation websites
CREATE TABLE IF NOT EXISTS sites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    host VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(255),
    description TEXT,
    favicon_url VARCHAR(1024),
    language VARCHAR(10) DEFAULT 'en',
    crawl_settings JSONB DEFAULT '{}' NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_crawled_at TIMESTAMP WITH TIME ZONE,
    total_pages INTEGER DEFAULT 0 NOT NULL,
    total_size_bytes BIGINT DEFAULT 0 NOT NULL,
    CONSTRAINT host_valid CHECK (host ~* '^[a-z0-9.-]+$')
);

-- Create pages table for individual documentation pages
CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    path VARCHAR(1024) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    content_hash VARCHAR(64) NOT NULL,
    html_storage_key VARCHAR(512),
    markdown_storage_key VARCHAR(512),
    html_size_bytes INTEGER,
    markdown_size_bytes INTEGER,
    extracted_text TEXT, -- First 10KB for search
    headers JSONB,
    metadata JSONB DEFAULT '{}' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    crawled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    search_vector tsvector,
    CONSTRAINT unique_site_path UNIQUE (site_id, path)
);

-- Create site navigation table for hierarchical structure
CREATE TABLE IF NOT EXISTS site_navigation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES site_navigation(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    path VARCHAR(1024) NOT NULL,
    order_index INTEGER DEFAULT 0 NOT NULL,
    level INTEGER DEFAULT 0 NOT NULL,
    is_expanded BOOLEAN DEFAULT true NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL
);

-- Create assets table for images and files
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    path VARCHAR(1024) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    size_bytes BIGINT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT unique_site_asset_path UNIQUE (site_id, path)
);

-- Create page links table for tracking internal links
CREATE TABLE IF NOT EXISTS page_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    to_page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    link_text VARCHAR(255),
    link_context TEXT,
    CONSTRAINT unique_page_link UNIQUE (from_page_id, to_page_id)
);

-- Create crawl history table for tracking changes
CREATE TABLE IF NOT EXISTS crawl_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    crawl_job_id UUID, -- References crawl_jobs(id) when using job system
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    pages_added INTEGER DEFAULT 0 NOT NULL,
    pages_updated INTEGER DEFAULT 0 NOT NULL,
    pages_deleted INTEGER DEFAULT 0 NOT NULL,
    errors JSONB DEFAULT '[]' NOT NULL,
    stats JSONB DEFAULT '{}' NOT NULL
);

-- Create indexes for performance
CREATE INDEX idx_sites_host ON sites(host);
CREATE INDEX idx_sites_is_active ON sites(is_active);

CREATE INDEX idx_pages_site_id ON pages(site_id);
CREATE INDEX idx_pages_site_path ON pages(site_id, path);
CREATE INDEX idx_pages_content_hash ON pages(content_hash);
CREATE INDEX idx_pages_search_vector ON pages USING gin(search_vector);
CREATE INDEX idx_pages_is_active ON pages(is_active);

CREATE INDEX idx_navigation_site_id ON site_navigation(site_id);
CREATE INDEX idx_navigation_parent ON site_navigation(parent_id);
CREATE INDEX idx_navigation_order ON site_navigation(site_id, parent_id, order_index);

CREATE INDEX idx_assets_site_id ON assets(site_id);
CREATE INDEX idx_assets_site_path ON assets(site_id, path);
CREATE INDEX idx_assets_content_hash ON assets(content_hash);

CREATE INDEX idx_page_links_from ON page_links(from_page_id);
CREATE INDEX idx_page_links_to ON page_links(to_page_id);

CREATE INDEX idx_crawl_history_site ON crawl_history(site_id, started_at DESC);

-- Create function to update search vectors
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

-- Create trigger for search vector updates
CREATE TRIGGER page_search_vector_update
BEFORE INSERT OR UPDATE OF title, description, extracted_text
ON pages
FOR EACH ROW
EXECUTE FUNCTION update_page_search_vector();

-- Add updated_at triggers
CREATE TRIGGER update_sites_updated_at BEFORE UPDATE ON sites
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pages_updated_at BEFORE UPDATE ON pages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE sites IS 'Documentation websites being hosted';
COMMENT ON TABLE pages IS 'Individual documentation pages with content stored in S3';
COMMENT ON TABLE site_navigation IS 'Hierarchical navigation structure for documentation';
COMMENT ON TABLE assets IS 'Static assets (images, files) used in documentation';
COMMENT ON TABLE page_links IS 'Internal links between documentation pages';
COMMENT ON TABLE crawl_history IS 'History of crawl operations with change tracking';

COMMENT ON COLUMN pages.extracted_text IS 'First 10KB of extracted text for search indexing';
COMMENT ON COLUMN pages.search_vector IS 'Full-text search vector (automatically maintained)';
COMMENT ON COLUMN site_navigation.level IS 'Depth in navigation tree (0 = root level)';
COMMENT ON COLUMN assets.storage_key IS 'S3/MinIO key for asset storage';
COMMENT ON COLUMN crawl_history.stats IS 'Detailed statistics about the crawl operation';
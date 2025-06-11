-- Create job status enum
CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

-- Create job type enum
CREATE TYPE job_type AS ENUM ('crawl', 'manifest_generation', 'scheduled_crawl');

-- Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type job_type NOT NULL DEFAULT 'crawl',
    status job_status NOT NULL DEFAULT 'pending',
    host VARCHAR(255) NOT NULL,
    max_pages INTEGER NOT NULL DEFAULT 100,
    follow_links BOOLEAN NOT NULL DEFAULT true,
    respect_robots_txt BOOLEAN NOT NULL DEFAULT true,
    
    -- Task metadata
    celery_task_id VARCHAR(255),
    queue_name VARCHAR(50) NOT NULL DEFAULT 'crawler',
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    
    -- Progress tracking
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    pages_discovered INTEGER NOT NULL DEFAULT 0,
    pages_failed INTEGER NOT NULL DEFAULT 0,
    bytes_downloaded BIGINT NOT NULL DEFAULT 0,
    
    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Results
    result JSONB,
    error TEXT,
    manifest_url TEXT,
    
    -- User tracking
    created_by VARCHAR(255),
    
    -- Indexes
    CONSTRAINT jobs_host_idx_idx INDEX (host),
    CONSTRAINT jobs_status_idx INDEX (status),
    CONSTRAINT jobs_created_at_idx INDEX (created_at DESC)
);

-- Create job progress tracking table for historical data
CREATE TABLE IF NOT EXISTS job_progress (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status job_status NOT NULL,
    pages_crawled INTEGER NOT NULL,
    pages_discovered INTEGER NOT NULL,
    pages_failed INTEGER NOT NULL,
    bytes_downloaded BIGINT NOT NULL,
    current_url TEXT,
    message TEXT,
    progress_percentage REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT job_progress_job_id_idx INDEX (job_id),
    CONSTRAINT job_progress_created_at_idx INDEX (created_at DESC)
);

-- Create function to update job modified time
CREATE OR REPLACE FUNCTION update_job_started_at()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status != 'running' AND NEW.status = 'running' THEN
        NEW.started_at = NOW();
    END IF;
    IF OLD.status NOT IN ('completed', 'failed', 'cancelled') 
       AND NEW.status IN ('completed', 'failed', 'cancelled') THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for job status updates
CREATE TRIGGER update_job_timestamps
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_job_started_at();
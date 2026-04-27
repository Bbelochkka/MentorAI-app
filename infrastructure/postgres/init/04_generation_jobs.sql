CREATE TABLE IF NOT EXISTS generation_jobs (
    id UUID PRIMARY KEY,
    company_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    job_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(30),
    entity_id BIGINT,

    status VARCHAR(20) NOT NULL DEFAULT 'queued',

    request_payload JSONB,
    result_payload JSONB,
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    CONSTRAINT chk_generation_jobs_type CHECK (
        job_type IN ('course_generate_draft', 'test_generate_draft')
    ),
    CONSTRAINT chk_generation_jobs_status CHECK (
        status IN ('queued', 'running', 'completed', 'failed', 'timeout')
    ),
    CONSTRAINT chk_generation_jobs_entity_type CHECK (
        entity_type IS NULL OR entity_type IN ('course', 'test')
    )
);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_company_created
    ON generation_jobs(company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_user_created
    ON generation_jobs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_status
    ON generation_jobs(status);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_type
    ON generation_jobs(job_type);
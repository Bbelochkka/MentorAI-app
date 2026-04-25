CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS bot_queries (
    id BIGSERIAL PRIMARY KEY,
    chat_session_id BIGINT REFERENCES chat_sessions(id) ON DELETE SET NULL,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id BIGINT NOT NULL,
    training_session_id BIGINT NULL,
    query_text TEXT NOT NULL,
    answer_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_query_sources (
    id BIGSERIAL PRIMARY KEY,
    bot_query_id BIGINT NOT NULL REFERENCES bot_queries(id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id BIGINT REFERENCES document_chunks(id) ON DELETE SET NULL,
    relevance_score NUMERIC(8,2)
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_queries_user_id ON bot_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_queries_company_id ON bot_queries(company_id);
CREATE INDEX IF NOT EXISTS idx_bot_query_sources_bot_query_id ON bot_query_sources(bot_query_id);

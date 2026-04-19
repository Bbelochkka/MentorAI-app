CREATE TABLE IF NOT EXISTS roles (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    CONSTRAINT chk_roles_code CHECK (code IN ('employer', 'manager', 'admin'))
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    team_id BIGINT,
    role_id SMALLINT NOT NULL REFERENCES roles(id),
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    uploaded_by BIGINT REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_path TEXT NOT NULL,
    raw_text TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_documents_file_type CHECK (file_type IN ('pdf', 'docx', 'txt', 'other')),
    CONSTRAINT chk_documents_status CHECK (status IN ('uploaded', 'processing', 'processed', 'failed', 'archived'))
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding_ref TEXT,
    page_num INTEGER,
    source_position VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS courses (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_by BIGINT REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    current_version_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_courses_status CHECK (status IN ('draft', 'approved', 'published', 'archived'))
);

CREATE TABLE IF NOT EXISTS course_versions (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    generated_from_document_id BIGINT REFERENCES documents(id),
    created_by BIGINT REFERENCES users(id),
    approved_by BIGINT REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_course_versions_status CHECK (status IN ('draft', 'approved', 'published', 'archived')),
    UNIQUE (course_id, version_number)
);

CREATE TABLE IF NOT EXISTS course_modules (
    id BIGSERIAL PRIMARY KEY,
    course_version_id BIGINT NOT NULL REFERENCES course_versions(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS course_topics (
    id BIGSERIAL PRIMARY KEY,
    module_id BIGINT NOT NULL REFERENCES course_modules(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    source_chunk_id BIGINT REFERENCES document_chunks(id),
    sort_order INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tests (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    course_id BIGINT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    topic_id BIGINT REFERENCES course_topics(id),
    title VARCHAR(255) NOT NULL,
    test_type VARCHAR(20) NOT NULL DEFAULT 'course',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    current_version_no INTEGER NOT NULL DEFAULT 1,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tests_status CHECK (status IN ('draft', 'approved', 'published', 'archived')),
    CONSTRAINT chk_tests_type CHECK (test_type IN ('course', 'topic', 'mini', 'final'))
);

CREATE TABLE IF NOT EXISTS test_versions (
    id BIGSERIAL PRIMARY KEY,
    test_id BIGINT NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    created_by BIGINT REFERENCES users(id),
    approved_by BIGINT REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_test_versions_status CHECK (status IN ('draft', 'approved', 'published', 'archived')),
    UNIQUE (test_id, version_number)
);

CREATE TABLE IF NOT EXISTS questions (
    id BIGSERIAL PRIMARY KEY,
    test_version_id BIGINT NOT NULL REFERENCES test_versions(id) ON DELETE CASCADE,
    topic_id BIGINT REFERENCES course_topics(id),
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) NOT NULL DEFAULT 'single_choice',
    weight NUMERIC(8,2) NOT NULL DEFAULT 1.00,
    sort_order INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT chk_questions_type CHECK (question_type IN ('single_choice'))
);

CREATE TABLE IF NOT EXISTS question_options (
    id BIGSERIAL PRIMARY KEY,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS test_attempts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    test_id BIGINT NOT NULL REFERENCES tests(id),
    test_version_id BIGINT NOT NULL REFERENCES test_versions(id),
    attempt_no INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    score NUMERIC(8,2) NOT NULL DEFAULT 0,
    percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'started',
    CONSTRAINT chk_test_attempts_status CHECK (status IN ('started', 'completed', 'abandoned')),
    UNIQUE (user_id, test_id, attempt_no)
);

CREATE TABLE IF NOT EXISTS question_responses (
    id BIGSERIAL PRIMARY KEY,
    attempt_id BIGINT NOT NULL REFERENCES test_attempts(id) ON DELETE CASCADE,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    selected_option_id BIGINT REFERENCES question_options(id),
    answer_text TEXT,
    is_correct BOOLEAN,
    earned_score NUMERIC(8,2) NOT NULL DEFAULT 0,
    responded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS public.course_document_links (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL REFERENCES public.documents(id) ON DELETE RESTRICT,
    UNIQUE (course_id, document_id)
);

INSERT INTO roles (id, code) VALUES
    (1, 'employer'),
    (2, 'manager'),
    (3, 'admin')
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, company_id, role_id, full_name, email, password_hash)
VALUES (1, 1, 2, 'Алёна', 'aoanuchina@hse.edu.ru', 'bootstrap-dev-password')
ON CONFLICT (id) DO NOTHING;

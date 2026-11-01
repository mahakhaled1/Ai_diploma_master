-- ============================================================================
-- HAQI | حقي — PostgreSQL Database Schema & Metadata Registry
-- Designed by: Maha (Backend, Database & Evaluation Lead)
-- ============================================================================

-- Optional pgvector extension for vector similarity search (Slide 14 & 15)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Official Documents & Metadata Registry (Slide 13: Metadata Schema)
CREATE TABLE IF NOT EXISTS official_documents (
    id SERIAL PRIMARY KEY,
    doc_code VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,                      -- 1. عنوان الوثيقة (Title)
    authority VARCHAR(255) NOT NULL,                  -- 2. الجهة الحكومية (Authority)
    original_url VARCHAR(1000) NOT NULL,              -- 3. الرابط الأصلي (Original URL)
    publication_date DATE NOT NULL,                   -- 4. تاريخ النشر (Publication Date)
    last_updated DATE NOT NULL,                       -- 5. تاريخ التحديث (Last Updated)
    service_category VARCHAR(150) NOT NULL,           -- 6. فئة الخدمة (Service Category)
    verification_date DATE NOT NULL,                  -- 7. تاريخ التحقق (Verification Date)
    version VARCHAR(50) NOT NULL DEFAULT '1.0',       -- 8. إصدار الوثيقة (Version)
    is_official_verified BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_official_docs_category ON official_documents(service_category);
CREATE INDEX IF NOT EXISTS idx_official_docs_authority ON official_documents(authority);

-- 2. Government Service Procedures & Structured Knowledge Chunks (Slide 11, 13, 16)
CREATE TABLE IF NOT EXISTS service_chunks (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(64) UNIQUE NOT NULL,
    document_id INTEGER NOT NULL REFERENCES official_documents(id) ON DELETE CASCADE,
    service_slug VARCHAR(100) NOT NULL,
    service_name_ar VARCHAR(255) NOT NULL,
    sub_type VARCHAR(100) DEFAULT 'general',          -- e.g., first_time, renewal, replacement, general
    intent_tag VARCHAR(100) NOT NULL,
    chunk_text TEXT NOT NULL,
    steps_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_documents_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    eligibility_criteria_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    fees_text VARCHAR(500),
    processing_time VARCHAR(255),
    keywords_ar TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_service_chunks_intent ON service_chunks(intent_tag);
CREATE INDEX IF NOT EXISTS idx_service_chunks_slug ON service_chunks(service_slug);

-- 3. Users Table (Data Minimization Compliant - Slide 19)
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(100) PRIMARY KEY,
    role VARCHAR(50) NOT NULL DEFAULT 'citizen',
    preferred_dialect VARCHAR(50) NOT NULL DEFAULT 'ar-EG',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Chat Sessions Table (Multi-turn Conversation & Clarification State - Slide 7 & 16)
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    pending_intent VARCHAR(100),
    pending_service_slug VARCHAR(100),
    awaiting_clarification BOOLEAN NOT NULL DEFAULT FALSE,
    clarification_options_json JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Chat Messages & Audit Log (Grounding & Latency Tracking - Slide 10, 14, 18)
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(30) NOT NULL,                        -- 'user' or 'assistant'
    message_text TEXT NOT NULL,
    detected_intent VARCHAR(100),
    rewritten_query TEXT,
    decision_type VARCHAR(50),                        -- 'answered', 'clarification_needed', 'safe_abstention'
    confidence_score REAL DEFAULT 0.0,
    citations_json JSONB DEFAULT '[]'::jsonb,
    retrieval_time_ms REAL DEFAULT 0.0,
    total_latency_ms REAL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Contradiction Flags for Human-in-the-Loop Review (Slide 8, 12, 19, 22)
CREATE TABLE IF NOT EXISTS contradiction_flags (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    doc_code_a VARCHAR(64) NOT NULL,
    doc_code_b VARCHAR(64) NOT NULL,
    conflict_description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending_human_review',
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 7. User Feedback Table (Slide 14: Monitoring & Evaluation)
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    message_id INTEGER,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    is_helpful BOOLEAN NOT NULL DEFAULT TRUE,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Evaluation Benchmark Runs (Slide 18: Quantitative & Qualitative Evaluation)
CREATE TABLE IF NOT EXISTS evaluation_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) UNIQUE NOT NULL,
    dataset_version VARCHAR(50) NOT NULL,
    total_cases INTEGER NOT NULL,
    recall_at_k REAL NOT NULL,
    mrr REAL NOT NULL,
    ndcg_at_k REAL NOT NULL,
    faithfulness REAL NOT NULL,
    answer_accuracy REAL NOT NULL,
    citation_precision REAL NOT NULL,
    abstention_quality REAL NOT NULL,
    unsupported_claim_rate REAL NOT NULL,
    avg_retrieval_time_ms REAL NOT NULL,
    avg_response_latency_ms REAL NOT NULL,
    detailed_results_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

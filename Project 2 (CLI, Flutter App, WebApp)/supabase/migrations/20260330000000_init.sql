-- NSU Degree Audit - CSE226 OCR Project Tables
-- ============================================
-- Isolated tables with cse226_ocr_ prefix to avoid conflicts

-- ─── CSE226 OCR Users Table ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cse226_ocr_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    provider VARCHAR(50) DEFAULT 'google',
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cse226_ocr_users_email ON cse226_ocr_users(email);

-- ─── CSE226 OCR Scan History Table ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cse226_ocr_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES cse226_ocr_users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    total_courses INTEGER DEFAULT 0,
    total_credits NUMERIC(5,2) DEFAULT 0,
    cgpa NUMERIC(4,3) DEFAULT 0,
    analysis_data JSONB DEFAULT '{}'::jsonb,
    source VARCHAR(50) DEFAULT 'web',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cse226_ocr_scans_user_id ON cse226_ocr_scans(user_id);
CREATE INDEX IF NOT EXISTS idx_cse226_ocr_scans_created_at ON cse226_ocr_scans(created_at DESC);

-- ─── CSE226 OCR API Keys Table ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cse226_ocr_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES cse226_ocr_users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) DEFAULT 'Default Key',
    last_used TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_cse226_ocr_api_keys_hash ON cse226_ocr_api_keys(key_hash);

-- ─── Row Level Security ────────────────────────────────────────────────────────
ALTER TABLE cse226_ocr_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cse226_ocr_scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE cse226_ocr_api_keys ENABLE ROW LEVEL SECURITY;

-- Allow all operations (backend uses service role)
DROP POLICY IF EXISTS "cse226_ocr_users_policy" ON cse226_ocr_users;
DROP POLICY IF EXISTS "cse226_ocr_scans_policy" ON cse226_ocr_scans;
DROP POLICY IF EXISTS "cse226_ocr_api_keys_policy" ON cse226_ocr_api_keys;

CREATE POLICY "cse226_ocr_users_policy" ON cse226_ocr_users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "cse226_ocr_scans_policy" ON cse226_ocr_scans FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "cse226_ocr_api_keys_policy" ON cse226_ocr_api_keys FOR ALL USING (true) WITH CHECK (true);

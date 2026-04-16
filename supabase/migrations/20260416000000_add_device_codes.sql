-- Add shared device-code storage for multi-instance CLI authentication
-- Run this in Supabase SQL Editor or via `supabase db push`

CREATE TABLE IF NOT EXISTS cse226_ocr_device_codes (
    device_code VARCHAR(32) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    token TEXT,
    user_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cse226_ocr_device_codes_status
ON cse226_ocr_device_codes(status);

CREATE INDEX IF NOT EXISTS idx_cse226_ocr_device_codes_expires_at
ON cse226_ocr_device_codes(expires_at);

ALTER TABLE cse226_ocr_device_codes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "cse226_ocr_device_codes_policy" ON cse226_ocr_device_codes;
CREATE POLICY "cse226_ocr_device_codes_policy"
ON cse226_ocr_device_codes
FOR ALL
USING (true)
WITH CHECK (true);

COMMENT ON TABLE cse226_ocr_device_codes IS
'Shared CLI device-code login state for multi-instance backend deployments.';

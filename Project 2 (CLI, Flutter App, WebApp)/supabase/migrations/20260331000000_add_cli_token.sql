-- Add cli_token column to support CLI/mobile simple auth
-- Run this in Supabase SQL Editor

ALTER TABLE cse226_ocr_users 
ADD COLUMN IF NOT EXISTS cli_token TEXT;

-- Create index for fast token lookups
CREATE INDEX IF NOT EXISTS idx_cse226_ocr_users_cli_token 
ON cse226_ocr_users(cli_token);

-- Comment
COMMENT ON COLUMN cse226_ocr_users.cli_token IS 'Session token for CLI/mobile auth';

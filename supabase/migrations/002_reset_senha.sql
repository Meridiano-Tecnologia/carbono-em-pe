-- Migration 002: colunas para reset de senha por token
-- Executar no SQL Editor do Supabase antes do deploy

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS reset_token_hash TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS reset_token_expira TIMESTAMPTZ;

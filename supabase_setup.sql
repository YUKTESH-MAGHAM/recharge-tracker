-- ============================================================
-- RECHARGE TRACKER — Supabase Database Setup
-- Run this entire script in your Supabase SQL Editor:
--   https://supabase.com/dashboard → your project → SQL Editor
-- ============================================================

-- 1. Create the transactions table
CREATE TABLE IF NOT EXISTS public.transactions (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type       TEXT        NOT NULL CHECK (type IN ('recharge', 'expense')),
  name       TEXT        NOT NULL,
  amount     NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Index for fast per-user queries
CREATE INDEX IF NOT EXISTS idx_transactions_user_id
  ON public.transactions (user_id, created_at ASC);

-- 3. Enable Row Level Security
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies — users can only access their OWN data
CREATE POLICY "select_own" ON public.transactions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "insert_own" ON public.transactions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own" ON public.transactions
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "delete_own" ON public.transactions
  FOR DELETE USING (auth.uid() = user_id);

-- 5. Verify setup
SELECT 'transactions table ready ✓' AS status;

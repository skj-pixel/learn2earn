-- Add per-product strategy overrides to existing task databases.
-- Local SQLite applies this idempotently through database._ensure_new_columns.
ALTER TABLE generation_tasks ADD COLUMN product_strategies TEXT;

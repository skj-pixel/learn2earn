-- 2026-08-04：为 products 表增加 generation_meta 列，记录每次生成选用的
-- skill_ids / skill_names / algorithms / techniques，便于质量追溯与复现。
-- 本地 SQLite 由 backend/app/database.py 的 _ensure_new_columns 在启动时自动 ALTER；
-- 云数据库（Supabase）请手动执行以下语句：

ALTER TABLE products ADD COLUMN generation_meta TEXT;

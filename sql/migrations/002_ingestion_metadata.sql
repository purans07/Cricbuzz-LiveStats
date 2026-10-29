-- Additive migration; the transaction is owned by database.migrate.
ALTER TABLE import_batches ADD COLUMN resource_key TEXT NOT NULL DEFAULT '';
ALTER TABLE import_batches ADD COLUMN snapshot_key TEXT;
CREATE UNIQUE INDEX uq_batches_source_snapshot ON import_batches(source_id, snapshot_key);
ALTER TABLE teams ADD COLUMN last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT;
ALTER TABLE venues ADD COLUMN last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT;
ALTER TABLE series ADD COLUMN last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT;

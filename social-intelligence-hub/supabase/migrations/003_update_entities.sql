-- ============================================================
-- 003_update_entities.sql
-- Vincula entities a su conglomerado + bandera de prioridad.
-- priority=TRUE  -> monitoreada en el cron diario (15 empresas)
-- priority=FALSE -> análisis on-demand (~20 empresas)
-- ============================================================
ALTER TABLE entities ADD COLUMN IF NOT EXISTS conglomerate_id UUID REFERENCES conglomerates(id);
ALTER TABLE entities ADD COLUMN IF NOT EXISTS priority BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_entities_conglomerate ON entities(conglomerate_id);
CREATE INDEX IF NOT EXISTS idx_entities_priority     ON entities(priority) WHERE priority = TRUE;

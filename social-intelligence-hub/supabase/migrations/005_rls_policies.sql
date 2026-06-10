-- ============================================================
-- 005_rls_policies.sql  (SEGURIDAD — bloqueante)
-- Row Level Security: el cliente (anon key) SOLO LEE.
-- Las escrituras quedan para el scraper, que usa la SERVICE ROLE KEY
-- (el rol service_role SALTA RLS por diseño en Supabase).
--
-- Tablas de cara al público (lectura anon): conglomerates, entities, mentions,
-- sources, crisis_alerts.
-- Tablas internas (sin policy anon -> invisibles al cliente, solo service_role):
-- entity_configs, scraper_runs.
-- ============================================================

-- 1) Habilitar RLS en todas las tablas
ALTER TABLE conglomerates  ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities       ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources        ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_runs   ENABLE ROW LEVEL SECURITY;
ALTER TABLE crisis_alerts  ENABLE ROW LEVEL SECURITY;

-- 2) Políticas de LECTURA PÚBLICA (SELECT para anon + authenticated)
DROP POLICY IF EXISTS "public_read_conglomerates" ON conglomerates;
CREATE POLICY "public_read_conglomerates" ON conglomerates
  FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_entities" ON entities;
CREATE POLICY "public_read_entities" ON entities
  FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_mentions" ON mentions;
CREATE POLICY "public_read_mentions" ON mentions
  FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_sources" ON sources;
CREATE POLICY "public_read_sources" ON sources
  FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_read_crisis_alerts" ON crisis_alerts;
CREATE POLICY "public_read_crisis_alerts" ON crisis_alerts
  FOR SELECT TO anon, authenticated USING (true);

-- 3) entity_configs y scraper_runs: SIN política para anon.
--    Con RLS activo y sin policy, el rol anon no ve ni escribe nada.
--    El scraper (service_role) salta RLS y opera con normalidad.

-- Nota: NO se crean políticas de INSERT/UPDATE/DELETE para anon en ninguna tabla.
-- Por tanto, cualquier intento de escritura desde el cliente con la anon key es
-- rechazado por RLS (criterio de seguridad #7).

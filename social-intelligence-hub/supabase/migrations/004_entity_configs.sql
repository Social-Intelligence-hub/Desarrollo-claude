-- ============================================================
-- 004_entity_configs.sql
-- El "setup" declarativo por entidad. El scraper LEE de aquí;
-- agregar una empresa nueva es un INSERT, nunca un cambio de código.
-- ============================================================
CREATE TABLE IF NOT EXISTS entity_configs (
  entity_id             UUID PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,

  -- Búsqueda activa (queries generadas por Gemini en el setup)
  search_queries        TEXT[] DEFAULT '{}',

  -- Google Maps Reviews
  google_maps_url       TEXT,
  google_maps_max_reviews INT DEFAULT 10,

  -- Subreddits y RSS extra
  reddit_subreddits     TEXT[] DEFAULT '{}',
  extra_rss_feeds       TEXT[] DEFAULT '{}',

  -- Filtro de relevancia DECLARATIVO (reemplaza el if/elif hardcodeado)
  required_terms        TEXT[] DEFAULT '{}',   -- al menos uno debe aparecer
  required_context      TEXT[] DEFAULT '{}',   -- contexto obligatorio
  forbidden_terms       TEXT[] DEFAULT '{}',   -- ninguno puede aparecer
  forbidden_domains     TEXT[] DEFAULT '{}',   -- dominios a bloquear (ej: .cl)
  geo_requirement       TEXT,                  -- "santiago_rd" | "dominicana" | NULL

  -- Desambiguación (señales generadas por Gemini)
  disambiguation        JSONB DEFAULT '{}',
  -- {"positive_signals": ["tabaco","fábrica"], "negative_signals": ["chile","metro"]}

  -- Metadata
  queries_generated_at  TIMESTAMPTZ,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Columnas nuevas en mentions para el pipeline v3
ALTER TABLE mentions ADD COLUMN IF NOT EXISTS collector_type  TEXT;
-- "rss" | "google_news" | "reddit" | "google_reviews" | "instagram" | "facebook"
ALTER TABLE mentions ADD COLUMN IF NOT EXISTS is_first_run    BOOLEAN DEFAULT FALSE;
ALTER TABLE mentions ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_mentions_collector_type ON mentions(collector_type);

-- Trigger updated_at en entity_configs
DROP TRIGGER IF EXISTS set_entity_configs_updated_at ON entity_configs;
CREATE TRIGGER set_entity_configs_updated_at
  BEFORE UPDATE ON entity_configs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Social Intelligence Hub v3 - Schema inicial (baseline)
-- Aplicado en proyecto Supabase nuevo (ejivsqgumonogddiftvq).
-- Nota v3: se omitió el seed demo del MVP (entidades/menciones hardcodeadas);
-- los datos reales vienen del seed de Zona Franca (F4) y la primera corrida (F5).
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------- entities ----------
CREATE TABLE IF NOT EXISTS entities (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug          TEXT UNIQUE NOT NULL,
  name          TEXT NOT NULL,
  category      TEXT NOT NULL,
  keywords      TEXT[] NOT NULL DEFAULT '{}',
  anti_keywords TEXT[] NOT NULL DEFAULT '{}',
  description   TEXT,
  logo_url      TEXT,
  active        BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ---------- sources ----------
CREATE TABLE IF NOT EXISTS sources (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug        TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  icon_url    TEXT,
  base_url    TEXT,
  active      BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ---------- mentions ----------
CREATE TABLE IF NOT EXISTS mentions (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_id         UUID REFERENCES entities(id) ON DELETE SET NULL,
  source_id         UUID REFERENCES sources(id) ON DELETE SET NULL,
  text_original     TEXT NOT NULL,
  text_normalized   TEXT,
  author_name       TEXT,
  author_avatar_url TEXT,
  source_url        TEXT,
  platform_post_id  TEXT,
  star_rating       SMALLINT CHECK (star_rating BETWEEN 1 AND 5),
  sentiment_label   TEXT CHECK (sentiment_label IN ('positive','negative','neutral','mixed')),
  sentiment_score   JSONB,
  confidence_score  NUMERIC(4,3),
  dominican_override     BOOLEAN DEFAULT FALSE,
  dominican_term_found   TEXT,
  published_at      TIMESTAMPTZ,
  collected_at      TIMESTAMPTZ DEFAULT NOW(),
  language          TEXT DEFAULT 'es',
  location_hint     TEXT,
  search_query      TEXT,
  content_hash      TEXT UNIQUE,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ---------- scraper_runs ----------
CREATE TABLE IF NOT EXISTS scraper_runs (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_slug     TEXT NOT NULL,
  entity_slug     TEXT,
  status          TEXT CHECK (status IN ('running','success','error')),
  mentions_found  INTEGER DEFAULT 0,
  mentions_new    INTEGER DEFAULT 0,
  error_message   TEXT,
  started_at      TIMESTAMPTZ DEFAULT NOW(),
  finished_at     TIMESTAMPTZ
);

-- ---------- crisis_alerts ----------
CREATE TABLE IF NOT EXISTS crisis_alerts (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_id       UUID REFERENCES entities(id),
  alert_type      TEXT,
  severity        TEXT CHECK (severity IN ('low','medium','high','critical')),
  message         TEXT,
  trigger_value   NUMERIC,
  threshold_value NUMERIC,
  acknowledged    BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ---------- índices ----------
CREATE INDEX IF NOT EXISTS idx_mentions_entity_id    ON mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_source_id    ON mentions(source_id);
CREATE INDEX IF NOT EXISTS idx_mentions_sentiment     ON mentions(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_mentions_published_at ON mentions(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_mentions_collected_at ON mentions(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_mentions_content_hash ON mentions(content_hash);

-- ---------- trigger updated_at ----------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_mentions_updated_at ON mentions;
CREATE TRIGGER set_mentions_updated_at
  BEFORE UPDATE ON mentions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ---------- vistas ----------
-- v_sentiment_summary: COUNT(m.id) (no COUNT(*)) para que entidades sin menciones cuenten 0.
CREATE OR REPLACE VIEW v_sentiment_summary AS
SELECT
  e.slug           AS entity_slug,
  e.name           AS entity_name,
  e.category,
  COUNT(m.id)      AS total_mentions,
  SUM(CASE WHEN m.sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_count,
  SUM(CASE WHEN m.sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_count,
  SUM(CASE WHEN m.sentiment_label = 'neutral'  THEN 1 ELSE 0 END) AS neutral_count,
  SUM(CASE WHEN m.sentiment_label = 'mixed'    THEN 1 ELSE 0 END) AS mixed_count,
  ROUND(
    100.0 * SUM(CASE WHEN m.sentiment_label = 'positive' THEN 1 ELSE 0 END) / NULLIF(COUNT(m.id), 0)
  , 1) AS positive_pct,
  ROUND(
    (
      SUM(CASE WHEN m.sentiment_label = 'positive' THEN 1 ELSE 0 END) -
      SUM(CASE WHEN m.sentiment_label = 'negative' THEN 1 ELSE 0 END)
    )::NUMERIC / NULLIF(COUNT(m.id), 0) * 100
  , 1) AS net_sentiment_score,
  MAX(m.collected_at) AS last_updated
FROM entities e
LEFT JOIN mentions m ON m.entity_id = e.id
  AND m.published_at >= NOW() - INTERVAL '30 days'
GROUP BY e.id, e.slug, e.name, e.category;

CREATE OR REPLACE VIEW v_daily_trend AS
SELECT
  DATE(m.published_at)   AS mention_date,
  e.slug                 AS entity_slug,
  m.sentiment_label,
  COUNT(*)               AS mention_count
FROM mentions m
JOIN entities e ON e.id = m.entity_id
WHERE m.published_at >= NOW() - INTERVAL '14 days'
GROUP BY DATE(m.published_at), e.slug, m.sentiment_label
ORDER BY mention_date DESC;

-- ---------- seed de fuentes (todos los colectores v3) ----------
INSERT INTO sources (slug, name, base_url) VALUES
('google_reviews', 'Google Reviews',    'https://maps.google.com'),
('reddit',         'Reddit',            'https://reddit.com'),
('google_alerts',  'Google Alerts RSS', 'https://google.com/alerts'),
('google_news',    'Google News',       'https://news.google.com'),
('rss',            'RSS Feeds',         NULL),
('instagram',      'Instagram',         'https://instagram.com'),
('facebook',       'Facebook',          'https://facebook.com'),
('tiktok',         'TikTok',            'https://tiktok.com'),
('twitter_x',      'X (Twitter)',        'https://x.com'),
('news_web',       'Noticias Web',      NULL)
ON CONFLICT (slug) DO NOTHING;

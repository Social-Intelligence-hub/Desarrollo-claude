-- ============================================================
-- 002_conglomerates.sql
-- Catálogo de clientes del producto (uno por instancia).
-- ============================================================
CREATE TABLE IF NOT EXISTS conglomerates (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug                TEXT UNIQUE NOT NULL,        -- "zona-franca"
  name                TEXT NOT NULL,               -- "Corporación Zona Franca Santiago"
  category            TEXT NOT NULL,               -- "zona-franca" | "mall" | "grupo-empresarial"
  website             TEXT,                        -- para auto-discovery del directorio
  context_description TEXT NOT NULL,               -- para prompts de Gemini (desambiguación)
  logo_url            TEXT,
  primary_geo         TEXT DEFAULT 'Santiago, RD', -- contexto geográfico por defecto
  active              BOOLEAN DEFAULT TRUE,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

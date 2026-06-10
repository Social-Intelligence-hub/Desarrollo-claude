# Social Intelligence Hub
### Motor de Búsqueda de Inteligencia de Reputación para Conglomerados

> **Documento maestro del proyecto** — versión 3.0
> **Última actualización**: Junio 2026
> **Estado**: Planificación aprobada, listo para implementación
> **Repositorio canónico**: `desarrollo-cloned/social-intelligence-hub/`

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Contexto y Problema](#2-contexto-y-problema)
3. [Visión del Producto](#3-visión-del-producto)
4. [Investigación de Clientes](#4-investigación-de-clientes)
5. [Arquitectura Técnica](#5-arquitectura-técnica)
6. [Modelo de Datos](#6-modelo-de-datos)
7. [Los Colectores](#7-los-colectores)
8. [Motor de Análisis NLP](#8-motor-de-análisis-nlp)
9. [Estrategia de Ejecución](#9-estrategia-de-ejecución)
10. [Estructura del Repositorio](#10-estructura-del-repositorio)
11. [Plan de Implementación](#11-plan-de-implementación)
12. [Configuración y Secrets](#12-configuración-y-secrets)
13. [Costos](#13-costos)
14. [Riesgos y Mitigaciones](#14-riesgos-y-mitigaciones)
15. [Verificación End-to-End](#15-verificación-end-to-end)
16. [Roadmap Futuro](#16-roadmap-futuro)
17. [Glosario](#17-glosario)

---

## 1. Resumen Ejecutivo

**Social Intelligence Hub** es un motor de búsqueda de inteligencia de reputación,
privatizado y contextualizado, vendido a **conglomerados** — una zona franca, un centro
comercial, un grupo empresarial.

Cada conglomerado que adquiere el producto recibe una **instancia propia** que conoce
todas las entidades de su ecosistema (empresas, tiendas, locales) y permite:

- **Buscar** cualquiera de esas entidades como en un buscador especializado
- **Visualizar** un dashboard de reputación contextualizado de cada una
- **Monitorear** automáticamente menciones desde 6 fuentes públicas y sociales
- **Detectar** sentimiento en español dominicano con IA

El producto se diferencia de un dashboard de social listening tradicional en que el
**contexto del conglomerado resuelve la desambiguación automáticamente**: buscar "CAPEX"
dentro de la instancia de Zona Franca solo puede referirse al CAPEX formativo de la
corporación, nunca al término financiero (capital expenditure); buscar "SPI" o "PIVEM"
devuelve la entidad correcta dentro del ecosistema.

> **Alcance de este documento**: el único entregable activo es la **Corporación Zona
> Franca de Santiago**. Otros conglomerados (p. ej. Ágora Santiago Center) NO se abordan
> hasta completar y validar el entregable de Zona Franca. Ver [Roadmap Futuro](#16-roadmap-futuro).

| Característica | Valor |
|---------------|-------|
| **Entregable actual (único)** | Corporación Zona Franca de Santiago (~35 empresas en demo) |
| **Stack** | Next.js 15 + Supabase + Python 3.13 + Gemini 2.0 Flash |
| **Hosting** | Vercel (frontend) + GitHub Actions (scraper) |
| **Costo operativo** | $0/mes (free tier) |
| **Modelo de escala** | Instancias separadas → multi-tenant cuando haya capital |

---

## 2. Contexto y Problema

### 2.1 El pivot conceptual

El proyecto pasó por una redefinición fundamental. La descripción inicial era incorrecta:

| Concepción errónea (descartada) | Producto real (validado) |
|----------------------------------|---------------------------|
| Dashboard de social listening con marcas fijas | Buscador de reputación dinámico |
| 5 entidades hardcodeadas en código | N entidades configurables por BD |
| El conglomerado = una marca a monitorear | El conglomerado = un ecosistema con N entidades |
| El sistema *muestra* menciones acumuladas | El sistema *responde* a búsquedas |
| Un cliente = una marca | Un cliente = un conglomerado completo |

### 2.2 Dos repositorios, un canónico

En el workspace coexisten dos iteraciones del producto:

- **Repo principal** (`Hub-sentimiento/`): MVP "medida desesperada" sobre Express +
  Firebase + Gemini. Monolítico, sin CI/CD. **Descartado como base.**
- **Repo clonado** (`desarrollo-cloned/social-intelligence-hub/`): el **proyecto
  canónico**. Arquitectura desacoplada (Next.js 15 + Python + Supabase), GitHub Actions
  configurado, schema SQL listo. **Esta es la base del producto.**

### 2.3 El cambio de proveedor de NLP

El repo canónico usaba **Azure AI Language** para análisis de sentimiento, lo cual:
- Tiene un tier gratuito limitado (5,000 transacciones/mes)
- Cobra al rebasarlo
- Es innecesario teniendo **Gemini 2.0 Flash** disponible y gratuito

**Decisión**: reemplazar Azure por Gemini en todo el pipeline, conservando el léxico
dominicano local como capa de override y un fallback heurístico como red de seguridad.

### 2.4 Principio rector: configuración sobre código

Toda la lógica específica de una entidad vive en la **base de datos** como "setup".
El scraper es un **motor genérico declarativo** que lee la configuración y la ejecuta.

> Agregar una nueva entidad (empresa o tienda) es un `INSERT` en la tabla, **nunca**
> un cambio de código Python.

---

## 3. Visión del Producto

### 3.1 Flujo de usuario

```
┌─────────────────────────────────────────────────────────────────┐
│  INSTANCIA: CORPORACIÓN ZONA FRANCA DE SANTIAGO                 │
│  URL: zonafranca.nuestrodominio.vercel.app                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [🔍 Buscar empresa, marca o local...        ]  ← siempre arriba│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ DASHBOARD DEL CONGLOMERADO (home)                        │   │
│  │                                                          │   │
│  │  Reputación de la Zona Franca como entidad global       │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                  │   │
│  │  │ 84%  │ │ 11%  │ │  5%  │ │ +73  │                  │   │
│  │  │ pos  │ │ neg  │ │ neu  │ │score │                  │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘                  │   │
│  │                                                          │   │
│  │  Tendencia 2 años [gráfico de área]                     │   │
│  │  Empresas más mencionadas [ranking]                      │   │
│  │  Últimas menciones del ecosistema [feed]                │   │
│  │  Alertas de crisis activas [badge rojo si aplica]        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Usuario escribe "Swisher" → autocomplete sugiere la empresa     │
│  Usuario selecciona → navega a /entidad/swisher-dominicana       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ DASHBOARD DE ENTIDAD (mismo diseño, distinto scope)      │   │
│  │  ← Volver        Swisher Dominicana — Zona Franca        │   │
│  │  [Mismos KPIs, gráficos y feed, filtrados a Swisher]    │   │
│  │                              [🔍 Analizar ahora (3/10)]  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Principios de diseño

1. **Un componente, dos scopes**: el dashboard del conglomerado y el de cada entidad
   son **idénticos en estructura**. Solo cambia el filtro de datos. Cero diseño extra.

2. **El home es el conglomerado**: al entrar, se ve el análisis del conglomerado *en sí*
   (la Zona Franca como corporación global), no de sus miembros individuales.

3. **Contexto siempre implícito**: cada query de scraping incluye el contexto del
   conglomerado. "La Aurora" se busca como "La Aurora Zona Franca Santiago", nunca en crudo.

4. **Instancias separadas por conglomerado**: cada cliente tiene su propio Vercel +
   Supabase + GitHub. Migración a multi-tenant cuando haya capital.

5. **Queries generadas por IA**: Gemini genera las variaciones de búsqueda de cada
   entidad **una vez en el setup**, y se guardan en BD para reutilización eficiente.

### 3.3 Modos de monitoreo

| Modo | Quién | Frecuencia | Disparador |
|------|-------|-----------|------------|
| **Automático** | Conglomerado + 15 empresas prioritarias | Diario (cron) | GitHub Actions |
| **Manual** | Cualquier empresa, hasta 10x/mes c/u | On-demand | Botón en dashboard |
| **Bajo demanda** | Empresas no prioritarias | Al buscarse | Función serverless |

---

## 4. Investigación de Clientes

> Esta sección documenta **únicamente** el cliente del entregable actual. La investigación
> de otros conglomerados se conserva como referencia en el [Roadmap](#16-roadmap-futuro),
> pero no forma parte del alcance presente.

### 4.1 Corporación Zona Franca de Santiago (el cliente)

| Campo | Dato |
|-------|------|
| Tipo | Zona franca industrial (B2B) |
| Parque principal | PIVEM (Parque Industrial Víctor Espaillat Mera) |
| Empresas en PIVEM | ~80-90 |
| Otros parques | Tamboril, CIP (Caribbean/Matanza), Santiago Norte |
| Afiliados confirmados (AEZFC) | 58 empresas |
| **Total estimado del ecosistema** | **~100-130 empresas** |
| Empleos | ~20,000-22,000 |
| Sectores | Tabaco, textiles, calzado, electrónica, logística |
| Web (auto-discovery) | zonafrancasantiago.com · aezfc.org/directorio-de-afiliados |

**Empresas representativas**: Swisher Dominicana, Hanesbrands, Grupo M (Tamboril),
La Aurora, Arturo Fuente, Bojos Tanning, Swedish Match, Keen Footwear, Eaton Souriau,
EMPA, IEM Corporation, CAPEX (centro de capacitación).

**Implicación técnica clave**: al ser empresas **B2B industriales**, tienen poca o nula
presencia en Google Reviews y Reddit. Los colectores realmente útiles para este
conglomerado son **RSS + Google News** (cobertura de prensa económica, laboral,
exportaciones) y, cuando estén disponibles, **Instagram + Facebook**.

**Riesgo de desambiguación**: "Santiago" también refiere a Santiago de Chile. El filtro
de relevancia debe exigir señal dominicana y bloquear dominios `.cl`.

### 4.2 Por qué Zona Franca primero

Al ser empresas **B2B industriales**, Zona Franca es el caso más exigente para validar el
valor del producto con las fuentes gratuitas (prensa, no reseñas de consumo). Si el sistema
demuestra valor aquí, el salto a un conglomerado de retail/consumo (donde abundan reseñas y
redes) es trivial. Validar primero el caso difícil reduce el riesgo del producto.

---

## 5. Arquitectura Técnica

### 5.1 Diagrama general

```
┌───────────────────────────────────────────────────────────────────┐
│                   SOCIAL INTELLIGENCE HUB v3                      │
├──────────────────────┬────────────────────────────────────────────┤
│  FRONTEND            │  Next.js 15 + Vercel (gratis)             │
│                      │  • Home: dashboard del conglomerado        │
│                      │  • Búsqueda con autocomplete               │
│                      │  • /entidad/[slug]: dashboard de entidad   │
│                      │    (mismo componente, distinto scope)      │
├──────────────────────┼────────────────────────────────────────────┤
│  DATABASE            │  Supabase Free (500 MB PostgreSQL)         │
│                      │  conglomerates · entities · entity_configs │
│                      │  mentions · sources · scraper_runs ·       │
│                      │  crisis_alerts                            │
├──────────────────────┼────────────────────────────────────────────┤
│  SCRAPER — 1ra corrida│ LOCAL (laptop, 6-8 h)                     │
│                      │  python main.py --first-run --all          │
│                      │  → Histórico 2 años (RSS/News/Reddit)      │
│                      │  → Histórico 3 meses (Instagram/Facebook)  │
│                      │  → Pobla Supabase de una sola vez          │
├──────────────────────┼────────────────────────────────────────────┤
│  SCRAPER — manten.   │  GitHub Actions (post-demo)                │
│                      │  Cron 06:00 y 18:00 UTC, incremental       │
│                      │  ~60-90 min/día → ≤2,000 min/mes ✅        │
├──────────────────────┼────────────────────────────────────────────┤
│  NLP                 │  Google Gemini 2.0 Flash (gratis)          │
│                      │  Cascada: Léxico DR → Gemini → Demo        │
│                      │  Prompt incluye contexto del conglomerado  │
├──────────────────────┼────────────────────────────────────────────┤
│  SETUP               │  discover_entities.py (1 vez por cliente)  │
│                      │  → Auto-discovery del directorio web        │
│                      │  → Gemini genera queries + filtros          │
│                      │  → Revisión humana en Supabase Studio       │
└──────────────────────┴────────────────────────────────────────────┘
```

### 5.2 Stack y tiers gratuitos

| Capa | Tecnología | Tier gratuito | Uso esperado |
|------|------------|---------------|---------------|
| Frontend | Next.js 15 + Vercel | Ilimitado (hobby) | ~10-50 visitas/día |
| Base de datos | Supabase (Postgres) | 500 MB · 50k API calls/día | ~5k calls/día |
| NLP | Gemini 2.0 Flash | 1,500 req/día · 1M tokens/día | ~60k tokens en 1ra corrida |
| Scraper (mantenimiento) | GitHub Actions | 2,000 min/mes | ~1,800 min/mes |
| Scraper (1ra corrida) | Laptop local | — | 6-8 horas, una vez |
| Reddit | API pública JSON | Sin clave | OK |
| Google News / RSS | Feeds públicos | Sin límite | OK |
| Google Reviews | Playwright headless | Best-effort | OK |
| Instagram / Facebook | Meta Graph API | 200 req/hora | Escalonado |

### 5.3 Decisiones de runtime y SDKs (junio 2026)

| Decisión | Elección | Por qué |
|----------|----------|---------|
| **Versión de Python** | **3.13** (no 3.12, no 3.14) | 3.13 es el punto óptimo: madura (~20 meses, hasta 3.13.13), soporte completo de todas las librerías del stack. 3.12 está 2 generaciones atrás; 3.14 tiene gaps de wheels en dependencias secundarias |
| **SDK de Gemini** | **`google-genai`** (no `google-generativeai`) | `google-generativeai` está deprecado. `google-genai` es el SDK unificado actual de Google Gen AI |
| **Pin de versiones** | Fijar versiones en `requirements.txt` | Reproducibilidad entre laptop local y GitHub Actions |
| **`python-version` en CI** | `'3.13'` en `setup-python@v5` | Igualar el runtime local para evitar sorpresas |

---

## 6. Modelo de Datos

### 6.1 Tabla nueva: `conglomerates`

```sql
CREATE TABLE conglomerates (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug                TEXT UNIQUE NOT NULL,        -- "zona-franca"
  name                TEXT NOT NULL,               -- "Corporación Zona Franca Santiago"
  category            TEXT NOT NULL,               -- "zona-franca" | "mall" | "grupo-empresarial"
  website             TEXT,                        -- para auto-discovery del directorio
  context_description TEXT NOT NULL,               -- para prompts de Gemini
  logo_url            TEXT,
  primary_geo         TEXT DEFAULT 'Santiago, RD', -- contexto geográfico por defecto
  active              BOOLEAN DEFAULT TRUE,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.2 Tabla `entities` — actualizada

```sql
-- Columnas añadidas a la tabla existente
ALTER TABLE entities ADD COLUMN conglomerate_id UUID REFERENCES conglomerates(id);
ALTER TABLE entities ADD COLUMN priority BOOLEAN DEFAULT FALSE;
-- priority=TRUE  → 15 empresas monitoreadas en el cron diario
-- priority=FALSE → ~20 empresas con análisis bajo demanda
```

Columnas heredadas del schema original: `id`, `slug`, `name`, `category`, `keywords[]`,
`anti_keywords[]`, `description`, `logo_url`, `active`, `created_at`.

### 6.3 Tabla nueva: `entity_configs` (el "setup" declarativo)

```sql
CREATE TABLE entity_configs (
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
```

### 6.4 Tabla `mentions` — actualizada

```sql
-- Columnas añadidas
ALTER TABLE mentions ADD COLUMN collector_type TEXT;
-- "rss" | "google_news" | "reddit" | "google_reviews" | "instagram" | "facebook"
ALTER TABLE mentions ADD COLUMN is_first_run BOOLEAN DEFAULT FALSE;
ALTER TABLE mentions ADD COLUMN last_updated_at TIMESTAMPTZ;
-- content_hash UNIQUE ya existe → deduplicación
```

Columnas heredadas: `id`, `entity_id`, `source_id`, `text_original`, `author_name`,
`source_url`, `star_rating`, `sentiment_label`, `sentiment_score` (JSONB),
`confidence_score`, `dominican_override`, `dominican_term_found`, `published_at`,
`collected_at`, `language`, `location_hint`, `search_query`, `content_hash`.

### 6.5 Tablas heredadas sin cambios

- **`sources`**: catálogo de fuentes (reddit, google_news, instagram, etc.)
- **`scraper_runs`**: historial de ejecuciones (status, mentions_found, timestamps)
- **`crisis_alerts`**: alertas (schema listo; lógica de disparo en roadmap)

### 6.6 Vistas

- **`v_sentiment_summary`**: resumen por entidad (totales, % positivo, net score) últimos 30 días
- **`v_daily_trend`**: tendencia diaria de menciones por entidad y sentimiento

> **Decisión deliberada**: NO se crea la tabla `collector_state`. La estrategia
> local-first elimina la necesidad de rastrear cursores de paginación entre corridas.

### 6.7 Relaciones

```
conglomerates (1)
     └── entities (N)              -- Swisher, CAPEX, La Aurora, PIVEM...
              ├── entity_configs (1:1)   -- cómo scrapear cada una
              └── mentions (N)           -- cada mención recogida
                       └── sources (N:1) -- de qué fuente vino
```

---

## 7. Los Colectores

### 7.1 Tabla comparativa

| Colector | Histórico 1ra corrida | Datos extraídos | Rate limit | Credenciales |
|----------|----------------------|-----------------|-----------|--------------|
| **RSS Feeds** | 2 años | Noticias dominicanas | Ninguno | NO |
| **Google News** | 2 años | Noticias globales | Ninguno | NO |
| **Reddit** | 6-12 meses | Posts + comentarios | Prudente (delays) | NO |
| **Google Reviews** | ~50-100 reseñas | Reseñas + ratings | Bloquea a veces | NO |
| **Instagram** | 3 meses → 2 años* | Posts + menciones + comentarios | 200 req/hora | SÍ |
| **Facebook** | 3 meses → 2 años* | Posts + comentarios | 200 req/hora | SÍ |
| **TikTok** | — (placeholder) | — | — | Pendiente |

\* Meta inicia con 3 meses en la primera corrida y expande histórico gradualmente.

### 7.2 Detalle por colector

**RSS Feeds** (`collectors/google_alerts.py`) — Lee feeds XML de 7 medios dominicanos
(El Nacional, Listín Diario, Diario Libre, Hoy, El Caribe, El Masacre) + Google News RSS.
Sin rate limit; en la primera corrida obtiene 2 años completos.

**Google News** (`collectors/google_alerts.py`) — Búsqueda parametrizada vía RSS de
Google News con filtro regional dominicano (`gl=DO`, `ceid=DO:es-419`).

**Reddit** (`collectors/reddit_collector.py`) — API JSON pública, sin autenticación.
Busca en subreddits objetivo (Dominican, RepublicaDominicana, Santiago, etc.) con
delays de 1.5s entre búsquedas y 0.5s entre subreddits.

**Google Reviews** (`collectors/google_reviews.py`) — Playwright headless sobre Google
Maps. Lento (~15-30 min). Tiene fallback con datos reales verificados si Google bloquea.
Solo para entidades con `google_maps_url` configurado.

**Instagram** (`collectors/instagram_collector.py` 🆕) — Instagram Graph API. Extrae
posts de hashtags de marca, menciones y comentarios. **Requiere Business/Creator Account.**
Primera corrida: 3 meses. Expansión histórica gradual hacia 2 años en corridas siguientes.

**Facebook** (`collectors/facebook_collector.py` 🆕) — Facebook Graph API. Extrae posts
de páginas de marcas y comentarios. Misma credencial centralizada que Instagram.

**TikTok** (`collectors/tiktok_collector.py` 🆕, **stub**) — Placeholder de primera
clase. Retorna `[]` sin credenciales. Pendiente de definir vía Research API (requiere
calificar como institución académica) o scraping (inestable). **No activo en la demo.**

### 7.3 Estrategia de credenciales Meta

**Decisión recomendada**: una sola credencial centralizada por instancia.

- Una cuenta "Social Intelligence Hub" de Meta con acceso a los perfiles de marcas
- Un `access_token` para Instagram + Facebook (ambos bajo Meta Graph API)
- Más simple que OAuth por marca; punto único de rotación si se revoca

**Escalonamiento de rate limits**: las corridas de Meta se reparten en horarios fijos
(02:00, 08:00, 14:00, 20:00 UTC), usando ~50-60 de los 200 requests/hora disponibles
en cada ventana, dejando margen para triggers manuales.

---

## 8. Motor de Análisis NLP

### 8.1 Cascada de análisis (3 niveles)

```
Texto de la mención
      │
      ▼
┌─────────────────────────────┐
│ 1. Léxico Dominicano        │  detect_dominican_sentiment()
│    (override prioritario)   │  Si hay match → label inmediato (conf 0.90)
└─────────────┬───────────────┘
              │ sin match
              ▼
┌─────────────────────────────┐
│ 2. Gemini 2.0 Flash         │  Prompt con contexto del conglomerado
│    (analizador principal)   │  Salida JSON estructurada
└─────────────┬───────────────┘
              │ falla/timeout
              ▼
┌─────────────────────────────┐
│ 3. Heurístico Demo          │  Conteo de palabras pos/neg ponderadas
│    (red de seguridad)       │  Nunca falla → siempre hay resultado
└─────────────────────────────┘
```

### 8.2 Léxico dominicano (`processors/dominican_lexicon.py`)

Diccionarios globales (aplican a todas las marcas, son palabras del idioma):

- **Positivos** (~20 términos): jevi, nítido, brutal, chévere, bacano, de primera, tremendo, enchulao...
- **Negativos** (~17 términos): en olla, dando carpeta, manganzón, jodido, desmadre, caído, en crisis...

Función `detect_dominican_sentiment(text)` retorna `{override, sentiment, term_found, term_meaning}`.

> El léxico tiene **prioridad absoluta**: si aparece un término dominicano, ese determina
> el sentimiento sin consultar a Gemini. Limitación conocida: no maneja negación
> contextual ("no estuvo jevi"). Aceptable para la demo.

### 8.3 Contrato del analizador

```python
def analyze(self, text: str, language: str = "auto") -> dict:
    """
    {
      "label": "positive" | "negative" | "neutral" | "mixed",
      "scores": {"positive": float, "negative": float, "neutral": float},
      "confidence": float,
      "dominican_override": bool,
      "dominican_term": str | None,
      "method": "dominican_lexicon" | "gemini" | "demo"
    }
    """
```

El reemplazo Azure→Gemini mantiene **esta firma exacta**, por lo que `main.py` y los
colectores no requieren cambios en cómo invocan el análisis.

### 8.4 Prompt contextualizado de Gemini

```
Eres un analizador de sentimiento especializado en español dominicano.

CONTEXTO: Analizas menciones de "{entity.name}" que opera dentro de
"{conglomerate.name}" ({conglomerate.context_description}).

TAREA: Clasifica el sentimiento. Conoces modismos dominicanos:
jevi (excelente), nítido (perfecto), en olla (en problemas)...

TEXTO: {text}

Responde SOLO con JSON:
{"label": "...", "scores": {...}, "confidence": 0.0, "reasoning": "..."}
```

Modelo: `gemini-2.0-flash`, con `response_mime_type=application/json`.

---

## 9. Estrategia de Ejecución

### 9.1 La idea clave: local-first

La primera corrida (histórico de 2 años) se ejecuta **localmente en la laptop**, evitando
todas las complicaciones de límites de GitHub Actions. Una vez la base de datos está
poblada, GitHub Actions solo se encarga del **mantenimiento incremental** diario.

```
┌─────────────────────────────────────────────────────────────┐
│  FASE 1 — PRIMERA CORRIDA (laptop local, 6-8 horas, 1 vez)  │
│                                                             │
│  python main.py --first-run --all-collectors \              │
│                 --conglomerate=zona-franca                   │
│                                                             │
│  Horas 1-2:  RSS + Google News + Reddit (paralelo)          │
│  Horas 3-4:  Google Reviews (Playwright, lento)             │
│  Horas 5-6:  Instagram (escalonado por rate limit)          │
│  Horas 6-8:  Facebook + NLP + escritura a Supabase          │
│                                                             │
│  Resultado: ~5,000-6,000 menciones en Supabase ✅          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  FASE 2 — MANTENIMIENTO (GitHub Actions, post-demo)         │
│                                                             │
│  Cron 06:00 y 18:00 UTC → modo incremental                  │
│  Solo lo nuevo del día, todos los colectores                │
│  ~60-90 min/día → ~1,800 min/mes ≤ 2,000 free tier ✅      │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Presupuesto de la demo (Zona Franca)

| Aspecto | Valor |
|---------|-------|
| Empresas en el sistema | 35 (15 prioritarias + 20 on-demand) |
| Primera corrida | Local, sin costo de Actions |
| Cron diario (post-demo) | 2 runs/día × ~30 min = ~1,800 min/mes |
| Triggers manuales | 10/mes por empresa × ~3 min = margen holgado |
| **Total Actions** | **~1,800 min/mes** (dentro de 2,000) ✅ |

### 9.3 Modos del scraper

| Flag | Comportamiento |
|------|----------------|
| `--first-run` | Histórico completo (2 años RSS/News/Reddit, 3 meses Meta) |
| `--all-collectors` | Activa los 6 colectores |
| `--collectors=rss,reddit` | Solo los listados |
| `--conglomerate=zona-franca` | Conglomerado objetivo |
| `--entity-filter=swisher-dominicana` | Una sola entidad (trigger manual) |
| `--dry-run` | Recolecta y muestra, no escribe a BD |

---

## 10. Estructura del Repositorio

```
desarrollo-cloned/social-intelligence-hub/
│
├── frontend/                       # Next.js 15 + Vercel
│   ├── app/
│   │   ├── page.tsx                # Home: dashboard del conglomerado
│   │   ├── entidad/[slug]/page.tsx # Dashboard de entidad
│   │   ├── error.tsx               🆕 Error boundary
│   │   └── api/
│   │       ├── entities/route.ts
│   │       ├── mentions/route.ts
│   │       ├── stats/route.ts
│   │       └── search-entity/route.ts  🆕 scraper bajo demanda
│   ├── components/                 # (sin cambios — reutilizables)
│   │   ├── KpiCard.tsx
│   │   ├── SentimentChart.tsx
│   │   ├── MentionCard.tsx
│   │   ├── SearchBar.tsx
│   │   ├── DisambiguationModal.tsx
│   │   └── DateRangeFilter.tsx
│   └── lib/
│       └── supabase.ts             ✏️ quitar key hardcodeada + queries conglomerado
│
├── scraper/                        # Python 3.13
│   ├── main.py                     ✏️ orquestación multi-colector + flags
│   ├── requirements.txt            ✏️ google-genai (SDK nuevo) + librerías Meta
│   ├── .env.example                ✏️ nuevas variables
│   ├── collectors/
│   │   ├── google_alerts.py        (RSS + Google News)
│   │   ├── reddit_collector.py     (sin cambios)
│   │   ├── google_reviews.py       ✏️ acepta google_maps_url del config
│   │   ├── active_search.py        ✏️ acepta search_queries del config
│   │   ├── relevance_filter.py     ✏️ función genérica declarativa
│   │   ├── instagram_collector.py  🆕
│   │   ├── facebook_collector.py   🆕
│   │   └── tiktok_collector.py     🆕 (stub)
│   ├── processors/
│   │   ├── gemini_sentiment.py     🆕 reemplaza azure_sentiment.py
│   │   ├── dominican_lexicon.py    ✏️ generalizar disambiguate
│   │   └── relevance_filter.py     (semántico, embeddings)
│   ├── setup/
│   │   └── discover_entities.py    🆕 auto-discovery + generación de queries
│   └── run_cleanup.py
│
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql          (existe)
│       ├── 002_conglomerates.sql           🆕
│       ├── 003_update_entities.sql         🆕
│       ├── 004_entity_configs.sql          🆕
│       ├── 005_rls_policies.sql            🆕
│       └── 006_zona_franca_seed.sql        🆕 (35 empresas + configs)
│
└── .github/workflows/
    ├── daily-incremental.yml       🆕 cron 06:00/18:00 UTC
    └── manual-single-entity.yml    🆕 trigger manual por empresa
```

**Leyenda**: 🆕 nuevo · ✏️ editar · (resto) sin cambios

---

## 11. Plan de Implementación

### Fase 0 — Higiene (30 min)
- Crear rama `feat/v3-local-first`
- Confirmar que el repo clonado corre en local (`npm run dev`, `python main.py --dry-run`)

### Fase 1 — Schema SQL (1 h)
Ejecutar migraciones 002→006 en Supabase. Verificar:
`SELECT COUNT(*) FROM entities WHERE conglomerate_id = (SELECT id FROM conglomerates WHERE slug='zona-franca')` → 35.

### Fase 2 — Scraper genérico (3-4 h)
- Crear `gemini_sentiment.py` (respeta el contrato de `analyze()`)
- Crear `instagram_collector.py`, `facebook_collector.py`, `tiktok_collector.py` (stub)
- Reescribir `relevance_filter.py` como motor declarativo (recibe `config: dict`)
- Editar `main.py` para orquestación multi-colector + flags
- Swap de dependencias en `requirements.txt`
- **Test**: `python main.py --first-run --all-collectors --conglomerate=zona-franca --dry-run`

### Fase 3 — Frontend (2-3 h, paralelo a Fase 2)
- `lib/supabase.ts`: quitar Service Role Key hardcodeada, añadir queries de conglomerado
- `app/page.tsx`: home muestra datos del conglomerado (no hardcodeado)
- `SearchBar.tsx`: autocomplete desde `entities` del conglomerado activo
- Crear `app/error.tsx`

### Fase 4 — Setup de Zona Franca (1 h)
- Ejecutar `discover_entities.py` contra el directorio de la Zona Franca
- Revisar entidades generadas en Supabase Studio
- Marcar 15 empresas como `priority=TRUE`

### Fase 5 — Primera corrida local (6-8 h)
- `python main.py --first-run --all-collectors --conglomerate=zona-franca`
- Configurar la laptop para NO suspender + conectada a corriente
- Validar: `SELECT COUNT(*), collector_type FROM mentions GROUP BY collector_type`

### Fase 6 — Despliegue Vercel (30 min)
- Conectar frontend a Supabase (ya poblada)
- Env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Deploy → URL pública `*.vercel.app`

### Fase 7 — GitHub Actions mantenimiento (15 min)
- Subir `daily-incremental.yml` y `manual-single-entity.yml`
- Agregar secrets al repo
- Verificar primer cron run

### Fase 8 — Panel de admin (post-demo, iteración futura)
- Formulario para agregar entidades sin SQL
- Botón "generar queries con Gemini" al crear entidad
- Toggle de `priority` desde UI

### Timeline

| Sesión | Contenido | Duración |
|--------|-----------|----------|
| 1 | Fases 0-2 (higiene + SQL + scraper) | 4-5 h |
| 2 | Fase 3 (frontend, paralelizable) | 2-3 h |
| 3 | Fases 4-7 (setup + corrida + deploy) | corrida 6-8 h + 1.5 h activa |

**Total trabajo activo**: 13-17 h en 2-3 sesiones.

---

## 12. Configuración y Secrets

### Variables de entorno

**Local (`scraper/.env`)** y **GitHub Actions secrets**:
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
GEMINI_API_KEY
INSTAGRAM_ACCESS_TOKEN
FACEBOOK_ACCESS_TOKEN
```

**Vercel (frontend)**:
```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
```

### Saneamiento de seguridad obligatorio

> **Hallazgo crítico**: el repo clonado tiene la **Service Role Key hardcodeada** en
> `frontend/lib/supabase.ts`. Esta clave da acceso total a la BD saltando RLS.
> **Debe corregirse antes del deploy** (Fase 3): usar solo `anon key` en el cliente,
> habilitar RLS con políticas de lectura pública (migración 005), y dejar las
> escrituras exclusivamente al scraper con Service Role Key del lado servidor.

---

## 13. Costos

```
Supabase   $0   (free tier: 500 MB + 50k API calls/día)
Vercel     $0   (hobby plan)
Gemini     $0   (free tier: 1M tokens/día)
GitHub     $0   (2,000 min/mes; uso ~1,800)
Dominio    $0   (*.vercel.app)
─────────────────────────────────────────
TOTAL      $0/mes
```

**Migración futura** (cuando el cliente pague): VPS Hetzner/Vultr ~$3-5/mes para
monitoreo diario uniforme sin límites de Actions.

---

## 14. Riesgos y Mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|--------|-------|---------|------------|
| Service Role Key expuesta en cliente | Alta si no se corrige | Crítico | Fase 3 obligatoria; bloquea deploy |
| Laptop se suspende en media corrida | Media | Alto | NO SLEEP + alimentación conectada |
| Tokens Meta vencen/revocados | Media | Medio | Verificar antes de correr; rotación documentada |
| Google bloquea Playwright (Reviews) | Media | Bajo | Fallback de datos reales ya existe |
| Confusión Santiago RD vs Santiago Chile | Media | Alto | `forbidden_domains=['.cl']` + `geo_requirement='santiago_rd'` |
| "CAPEX" como término financiero (no la institución) | Media | Alto | `disambiguation` con señales formativas vs financieras |
| Gemini supera free tier | Baja | Medio | ~60k tokens en 1ra corrida vs 1M/día; cascada con fallback |
| Refactor rompe entidades CZFS existentes | Media | Medio | Migración 003 reproduce comportamiento actual con fidelidad |
| Auto-discovery falla (web cambia) | Media | Medio | Fallback a importación manual CSV |

---

## 15. Verificación End-to-End

| Test | Comando / Acción | Pasa si |
|------|------------------|---------|
| **1. Scraper dry-run** | `python main.py --first-run --all-collectors --dry-run` | Lista menciones por colector sin errores |
| **2. BD poblada** | `SELECT COUNT(*) FROM mentions` | ~5,000-6,000 registros |
| **3. NLP contextualizado** | Revisar campo `reasoning` en menciones | Menciona el contexto del conglomerado |
| **4. Frontend home** | `npm run dev` → localhost:3000 | Muestra dashboard del conglomerado, no de una empresa |
| **5. Búsqueda** | Buscar "Swisher" | Navega a mini-dashboard de la empresa |
| **6. Genericidad** | INSERT empresa nueva en Studio + run | Scraper la recoge sin tocar código |
| **7. Seguridad** | Network tab del navegador | Solo `anon key` visible; INSERT desde consola → RLS rechaza |
| **8. Mantenimiento** | Esperar cron 06:00 UTC | Artifact de logs generado, count de mentions sube |

---

## 16. Roadmap Futuro

| Mejora | Disparador | Esfuerzo estimado |
|--------|-----------|-------------------|
| **Aprobación Meta (IG + FB)** | Business Verification de Meta | Solicitud ya en curso; activar al aprobar |
| **TikTok** | Definir vía Research API o scraping | 2-3 días post-decisión |
| **Expansión histórica Meta a 2 años** | Automático tras 1ra corrida | ~8 semanas (1 mes extra/semana) |
| **Panel de admin (UI)** | Post-demo | Fase 8 |
| **Alertas de crisis activas** | Definir umbrales por marca | 2-3 días |
| **Loop de aprendizaje** | Correcciones del operador → few-shot Gemini | 3-4 días |
| **Búsqueda omnifuente estilo Perplexity** | Decisión de producto | 1 semana |
| **Despliegue Ágora Santiago** | Tras validar Zona Franca | ~1 día (mismo proceso) |
| **Migración a multi-tenant** | Crecimiento + capital | 3-5 días |
| **VPS dedicado** | Cliente paga | 1 día |

### Sobre las alertas de crisis (pendiente de definición)

La tabla `crisis_alerts` existe pero su lógica de disparo no está implementada. Tipos
contemplados: `sentiment_drop`, `volume_spike`, `negative_surge`. Falta definir umbrales
(ej: ¿`negative_surge` = >50% menciones negativas en 24h?) y el canal de notificación
(badge en dashboard, email, webhook).

### Próximo conglomerado de referencia: Ágora Santiago Center

No se aborda hasta validar Zona Franca, pero la investigación ya está hecha para acelerar
el despliegue futuro:

| Campo | Dato |
|-------|------|
| Tipo | Centro comercial (retail / consumo) |
| Apertura | Abril 2025 · Santiago |
| Tamaño | 120,000 m², 180+ establecimientos |
| Instagram | @agorasantiagocenter (161K seguidores) |
| Web (auto-discovery) | agora.com.do/santiago/establecimientos/ |
| Marcas | Zara, H&M, Nike, Adidas, Starbucks, Jumbo, Pandora, MAC, Samsung... |
| Ventaja técnica | Retail SÍ tiene reseñas + redes → los 6 colectores aplican plenamente |
| Riesgo | Existe un Ágora Mall en Santo Domingo (distinto) → excluir "Santo Domingo" |

Al ser instancias separadas, desplegar Ágora es replicar el proceso de Zona Franca con su
propio Supabase + Vercel + GitHub y correr `discover_entities.py` sobre su directorio.

---

## 17. Glosario

| Término | Definición |
|---------|------------|
| **Conglomerado** | Cliente del producto: zona franca, mall, grupo empresarial. Contiene N entidades. |
| **Entidad** | Empresa, tienda o local dentro de un conglomerado (Swisher, CAPEX, La Aurora). |
| **Mención** | Una pieza de contenido (noticia, post, reseña, comentario) sobre una entidad. |
| **Colector** | Módulo que extrae menciones de una fuente específica. |
| **Setup** | La configuración declarativa de una entidad en `entity_configs`. |
| **Primera corrida** | Ingesta histórica inicial (local, 6-8 h). |
| **Incremental** | Actualización diaria con solo lo nuevo (GitHub Actions). |
| **Léxico dominicano** | Diccionario de modismos para detección de sentimiento local. |
| **Desambiguación** | Resolver qué entidad se refiere usando el contexto del conglomerado. |
| **Priority** | Bandera que marca empresas monitoreadas en el cron diario (vs on-demand). |
| **RLS** | Row Level Security de Postgres/Supabase: aísla y protege datos. |

---

> **Estado del documento**: este `.md` consolida todas las decisiones validadas durante
> la fase de planificación. Sirve como referencia canónica del proyecto para el equipo
> técnico y como base de onboarding.

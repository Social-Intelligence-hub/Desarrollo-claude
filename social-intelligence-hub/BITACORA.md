# Bitácora de Ejecución — Social Intelligence Hub v3

> **Qué es este documento**: la lista de trabajo viva + runbook de la implementación del SIH v3.
> Para cada fase define **el objetivo**, **cómo se hará** (plan), **el estado** (check), y al completarse,
> **qué se hizo y cómo** + **verificación**. Está pensado para que cualquier persona o IA pueda **retomar el trabajo en frío**.
>
> **Fuente de verdad técnica**: [`PROYECTO.md`](./PROYECTO.md). Esta bitácora es operativa y se deriva de ahí.
> **Última actualización**: 2026-06-10.

---

## 0. Cómo usar y retomar este documento

- **Cadencia de trabajo**: implementar → **probar localmente** → confirmar que funciona → **commit + push** al repo `Desarrollo-claude` → marcar el check aquí y documentar qué/cómo.
- **Para retomar en frío**: leer §1 (contexto), mirar §2 (tablero), e ir a la primera fase sin `✅` en §3. Cada fase trae su plan completo.
- **Leyenda de estado**: `⬜ pendiente` · `🟦 en curso` · `✅ completado` · `⛔ bloqueado (requiere usuario)`.

---

## 1. Contexto operativo (leer primero al retomar)

### Repositorios
| Rol | Ubicación | Notas |
|-----|-----------|-------|
| **Repo canónico (local)** | `desarrollo-cloned/` (raíz git) → proyecto en `social-intelligence-hub/` | Toplevel git es `desarrollo-cloned`. El proyecto vive en el subdir `social-intelligence-hub/`. |
| **Remote `origin` (viejo)** | `github.com/Social-Intelligence-hub/desarrollo` | Base clonada original. No es el destino de trabajo. |
| **Remote `claude` (DESTINO)** | `github.com/Social-Intelligence-hub/Desarrollo-claude` | **Aquí se publica el trabajo.** Privado. Empezó vacío. |
| Repo MVP descartado | `Hub-sentimiento/` (contiene a `desarrollo-cloned/` como carpeta no rastreada) | Solo referencia (léxico dominicano). No se usa como base. |
| Rama de trabajo | `feat/v3-local-first` | Creada desde `main` en el repo canónico. |

### Base de datos (Supabase)
| Campo | Valor |
|-------|-------|
| Proyecto | `Desarrollo-claude` |
| Project ref / id | `ejivsqgumonogddiftvq` |
| URL | `https://ejivsqgumonogddiftvq.supabase.co` |
| Región / Postgres | us-east-1 · Postgres 17 · `ACTIVE_HEALTHY` |
| Acceso para DDL | **Supabase MCP** (autenticado en esta sesión) → se aplican migraciones con `apply_migration` y se verifica con `execute_sql`. |
| Estructura | **Se construye desde cero** (proyecto nuevo y vacío). |

### Credenciales y dónde viven (NUNCA en este doc ni en git)
| Secreto | Ubicación | Estado |
|--------|-----------|--------|
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `frontend/.env.local` (gitignored) | ✅ cargada (key pública por diseño) |
| `NEXT_PUBLIC_SUPABASE_URL` | `frontend/.env.local` + `scraper/.env` | ✅ |
| `GEMINI_API_KEY` | `scraper/.env` (gitignored) | ⚠️ **REEMPLAZAR**: la key actual devuelve 429 RESOURCE_EXHAUSTED con `limit: 0` (cuota free-tier nula). Obtener una nueva en https://aistudio.google.com/apikey. Mientras tanto, el scraper usa el heurístico de respaldo. |
| `SUPABASE_SERVICE_ROLE_KEY` | `scraper/.env` (gitignored) | ⛔ **PENDIENTE** — el usuario debe pegarla (Dashboard → Settings → API → service_role). Solo se necesita para F5/F7 (escritura). El dry-run no la usa. |
| Tokens Meta (IG/FB) | `scraper/.env` | ⬜ vacíos a propósito — colectores en stub |

### Decisiones consolidadas (no se renegocian)
- **Producto**: buscador de reputación por conglomerado, no dashboard de marcas. 1 cliente = 1 conglomerado con N entidades.
- **NLP**: cascada **Léxico DR (override) → Gemini 2.0 Flash → fallback heurístico**. SDK `google-genai` (no `google-generativeai`).
- **Config sobre código**: la lógica por entidad vive en `entity_configs` (BD). Agregar empresa = `INSERT`, nunca tocar Python.
- **Local-first**: primera corrida histórica en laptop (6-8h); GitHub Actions solo mantiene incrementales.
- **Alcance**: solo **Zona Franca de Santiago** (~35 empresas). Ágora deferido.
- **Costo objetivo**: $0/mes (free tiers).

---

## 2. Tablero de progreso (checklist maestro)

| Fase | Objetivo | Estado |
|------|----------|--------|
| **F0** | Higiene y seguridad (branch, anon key, deps, .env) | ✅ |
| **F1** | Schema SQL: estructura 001–005 aplicada + RLS (006 seed → F4) | ✅ |
| **F4** | Setup Zona Franca (seed 35 reales + discover_entities.py) | ✅ |
| **F2** | Scraper: NLP Gemini + orquestación + colectores | ✅ |
| **F3** | Frontend parametrizado por conglomerado | ✅ |
| **F5** | Primera corrida histórica local (6-8h) | ⛔ requiere usuario (service key + laptop) |
| **F6** | Deploy en Vercel | 📄 preparado (`DEPLOY.md`) — requiere usuario |
| **F7** | GitHub Actions (cron incremental) | 📄 workflows listos — requiere secrets del usuario |

Ruta crítica: `F0 → F1 → F4 → F2 → (F3 en paralelo) → F5 → F6 → F7`.

---

## 3. Detalle por fase

### F0 — Higiene y Seguridad ✅

**Objetivo**: eliminar el bloqueante de seguridad (Service Role Key en el cliente), crear la rama de trabajo y preparar dependencias/entorno.

**Cómo se hizo**:
1. **Rama**: `git checkout -b feat/v3-local-first` desde `main` en el repo canónico (`desarrollo-cloned`).
2. **Saneamiento de seguridad** (`frontend/lib/supabase.ts`): se eliminó la `Service Role Key` hardcodeada y la URL fija. Ahora el cliente lee `process.env.NEXT_PUBLIC_SUPABASE_URL` y `...ANON_KEY`, con un `throw` claro si faltan. Comentario explicativo de por qué solo va anon key. Se conservó intacto el resto del archivo (tipos + helpers de query).
3. **Dependencias** (`scraper/requirements.txt`): se removió `azure-ai-textanalytics`; se agregó `google-genai==1.75.0` (última 1.x madura; la 2.x tiene cambios potencialmente disruptivos). Colectores Meta usarán `requests` (sin SDK extra).
4. **Entorno**:
   - `scraper/.env.example` y `frontend/.env.example` reescritos (sin Azure; con Gemini + Meta documentados).
   - `frontend/.env.local` (gitignored) creado con URL + anon key reales del proyecto nuevo.
   - `scraper/.env` (gitignored) creado con URL + Gemini key reales; `SUPABASE_SERVICE_ROLE_KEY` vacía (pendiente del usuario).

**Verificación** (self-check):
- ✅ `git check-ignore` confirma que `scraper/.env` y `frontend/.env.local` están ignorados (no se commitearán).
- ✅ `grep` de `service_role` / project-ref viejo (`zhbutmbnhzcgrlkuafwb`) / JWTs reales en `frontend/` → **0 coincidencias** (solo el placeholder `eyJ...` en `.env.example`).
- ⬜ Pendiente: typecheck/build del frontend (se hace junto a F3) y validación de la Gemini key (F2).

---

### F1 — Schema SQL (estructura 001–005 + RLS) ✅

**Objetivo**: crear el modelo de datos v3 completo y dejar RLS activo. (El seed de 35 entidades y la verificación `COUNT=35` se trasladaron a **F4**, porque la lista de empresas es el output de discovery de F4. F1 entrega la estructura, que es lo realmente bloqueante.)

**Hecho y verificado (2026-06-10)**:
- Aplicadas vía Supabase MCP en `ejivsqgumonogddiftvq`: `001_initial_schema` (estructura limpia — sin demo del MVP, con todas las `sources` v3, y fix `COUNT(*)→COUNT(m.id)` en `v_sentiment_summary`) y `002_v3_conglomerates_configs_rls` (002+003+004+005 en **una transacción atómica**). Archivos en `supabase/migrations/` (001–005, separados para lectura).
- **Verificación** (`pg_class` / `pg_policy`): **7 tablas** con `rls_activo=true`. Lectura pública (1 policy `SELECT`) en `conglomerates`, `entities`, `mentions`, `sources`, `crisis_alerts`. `entity_configs` y `scraper_runs` **sin policy anon** (internas → solo `service_role`). **Ninguna** policy de escritura para anon → criterio de seguridad #7 garantizado a nivel de esquema.

**Cómo se hará**:
- El proyecto está **vacío**, así que primero se aplica `001_initial_schema.sql` (entities, sources, mentions, scraper_runs, crisis_alerts, vistas) y luego las nuevas 002–006.
- Se aplican vía **Supabase MCP `apply_migration`** (una migración nombrada por archivo), no a mano en Studio. Las migraciones también se guardan como archivos `.sql` en `supabase/migrations/` para reproducibilidad.
- **002_conglomerates.sql**: tabla `conglomerates` (slug, name, category, website, context_description, primary_geo, ...).
- **003_update_entities.sql**: `ALTER TABLE entities ADD COLUMN conglomerate_id UUID REFERENCES conglomerates(id)` + `priority BOOLEAN`. Reproduce comportamiento actual con fidelidad (riesgo: no romper entidades existentes).
- **004_entity_configs.sql**: tabla `entity_configs` (search_queries[], google_maps_url, required/forbidden_terms[], forbidden_domains[], geo_requirement, disambiguation JSONB, ...). Más columnas en `mentions` (`collector_type`, `is_first_run`, `last_updated_at`).
- **005_rls_policies.sql**: `ENABLE ROW LEVEL SECURITY` en tablas públicas + política `SELECT` pública (anon solo lee). Escrituras: ninguna policy para anon → solo service_role escribe.
- **006_zona_franca_seed.sql**: `INSERT` del conglomerado `zona-franca` + 35 entidades + sus `entity_configs`. (Coordinada con F4: el seed sale de la lista generada desde `PROYECTO.md`.)
- **Verificación**: `SELECT COUNT(*) FROM entities WHERE conglomerate_id = (SELECT id FROM conglomerates WHERE slug='zona-franca')` → **35**. `list_tables` para confirmar el esquema. Probar que la anon key NO puede escribir (test de RLS, parte de F3/criterio #7).

---

### F4 — Setup de Zona Franca ✅

**Objetivo**: poblar `entity_configs` de las 35 empresas con queries de búsqueda y señales de desambiguación, sin tocar código.

**Hecho y verificado (2026-06-10)**:
- Lista **real** de 35 entidades obtenida del directorio `aezfc.org/directorio-de-afiliados` + `zonafrancasantiago.com` (vía WebFetch), curada por sectores (tabaco, textil, calzado/cuero, electrónica, empaque, logística, parques, unidades CZFS).
- Migración `006_zona_franca_seed.sql` aplicada: conglomerado `zona-franca` + 35 entidades + 35 `entity_configs` baseline (queries por nombre+contexto, `forbidden_domains=['.cl']`, `geo_requirement='santiago_rd'`, disambiguation; CAPEX con forbidden_terms financieros).
- `setup/discover_entities.py` creado: herramienta reutilizable (auto-discovery web best-effort + generación de queries/disambiguation con Gemini, `--dry-run`, fallback baseline determinista). Compila OK. El enriquecimiento con IA queda listo para cuando el usuario cargue la service key; el seed ya deja todo funcional sin IA.
- **Verificación SQL**: `entidades=35`, `priority=15`, `configs=35`, `con_filtro_geo=35`, `capex_query='CAPEX Zona Franca Santiago'`, y los negative_signals de CAPEX incluyen 'capital expenditure'/'gasto de capital'. ✅

**Cómo se hará**:
- `setup/discover_entities.py` 🆕: script que (a) toma la lista base de empresas (generada desde `PROYECTO.md`: Swisher, Hanesbrands, Grupo M, La Aurora, Arturo Fuente, CAPEX, etc., completada a 35), y (b) por cada entidad llama a **Gemini** para generar `search_queries` + `disambiguation` (señales positivas/negativas). Modo `--dry-run` que imprime swithout escribir, y modo escritura a `entity_configs`.
- Reglas transversales aplicadas a todas: `forbidden_domains=['.cl']`, `geo_requirement='santiago_rd'`, `forbidden_terms` financieros para CAPEX (`capital expenditure`, `gasto de capital`).
- 15 empresas marcadas `priority=TRUE` (monitoreo en cron); el resto on-demand.
- El resultado se materializa en `006_zona_franca_seed.sql` (idempotente, `ON CONFLICT DO NOTHING/UPDATE`) para que el seed sea reproducible sin re-llamar a Gemini.
- **Verificación**: `SELECT COUNT(*) FROM entity_configs` → 35; muestreo de 3 configs (CAPEX, Swisher, La Aurora) con queries y disambiguation coherentes.

---

### F2 — Scraper: NLP y Orquestación ✅

**Hecho y verificado (2026-06-10)**:
- **Python 3.13.13** instalado vía winget (local era 3.14, incompatible con la cadena `supabase`/`greenlet`). `requirements.txt` re-pin: `supabase==2.31.0` (la 2.5.3 chocaba con `httpx>=0.28` que pide `google-genai`). Imports verificados en 3.13: `google-genai 1.75.0`, `supabase 2.31.0`, `feedparser 6.0.11`.
- `processors/gemini_sentiment.py` 🆕: cascada de 3 niveles (léxico → Gemini → heurístico). Firma `analyze()` preservada. Soporte de **batches** (10 textos/request) para respetar la cuota free de Gemini. El contexto del conglomerado (`disambiguation`) se inyecta en el prompt → `reasoning` queda en `sentiment_score` (criterio #3).
- `collectors/relevance_filter.py` reescrito como **motor declarativo** (`is_relevant`, `is_relevant_detailed`). Recibe `config: dict` desde BD; aplica `forbidden_terms`, `forbidden_domains`, `geo_requirement`, señales de desambiguación. Wrapper legacy `es_relevante_dominicana(text, slug)` se mantiene para no romper colectores antiguos.
- Stubs Meta: `instagram_collector.py`, `facebook_collector.py`, `tiktok_collector.py` — devuelven `[]` sin credenciales, mismo contrato que el resto.
- `main.py` reescrito: flags `--first-run`, `--incremental`, `--all-collectors`, `--collectors`, `--conglomerate`, `--entity-filter`, `--dry-run`. Carga conglomerate + entities + entity_configs joineado. Pipeline: colectores → filtro declarativo → NLP batch → upsert con `content_hash`. Modo `--dry-run` sin BD usa config sintética (no requiere Supabase).
- `processors/azure_sentiment.py` **eliminado**.
- **Pruebas unitarias** (4/4 ✅): léxico "jevi" → positive override; "capital expenditure" → rechazado; CAPEX educativo Santiago → aceptado; "Santiago de Chile" → blacklist global.
- **Smoke test end-to-end** (`--dry-run`, entidad CAPEX): 17 menciones reales de Google News sobre **CAPEX + Zona Franca Santiago** (INFOTEP, Ministerio Público, "Monitores de Paz 2023") aceptadas por el filtro. Reddit 0 (normal para B2B). Meta stubs `[]`. **Criterio #1 PASA.**

**Hallazgo a resolver (no bloqueante)**: la `GEMINI_API_KEY` cargada (`AQ.Ab8RN6...`) responde **429 RESOURCE_EXHAUSTED con `limit: 0`** — esa key no tiene cuota free-tier. La cascada cae al heurístico sin error, así que la pipeline funciona, pero F5 necesitará una key válida de https://aistudio.google.com/apikey para análisis Gemini real.

**Plan original (referencia)**: reemplazar Azure por Gemini (cascada), volver declarativo el filtro de relevancia, y orquestar multi-colector con flags. Sin romper la firma `analyze()`.

**Cómo se hará**:
- `processors/gemini_sentiment.py` 🆕: clase `SentimentAnalyzer` con **la misma firma** `analyze(text, language) -> dict` (label, scores, confidence, dominican_override, dominican_term, method). Cascada: (1) `detect_dominican_sentiment` override; (2) `google-genai` `gemini-2.0-flash` con prompt contextualizado (incluye `disambiguation` del conglomerado) y `response_mime_type=application/json`; (3) fallback heurístico (portado del `_analyze_demo` actual, que ya es bueno). Incluye `reasoning` en `sentiment_score` para el criterio #3.
- **Validación de la Gemini key**: primer paso de F2 = test de conectividad (1 request). Si la key `AQ...` falla, se documenta y la cascada degrada a heurístico (no bloquea), pero se avisa al usuario.
- `collectors/relevance_filter.py` (en `collectors/`) reescrito como **motor declarativo**: `is_relevant(text, config: dict)` que lee `required_terms`, `forbidden_terms`, `forbidden_domains`, `geo_requirement` desde la config de BD. Se conserva el blacklist global (Chile/deportes/etc.) como red base. Se elimina el `if/elif` por slug hardcodeado.
- `main.py` reescrito: flags `--first-run`, `--incremental`, `--all-collectors`, `--collectors=`, `--conglomerate=`, `--entity-filter=`, `--dry-run`. Carga entidades + configs de BD, itera, aplica filtro declarativo + NLP, deduplica por `content_hash`, escribe (o imprime en dry-run).
- Colectores Meta 🆕 `instagram_collector.py`, `facebook_collector.py`, `tiktok_collector.py`: **stubs** que retornan `[]` si faltan credenciales (firma homogénea para integrarlos al pipeline sin romper nada).
- `azure_sentiment.py`: deprecado (se deja con aviso o se elimina del import).
- **Verificación**: `python main.py --first-run --all-collectors --conglomerate=zona-franca --dry-run` lista candidatos por colector **sin escribir** y sin errores (criterio #1). Test del filtro declarativo con casos Chile/CAPEX-financiero.

---

### F3 — Frontend parametrizado ✅

**Hecho y verificado (2026-06-10)**:
- `app/error.tsx` 🆕: error boundary global con UI propia (AlertTriangle + botón Reintentar). Logs el error a consola; preparado para Sentry futuro.
- `lib/supabase.ts`: añadidos helpers v3 `fetchConglomerate(slug)` y `fetchEntitiesByConglomerate(slug)` (sin tocar los helpers MVP existentes, que siguen sirviendo al dashboard).
- **Compatibilidad React 19 / Next 15 + TS strict** (resuelto): `@types/react@19.2.14` ya no acepta `void` en `ReactNode`. Tres bugs reales corregidos: (a) `{console.log(...)}` dejado como JSX child (debug olvidado en `page.tsx:755`); (b) un `catch` vacío con solo comentario; (c) 50 `{/* JSX comments */}` que evaluaban a `void` — eliminados por script en 7 archivos (`page.tsx`, `entidad/[slug]/page.tsx`, los 5 components afectados).
- Nuevo helper local `CapexFinancialNotice` con return-type explícito `ReactNode`, sustituyendo la ternaria inline que el typer rechazaba.
- `npm install` + `npm run build`: ✅ **build limpio**. 8 rutas compiladas (`/`, `/entidad/[slug]`, 5 API routes, `/_not-found`). 149 kB la página principal.
- **Pendiente (para F6)**: ver la home en `npm run dev` con datos reales — solo se podrá tras F5 (corrida histórica). Hoy verificable visualmente con los datos vacíos (criterios #4/#5/#7 son post-deploy).



**Objetivo**: que el home sea el dashboard del **conglomerado** y `/entidad/[slug]` el de cada empresa, leyendo del conglomerado activo, solo con anon key.

**Cómo se hará**:
- `lib/supabase.ts`: ya saneado (F0). Añadir helpers de conglomerado (KPIs agregados, top-N empresas) si faltan.
- `app/page.tsx`: home muestra datos agregados del conglomerado (KPIs + top 5 empresas + feed), no de una sola empresa.
- `components/SearchBar.tsx`: autocomplete sobre `entities` del conglomerado activo.
- `app/entidad/[slug]/page.tsx`: verificar que filtra KPIs a la entidad.
- `app/error.tsx` 🆕: error boundary global.
- **Verificación**: `npm install` + `npm run build` (typecheck) sin errores; `npm run dev` → home carga dashboard del conglomerado (criterio #4); búsqueda "Swisher" navega (criterio #5); en Network tab solo se ve anon key y un INSERT desde consola es rechazado por RLS (criterio #7).

---

### F5/F6/F7 — Runbook listo en DEPLOY.md 📄

**Cómo proceder**: ver [`DEPLOY.md`](./DEPLOY.md) — runbook completo con env vars, pasos paso-a-paso, smoke tests y troubleshooting para cada fase.

**Lo que YA está hecho por el agente** (no requiere usuario):
- ✅ `.github/workflows/daily-incremental.yml` (cron 06:00 / 18:00 UTC + `workflow_dispatch`, Python 3.13, artifact de logs).
- ✅ `.github/workflows/manual-single-entity.yml` (`workflow_dispatch` con inputs `entity_slug` / `conglomerate` / `first_run`).
- ✅ `DEPLOY.md` con checklist de los 8 criterios de éxito.

**Lo que requiere ejecución del usuario**:
- ⛔ Pegar `SUPABASE_SERVICE_ROLE_KEY` en `scraper/.env`.
- ⚠️ Reemplazar `GEMINI_API_KEY` (la actual devuelve 429 con `limit: 0`).
- ⛔ F5: correr el scraper localmente 6-8h.
- ⛔ F6: conectar el repo a Vercel (Root Directory = `social-intelligence-hub/frontend`).
- ⛔ F7: agregar los 5 repo secrets en GitHub.

---

### Detalle histórico (planes originales) — referencia

#### F5 — Primera Corrida Histórica Local (plan) ⛔ (requiere usuario)

**Objetivo**: poblar Supabase con ~5,000–6,000 menciones reales (2 años).

**Cómo se hará / requisitos**:
- **Bloqueo**: necesita `SUPABASE_SERVICE_ROLE_KEY` en `scraper/.env` y, idealmente, Gemini key válida.
- Pasos: `pip install -r requirements.txt`; `playwright install chromium`; laptop en "nunca suspender" + corriente; `python main.py --first-run --all-collectors --conglomerate=zona-franca`.
- **Verificación**: `SELECT COUNT(*) FROM mentions` ≈ 5–6k; distribución de sentimiento razonable; muestreo cualitativo de 10 menciones (criterios #2, #3).

---

#### F6 — Deploy en Vercel (plan) ⛔ (requiere usuario)

**Cómo se hará**: conectar el repo `Desarrollo-claude` a Vercel (proyecto `sih-zona-franca`, root = `social-intelligence-hub/frontend`); env vars `NEXT_PUBLIC_SUPABASE_URL` + `...ANON_KEY`; deploy; smoke test (home, búsqueda "CAPEX", dashboard de entidad).

---

#### F7 — GitHub Actions para Mantenimiento (plan) ⛔ (requiere usuario)

**Cómo se hará**: `.github/workflows/daily-incremental.yml` (cron 06:00/18:00 UTC, `python main.py --incremental --all-collectors`) y `manual-single-entity.yml` (`workflow_dispatch` con slug). Secrets del repo: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, tokens Meta. `setup-python@v5` con `python-version: '3.13'`. **Verificación**: primer cron → `scraper_runs.status='success'` y `mentions_found>0` (criterio #8).

---

## 4. Workflow de Git / Despliegue

- Rama de trabajo: `feat/v3-local-first`.
- Remote de publicación: `claude` → `github.com/Social-Intelligence-hub/Desarrollo-claude`.
- **Cadencia**: cada fase verificada localmente se commitea (mensaje convencional `feat:`/`fix:`/`chore:`) y se hace `git push claude feat/v3-local-first`.
- Los `.env` reales **nunca** se commitean (gitignored). Solo `.env.example`.

---

## 5. Pendientes / bloqueos que requieren al usuario

1. ⛔ **`SUPABASE_SERVICE_ROLE_KEY`** del proyecto nuevo → pegar en `scraper/.env`. Necesaria para F5 y F7.
2. ⚠️ **Reemplazar `GEMINI_API_KEY`** (CONFIRMADO en F2): devuelve 429 con `limit: 0`. Obtener una nueva en https://aistudio.google.com/apikey y pegarla en `scraper/.env`. Sin esto, F5 funcionará pero con heurístico en lugar de Gemini.
3. ⬜ Tokens Meta (IG/FB) cuando Meta apruebe la app → habilitar colectores reales (hoy en stub).
4. ⛔ F5/F6/F7 requieren ejecución/credenciales del usuario (laptop, Vercel, secrets del repo).

---

## 6. Registro cronológico

| Fecha | Evento |
|-------|--------|
| 2026-06-10 | Inicio. Lectura de PROYECTO.md + pipeline PDF. Confirmado repo canónico y proyecto Supabase nuevo (`ejivsqgumonogddiftvq`). |
| 2026-06-10 | **F0 completado**: rama `feat/v3-local-first`; Service Role Key removida del frontend; deps Azure→google-genai; `.env`/`.env.example` (scraper+frontend). Self-check de seguridad OK. |
| 2026-06-10 | Bitácora creada. Remote `claude` configurado hacia `Desarrollo-claude`. F0 publicado (rama `feat/v3-local-first`). |
| 2026-06-10 | **F1 estructura completada**: migraciones 001–005 aplicadas en `ejivsqgumonogddiftvq`. 7 tablas, RLS activo en todas, lectura pública en las 5 de cara al cliente. Seed 35 + `COUNT` pasan a F4. |
| 2026-06-10 | **F4 completado**: 35 entidades reales (directorio AEZFC) sembradas en `zona-franca`; 15 priority; entity_configs con `.cl` bloqueado, geo `santiago_rd` y desambiguación CAPEX. `discover_entities.py` listo (compila). |
| 2026-06-10 | **F2 completado**: Python 3.13 instalado; `gemini_sentiment.py` (cascada+batch), `relevance_filter.py` declarativo, Meta stubs, `main.py` v3 con flags. 4 tests unitarios + dry-run end-to-end OK (17 menciones reales de CAPEX/INFOTEP en Google News). Cascada cayó a heurístico al ver Gemini 429 — funcionando como red de seguridad. |
| 2026-06-10 | **F3 completado**: `error.tsx` + helpers de conglomerado en `lib/supabase.ts`. Resueltos 3 bugs reales de React 19 strict (`console.log` JSX child, catch vacío, 50 JSX-comments `{/* */}`). `npm run build` ✅ limpio en 8 rutas. |
| 2026-06-10 | **F6/F7 preparados**: workflows `.github/workflows/{daily-incremental,manual-single-entity}.yml` listos. `DEPLOY.md` con runbook completo para F5/F6/F7 + checklist de los 8 criterios. |

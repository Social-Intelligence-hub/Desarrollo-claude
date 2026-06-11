# Despliegue — Social Intelligence Hub v3

Runbook operativo para llevar el SIH v3 a producción (Corporación Zona Franca de Santiago).

Las fases F0–F4 + F2 + F3 ya están **implementadas y verificadas** (ver [`BITACORA.md`](./BITACORA.md)).
Este documento cubre las fases que necesitan ejecución/credenciales del operador: **F5 (primera corrida histórica), F6 (Vercel) y F7 (GitHub Actions)**.

---

## Pre-requisitos

| Recurso | Estado |
|--------|--------|
| Proyecto Supabase `Desarrollo-claude` (`ejivsqgumonogddiftvq`) con schema v3 aplicado | ✅ listo |
| 35 entidades sembradas + `entity_configs` | ✅ listo |
| `frontend/.env.local` con `NEXT_PUBLIC_SUPABASE_URL` + `...ANON_KEY` | ✅ listo (gitignored) |
| `scraper/.env` con `SUPABASE_URL` | ✅ listo |
| `scraper/.env` con `SUPABASE_SERVICE_ROLE_KEY` | ⛔ **TÚ debes pegarla** — Supabase Dashboard → Settings → API → service_role (secret) |
| `scraper/.env` con `GEMINI_API_KEY` (válida) | ⚠️ La actual devuelve 429 con quota 0; reemplazar desde https://aistudio.google.com/apikey |
| Python **3.13** en la laptop (no 3.14) | ✅ instalado |
| Cuenta de Vercel | ⬜ |
| Cuenta de GitHub con acceso al repo `Desarrollo-claude` | ✅ |

---

## F5 — Primera corrida histórica (laptop local · 6-8h)

> ⚠️ Esta es la corrida grande que poblará Supabase con ~5,000–6,000 menciones de los últimos 2 años.
> Se hace **una sola vez**, localmente, para no chocar con los límites de GitHub Actions.

### Pasos

```powershell
# 1) Variables — confirma que scraper\.env tenga SERVICE_ROLE_KEY y GEMINI_API_KEY válida.
cd desarrollo-cloned\social-intelligence-hub\scraper
notepad .env

# 2) Instala dependencias (si no se hizo en F2).
py -3.13 -m pip install -r requirements.txt
py -3.13 -m playwright install chromium

# 3) Configura la laptop:
#    - Energía → "Nunca suspender"
#    - Cargador conectado
#    - Wi-Fi estable

# 4) Dry-run de control (lista candidatos sin escribir):
py -3.13 main.py --first-run --all-collectors --conglomerate zona-franca --dry-run

# 5) Corrida real (déjala correr; logs en scraper\scraper.log):
py -3.13 main.py --first-run --all-collectors --conglomerate zona-franca
```

### Verificación al final (criterios #2, #3, #6)

En Supabase SQL Editor:

```sql
-- Criterio #2: BD poblada
SELECT COUNT(*) FROM mentions;
-- Esperado: 5,000–6,000 (rango razonable; depende de la fecha)

-- Distribución por colector
SELECT collector_type, COUNT(*) FROM mentions GROUP BY collector_type ORDER BY 2 DESC;

-- Criterio #3: NLP contextualizado — el reasoning debe mencionar Zona Franca/Santiago
SELECT entity_id, sentiment_label, sentiment_score->>'reasoning' AS reasoning
FROM mentions
WHERE sentiment_score->>'reasoning' IS NOT NULL
ORDER BY collected_at DESC LIMIT 10;
```

---

## F6 — Deploy en Vercel (30 min)

El repo monorepo tiene **dos roots posibles**:
- raíz git: `desarrollo-cloned/`
- frontend Next.js: `desarrollo-cloned/social-intelligence-hub/frontend/`

Vercel necesita saber que el frontend está en el subdirectorio.

### Pasos

1. **Conectar el repo a Vercel**
   - Vercel Dashboard → New Project → Import Git Repository
   - Elegir `Social-Intelligence-hub/Desarrollo-claude`
   - **Framework Preset**: Next.js (auto-detect)
   - **Root Directory**: `social-intelligence-hub/frontend`   ← importante
   - **Build & Output Settings**: defaults de Next.js 15
   - Nombre del proyecto sugerido: `sih-zona-franca`

2. **Configurar Environment Variables** (Vercel Dashboard → Settings → Environment Variables)
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://ejivsqgumonogddiftvq.supabase.co` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | (la anon key del proyecto Supabase) |

   ✅ **NUNCA** pegar la `SUPABASE_SERVICE_ROLE_KEY` aquí — solo en el scraper.

3. **Deploy**: botón "Deploy". URL pública: `https://sih-zona-franca-XXX.vercel.app`.

### Smoke test (criterios #4, #5, #7)

- `/` (home): se ve el dashboard del **conglomerado** con KPIs agregados (no de una sola empresa).
- Buscar "Swisher" → navega a `/entidad/swisher-dominicana` con KPIs.
- DevTools → Network: solo aparece la **anon key** (verifica que no haya nada con `role:service_role`).
- DevTools → Console:
  ```js
  // Intento de INSERT desde el cliente → RLS debe rechazar.
  await window.fetch(
    "https://ejivsqgumonogddiftvq.supabase.co/rest/v1/mentions",
    { method: "POST",
      headers: { apikey: "<anon>", Authorization: "Bearer <anon>", "Content-Type": "application/json" },
      body: JSON.stringify({ text_original: "test" })
    }
  ).then(r => r.status)  // → 401 o 403 (RLS rechaza)
  ```

---

## F7 — GitHub Actions de mantenimiento (15 min)

Los workflows ya están en el repo (`.github/workflows/`):
- **`daily-incremental.yml`**: corre cada día a 06:00 y 18:00 UTC.
- **`manual-single-entity.yml`**: trigger manual con `entity_slug` como input.

### Configurar repo secrets

GitHub → repo `Desarrollo-claude` → Settings → Secrets and variables → Actions → New repository secret.

| Secret | Valor |
|--------|-------|
| `SUPABASE_URL` | `https://ejivsqgumonogddiftvq.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | (service_role del proyecto Supabase) |
| `GEMINI_API_KEY` | (Gemini key válida) |
| `INSTAGRAM_ACCESS_TOKEN` | (opcional — sin esto, IG en stub) |
| `FACEBOOK_ACCESS_TOKEN` | (opcional) |

### Validación (criterio #8)

1. **Trigger manual** del workflow `manual-single-entity.yml` con `entity_slug=swisher-dominicana`.
2. Confirmar `status: success` y el artifact `scraper.log`.
3. En Supabase:
   ```sql
   SELECT * FROM scraper_runs ORDER BY started_at DESC LIMIT 5;
   -- status='success', mentions_found > 0
   ```
4. Esperar al primer cron (06:00 UTC) y verificar igual.

---

## Checklist final (los 8 criterios del PROYECTO.md §15)

- [ ] **#1** Dry-run del scraper lista candidatos sin errores — ✅ ya verificado en F2.
- [ ] **#2** `SELECT COUNT(*) FROM mentions` ≈ 5,000–6,000 — requiere F5.
- [ ] **#3** `sentiment_score.reasoning` menciona el contexto del conglomerado — requiere F5 con Gemini key válida.
- [ ] **#4** Home muestra el dashboard del conglomerado — requiere F6.
- [ ] **#5** Buscar "Swisher" navega a `/entidad/swisher-dominicana` — requiere F6.
- [ ] **#6** INSERT de empresa nueva en Studio + corrida → menciones llegan sin tocar código — requiere F5 (validable post-corrida).
- [ ] **#7** Solo anon key en Network; INSERT desde consola rechazado por RLS — requiere F6.
- [ ] **#8** Primer cron 06:00 UTC genera artifact y aumenta el count — requiere F7.

---

## Si algo falla

| Síntoma | Causa probable | Acción |
|---------|---------------|--------|
| Scraper: "Faltan SUPABASE_URL / SERVICE_ROLE_KEY" | `.env` incompleto | Pegar service_role key |
| Scraper: cascada cae a heurístico siempre | Gemini key inválida (429 limit:0) | Reemplazar `GEMINI_API_KEY` desde aistudio.google.com |
| Vercel build: "Module not found" | Root Directory incorrecto | Setear a `social-intelligence-hub/frontend` |
| Vercel runtime: "Faltan NEXT_PUBLIC_SUPABASE_*" | Env vars no configuradas en Vercel | Añadirlas en Settings → Environment Variables |
| GitHub Actions falla en `pip install` | Cache corrupto | Re-run del job; `cache-dependency-path` apunta al `requirements.txt` correcto |
| `SELECT FROM mentions` con anon key devuelve 0 filas | RLS bloquea sin policy | Confirmar migración 005 aplicada (debería) |
| Laptop suspendió a media corrida | Plan de energía | Reanudar con `--first-run` — `content_hash` deduplica lo ya cargado |

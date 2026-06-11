# -*- coding: utf-8 -*-
"""
discover_entities.py — Setup declarativo por conglomerado (F4).

Hace DOS cosas, ambas opcionales y desacopladas del scraper:

  1) (Opcional) AUTO-DISCOVERY: descubre nombres de empresas candidatas desde
     el directorio web del conglomerado (best-effort con BeautifulSoup).
  2) ENRIQUECIMIENTO: por cada entidad del conglomerado, pide a Gemini que genere
     `search_queries` + `disambiguation` (señales positivas/negativas) usando el
     CONTEXTO del conglomerado, y los escribe en `entity_configs`.

Principio rector: esto es CONFIGURACIÓN, no código. El scraper nunca cambia;
solo lee `entity_configs`. Agregar/ajustar una entidad = correr esto (o un INSERT).

Uso:
  python setup/discover_entities.py --conglomerate zona-franca --dry-run
  python setup/discover_entities.py --conglomerate zona-franca            # escribe
  python setup/discover_entities.py --conglomerate zona-franca --entity capex
  python setup/discover_entities.py --discover-web https://aezfc.org/directorio-de-afiliados

Requisitos:
  - SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY en scraper/.env (para leer/escribir).
  - GEMINI_API_KEY para la generación con IA (si falta o falla, usa baseline local).
"""

import argparse
import json
import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scraper/
sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("discover_entities")


# ============================================================
# Supabase
# ============================================================
def get_supabase():
    """Cliente Supabase con service_role (lectura + escritura)."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY en scraper/.env")
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        logger.error(f"No se pudo inicializar Supabase: {e}")
        return None


def load_conglomerate(supabase, slug):
    res = supabase.table("conglomerates").select("*").eq("slug", slug).limit(1).execute()
    return res.data[0] if res.data else None


def load_entities(supabase, conglomerate_id, only_slug=None):
    q = supabase.table("entities").select("*").eq("conglomerate_id", conglomerate_id)
    if only_slug:
        q = q.eq("slug", only_slug)
    return q.order("priority", desc=True).execute().data or []


# ============================================================
# Gemini — generación de queries + desambiguación
# ============================================================
def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY ausente — se usará baseline local (sin IA).")
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning(f"google-genai no disponible ({e}) — baseline local.")
        return None


def gemini_generate_config(client, entity, conglomerate):
    """
    Pide a Gemini search_queries + disambiguation para una entidad, en el contexto
    del conglomerado. Devuelve dict o None si falla.
    """
    if client is None:
        return None

    prompt = f"""Eres un experto en inteligencia de reputación y búsqueda web para el conglomerado
"{conglomerate['name']}" ({conglomerate.get('context_description', '')}).
Geografía principal: {conglomerate.get('primary_geo', 'Santiago, RD')}.

Genera la configuración de búsqueda para la entidad "{entity['name']}"
(categoría: {entity.get('category')}, alias conocidos: {entity.get('keywords')}).

Devuelve SOLO un JSON con esta forma exacta:
{{
  "search_queries": ["3 a 5 variantes de búsqueda que aíslen a esta entidad EN ESTE conglomerado y geografía"],
  "disambiguation": {{
    "positive_signals": ["términos que confirman que la mención es de esta entidad/ecosistema"],
    "negative_signals": ["términos que indican un homónimo o contexto equivocado a excluir"]
  }},
  "forbidden_terms": ["términos que, si aparecen, descartan la mención"]
}}

Reglas: el contexto dominicano (Santiago RD) manda; excluye Santiago de Chile y dominios .cl.
Si la entidad es un término ambiguo (p.ej. CAPEX = capacitación, no 'capital expenditure'),
refleja esa desambiguación en las señales y forbidden_terms."""

    try:
        from google.genai import types
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        data = json.loads(resp.text)
        # Validación mínima
        if "search_queries" in data and isinstance(data["search_queries"], list):
            return data
        logger.warning(f"Respuesta Gemini sin search_queries para {entity['slug']}")
        return None
    except Exception as e:
        logger.warning(f"Gemini falló para {entity['slug']}: {e}")
        return None


def baseline_config(entity, conglomerate):
    """Config baseline determinista (sin IA), idéntica al seed 006."""
    name = entity["name"]
    is_capex_like = "capex" in entity["slug"]
    return {
        "search_queries": [
            f"{name} Zona Franca Santiago",
            f"{name} Santiago República Dominicana",
            f"{name} Zona Franca",
        ],
        "disambiguation": (
            {
                "positive_signals": ["capacitación", "formación", "curso", "taller",
                                     "egresados", "técnico", "zona franca", "santiago"],
                "negative_signals": ["capital expenditure", "gasto de capital",
                                     "capex ratio", "depreciación", "chile"],
            }
            if is_capex_like else
            {
                "positive_signals": ["santiago", "república dominicana", "zona franca", "cibao"],
                "negative_signals": ["chile", "santiago de chile", "santo domingo"],
            }
        ),
        "forbidden_terms": (
            ["capital expenditure", "gasto de capital", "capex ratio"] if is_capex_like else []
        ),
    }


# ============================================================
# Escritura a entity_configs
# ============================================================
def upsert_config(supabase, entity, cfg):
    record = {
        "entity_id": entity["id"],
        "search_queries": cfg.get("search_queries", []),
        "required_terms": entity.get("keywords", []),
        "forbidden_terms": cfg.get("forbidden_terms", []),
        "forbidden_domains": [".cl"],
        "geo_requirement": "santiago_rd",
        "disambiguation": cfg.get("disambiguation", {}),
    }
    supabase.table("entity_configs").upsert(record, on_conflict="entity_id").execute()


# ============================================================
# Auto-discovery web (best-effort)
# ============================================================
def discover_from_web(url):
    """Lista nombres candidatos desde un directorio web. Best-effort (no escribe)."""
    try:
        import requests
        from bs4 import BeautifulSoup
        html = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
        soup = BeautifulSoup(html, "html.parser")
        candidates = set()
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "li", "td", "strong", "a"]):
            text = tag.get_text(strip=True)
            if 2 < len(text) < 60 and not text.lower().startswith(("http", "www")):
                candidates.add(text)
        logger.info(f"Candidatos encontrados en {url}: {len(candidates)}")
        for c in sorted(candidates):
            print(f"  - {c}")
        return candidates
    except Exception as e:
        logger.error(f"Auto-discovery falló: {e}. Fallback: importar lista manual desde CSV.")
        return set()


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Setup declarativo de entidades (F4)")
    parser.add_argument("--conglomerate", default="zona-franca", help="slug del conglomerado")
    parser.add_argument("--entity", default=None, help="procesar una sola entidad (slug)")
    parser.add_argument("--dry-run", action="store_true", help="genera e imprime; no escribe en BD")
    parser.add_argument("--discover-web", default=None, help="URL de directorio para listar candidatos")
    args = parser.parse_args()

    if args.discover_web:
        discover_from_web(args.discover_web)
        return

    supabase = get_supabase()
    if not supabase:
        sys.exit(1)

    cong = load_conglomerate(supabase, args.conglomerate)
    if not cong:
        logger.error(f"Conglomerado '{args.conglomerate}' no existe. Corre antes la migración 006.")
        sys.exit(1)

    entities = load_entities(supabase, cong["id"], args.entity)
    logger.info(f"Conglomerado '{cong['name']}' — {len(entities)} entidad(es) a procesar.")

    gem = get_gemini_client()
    used_ai, used_baseline = 0, 0

    for e in entities:
        cfg = gemini_generate_config(gem, e, cong)
        if cfg:
            used_ai += 1
            source = "gemini"
        else:
            cfg = baseline_config(e, cong)
            used_baseline += 1
            source = "baseline"

        if args.dry_run:
            print(f"\n=== {e['slug']} ({source}) ===")
            print(json.dumps(cfg, ensure_ascii=False, indent=2))
        else:
            upsert_config(supabase, e, cfg)
            logger.info(f"  ✓ {e['slug']} actualizado ({source})")

    logger.info(f"Listo. {used_ai} vía Gemini, {used_baseline} vía baseline. "
                f"{'(dry-run: no se escribió)' if args.dry_run else ''}")


if __name__ == "__main__":
    main()

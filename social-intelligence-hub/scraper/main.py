# -*- coding: utf-8 -*-
"""
Orquestador del Scraper — Social Intelligence Hub v3.

Lee del conglomerado activo en Supabase, itera entidades + entity_configs,
ejecuta los colectores pertinentes, aplica el filtro de relevancia DECLARATIVO
y el motor de sentimiento en cascada (léxico → Gemini → heurístico), y persiste
con deduplicación por content_hash.

Flags:
  --first-run                 Histórico completo (RSS/News/Reddit 2y, Meta 3m)
  --incremental               Solo lo nuevo desde la última corrida
  --all-collectors            Activa los 6 colectores disponibles
  --collectors rss,reddit     Solo los listados (coma separados)
  --conglomerate zona-franca  Conglomerado objetivo (slug)
  --entity-filter swisher     Solo una entidad (slug)
  --dry-run                   No escribe en BD; lista candidatos por colector

Ejemplo:
  python main.py --first-run --all-collectors --conglomerate zona-franca --dry-run
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(os.path.join(BASE_DIR, "scraper.log"), encoding="utf-8"),
              logging.StreamHandler()],
)
logger = logging.getLogger("main")

ALL_COLLECTORS = ["rss", "google_news", "reddit", "google_reviews", "instagram", "facebook", "tiktok"]


# ============================================================
# Supabase
# ============================================================
def get_supabase(dry_run: bool):
    if dry_run:
        return None
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY en scraper/.env")
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        logger.error("No se pudo inicializar Supabase: %s", e)
        return None


def load_workplan(supabase, conglomerate_slug: str, entity_filter: str | None) -> tuple[dict, list[dict]]:
    """
    Devuelve (conglomerado, [ {entity, config} ... ]).
    En --dry-run sin BD, devuelve un mínimo sintético basado en el filtro.
    """
    if supabase is None:
        synth_cong = {
            "slug": conglomerate_slug,
            "name": f"[DRY-RUN] {conglomerate_slug}",
            "context_description": "Conglomerado sintético para dry-run sin BD",
            "primary_geo": "Santiago, RD",
        }
        synth_entity = {
            "slug": entity_filter or "capex",
            "name": entity_filter or "CAPEX",
            "category": "educacion",
            "keywords": ["capex", "capacitación"],
            "priority": True,
        }
        synth_config = {
            "search_queries": [f"{synth_entity['name']} Zona Franca Santiago"],
            "required_terms": synth_entity["keywords"],
            "forbidden_terms": ["capital expenditure"],
            "forbidden_domains": [".cl"],
            "geo_requirement": "santiago_rd",
            "disambiguation": {
                "positive_signals": ["capacitación", "zona franca"],
                "negative_signals": ["capital expenditure", "chile"],
            },
        }
        return synth_cong, [{"entity": synth_entity, "config": synth_config}]

    cong = supabase.table("conglomerates").select("*").eq("slug", conglomerate_slug).limit(1).execute()
    if not cong.data:
        logger.error("Conglomerado '%s' no existe. Corre la migración 006.", conglomerate_slug)
        sys.exit(1)
    conglomerate = cong.data[0]

    q = supabase.table("entities").select("*, entity_configs(*)") \
        .eq("conglomerate_id", conglomerate["id"]).eq("active", True)
    if entity_filter:
        q = q.eq("slug", entity_filter)
    entities = q.order("priority", desc=True).execute().data or []

    workplan = []
    for e in entities:
        raw_cfg = e.pop("entity_configs", None)
        # Supabase puede devolver list (1-a-many) o dict (1-a-1 reconocido por PostgREST)
        if isinstance(raw_cfg, list):
            config = raw_cfg[0] if raw_cfg else {}
        elif isinstance(raw_cfg, dict):
            config = raw_cfg
        else:
            config = {}
        workplan.append({"entity": e, "config": config})
    return conglomerate, workplan


# ============================================================
# Resolución de colectores
# ============================================================
def resolve_collectors(args) -> list[str]:
    if args.all_collectors:
        return ALL_COLLECTORS
    if args.collectors:
        chosen = [c.strip() for c in args.collectors.split(",") if c.strip()]
        bad = [c for c in chosen if c not in ALL_COLLECTORS]
        if bad:
            logger.error("Colectores desconocidos: %s. Válidos: %s", bad, ALL_COLLECTORS)
            sys.exit(2)
        return chosen
    # Por defecto: los gratuitos sin credenciales
    return ["rss", "google_news", "reddit"]


# ============================================================
# Pipeline por entidad
# ============================================================
async def collect_for_entity(plan_item, conglomerate, collectors_active, analyzer, args):
    """Devuelve lista de menciones (dicts) ya con sentimiento aplicado."""
    from collectors.relevance_filter import is_relevant_detailed

    entity = plan_item["entity"]
    config = plan_item["config"]
    e_slug = entity["slug"]
    raw_mentions: list[dict] = []

    # ---- RSS + Google News (collector legacy: usa entity_slug) ----
    if "rss" in collectors_active or "google_news" in collectors_active:
        try:
            from collectors.google_alerts import GoogleAlertsCollector
            ga = GoogleAlertsCollector(sentiment_analyzer=None)
            if "google_news" in collectors_active:
                # Por cada search_query declarada en config, una llamada
                for q in (config.get("search_queries") or [entity["name"]])[:3]:
                    try:
                        raw_mentions.extend(ga.collect_from_google_news(e_slug, search_query=q, max_items=30))
                    except Exception as ex:
                        logger.warning("  google_news '%s' falló: %s", q, ex)
            if "rss" in collectors_active:
                try:
                    raw_mentions.extend(ga.collect_from_news_rss(e_slug))
                except Exception as ex:
                    logger.warning("  rss falló: %s", ex)
        except Exception as e:
            logger.warning("  RSS/News no disponible: %s", e)

    # ---- Reddit ----
    if "reddit" in collectors_active:
        try:
            from collectors.reddit_collector import RedditCollector
            rc = RedditCollector(sentiment_analyzer=None)
            for q in (config.get("search_queries") or [entity["name"]])[:2]:
                try:
                    raw_mentions.extend(rc.search_reddit(q, e_slug, limit=15))
                except Exception as ex:
                    logger.warning("  reddit '%s' falló: %s", q, ex)
        except Exception as e:
            logger.warning("  Reddit no disponible: %s", e)

    # ---- Google Reviews ----
    if "google_reviews" in collectors_active and config.get("google_maps_url"):
        try:
            from collectors.google_reviews import GoogleReviewsCollector
            gr = GoogleReviewsCollector(sentiment_analyzer=None)
            max_r = config.get("google_maps_max_reviews", 10)
            try:
                reviews = await gr.collect_reviews(e_slug, max_reviews=max_r)
                raw_mentions.extend(reviews)
            except Exception as ex:
                logger.warning("  google_reviews falló: %s", ex)
        except Exception as e:
            logger.warning("  Google Reviews no disponible: %s", e)

    # ---- Meta (stubs por ahora) ----
    if "instagram" in collectors_active:
        from collectors.instagram_collector import InstagramCollector
        raw_mentions.extend(InstagramCollector().collect_for_entity(entity, config))
    if "facebook" in collectors_active:
        from collectors.facebook_collector import FacebookCollector
        raw_mentions.extend(FacebookCollector().collect_for_entity(entity, config))
    if "tiktok" in collectors_active:
        from collectors.tiktok_collector import TikTokCollector
        raw_mentions.extend(TikTokCollector().collect_for_entity(entity, config))

    # ---- Filtro declarativo v3 ----
    filtered = []
    rejected_summary = {}
    for m in raw_mentions:
        verdict = is_relevant_detailed(m.get("text_original", ""), config)
        if verdict["accepted"]:
            filtered.append(m)
        else:
            rejected_summary[verdict["reason"]] = rejected_summary.get(verdict["reason"], 0) + 1

    # ---- NLP cascada (batch) ----
    if filtered and analyzer:
        texts = [m["text_original"] for m in filtered]
        sentiments = analyzer.analyze_batch(texts, entity_config=config, conglomerate=conglomerate)
        for m, s in zip(filtered, sentiments):
            m["sentiment_label"] = s["label"]
            # Guardar también `method` y `dominican_term` para criterio #3 del DEPLOY
            m["sentiment_score"] = {
                **s.get("scores", {}),
                "reasoning": s.get("reasoning", ""),
                "method": s.get("method", "unknown"),
                "dominican_term": s.get("dominican_term"),
            }
            m["confidence_score"] = s.get("confidence", 0.5)
            m["dominican_override"] = s.get("dominican_override", False)
            m["dominican_term_found"] = s.get("dominican_term")

    logger.info("  [%s] candidatos=%d aceptados=%d rejected=%s",
                e_slug, len(raw_mentions), len(filtered), rejected_summary or "{}")
    return filtered


# ============================================================
# Persistencia
# ============================================================
def save_mentions(supabase, mentions, entity_map, source_map):
    if not mentions or not supabase:
        return 0
    records = []
    for m in mentions:
        e_id = entity_map.get(m.get("entity_slug"))
        s_id = source_map.get(m.get("source_slug"))
        if not e_id:
            continue
        rec = {k: v for k, v in m.items() if v is not None and k not in ("entity_slug", "source_slug")}
        rec["entity_id"] = e_id
        rec["source_id"] = s_id
        # NO hacer json.dumps aquí: supabase-py serializa automáticamente,
        # y un json.dumps previo causa doble-encoding (string dentro de JSONB).
        records.append(rec)
    try:
        result = supabase.table("mentions").upsert(records, on_conflict="content_hash", ignore_duplicates=True).execute()
        return len(result.data) if result.data else 0
    except Exception as e:
        logger.error("Error en upsert mentions: %s", e)
        return 0


def preload_lookups(supabase):
    if supabase is None:
        return {}, {}
    ents = supabase.table("entities").select("id, slug").execute()
    srcs = supabase.table("sources").select("id, slug").execute()
    return {x["slug"]: x["id"] for x in (ents.data or [])}, \
           {x["slug"]: x["id"] for x in (srcs.data or [])}


# ============================================================
# Main async
# ============================================================
async def run(args):
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info("=" * 60)
    logger.info("SIH v3 — first_run=%s incremental=%s dry_run=%s conglomerate=%s",
                args.first_run, args.incremental, args.dry_run, args.conglomerate)
    logger.info("=" * 60)

    supabase = get_supabase(args.dry_run)
    conglomerate, workplan = load_workplan(supabase, args.conglomerate, args.entity_filter)
    entity_map, source_map = preload_lookups(supabase)
    collectors_active = resolve_collectors(args)
    logger.info("Conglomerado: %s — entidades en plan: %d — colectores: %s",
                conglomerate["name"], len(workplan), collectors_active)

    from processors.groq_sentiment import SentimentAnalyzer
    analyzer = SentimentAnalyzer()

    total_collected = 0
    total_saved = 0
    for item in workplan:
        logger.info("→ %s (%s)", item["entity"]["name"], item["entity"]["slug"])
        mentions = await collect_for_entity(item, conglomerate, collectors_active, analyzer, args)
        total_collected += len(mentions)
        if args.dry_run:
            for m in mentions[:3]:
                print(f"   · [{m.get('source_slug')}] {m.get('text_original','')[:120]}…")
        else:
            saved = save_mentions(supabase, mentions, entity_map, source_map)
            total_saved += saved
            logger.info("   guardadas %d/%d", saved, len(mentions))

    finished_at = datetime.now(timezone.utc).isoformat()
    logger.info("=" * 60)
    logger.info("FIN — recolectadas=%d guardadas=%d (%s → %s)",
                total_collected, total_saved, started_at, finished_at)
    logger.info("=" * 60)


def parse_args():
    p = argparse.ArgumentParser(description="SIH v3 Scraper")
    p.add_argument("--first-run", action="store_true", help="Histórico completo")
    p.add_argument("--incremental", action="store_true", help="Solo nuevo desde última corrida")
    p.add_argument("--all-collectors", action="store_true", help="Activa los 6 colectores")
    p.add_argument("--collectors", default=None, help="Subconjunto coma-separado")
    p.add_argument("--conglomerate", default="zona-franca", help="Slug del conglomerado")
    p.add_argument("--entity-filter", default=None, help="Una sola entidad (slug)")
    p.add_argument("--dry-run", action="store_true", help="No escribe en BD")
    return p.parse_args()


if __name__ == "__main__":
    try:
        asyncio.run(run(parse_args()))
    except KeyboardInterrupt:
        logger.info("Interrumpido por usuario.")
    except Exception as e:
        logger.error("Error fatal: %s", e, exc_info=True)
        sys.exit(1)

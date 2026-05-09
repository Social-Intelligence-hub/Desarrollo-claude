# -*- coding: utf-8 -*-
"""
Orquestador Principal del Scraper - Social Intelligence Hub
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(os.path.join(BASE_DIR, "scraper.log")), logging.StreamHandler()],
)
logger = logging.getLogger("main")

# Cargar variables de entorno
load_dotenv(os.path.join(BASE_DIR, ".env"))


def get_supabase_client():
    """
    Inicializa el cliente de Supabase.
    Si la librería oficial falla, retorna None para activar el modo REST.
    """
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            logger.error("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")
            return None
        return create_client(url, key)
    except Exception as e:
        logger.warning(f"Usando modo REST (Librería Supabase no disponible): {e}")
        return None


def preload_lookup_tables(supabase):
    """
    Obtiene los IDs de entidades y fuentes para evitar buscar por slug en cada inserción.
    """
    entity_map = {}
    source_map = {}

    try:
        if supabase:
            entities = supabase.table("entities").select("id, slug").execute()
            entity_map = {item["slug"]: item["id"] for item in entities.data}

            sources = supabase.table("sources").select("id, slug").execute()
            source_map = {item["slug"]: item["id"] for item in sources.data}
        else:
            # Fallback REST
            url_ent = f"{os.getenv('SUPABASE_URL')}/rest/v1/entities?select=id,slug"
            url_src = f"{os.getenv('SUPABASE_URL')}/rest/v1/sources?select=id,slug"
            headers = {
                "apikey": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}"
            }
            res_ent = requests.get(url_ent, headers=headers)
            entity_map = {item["slug"]: item["id"] for item in res_ent.json()}

            res_src = requests.get(url_src, headers=headers)
            source_map = {item["slug"]: item["id"] for item in res_src.json()}

    except Exception as e:
        logger.error(f"Error precargando tablas: {e}")

    return entity_map, source_map


def save_mentions_rest(mentions, entity_map, source_map):
    """Guarda menciones vía REST API."""
    if not mentions: return 0, 0
    url = f"{os.getenv('SUPABASE_URL')}/rest/v1/mentions"
    headers = {
        "apikey": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    saved = 0
    for m in mentions:
        entity_id = entity_map.get(m.get("entity_slug"))
        source_id = source_map.get(m.get("source_slug"))
        if not entity_id: continue
        
        record = {
            "entity_id": entity_id,
            "source_id": source_id,
            "text_original": m.get("text_original", "")[:2000],
            "author_name": m.get("author_name", "Desconocido"),
            "source_url": m.get("source_url"),
            "sentiment_label": m.get("sentiment_label", "neutral"),
            "sentiment_score": m.get("sentiment_score"),
            "confidence_score": m.get("confidence_score", 0.5),
            "published_at": m.get("published_at"),
            "language": m.get("language", "es"),
            "content_hash": m.get("content_hash")
        }
        try:
            res = requests.post(url, headers=headers, json=record)
            if res.status_code in [200, 201]: saved += 1
        except: pass
    return len(mentions), saved


def save_mentions(supabase, mentions, entity_map, source_map):
    """Persiste las menciones usando el mejor método disponible."""
    if not mentions: return 0, 0
    
    if not supabase:
        return save_mentions_rest(mentions, entity_map, source_map)

    records = []
    
    # Instantiate and load the relevance filter
    from processors.relevance_filter import RelevanceFilter
    filter_engine = RelevanceFilter(supabase)
    filter_engine.load_feedback()
    
    for m in mentions:
        # Check relevance
        text = m.get("text_original", "")
        if not filter_engine.is_relevant(text):
            continue
            
        e_slug = m.pop("entity_slug", None)
        s_slug = m.pop("source_slug", None)
        e_id = entity_map.get(e_slug)
        s_id = source_map.get(s_slug)
        if not e_id: continue
        
        rec = {**m, "entity_id": e_id, "source_id": s_id}
        if isinstance(rec.get("sentiment_score"), dict):
            rec["sentiment_score"] = json.dumps(rec["sentiment_score"])
        records.append({k: v for k, v in rec.items() if v is not None})

    if not records: return len(mentions), 0

    try:
        result = supabase.table("mentions").upsert(records, on_conflict="content_hash", ignore_duplicates=True).execute()
        new = len(result.data) if result.data else 0
        logger.info(f"Insertadas {new} menciones.")
        return len(mentions), new
    except Exception as e:
        logger.error(f"Error en upsert: {e}")
        return len(mentions), 0


async def main_async():
    """
    Versión async de main que ejecuta múltiples collectors en paralelo.
    """
    import asyncio

    logger.info("=" * 60)
    logger.info("SOCIAL INTELLIGENCE HUB - Iniciando recolección (async)")
    logger.info("=" * 60)

    parser = argparse.ArgumentParser(description="Scraper - Social Intelligence Hub")
    parser.add_argument("--dry-run", action="store_true", help="No guarda en base de datos")
    parser.add_argument("--no-active", action="store_true", help="Omite búsqueda activa")
    parser.add_argument("--no-reviews", action="store_true", help="Omite Google Reviews")
    args = parser.parse_args()

    supabase = None if args.dry_run else get_supabase_client()
    entity_map, source_map = preload_lookup_tables(supabase)

    from collectors.google_alerts import GoogleAlertsCollector
    from collectors.reddit_collector import RedditCollector
    from collectors.google_reviews import GoogleReviewsCollector
    from collectors.active_search import ActiveSearchCollector
    from processors.azure_sentiment import SentimentAnalyzer

    analyzer = SentimentAnalyzer()
    collector_ga = GoogleAlertsCollector()
    collector_re = RedditCollector()
    collector_gr = GoogleReviewsCollector(sentiment_analyzer=analyzer) if not args.no_reviews else None
    collector_as = ActiveSearchCollector(sentiment_analyzer=analyzer) if not args.no_active else None

    total_collected = 0
    total_saved = 0

    for entity_slug in entity_map.keys():
        logger.info(f"\n{'='*60}")
        logger.info(f">>> Procesando entidad: {entity_slug.upper()}")
        logger.info(f"{'='*60}")

        all_mentions = []

        # 1. Google News RSS
        logger.info(f"  [1/4] Ejecutando Google Alerts/News...")
        try:
            mentions_gn = collector_ga.collect_from_google_news(entity_slug)
            if mentions_gn:
                for m in mentions_gn:
                    s = analyzer.analyze(m["text_original"])
                    m.update({
                        "sentiment_label": s["label"],
                        "sentiment_score": s["scores"],
                        "confidence_score": s["confidence"]
                    })
                all_mentions.extend(mentions_gn)
                logger.info(f"    ✓ Recolectadas {len(mentions_gn)} menciones de Google News")
        except Exception as e:
            logger.error(f"    ✗ Error en Google News: {e}")

        # 2. Reddit
        logger.info(f"  [2/4] Ejecutando Reddit...")
        try:
            mentions_rd = collector_re.search_reddit(entity_slug, entity_slug)
            if mentions_rd:
                for m in mentions_rd:
                    s = analyzer.analyze(m["text_original"])
                    m.update({
                        "sentiment_label": s["label"],
                        "sentiment_score": s["scores"],
                        "confidence_score": s["confidence"]
                    })
                all_mentions.extend(mentions_rd)
                logger.info(f"    ✓ Recolectadas {len(mentions_rd)} menciones de Reddit")
        except Exception as e:
            logger.error(f"    ✗ Error en Reddit: {e}")

        # 3. Google Reviews (para ubicaciones específicas)
        if collector_gr and entity_slug in ["czfs", "capex-institucion", "medica-czfs", "plazona"]:
            logger.info(f"  [3/4] Ejecutando Google Reviews...")
            try:
                location_key = entity_slug if entity_slug != "czfs" else "pivem"  # PIVEM es sub-entidad de CZFS
                reviews = await collector_gr.collect_reviews(location_key, max_reviews=15)
                if reviews:
                    all_mentions.extend(reviews)
                    logger.info(f"    ✓ Recolectadas {len(reviews)} reseñas de Google Maps")
            except Exception as e:
                logger.error(f"    ✗ Error en Google Reviews: {e}")
        else:
            logger.info(f"  [3/4] Google Reviews (omitido para esta entidad)")

        # 4. Búsqueda Activa (inyección de datos semilla)
        if collector_as:
            logger.info(f"  [4/4] Ejecutando Búsqueda Activa...")
            try:
                mentions_as = collector_as.collect_for_entity(entity_slug, max_results=8)
                if mentions_as:
                    all_mentions.extend(mentions_as)
                    logger.info(f"    ✓ Recolectadas {len(mentions_as)} menciones de búsqueda activa")
            except Exception as e:
                logger.error(f"    ✗ Error en búsqueda activa: {e}")
        else:
            logger.info(f"  [4/4] Búsqueda Activa (omitida)")

        # Guardar todas las menciones
        if all_mentions:
            collected, saved = save_mentions(supabase, all_mentions, entity_map, source_map)
            total_collected += collected
            total_saved += saved
            logger.info(f"\n  Resumen para {entity_slug}: {saved}/{collected} guardadas")

    logger.info(f"\n{'='*60}")
    logger.info(f"Recolección finalizada:")
    logger.info(f"  Total recolectado: {total_collected}")
    logger.info(f"  Total guardado: {total_saved}")
    logger.info(f"{'='*60}")


def main():
    """Wrapper síncrono para ejecutar la versión async."""
    import asyncio

    parser = argparse.ArgumentParser(description="Scraper - Social Intelligence Hub")
    parser.add_argument("--dry-run", action="store_true", help="No guarda en base de datos")
    parser.add_argument("--no-active", action="store_true", help="Omite búsqueda activa")
    parser.add_argument("--no-reviews", action="store_true", help="Omite Google Reviews")
    args = parser.parse_args()

    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\nInterrupción del usuario.")
    except Exception as e:
        logger.error(f"Error fatal: {e}")


if __name__ == "__main__":
    main()

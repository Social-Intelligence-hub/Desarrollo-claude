"""
Social Intelligence Hub - Scraper Principal
CZFS & CAPEX MVP

Ejecuta todos los colectores y persiste los datos en Supabase.
Uso:
    python main.py                 # Ejecutar una vez
    python main.py --schedule      # Ejecutar cada 12 horas
    python main.py --demo          # Insertar datos demo
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

# Imports locales
from processors.azure_sentiment import SentimentAnalyzer
from collectors.google_reviews import GoogleReviewsCollector, LOCATIONS
from collectors.google_alerts import GoogleAlertsCollector
from collectors.reddit_collector import RedditCollector


# ============================================================
# Supabase helpers
# ============================================================

def get_supabase_client():
    """Inicializa el cliente de Supabase."""
    try:
        from supabase import create_client, Client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            logger.error("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos en .env")
            return None
        return create_client(url, key)
    except ImportError:
        logger.error("supabase-py no instalado. pip install supabase")
        return None
    except Exception as e:
        logger.error(f"Error conectando a Supabase: {e}")
        return None


def verify_connection(supabase) -> bool:
    """Valida que Supabase sea alcanzable haciendo una consulta ligera."""
    if not supabase:
        logger.info("Modo DRY RUN: Omitiendo verificacion de conexion")
        return True
    try:
        result = supabase.table("entities").select("id", count="exact").limit(1).execute()
        logger.info(f"Conexion a Supabase OK — {result.count} entidades registradas")
        return True
    except Exception as e:
        logger.error(f"No se pudo conectar a Supabase: {e}")
        logger.error("Verifica SUPABASE_URL (debe terminar en .supabase.co, no .com)")
        return False


def preload_lookup_tables(supabase) -> tuple[dict, dict]:
    """
    Carga TODAS las entidades y fuentes de una sola vez.
    Retorna dos diccionarios: {slug: uuid}.
    """
    entity_map: dict[str, str] = {}
    source_map: dict[str, str] = {}

    if not supabase:
        # Retornar mapas ficticios para dry-run
        return {"czfs": "demo", "capex-institucion": "demo", "pivem": "demo"}, {"google_reviews": "demo", "reddit": "demo", "news_web": "demo"}

    try:
        entities = supabase.table("entities").select("id, slug").execute()
        for row in entities.data or []:
            entity_map[row["slug"]] = row["id"]
        logger.info(f"Entidades cargadas: {list(entity_map.keys())}")
    except Exception as e:
        logger.error(f"Error cargando entidades: {e}")

    try:
        sources = supabase.table("sources").select("id, slug").execute()
        for row in sources.data or []:
            source_map[row["slug"]] = row["id"]
        logger.info(f"Fuentes cargadas: {list(source_map.keys())}")
    except Exception as e:
        logger.error(f"Error cargando fuentes: {e}")

    return entity_map, source_map


def save_mentions(
    supabase,
    mentions: list[dict],
    entity_map: dict[str, str],
    source_map: dict[str, str],
) -> tuple[int, int]:
    """
    Persiste las menciones en Supabase.
    Usa los mapas precargados para resolver slugs a UUIDs (sin queries adicionales).

    Returns:
        (total_processed, new_inserted)
    """
    if not mentions:
        return 0, 0

    records_to_insert = []

    for mention in mentions:
        entity_slug = mention.pop("entity_slug", None)
        source_slug = mention.pop("source_slug", None)

        # Resolver UUIDs desde el mapa en memoria
        entity_id = entity_map.get(entity_slug)
        source_id = source_map.get(source_slug)

        if not entity_id:
            logger.warning(f"Entidad desconocida (no existe en BD): '{entity_slug}'")
            continue

        # Preparar registro
        record = {
            **mention,
            "entity_id": entity_id,
            "source_id": source_id,
        }

        # Serializar el dict de scores a JSON string para Supabase
        if isinstance(record.get("sentiment_score"), dict):
            record["sentiment_score"] = json.dumps(record["sentiment_score"])

        # Limpiar campos None (Supabase no los necesita)
        record = {k: v for k, v in record.items() if v is not None}
        records_to_insert.append(record)

    if not records_to_insert:
        return len(mentions), 0

    if not supabase:
        logger.info(f"Modo DRY RUN: Omitiendo guardado de {len(records_to_insert)} menciones")
        return len(records_to_insert), 0

    try:
        # Upsert con ON CONFLICT DO NOTHING para content_hash
        result = supabase.table("mentions").upsert(
            records_to_insert,
            on_conflict="content_hash",
            ignore_duplicates=True
        ).execute()

        new_count = len(result.data) if result.data else 0
        logger.info(f"Insertadas {new_count} de {len(records_to_insert)} menciones")
        return len(records_to_insert), new_count

    except Exception as e:
        logger.error(f"Error en upsert batch: {e}")
        # Fallback: insertar una por una
        inserted = 0
        for record in records_to_insert:
            try:
                supabase.table("mentions").upsert(
                    record, on_conflict="content_hash", ignore_duplicates=True
                ).execute()
                inserted += 1
            except Exception as ex:
                logger.debug(f"Skip duplicado o error: {ex}")
        return len(records_to_insert), inserted


def log_scraper_run(
    supabase,
    source_slug: str,
    entity_slug: str,
    status: str,
    found: int,
    new: int,
    error: str = None,
    started_at: str = None,
) -> str | None:
    """Registra una ejecución del scraper."""
    if not supabase:
        return None
    try:
        record = {
            "source_slug": source_slug,
            "entity_slug": entity_slug,
            "status": status,
            "mentions_found": found,
            "mentions_new": new,
            "error_message": error,
            "started_at": started_at or datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        result = supabase.table("scraper_runs").insert(record).execute()
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        logger.debug(f"Error logging scraper run: {e}")
        return None


# ============================================================
# Colectores
# ============================================================

async def run_google_reviews(supabase, analyzer, entity_map, source_map) -> int:
    """Ejecuta el colector de Google Reviews."""
    collector = GoogleReviewsCollector(sentiment_analyzer=analyzer)
    total_new = 0
    started = datetime.now(timezone.utc).isoformat()

    for location_key in LOCATIONS.keys():
        try:
            logger.info(f"  Google Reviews: {location_key}")
            mentions = await collector.collect_reviews(location_key, max_reviews=20)
            if not mentions:
                print(f"INFO: Fuente Google Reviews ({location_key}) revisada con éxito, pero no hay contenido nuevo")
            else:
                _, new = save_mentions(supabase, mentions, entity_map, source_map)
                total_new += new
                log_scraper_run(supabase, "google_reviews", location_key,
                               "success", len(mentions), new, started_at=started)
        except Exception as e:
            logger.error(f"  Error en Google Reviews {location_key}: {e}")
            log_scraper_run(supabase, "google_reviews", location_key,
                           "error", 0, 0, str(e), started_at=started)

    return total_new


def run_google_alerts(supabase, analyzer, entity_map, source_map) -> int:
    """Ejecuta el colector de Google Alerts."""
    collector = GoogleAlertsCollector(sentiment_analyzer=analyzer)
    total_new = 0
    started = datetime.now(timezone.utc).isoformat()

    # Google Alerts feeds
    all_mentions = collector.collect_all()
    if all_mentions:
        _, new = save_mentions(supabase, all_mentions, entity_map, source_map)
        total_new += new
    else:
        print("INFO: Fuente Google Alerts revisada con éxito, pero no hay contenido nuevo")

    # 2. RSS de noticias dominicanas (Fuentes locales)
    for entity_slug in ["czfs", "capex-institucion", "pivem"]:
        try:
            news_mentions = collector.collect_from_news_rss(entity_slug)
            if news_mentions:
                _, new = save_mentions(supabase, news_mentions, entity_map, source_map)
                total_new += new
                log_scraper_run(supabase, "news_web", entity_slug,
                               "success", len(news_mentions), new, started_at=started)
            else:
                print(f"INFO: Fuente RSS Noticias ({entity_slug}) revisada con éxito, pero no hay contenido nuevo")
        except Exception as e:
            logger.error(f"  Error en news RSS {entity_slug}: {e}")

    # 3. Google News Active Search (Búsqueda proactiva)
    for entity_slug in ["czfs", "capex-institucion", "pivem", "plazona", "medica-czfs"]:
        try:
            active_mentions = collector.collect_from_google_news(entity_slug)
            if active_mentions:
                _, new = save_mentions(supabase, active_mentions, entity_map, source_map)
                total_new += new
                log_scraper_run(supabase, "google_news", entity_slug,
                               "success", len(active_mentions), new, started_at=started)
            else:
                print(f"INFO: Google News Activo ({entity_slug}) revisado, sin resultados nuevos")
        except Exception as e:
            logger.error(f"  Error en Google News Activo {entity_slug}: {e}")

    return total_new


def run_reddit(supabase, analyzer, entity_map, source_map) -> int:
    """Ejecuta el colector de Reddit."""
    collector = RedditCollector(sentiment_analyzer=analyzer)
    started = datetime.now(timezone.utc).isoformat()

    try:
        mentions = collector.collect_all(max_per_term=10)
        if not mentions:
            print("INFO: Fuente Reddit revisada con éxito, pero no hay contenido nuevo")
            return 0
            
        _, new = save_mentions(supabase, mentions, entity_map, source_map)
        log_scraper_run(supabase, "reddit", "all",
                       "success", len(mentions), new, started_at=started)
        return new
    except Exception as e:
        logger.error(f"  Error en Reddit collector: {e}")
        log_scraper_run(supabase, "reddit", "all",
                       "error", 0, 0, str(e), started_at=started)
        return 0


# ============================================================
# Orquestador
# ============================================================

async def run_all_collectors(supabase):
    """Ejecuta todos los colectores en secuencia."""
    started_run = datetime.now(timezone.utc).isoformat()
    logger.info("=" * 60)
    logger.info("SOCIAL INTELLIGENCE HUB — Iniciando recoleccion")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    # 1. Validar conexión
    if not verify_connection(supabase):
        logger.error("Abortando: sin conexion a Supabase.")
        return 0

    # 2. Pre-cargar tablas de lookup (1 query por tabla, NO 1 por mención)
    entity_map, source_map = preload_lookup_tables(supabase)
    if not entity_map:
        logger.error("Abortando: no hay entidades en la BD. Ejecuta la migracion SQL primero.")
        return 0

    # 3. Motor de sentimiento
    analyzer = SentimentAnalyzer()
    total_new = 0

    # 4. Colectores
    logger.info("\n[1/3] Google Reviews...")
    gr_new = await run_google_reviews(supabase, analyzer, entity_map, source_map)
    total_new += gr_new
    logger.info(f"  -> {gr_new} nuevas menciones")

    logger.info("\n[2/3] Google Alerts y Noticias...")
    alerts_new = run_google_alerts(supabase, analyzer, entity_map, source_map)
    total_new += alerts_new
    logger.info(f"  -> {alerts_new} nuevas menciones")

    logger.info("\n[3/3] Reddit...")
    reddit_new = run_reddit(supabase, analyzer, entity_map, source_map)
    total_new += reddit_new
    logger.info(f"  -> {reddit_new} nuevas menciones")

    logger.info("\n" + "=" * 60)
    logger.info(f"COMPLETADO. Total nuevas menciones: {total_new}")
    logger.info("=" * 60)
    print(f"\nConexión con Supabase exitosa. Se intentaron guardar {total_new} filas")

    # Registrar el resumen de la ejecución general
    log_scraper_run(supabase, "orchestrator", "all", "success", total_new, total_new, started_at=started_run)

    return total_new


def main():
    parser = argparse.ArgumentParser(
        description="Social Intelligence Hub Scraper — CZFS & CAPEX MVP"
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="Ejecutar en modo programado cada 12 horas"
    )

    parser.add_argument(
        "--dry-run", action="store_true",
        help="Ejecutar sin guardar en base de datos"
    )
    args = parser.parse_args()

    supabase = None if args.dry_run else get_supabase_client()
    if not supabase and not args.dry_run:
        logger.error("No se pudo crear el cliente Supabase. Verificar .env")
        sys.exit(1)

    if args.schedule:
        try:
            import schedule
            import time

            logger.info("Modo programado: cada 12 horas")
            schedule.every(12).hours.do(
                lambda: asyncio.run(run_all_collectors(supabase))
            )
            asyncio.run(run_all_collectors(supabase))  # Ejecutar inmediatamente
            while True:
                schedule.run_pending()
                time.sleep(60)
        except ImportError:
            logger.error("pip install schedule para modo programado")
            sys.exit(1)
    else:
        asyncio.run(run_all_collectors(supabase))


if __name__ == "__main__":
    main()

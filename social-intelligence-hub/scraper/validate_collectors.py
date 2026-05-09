#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Validación - Prueba la integración de múltiples collectors
Demuestra: Google News + Reddit + Google Reviews + Active Search

Este script corre en modo "dry-run" para no modificar la base de datos.
"""

import asyncio
import logging
import sys
from datetime import datetime

# Configurar logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_validation():
    """Valida que todos los collectors funcionen correctamente."""

    logger.info("╔" + "="*70 + "╗")
    logger.info("║" + " VALIDACIÓN DE COLLECTORS INTEGRADOS ".center(70) + "║")
    logger.info("╚" + "="*70 + "╝")

    from collections import defaultdict
    from collectors.google_alerts import GoogleAlertsCollector
    from collectors.reddit_collector import RedditCollector
    from collectors.google_reviews import GoogleReviewsCollector
    from collectors.active_search import ActiveSearchCollector
    from processors.azure_sentiment import SentimentAnalyzer

    # Inicializar componentes
    logger.info("\n[*] Inicializando collectors y analizador de sentimiento...")
    analyzer = SentimentAnalyzer()
    collector_ga = GoogleAlertsCollector()
    collector_re = RedditCollector()
    collector_gr = GoogleReviewsCollector(sentiment_analyzer=analyzer)
    collector_as = ActiveSearchCollector(sentiment_analyzer=analyzer)

    # Diccionario para acumular resultados
    results = defaultdict(lambda: {"google_news": 0, "reddit": 0, "google_reviews": 0, "active_search": 0})

    # Entidades de prueba
    test_entities = ["czfs", "capex-institucion"]

    for entity_slug in test_entities:
        logger.info(f"\n┌─ Probando con entidad: {entity_slug.upper()}")

        # 1. Google News/Alerts
        logger.info(f"│  [1/4] Google News/Alerts...")
        try:
            mentions = collector_ga.collect_from_google_news(entity_slug)
            results[entity_slug]["google_news"] = len(mentions) if mentions else 0
            logger.info(f"│    ✓ {results[entity_slug]['google_news']} menciones")
        except Exception as e:
            logger.warning(f"│    ✗ Error: {e}")

        # 2. Reddit
        logger.info(f"│  [2/4] Reddit...")
        try:
            mentions = collector_re.search_reddit(entity_slug, entity_slug)
            results[entity_slug]["reddit"] = len(mentions) if mentions else 0
            logger.info(f"│    ✓ {results[entity_slug]['reddit']} menciones")
        except Exception as e:
            logger.warning(f"│    ✗ Error: {e}")

        # 3. Google Reviews (solo si es aplicable)
        logger.info(f"│  [3/4] Google Reviews...")
        location_key = entity_slug if entity_slug in ["medica-czfs", "plazona"] else None
        if entity_slug == "czfs":
            location_key = "pivem"
        
        if location_key:
            try:
                reviews = await collector_gr.collect_reviews(location_key, max_reviews=10)
                results[entity_slug]["google_reviews"] = len(reviews) if reviews else 0
                logger.info(f"│    ✓ {results[entity_slug]['google_reviews']} reseñas")
            except Exception as e:
                logger.warning(f"│    ✗ Error: {e}")
        else:
            logger.info(f"│    ⊘ No aplicable para esta entidad")

        # 4. Active Search
        logger.info(f"│  [4/4] Búsqueda Activa...")
        try:
            mentions = collector_as.collect_for_entity(entity_slug, max_results=5)
            results[entity_slug]["active_search"] = len(mentions) if mentions else 0
            logger.info(f"│    ✓ {results[entity_slug]['active_search']} menciones")
        except Exception as e:
            logger.warning(f"│    ✗ Error: {e}")

        logger.info(f"└─ Completado: {entity_slug}")

    # Resumen
    logger.info(f"\n┌─ RESUMEN DE VALIDACIÓN")
    logger.info(f"│")
    total_by_source = defaultdict(int)
    for entity_slug, sources in results.items():
        logger.info(f"│  {entity_slug}:")
        for source, count in sources.items():
            logger.info(f"│    • {source}: {count}")
            total_by_source[source] += count

    logger.info(f"│")
    logger.info(f"│  TOTALES POR FUENTE:")
    for source, total in total_by_source.items():
        logger.info(f"│    • {source}: {total}")

    grand_total = sum(total_by_source.values())
    logger.info(f"│")
    logger.info(f"│  TOTAL GENERAL: {grand_total} menciones recolectadas")
    logger.info(f"└─ Fin de validación")

    logger.info(f"\n╔" + "="*70 + "╗")
    logger.info(f"║ ✓ VALIDACIÓN COMPLETADA".ljust(71) + "║")
    logger.info(f"╚" + "="*70 + "╝\n")


if __name__ == "__main__":
    try:
        asyncio.run(run_validation())
    except KeyboardInterrupt:
        logger.info("\nInterrupción del usuario.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)

# -*- coding: utf-8 -*-
"""
TikTok Collector — STUB FORMAL.

Pendiente de definición arquitectónica:
  - Research API (requiere calificar como institución académica), o
  - Scraping (inestable, riesgo legal).

Hasta entonces el colector existe formalmente y retorna [] para no romper el
pipeline cuando se invoque con --all-collectors.
"""

import logging

logger = logging.getLogger(__name__)


class TikTokCollector:
    def __init__(self, sentiment_analyzer=None):
        self.analyzer = sentiment_analyzer
        logger.info("TikTokCollector: stub formal (retorna []). Roadmap post-demo.")

    def collect_for_entity(self, entity: dict, config: dict, max_results: int = 25) -> list[dict]:
        return []

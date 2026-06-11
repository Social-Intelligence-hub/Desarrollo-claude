# -*- coding: utf-8 -*-
"""
Facebook Collector — Meta Graph API.

Estado actual: STUB FUNCIONAL. Si no hay FACEBOOK_ACCESS_TOKEN, retorna [].
La implementación real consume:
  - /{page-id}/feed         → posts de la página
  - /{post-id}/comments     → comentarios
  - búsqueda por nombre limitada al tier público
"""

import logging
import os

logger = logging.getLogger(__name__)

META_GRAPH_BASE = "https://graph.facebook.com/v20.0"


class FacebookCollector:
    """Stub funcional. Mismo contrato que el resto de colectores."""

    def __init__(self, sentiment_analyzer=None):
        self.analyzer = sentiment_analyzer
        self.token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        if not self.token:
            logger.info("FacebookCollector: sin FACEBOOK_ACCESS_TOKEN → stub (retorna []).")

    def collect_for_entity(self, entity: dict, config: dict, max_results: int = 25) -> list[dict]:
        if not self.token:
            return []
        logger.warning("FacebookCollector real: pendiente de implementación post-aprobación Meta.")
        return []

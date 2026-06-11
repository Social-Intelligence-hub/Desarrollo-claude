# -*- coding: utf-8 -*-
"""
Instagram Collector — Meta Graph API.

Estado actual: STUB FUNCIONAL. Si no hay INSTAGRAM_ACCESS_TOKEN, retorna [].
La implementación real (cuando Meta apruebe la app) consume:
  - /{ig-user-id}/recent_media          → posts del perfil
  - /ig_hashtag_search + /{hashtag-id}  → menciones por hashtag de marca
  - /{media-id}/comments                → comentarios

Rate limit Meta: 200 req/hora. La 1ra corrida pide 3 meses (expansión gradual).
"""

import logging
import os

logger = logging.getLogger(__name__)

META_GRAPH_BASE = "https://graph.facebook.com/v20.0"


class InstagramCollector:
    """Stub funcional. Compatible con la firma del pipeline."""

    def __init__(self, sentiment_analyzer=None):
        self.analyzer = sentiment_analyzer
        self.token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        if not self.token:
            logger.info("InstagramCollector: sin INSTAGRAM_ACCESS_TOKEN → stub (retorna []).")

    def collect_for_entity(self, entity: dict, config: dict, max_results: int = 25) -> list[dict]:
        """Devuelve menciones del perfil/hashtags de la entidad. Vacío si no hay token."""
        if not self.token:
            return []
        # Implementación real:
        # 1) GET /ig_hashtag_search?q={brand}
        # 2) GET /{hashtag-id}/recent_media?fields=caption,permalink,timestamp
        # 3) Para cada media, opcionalmente comentarios
        # 4) Mapear a dict de menciones del pipeline
        logger.warning("InstagramCollector real: pendiente de implementación post-aprobación Meta.")
        return []

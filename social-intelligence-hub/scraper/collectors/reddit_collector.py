"""
Colector de Reddit
Busca menciones de CZFS y CAPEX en subreddits relevantes.
API pública de Reddit (sin autenticación para búsqueda básica).
Incluye filtrado de relevancia para descartar resultados irrelevantes.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from collectors.relevance_filter import es_relevante_dominicana

logger = logging.getLogger(__name__)

# Subreddits a monitorear
TARGET_SUBREDDITS = [
    "Dominican",
    "RepublicaDominicana",
    "republicadominicana",
    "Santiago",
    "trabajos_rd",
    "DominicanRepublic",
    "latinoamerica",
    "asklatinamerica",
]

# Términos de búsqueda por entidad
SEARCH_CONFIGS = {
    "czfs": {
        "terms": [
            "zona franca santiago dominicana",
            "zona franca santiago mera",
            "czfs santiago",
            "corporacion zona franca santiago",
            "corporación zona franca santiago",
        ],
        "entity_slug": "czfs",
    },
    "capex-institucion": {
        "terms": [
            "capex santiago", "capex capacitacion", "capex capacitación", "capex rd",
            "capex taller", "capex egresados", "capex formacion", "capex formación"
        ],
        "entity_slug": "capex-institucion",
    },
    "pivem": {
        "terms": ["pivem", "parque industrial villa europa", "parque industrial villa europa mediterráneo"],
        "entity_slug": "pivem",
    },
}

REDDIT_BASE = "https://www.reddit.com"
HEADERS = {
    "User-Agent": "SocialIntelligenceHub/1.0 CZFS-MVP (contact: admin@czfs.com)",
    "Accept": "application/json",
}


class RedditCollector:
    """
    Colector de menciones en Reddit usando la API JSON pública.
    No requiere credenciales para lectura básica.
    """

    def __init__(self, sentiment_analyzer=None):
        self.analyzer = sentiment_analyzer
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def collect_all(self, max_per_term: int = 25) -> list[dict]:
        """Recolecta menciones de todas las entidades configuradas."""
        all_mentions = []
        for config_key, config in SEARCH_CONFIGS.items():
            for term in config["terms"]:
                mentions = self.search_reddit(
                    term, config["entity_slug"], max_per_term
                )
                all_mentions.extend(mentions)
                time.sleep(1.5)  # Rate limiting ético
        return all_mentions

    def search_reddit(
        self, query: str, entity_slug: str, limit: int = 25
    ) -> list[dict]:
        """
        Busca posts en subreddits específicos dominicanos.
        Filtra resultados irrelevantes que no mencionan keywords de la entidad.
        """
        mentions = []

        # Buscar solo en subreddits específicos (no búsqueda global)
        for subreddit in TARGET_SUBREDDITS:
            try:
                posts = self._search_subreddit(subreddit, query, limit)
                for post in posts:
                    mention = self._format_post(post, entity_slug, query)
                    if mention:
                        mentions.append(mention)
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Error buscando en r/{subreddit}: {e}")

        logger.info(f"Reddit: {len(mentions)} menciones para '{query}'")
        return mentions

    def _search_subreddit(
        self, subreddit: str, query: str, limit: int
    ) -> list[dict]:
        """Busca en un subreddit específico."""
        url = (
            f"{REDDIT_BASE}/r/{subreddit}/search.json"
            f"?q={requests.utils.quote(query)}&restrict_sr=1"
            f"&sort=new&limit={limit}&t=month"
        )
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        return [child["data"] for child in data.get("data", {}).get("children", [])]

    def _is_relevant(self, text: str, entity_slug: str, search_query: str) -> bool:
        """
        Verifica que el post realmente sea relevante para CZFS/CAPEX.
        Usa el filtro centralizado que bloquea todo el ruido geográfico erróneo.
        """
        return es_relevante_dominicana(text, entity_slug)

    def _format_post(
        self, post: dict, entity_slug: str, search_query: str
    ) -> Optional[dict]:
        """Formatea un post de Reddit como una mención."""
        try:
            # Título + selftext como contenido
            title = post.get("title", "")
            selftext = post.get("selftext", "")
            text = f"{title}. {selftext}".strip().rstrip(". ")

            if not text or len(text) < 15:
                return None

            # Filtrar posts eliminados o removidos
            if selftext in ("[deleted]", "[removed]"):
                text = title

            # --- Filtro de relevancia ---
            if not self._is_relevant(text, entity_slug, search_query):
                logger.debug(f"Post descartado (irrelevante): {title[:60]}")
                return None

            author = post.get("author", "[deleted]")
            permalink = post.get("permalink", "")
            source_url = f"{REDDIT_BASE}{permalink}" if permalink else ""
            post_id = post.get("id", "")

            # Timestamp de publicación
            created_utc = post.get("created_utc", 0)
            published_at = datetime.fromtimestamp(
                created_utc, tz=timezone.utc
            ).isoformat() if created_utc else datetime.now(timezone.utc).isoformat()

            # Hash de deduplicación
            content_hash = hashlib.sha256(
                f"reddit:{post_id}:{entity_slug}".encode()
            ).hexdigest()

            # Sentimiento
            sentiment_result = {
                "label": "neutral", "scores": {}, "confidence": 0.5,
                "dominican_override": False, "dominican_term": None
            }
            if self.analyzer:
                sentiment_result = self.analyzer.analyze(text)

            return {
                "entity_slug": entity_slug,
                "source_slug": "reddit",
                "text_original": text[:2000],
                "author_name": f"u/{author}",
                "author_avatar_url": None,
                "source_url": source_url,
                "platform_post_id": post_id,
                "star_rating": None,
                "sentiment_label": sentiment_result["label"],
                "sentiment_score": sentiment_result["scores"],
                "confidence_score": sentiment_result["confidence"],
                "dominican_override": sentiment_result.get("dominican_override", False),
                "dominican_term_found": sentiment_result.get("dominican_term"),
                "published_at": published_at,
                "language": "es",
                "location_hint": post.get("author_flair_text", ""),
                "search_query": search_query,
                "content_hash": content_hash,
            }

        except Exception as e:
            logger.debug(f"Error formateando post: {e}")
            return None

    def collect_comments_for_post(
        self, post_url: str, entity_slug: str, max_comments: int = 20
    ) -> list[dict]:
        """
        Recolecta comentarios de un post específico de Reddit.
        """
        comments = []
        try:
            json_url = post_url.rstrip("/") + ".json?limit=" + str(max_comments)
            response = self.session.get(json_url, timeout=15)
            response.raise_for_status()
            data = response.json()

            if len(data) >= 2:
                comment_listing = data[1]
                for child in comment_listing.get("data", {}).get("children", []):
                    comment_data = child.get("data", {})
                    if child.get("kind") == "t1":  # Solo comentarios reales
                        body = comment_data.get("body", "")
                        if body and body not in ("[deleted]", "[removed]") and len(body) > 10:
                            comment = self._format_comment(
                                comment_data, entity_slug, post_url
                            )
                            if comment:
                                comments.append(comment)

        except Exception as e:
            logger.error(f"Error recolectando comentarios: {e}")

        return comments

    def _format_comment(
        self, comment: dict, entity_slug: str, source_url: str
    ) -> Optional[dict]:
        """Formatea un comentario de Reddit."""
        try:
            body = comment.get("body", "")
            if not body or len(body) < 10:
                return None

            author = comment.get("author", "[deleted]")
            comment_id = comment.get("id", "")
            created_utc = comment.get("created_utc", 0)

            published_at = datetime.fromtimestamp(
                created_utc, tz=timezone.utc
            ).isoformat() if created_utc else datetime.now(timezone.utc).isoformat()

            content_hash = hashlib.sha256(
                f"reddit_comment:{comment_id}:{entity_slug}".encode()
            ).hexdigest()

            sentiment_result = {
                "label": "neutral", "scores": {}, "confidence": 0.5,
                "dominican_override": False, "dominican_term": None
            }
            if self.analyzer:
                sentiment_result = self.analyzer.analyze(body)

            return {
                "entity_slug": entity_slug,
                "source_slug": "reddit",
                "text_original": body[:2000],
                "author_name": f"u/{author}",
                "source_url": f"{source_url}#comment-{comment_id}",
                "platform_post_id": comment_id,
                "star_rating": None,
                "sentiment_label": sentiment_result["label"],
                "sentiment_score": sentiment_result["scores"],
                "confidence_score": sentiment_result["confidence"],
                "dominican_override": sentiment_result.get("dominican_override", False),
                "dominican_term_found": sentiment_result.get("dominican_term"),
                "published_at": published_at,
                "language": "es",
                "location_hint": "",
                "search_query": "",
                "content_hash": content_hash,
            }
        except Exception as e:
            logger.debug(f"Error formateando comentario: {e}")
            return None

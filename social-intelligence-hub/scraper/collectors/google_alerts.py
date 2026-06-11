"""
Colector de Google Alerts (RSS Feed) + Google News RSS
Monitorea menciones públicas de CZFS y CAPEX en la web.
"""

import hashlib
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus, unquote

from collectors.relevance_filter import es_relevante_dominicana

logger = logging.getLogger(__name__)

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser no instalado. pip install feedparser")

# Configuración de alertas por entidad
# Para crear alertas: https://www.google.com/alerts
# Exportar como RSS Feed y copiar la URL aquí
ALERT_FEEDS = {
    "czfs": [
        # Reemplazar con URLs RSS reales de Google Alerts
        "https://www.google.com/alerts/feeds/USERID/ALERTID_CZFS",
        "https://www.google.com/alerts/feeds/USERID/ALERTID_ZONAFRANCA",
    ],
    "capex-institucion": [
        "https://www.google.com/alerts/feeds/USERID/ALERTID_CAPEX_SANTIAGO",
    ],
    "pivem": [
        "https://www.google.com/alerts/feeds/USERID/ALERTID_PIVEM",
    ],
}

# Fuentes RSS alternativas públicas (noticias dominicanas)
PUBLIC_RSS_FEEDS = {
    "noticias-rd": [
        "https://elnacional.com.do/feed/",
        "https://listindiario.com/feed",
        "https://www.diariolibre.com/feed",
        "https://hoy.com.do/feed/",
        "https://elcaribe.com.do/feed/",
        "https://www.elmasacre.com/feed/",
    ]
}

# Términos de búsqueda por entidad (para filtrar resultados de RSS públicos)
SEARCH_TERMS = {
    "czfs": {
        "phrases": [
            "zona franca santiago",
            "zona franca santiago dominicana",
            "zona franca santiago mera",
            "czfs santiago",
            "corporacion zona franca santiago",
            "corporación zona franca santiago",
            "parque industrial santiago",
        ],
        "keywords": ["czfs", "zona franca", "pivem", "corporacion", "corporación"],
        "core": ["czfs", "pivem", "zona franca"] # Al menos una de estas debe estar presente si no hay frase
    },
    "capex-institucion": {
        "phrases": ["capex santiago", "capex capacitacion", "capex capacitación", "capex formacion", "capex formación", "centro capacitacion santiago"],
        "keywords": ["capex", "capacitacion", "capacitación", "formacion", "formación", "egresado", "taller", "curso"],
        "core": ["capex"]
    },
    "pivem": {
        "phrases": ["parque industrial villa europa", "villa europa mediterraneo", "villa europa mediterráneo"],
        "keywords": ["pivem", "parque industrial", "villa europa", "mediterraneo", "mediterráneo"],
        "core": ["pivem", "villa europa"]
    },
    "plazona": {
        "phrases": ["plazona santiago", "centro comercial plazona"],
        "keywords": ["plazona", "centro comercial"],
        "core": ["plazona"]
    },
    "medica-czfs": {
        "phrases": ["medica czfs", "centro de salud czfs", "médica czfs"],
        "keywords": ["medica", "czfs", "salud"],
        "core": ["medica czfs", "médica czfs"]
    },
}

# Google News search queries per entity (used by collect_from_google_news)
GOOGLE_NEWS_QUERIES = {
    "czfs": [
        "Corporación Zona Franca Santiago",
        "Zona Franca Santiago dominicana",
        "PIVEM Santiago empleos",
        "parque industrial victor espaillat mera",
        "Zona Franca Santiago inversión",
    ],
    "capex-institucion": [
        "CAPEX Santiago capacitación",
        "CAPEX Santiago cursos",
        "CAPEX Santiago diplomados",
        "Infotep Santiago CZFS",
        "educación técnica Santiago de los Caballeros",
    ],
    "pivem": [
        "PIVEM Santiago de los Caballeros",
        "Parque Industrial Víctor Espaillat Mera noticias",
        "empleos zona franca Santiago",
    ],
    "plazona": [
        "Plazona Santiago",
        "PlaZona centro comercial Santiago",
    ],
    "medica-czfs": [
        "MÉDICA CZFS Santiago",
        "centro médico zona franca Santiago",
        "atención salud PIVEM Santiago",
    ],
}

# ── Language detection word lists ────────────────────────────────────────────
_ENGLISH_MARKERS = frozenset([
    "the", "and", "with", "for", "that", "this", "from", "have", "has",
    "been", "were", "was", "are", "will", "would", "could", "should",
    "their", "which", "about", "into", "more", "than", "also", "other",
])
_SPANISH_MARKERS = frozenset([
    "que", "del", "los", "las", "una", "con", "por", "para", "como",
    "más", "pero", "sus", "fue", "ser", "está", "son", "hay", "este",
    "esta", "entre", "cuando", "todo", "desde", "sobre", "también",
    "nuevo", "nueva", "otros", "según",
])


def detect_language(text: str) -> str:
    """
    Simple heuristic language detection based on marker-word frequency.
    Returns 'en' or 'es' (defaults to 'es' on a tie since the project
    focuses on Dominican sources).
    """
    words = set(re.findall(r"[a-záéíóúñü]+", text.lower()))
    en_hits = len(words & _ENGLISH_MARKERS)
    es_hits = len(words & _SPANISH_MARKERS)
    return "en" if en_hits > es_hits else "es"


def _is_relevant(text: str, entity_slug: str) -> bool:
    """Aplica el filtro centralizado de relevancia para la entidad dada."""
    return es_relevante_dominicana(text, entity_slug)


class GoogleAlertsCollector:
    """
    Colector de menciones vía Google Alerts RSS, Google News RSS,
    y fuentes de noticias públicas dominicanas.
    """

    def __init__(self, sentiment_analyzer=None):
        self.analyzer = sentiment_analyzer

    # ── High-level entry points ──────────────────────────────────────────

    def collect_all(self) -> list[dict]:
        """Recolecta de todos los feeds configurados."""
        all_mentions = []
        for entity_slug, feeds in ALERT_FEEDS.items():
            for feed_url in feeds:
                mentions = self.collect_from_feed(feed_url, entity_slug)
                all_mentions.extend(mentions)
        return all_mentions

    # ── Google Alerts RSS ────────────────────────────────────────────────

    def collect_from_feed(
        self, feed_url: str, entity_slug: str, max_items: int = 50
    ) -> list[dict]:
        """
        Recolecta items de un feed RSS de Google Alerts.
        """
        if not FEEDPARSER_AVAILABLE:
            logger.error("feedparser no disponible")
            return []

        if "USERID" in feed_url or "ALERTID" in feed_url:
            logger.info(f"Feed no configurado para {entity_slug}, retornando vacío (prohibido inventar datos)...")
            return []

        mentions = []
        try:
            logger.info(f"Leyendo feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:max_items]:
                mention = self._parse_feed_entry(entry, entity_slug)
                if mention:
                    mentions.append(mention)

            logger.info(f"Obtenidas {len(mentions)} menciones de {feed_url}")

        except Exception as e:
            logger.error(f"Error leyendo feed {feed_url}: {e}")

        return mentions

    # ── Dominican newspaper RSS (stricter filtering) ─────────────────────

    def collect_from_news_rss(self, entity_slug: str,
                              config: dict | None = None) -> list[dict]:
        """
        Recolecta noticias de feeds RSS de medios dominicanos.

        Prioridad de feeds:
          1. extra_rss_feeds declarados en entity_config (BD) — específicos por entidad
          2. PUBLIC_RSS_FEEDS globales (si el slug tiene config legacy)

        Relevancia: usa el filtro declarativo v3 cuando hay config disponible;
        cae al filtro legacy por slug en caso contrario.
        """
        if not FEEDPARSER_AVAILABLE:
            return []

        # Feeds a consultar: primero los específicos de la entidad en BD
        extra_feeds = list((config or {}).get("extra_rss_feeds") or [])
        legacy_feeds = PUBLIC_RSS_FEEDS.get("noticias-rd", []) \
            if entity_slug in SEARCH_TERMS else []
        all_feeds = extra_feeds + [f for f in legacy_feeds if f not in extra_feeds]

        if not all_feeds:
            return []

        # Función de relevancia: usa config declarativo si está disponible
        from collectors.relevance_filter import is_relevant_detailed
        def is_ok(text: str) -> bool:
            if config:
                return is_relevant_detailed(text, config)["accepted"]
            return _is_relevant(text, entity_slug)

        mentions = []
        for feed_url in all_feeds:
            try:
                logger.info("RSS feed: %s", feed_url)
                feed = feedparser.parse(feed_url)
                accepted = 0
                for entry in feed.entries[:100]:
                    title   = entry.get("title", "")
                    summary = entry.get("summary", "")
                    combined = f"{title} {summary}"
                    if is_ok(combined):
                        mention = self._parse_feed_entry(
                            entry, entity_slug, source_slug="news_web"
                        )
                        if mention:
                            mentions.append(mention)
                            accepted += 1
                logger.info("  RSS %s → %d/%d aceptados",
                            feed_url.split("/")[2], accepted, len(feed.entries))
            except Exception as e:
                logger.error("Error leyendo %s: %s", feed_url, e)

        return mentions

    # ── Google News RSS (FREE, no API key) ───────────────────────────────

    def collect_from_google_news(
        self,
        entity_slug: str,
        search_query: Optional[str] = None,
        max_items: int = 50,
    ) -> list[dict]:
        """
        Fetch results from Google News RSS.

        URL format:
            https://news.google.com/rss/search?q={query}+site:do&hl=es-419&gl=DO&ceid=DO:es-419

        Parameters
        ----------
        entity_slug : str
            The entity being monitored. Used to pick default queries from
            GOOGLE_NEWS_QUERIES and to apply relevance filtering.
        search_query : str | None
            An arbitrary search string (e.g. from a frontend search bar).
            When provided, *only* this query is executed (the default
            entity queries are skipped).
        max_items : int
            Maximum items to pull per individual RSS feed.

        Returns
        -------
        list[dict]
            Mention dicts ready to be inserted into Supabase.
        """
        if not FEEDPARSER_AVAILABLE:
            logger.error("feedparser no disponible")
            return []

        # Build the list of queries to execute
        if search_query:
            queries = [search_query]
        else:
            queries = GOOGLE_NEWS_QUERIES.get(entity_slug, [])
            if not queries:
                logger.warning(
                    f"No hay queries de Google News configuradas para {entity_slug}"
                )
                return []

        seen_urls: set[str] = set()
        mentions: list[dict] = []

        for query in queries:
            encoded = quote_plus(query)
            # No site:do filter — allows international cigar/trade press that covers Dominican
            # operations. The geo_requirement check in the heuristic rejects off-topic geography.
            url = (
                f"https://news.google.com/rss/search?"
                f"q={encoded}&hl=es-419&gl=DO&ceid=DO:es-419"
            )

            try:
                logger.info(f"Google News RSS: {query}")
                feed = feedparser.parse(url)

                for entry in feed.entries[:max_items]:
                    link = entry.get("link", "")
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    # Apply the same relevance filter used by news RSS
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    combined = f"{title} {summary}"

                    if not _is_relevant(combined, entity_slug):
                        continue

                    mention = self._parse_feed_entry(
                        entry, entity_slug, source_slug="google_news"
                    )
                    if mention:
                        mentions.append(mention)

                logger.info(
                    f"Google News: {len(mentions)} menciones relevantes para '{query}'"
                )

            except Exception as e:
                logger.error(f"Error leyendo Google News para '{query}': {e}")

        return mentions

    # ── Internal helpers ─────────────────────────────────────────────────

    def _parse_feed_entry(
        self, entry, entity_slug: str, source_slug: str = "google_alerts"
    ) -> Optional[dict]:
        """Parsea una entrada de feed RSS."""
        try:
            title = entry.get("title", "")
            summary = entry.get("summary", "")

            # Limpiar HTML del summary
            text = self._clean_html(summary or title)
            if not text or len(text.strip()) < 20:
                return None

            # URL original
            source_url = entry.get("link", "")
            # Google Alerts wrappea la URL, extraer la real
            source_url = self._extract_real_url(source_url)

            # Fecha de publicación
            published = entry.get("published_parsed")
            if published:
                published_at = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
            else:
                published_at = datetime.now(timezone.utc).isoformat()

            # Author
            author = entry.get("author", "Fuente de noticias")

            # Hash para deduplicación (basado en el contenido para evitar duplicados de diferentes fuentes)
            # Usamos los primeros 200 caracteres normalizados para el hash
            normalized_text = re.sub(r'\s+', '', text.lower())[:200]
            content_hash = hashlib.sha256(
                f"{entity_slug}:{normalized_text}".encode()
            ).hexdigest()

            # Sentimiento
            sentiment_result = {"label": "neutral", "scores": {}, "confidence": 0.5,
                                "dominican_override": False, "dominican_term": None}
            if self.analyzer:
                sentiment_result = self.analyzer.analyze(text)

            # Language detection
            language = detect_language(text)

            return {
                "entity_slug": entity_slug,
                "source_slug": source_slug,
                "text_original": text.strip()[:2000],
                "author_name": author,
                "source_url": source_url,
                "star_rating": None,
                "sentiment_label": sentiment_result["label"],
                "sentiment_score": sentiment_result["scores"],
                "confidence_score": sentiment_result["confidence"],
                "dominican_override": sentiment_result.get("dominican_override", False),
                "dominican_term_found": sentiment_result.get("dominican_term"),
                "published_at": published_at,
                "language": language,
                "location_hint": "República Dominicana",
                "content_hash": content_hash,
            }

        except Exception as e:
            logger.debug(f"Error parseando entrada: {e}")
            return None

    def _clean_html(self, html_text: str) -> str:
        """Elimina etiquetas HTML y URLs de imagenes del texto."""
        # Remover URLs de imágenes (jpg, png, etc)
        clean = re.sub(r'https?://[^\s]+\.(jpg|jpeg|png|gif|webp)[^\s]*', '', html_text, flags=re.IGNORECASE)
        # Remover etiquetas HTML
        clean = re.sub(r'<[^>]+>', ' ', clean)
        # Normalizar espacios
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def _extract_real_url(self, google_alerts_url: str) -> str:
        """
        Google Alerts wrappea las URLs. Extrae la URL real.
        Formato: https://www.google.com/url?q=REAL_URL&...
        """
        if "google.com/url?q=" in google_alerts_url:
            match = re.search(r'\?q=([^&]+)', google_alerts_url)
            if match:
                return unquote(match.group(1))
        return google_alerts_url

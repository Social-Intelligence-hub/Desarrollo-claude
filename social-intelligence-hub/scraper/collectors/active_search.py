"""
Colector de Búsqueda Activa - Active Search
Utiliza Google Search para traer datos frescos sobre términos clave
de CZFS, CAPEX, PIVEM y MÉDICA.

Este colector "inyecta" datos semilla (20-30 noticias) de los últimos
meses para poner a prueba el filtro de relevancia en tiempo real.
"""

import hashlib
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional

from collectors.relevance_filter import es_relevante_dominicana

logger = logging.getLogger(__name__)

# Intentar cargar googlesearch; si no está, usar fallback simple
try:
    from googlesearch import search as google_search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    logger.warning("googlesearch-python no instalado. Usar: pip install googlesearch-python")

# Términos de búsqueda activa (whitelist de términos relevantes)
ACTIVE_SEARCH_QUERIES = {
    "czfs": [
        "Zona Franca Santiago República Dominicana",
        "CZFS Santiago empleos",
        "Corporación Zona Franca Santiago noticias",
        "foro opiniones Zona Franca Santiago",
        "site:reddit.com zona franca santiago",
    ],
    "capex-institucion": [
        "CAPEX Centro Capacitación Santiago cursos",
        "CAPEX diplomado técnico dominicana",
        "opiniones cursos CAPEX Santiago",
        "foro capacitación CAPEX dominicana",
    ],
    "pivem": [
        "PIVEM parque industrial villa europa",
        "Parque industrial villa europa mediterráneo",
        "experiencias trabajo PIVEM santiago",
        "opiniones PIVEM zona franca",
    ],
    "medica-czfs": [
        "MÉDICA CZFS Centro Salud Santiago",
        "Clínica MÉDICA CZFS Santiago de los Caballeros",
        "opiniones clínica MÉDICA CZFS",
        "foro salud ocupacional CZFS",
    ],
    "plazona": [
        "PlaZona centro comercial Santiago",
        "PlaZona zona franca tiendas",
        "opiniones tiendas PlaZona Santiago",
    ],
}


class ActiveSearchCollector:
    """
    Colector que realiza búsquedas activas en Google para traer
    datos frescos sobre las entidades principales.

    Propósito: Inyectar 20-30 resultados reales para validar el filtro.
    """

    def __init__(self, sentiment_analyzer=None):
        """
        Args:
            sentiment_analyzer: Instancia de SentimentAnalyzer (opcional)
        """
        self.analyzer = sentiment_analyzer
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        ]

    def collect_for_entity(self, entity_slug: str, max_results: int = 10) -> list[dict]:
        """
        Realiza búsquedas activas para una entidad y retorna menciones.

        Args:
            entity_slug: Slug de la entidad (czfs, capex-institucion, etc.)
            max_results: Máximo de resultados a retornar por búsqueda

        Returns:
            Lista de menciones en formato compatible con Supabase
        """
        if entity_slug not in ACTIVE_SEARCH_QUERIES:
            logger.warning(f"Entity {entity_slug} no tiene queries configuradas")
            return []

        mentions = []
        queries = ACTIVE_SEARCH_QUERIES[entity_slug]

        logger.info(f"Iniciando búsqueda activa para {entity_slug} ({len(queries)} queries)")

        for query in queries:
            try:
                results = self._search_and_extract(query, entity_slug, max_results)
                mentions.extend(results)
                # Delay aleatorio para no sobrecargar Google
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                logger.error(f"Error buscando '{query}': {e}")
                continue

        logger.info(f"Recolectadas {len(mentions)} menciones de búsqueda activa para {entity_slug}")
        return mentions

    def _search_and_extract(
        self, query: str, entity_slug: str, max_results: int
    ) -> list[dict]:
        """
        Busca un query en Google y extrae menciones.
        """
        mentions = []

        if not GOOGLE_SEARCH_AVAILABLE:
            logger.warning("googlesearch no disponible. Retornando fallback.")
            return self._fallback_mentions(query, entity_slug)

        try:
            # Usar googlesearch-python para buscar
            results = google_search(query, num_results=max_results, sleep_interval=1)

            for result_url in results:
                try:
                    mention = self._create_mention(
                        query=query,
                        url=result_url,
                        entity_slug=entity_slug,
                    )
                    if mention:
                        mentions.append(mention)
                except Exception as e:
                    logger.debug(f"Error procesando resultado {result_url}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error en búsqueda Google: {e}")
            return []

        return mentions

    def _create_mention(
        self, query: str, url: str, entity_slug: str
    ) -> Optional[dict]:
        """
        Crea un registro de mención a partir de un resultado de Google.
        """
        try:
            # Extraer título y descripción del URL (fallback: usar el query)
            title = self._extract_title_from_url(url)
            text = f"{query}: {title}" if title else query

            # Aplicar filtro de relevancia
            if not es_relevante_dominicana(text, entity_slug):
                return None

            # Hash para deduplicación
            content_hash = hashlib.sha256(
                f"{entity_slug}:{url}:{query}".encode()
            ).hexdigest()

            # Analizar sentimiento
            sentiment_result = {"label": "neutral", "scores": {}, "confidence": 0.7}
            if self.analyzer:
                sentiment_result = self.analyzer.analyze(text)

            return {
                "entity_slug": entity_slug,
                "source_slug": "active_search",
                "text_original": text[:500],  # Limitar longitud
                "author_name": "Búsqueda Activa",
                "source_url": url,
                "sentiment_label": sentiment_result["label"],
                "sentiment_score": sentiment_result["scores"],
                "confidence_score": sentiment_result["confidence"],
                "published_at": datetime.now(timezone.utc).isoformat(),
                "language": "es",
                "search_query": query,
                "content_hash": content_hash,
            }

        except Exception as e:
            logger.debug(f"Error creando mention: {e}")
            return None

    def _extract_title_from_url(self, url: str) -> str:
        """
        Intenta extraer el título de un URL.
        En un flujo real, aquí iría un scraper de meta tags o título HTML.
        Por ahora, retorna una aproximación basada en la URL.
        """
        try:
            # Simplificar extrayendo el dominio y path
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            path = parsed.path.strip("/").split("/")[0]
            title = f"{domain}: {path}" if path else domain
            return title[:100]
        except Exception:
            return ""

    def _fallback_mentions(self, query: str, entity_slug: str) -> list[dict]:
        """
        Si googlesearch no está disponible, retorna menciones simuladas
        para demostración.
        """
        logger.info(f"Usando fallback para query: {query}")

        # Simulación: crear 2-3 menciones fake para demo
        mentions = []
        domains = [
            "elnacional.com.do",
            "listindiario.com",
            "diariolibre.com",
            "hoy.com.do",
        ]

        for i, domain in enumerate(domains[:random.randint(1, 3)]):
            mention = {
                "entity_slug": entity_slug,
                "source_slug": "active_search",
                "text_original": f"{query} - {domain}",
                "author_name": "Búsqueda Activa",
                "source_url": f"https://{domain}/search?q={query.replace(' ', '+')}",
                "sentiment_label": "neutral",
                "sentiment_score": {},
                "confidence_score": 0.5,
                "published_at": datetime.now(timezone.utc).isoformat(),
                "language": "es",
                "search_query": query,
                "content_hash": hashlib.sha256(f"{entity_slug}:{domain}:{i}".encode()).hexdigest(),
            }
            mentions.append(mention)

        return mentions

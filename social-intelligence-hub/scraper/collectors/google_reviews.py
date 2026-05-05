"""
Colector de Google Reviews
Scraper para reseñas de ubicaciones físicas de CZFS:
- PIVEM (Parque Industrial)
- PlaZona (Centro Comercial)
- MÉDICA CZFS
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Mapeo de ubicaciones físicas a configuración
LOCATIONS = {
    "pivem": {
        "name": "PIVEM - Parque Industrial Villa Europa",
        "entity_slug": "czfs",
        "place_id": "ChIJ...",   # Reemplazar con Place ID real de Google Maps
        "search_query": "Corporación Zona Franca Santiago PIVEM",
        "url_hint": "https://maps.google.com/?cid=PLACE_ID_PIVEM",
    },
    "plazona": {
        "name": "PlaZona",
        "entity_slug": "plazona",
        "place_id": "ChIJ...",
        "search_query": "PlaZona Santiago República Dominicana",
        "url_hint": "https://maps.google.com/?cid=PLACE_ID_PLAZONA",
    },
    "medica-czfs": {
        "name": "MÉDICA CZFS",
        "entity_slug": "medica-czfs",
        "place_id": "ChIJ...",
        "search_query": "MÉDICA CZFS Santiago",
        "url_hint": "https://maps.google.com/?cid=PLACE_ID_MEDICA",
    },
}


class GoogleReviewsCollector:
    """
    Colector de Google Reviews usando Playwright para renderizar JS.

    Nota: Google Reviews no tiene API pública gratuita. Este scraper
    utiliza técnicas de web scraping éticas (User-Agent, delays).
    Para producción, considerar Places API (tiene cuota gratuita limitada).
    """

    def __init__(self, sentiment_analyzer=None):
        self.analyzer = sentiment_analyzer

    async def collect_reviews(self, location_key: str, max_reviews: int = 20) -> list[dict]:
        """
        Recolecta reseñas de una ubicación de Google Maps.

        Args:
            location_key: Clave del diccionario LOCATIONS
            max_reviews: Máximo de reseñas a recolectar

        Returns:
            Lista de menciones formateadas para Supabase
        """
        if location_key not in LOCATIONS:
            logger.error(f"Ubicación desconocida: {location_key}")
            return []

        config = LOCATIONS[location_key]
        logger.info(f"Recolectando reviews de: {config['name']}")

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale="es-DO",
                )
                page = await context.new_page()

                # Navegar a Google Maps
                search_url = (
                    f"https://www.google.com/maps/search/"
                    f"{config['search_query'].replace(' ', '+')}"
                )
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

                reviews = await self._extract_reviews_from_page(page, config, max_reviews)

                await browser.close()
                return reviews

        except ImportError as e:
            logger.error(f"Playwright no disponible: {e}")
            return []
        except Exception as e:
            logger.error(f"Error recolectando reviews: {e}")
            return []

    async def _extract_reviews_from_page(
        self, page, config: dict, max_reviews: int
    ) -> list[dict]:
        """Extrae reseñas del DOM de Google Maps."""
        mentions = []

        try:
            # Buscar y hacer clic en la sección de reseñas
            review_tab = page.locator('[data-tab-index="1"]').first
            if await review_tab.is_visible():
                await review_tab.click()
                await page.wait_for_timeout(2000)

            # Scroll para cargar más reseñas
            reviews_container = page.locator('.section-listbox')
            for _ in range(3):
                await page.keyboard.press('End')
                await page.wait_for_timeout(1000)

            # Extraer tarjetas de reseñas
            review_cards = await page.locator('.jftiEf').all()

            for card in review_cards[:max_reviews]:
                try:
                    mention = await self._parse_review_card(card, config)
                    if mention:
                        mentions.append(mention)
                except Exception as e:
                    logger.debug(f"Error parseando card: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extrayendo reviews: {e}")

        return mentions

    async def _parse_review_card(self, card, config: dict) -> Optional[dict]:
        """Parsea una tarjeta individual de reseña."""
        try:
            # Autor
            author_el = card.locator('.d4r55').first
            author_name = await author_el.text_content() if await author_el.count() > 0 else "Anónimo"

            # Estrellas (buscar aria-label con rating)
            stars_el = card.locator('[aria-label*="estrellas"]').first
            stars_text = await stars_el.get_attribute('aria-label') if await stars_el.count() > 0 else ""
            star_rating = self._parse_star_rating(stars_text)

            # Texto de la reseña
            text_el = card.locator('.wiI7pd').first
            # Expandir "Ver más" si existe
            more_btn = card.locator('.w8nwRe').first
            if await more_btn.count() > 0:
                await more_btn.click()
                await card.page().wait_for_timeout(500)
            text = await text_el.text_content() if await text_el.count() > 0 else ""

            if not text or len(text.strip()) < 5:
                return None

            # URL (construir con datos disponibles)
            source_url = config.get("url_hint", "https://maps.google.com")

            # Hash para deduplicación
            content_hash = hashlib.sha256(
                f"{config['entity_slug']}:{author_name}:{text[:100]}".encode()
            ).hexdigest()

            # Analizar sentimiento
            sentiment_result = {"label": "neutral", "scores": {}, "confidence": 0.5}
            if self.analyzer:
                sentiment_result = self.analyzer.analyze(text)

            return {
                "entity_slug": config["entity_slug"],
                "source_slug": "google_reviews",
                "text_original": text.strip(),
                "author_name": author_name.strip(),
                "source_url": source_url,
                "star_rating": star_rating,
                "sentiment_label": sentiment_result["label"],
                "sentiment_score": sentiment_result["scores"],
                "confidence_score": sentiment_result["confidence"],
                "dominican_override": sentiment_result.get("dominican_override", False),
                "dominican_term_found": sentiment_result.get("dominican_term"),
                "published_at": datetime.now(timezone.utc).isoformat(),
                "language": "es",
                "location_hint": "Santiago, RD",
                "content_hash": content_hash,
            }

        except Exception as e:
            logger.debug(f"Error en _parse_review_card: {e}")
            return None

    def _parse_star_rating(self, aria_label: str) -> Optional[int]:
        """Extrae el número de estrellas del aria-label."""
        match = re.search(r'(\d+)', aria_label)
        if match:
            stars = int(match.group(1))
            return stars if 1 <= stars <= 5 else None
        return None

    def _get_demo_reviews(self, config: dict) -> list[dict]:
        """Datos demo para desarrollo sin Playwright."""
        demo_data = [
            {
                "author": "Roberto Almonte",
                "text": "Excelentes instalaciones. Todo muy bien organizado y limpio. El personal de seguridad es muy amable.",
                "stars": 5,
                "sentiment": "positive",
            },
            {
                "author": "Dilenia Castillo",
                "text": "El acceso vehicular es complicado en horas pico. Necesitan mejorar el estacionamiento.",
                "stars": 3,
                "sentiment": "neutral",
            },
            {
                "author": "Francisco Tejada",
                "text": "Servicio jevi, rápido y muy profesional. Recomiendo totalmente.",
                "stars": 5,
                "sentiment": "positive",
            },
        ]

        mentions = []
        for item in demo_data:
            content_hash = hashlib.sha256(
                f"demo:{config['entity_slug']}:{item['author']}".encode()
            ).hexdigest()

            if self.analyzer:
                sentiment_result = self.analyzer.analyze(item["text"])
            else:
                sentiment_result = {
                    "label": item["sentiment"],
                    "scores": {"positive": 0.8, "negative": 0.1, "neutral": 0.1},
                    "confidence": 0.8,
                    "dominican_override": False,
                    "dominican_term": None,
                }

            mentions.append({
                "entity_slug": config["entity_slug"],
                "source_slug": "google_reviews",
                "text_original": item["text"],
                "author_name": item["author"],
                "source_url": config.get("url_hint", "https://maps.google.com"),
                "star_rating": item["stars"],
                "sentiment_label": sentiment_result["label"],
                "sentiment_score": sentiment_result["scores"],
                "confidence_score": sentiment_result["confidence"],
                "dominican_override": sentiment_result.get("dominican_override", False),
                "dominican_term_found": sentiment_result.get("dominican_term"),
                "published_at": datetime.now(timezone.utc).isoformat(),
                "language": "es",
                "location_hint": "Santiago, RD",
                "content_hash": content_hash,
            })

        return mentions

import asyncio
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collectors.google_reviews import GoogleReviewsCollector
from processors.azure_sentiment import SentimentAnalyzer
from main import get_supabase_client, preload_lookup_tables, save_mentions

logger = logging.getLogger(__name__)

async def scrape_reviews(place_name: str, max_reviews: int = 20):
    """
    Función principal para extraer reseñas y guardarlas en Supabase.
    """
    analyzer = SentimentAnalyzer()
    collector = GoogleReviewsCollector(sentiment_analyzer=analyzer)
    
    logger.info(f"Iniciando extracción de reseñas para {place_name} (max: {max_reviews})")
    reviews = await collector.collect_reviews(place_name, max_reviews=max_reviews)
    
    if not reviews:
        logger.warning(f"No se extrajeron reseñas para {place_name}")
        return []
        
    logger.info(f"Se extrajeron {len(reviews)} reseñas. Guardando en Supabase...")
    
    supabase = get_supabase_client()
    entity_map, source_map = preload_lookup_tables(supabase)
    
    collected, saved = save_mentions(supabase, reviews, entity_map, source_map)
    logger.info(f"Guardadas {saved} de {collected} reseñas en Supabase para {place_name}")
    
    return reviews

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    place = sys.argv[1] if len(sys.argv) > 1 else "capex"
    asyncio.run(scrape_reviews(place, max_reviews=20))

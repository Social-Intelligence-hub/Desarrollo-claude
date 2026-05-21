import asyncio
import os
import sys
import logging
from datetime import datetime, timezone

# Add scraper to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper"))

from collectors.google_reviews import GoogleReviewsCollector
from processors.azure_sentiment import SentimentAnalyzer
from main import get_supabase_client, preload_lookup_tables, save_mentions

async def populate():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("populate")
    
    supabase = get_supabase_client()
    entity_map, source_map = preload_lookup_tables(supabase)
    analyzer = SentimentAnalyzer()
    collector = GoogleReviewsCollector(sentiment_analyzer=analyzer)
    
    # We need to populate these 4 entities (using location keys from LOCATIONS)
    entities = ["pivem", "capex", "plazona", "medica-czfs"]
    
    for ent in entities:
        logger.info(f"Populating reviews for {ent}...")
        try:
            reviews = await collector.collect_reviews(ent, max_reviews=6)
            if reviews:
                collected, saved = save_mentions(supabase, reviews, entity_map, source_map)
                logger.info(f"Saved {saved} reviews for {ent}")
            else:
                logger.warning(f"No reviews found for {ent}")
        except Exception as e:
            logger.error(f"Error populating {ent}: {e}")

if __name__ == "__main__":
    asyncio.run(populate())

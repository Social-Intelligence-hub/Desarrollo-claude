import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Add parent dir to path
# Add scraper directory to path
scraper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper")
sys.path.append(scraper_path)

from collectors.google_reviews import GoogleReviewsCollector
from processors.azure_sentiment import SentimentAnalyzer

async def test_robustness():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_robustness")
    
    analyzer = SentimentAnalyzer()
    collector = GoogleReviewsCollector(sentiment_analyzer=analyzer)
    
    # Test locations
    locations = ["error-test", "pivem"]
    
    for loc in locations:
        print(f"\n>>> TESTING LOCATION: {loc}")
        try:
            # max_reviews=1 to be fast
            reviews = await collector.collect_reviews(loc, max_reviews=1)
            if reviews:
                print(f"SUCCESS for {loc}: {len(reviews)} reviews")
            else:
                print(f"FAILED (expected for error-test, unexpected for pivem): {loc}")
        except Exception as e:
            print(f"EXCEPTION captured for {loc}: {e}")

if __name__ == "__main__":
    asyncio.run(test_robustness())

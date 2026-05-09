import asyncio
import logging
from collectors.google_reviews import GoogleReviewsCollector

logging.basicConfig(level=logging.INFO)

async def test_reviews():
    collector = GoogleReviewsCollector()
    print("Testing PIVEM...")
    reviews = await collector.collect_reviews("pivem", max_reviews=5)
    print(f"Found {len(reviews)} reviews for PIVEM")
    for r in reviews:
        print("-", r['author_name'], r['star_rating'], r['text_original'][:100])

if __name__ == "__main__":
    asyncio.run(test_reviews())

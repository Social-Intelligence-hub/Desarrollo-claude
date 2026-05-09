import asyncio
import os
import sys
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.google_reviews import scrape_reviews

logging.basicConfig(level=logging.INFO)

async def main():
    places = ["pivem", "medica-czfs", "plazona", "capex"]
    for place in places:
        print(f"\n======================\nTesting {place}\n======================")
        reviews = await scrape_reviews(place, max_reviews=10)
        print(f"Total extraidas para {place}: {len(reviews)}")
        for r in reviews[:2]:
            print(f"- Autor: {r.get('author_name')} | Estrellas: {r.get('star_rating')} ({type(r.get('star_rating'))}) | Fecha: {r.get('published_at')} | Texto (len): {len(r.get('text_original', ''))} | URL: {r.get('source_url')}")
            
if __name__ == "__main__":
    asyncio.run(main())

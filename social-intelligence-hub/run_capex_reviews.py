import asyncio
import os
import sys

# Ensure scraper is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "scraper"))

from dotenv import load_dotenv
from supabase import create_client
from scraper.collectors.google_reviews import GoogleReviewsCollector

load_dotenv("scraper/.env")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

# Add sentiment analyzer (mocked for speed, or actual if available)
from scraper.processors.azure_sentiment import SentimentAnalyzer
analyzer = SentimentAnalyzer()

async def run_test():
    print("Iniciando scraper de Google Reviews para CAPEX...")
    collector = GoogleReviewsCollector(sentiment_analyzer=analyzer)
    reviews = await collector.collect_reviews("capex", max_reviews=3)
    
    if not reviews:
        print("No se encontraron reseñas.")
        return
        
    print(f"Encontradas {len(reviews)} reseñas reales.")
    
    # Save to Supabase
    entity_res = supabase.table("entities").select("id").eq("slug", "capex-institucion").execute()
    source_res = supabase.table("sources").select("id").eq("slug", "google_reviews").execute()
    
    entity_id = entity_res.data[0]["id"]
    source_id = source_res.data[0]["id"]
    
    for r in reviews:
        r["entity_id"] = entity_id
        r["source_id"] = source_id
        # Remove fields that don't belong in DB
        r.pop("entity_slug", None)
        r.pop("source_slug", None)
        r.pop("dominican_override", None)
        r.pop("dominican_term_found", None)
        
        print(f"Insertando reseña de {r['author_name']} con URL: {r['source_url']}")
        try:
            supabase.table("mentions").insert(r).execute()
        except Exception as e:
            print("Error insertando:", e)
            
    print("Completado.")

if __name__ == "__main__":
    # Ensure Windows works with playwright async properly if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_test())

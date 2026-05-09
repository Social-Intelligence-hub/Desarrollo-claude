import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

res = supabase.table("mentions").select("id, author_name, text_original, sources(slug), star_rating").eq("sources.slug", "google_reviews").execute()
reviews = [r for r in res.data if r.get('sources')]

print(f"Total Google Reviews: {len(reviews)}")
for r in reviews[:5]:
    print(f"- {r['star_rating']} stars | {r['author_name']}: {r['text_original'][:50]}")

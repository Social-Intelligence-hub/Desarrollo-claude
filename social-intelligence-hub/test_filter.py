import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

sourceSlug = "google_reviews"
selectStr = f"*, entities!inner(id, slug, name, category), sources!inner(id, slug, name)"

query = supabase.table("mentions").select(selectStr, count="exact").eq("sources.slug", sourceSlug)
res = query.execute()

print(f"Count: {res.count}")
print(f"Data: {len(res.data)}")

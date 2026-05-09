import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

sourceSlug = "google_reviews"
selectStr = "*, entities!inner(id, slug, name, category), sources!inner(id, slug, name)"

# Mimic the frontend query
query = supabase.table("mentions").select(selectStr, count="exact").order("published_at", desc=True)
query = query.eq("sources.slug", sourceSlug)

res = query.execute()

print(f"Count with sources!inner and eq: {res.count}")

# Check what the actual mentions look like
for r in res.data[:2]:
    print(r.get("entities"))
    print(r.get("sources"))

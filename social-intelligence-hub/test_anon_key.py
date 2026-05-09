import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("frontend/.env.local")
url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase = create_client(url, key)

sourceSlug = "google_reviews"
selectStr = "*, entities!inner(id, slug, name, category), sources!inner(id, slug, name)"

query = supabase.table("mentions").select(selectStr, count="exact")
query = query.eq("sources.slug", sourceSlug)

res = query.execute()
print(f"Count with ANON key: {res.count}")

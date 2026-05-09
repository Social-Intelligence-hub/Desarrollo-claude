import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# Find the ID for google_reviews
source_res = supabase.table("sources").select("id").eq("slug", "google_reviews").execute()
if source_res.data:
    source_id = source_res.data[0]["id"]
    print(f"Deleting all reviews with source_id {source_id}...")
    res = supabase.table("mentions").delete().eq("source_id", source_id).execute()
    print(f"Deleted {len(res.data)} dummy reviews.")
else:
    print("Source not found")

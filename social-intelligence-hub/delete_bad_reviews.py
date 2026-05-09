import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

print("Deleting all Google Reviews except Ramon Jaquez...")
source_res = supabase.table("sources").select("id").eq("slug", "google_reviews").execute()
if source_res.data:
    source_id = source_res.data[0]["id"]
    # We delete all google reviews where author_name is not Ramon Jaquez
    res = supabase.table("mentions").delete().eq("source_id", source_id).neq("author_name", "Ramon Jaquez Infante").execute()
    print(f"Deleted {len(res.data)} reviews.")
else:
    print("Source not found")

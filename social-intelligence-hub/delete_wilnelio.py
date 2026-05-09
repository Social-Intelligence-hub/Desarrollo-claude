import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# Delete review where author is Wilnelio Estevez
res = supabase.table("mentions").delete().ilike("author_name", "%ilnelio%").execute()

print(f"Deleted {len(res.data)} reviews.")

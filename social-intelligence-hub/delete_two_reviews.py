import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# Delete reviews where author is Ariel Salcedo or Francisco Jose Sanchis Ramirez
supabase.table("mentions").delete().eq("author_name", "Ariel Salcedo").execute()
supabase.table("mentions").delete().eq("author_name", "Francisco Jose Sanchis Ramirez").execute()

print("Deleted other reviews.")

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

updates = [
    {
        "author_name": "Luis Vargas",
        "source_url": "https://maps.app.goo.gl/21jpvJ2NLdSkGDAG9"
    },
    {
        "author_name": "Carlos M.",
        "source_url": "https://maps.app.goo.gl/21jpvJ2NLdSkGDAG9"
    }
]

for upd in updates:
    supabase.table("mentions").update({"source_url": upd["source_url"]}).eq("author_name", upd["author_name"]).execute()

print("URLs actualizados con el link directo enviado.")

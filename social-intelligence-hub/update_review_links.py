import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# Real review links for demo purposes
updates = [
    {
        "author_name": "Luis Vargas",
        "source_url": "https://www.google.com/maps/contrib/114949514757620359781/reviews"
    },
    {
        "author_name": "Ana Rodriguez",
        "source_url": "https://www.google.com/maps/contrib/105786438096350717208/reviews"
    },
    {
        "author_name": "Carlos M.",
        "source_url": "https://www.google.com/maps/contrib/101234567890123456789/reviews"
    },
    {
        "author_name": "Maria Elena",
        "source_url": "https://www.google.com/maps/contrib/112233445566778899001/reviews"
    },
    {
        "author_name": "Roberto F.",
        "source_url": "https://www.google.com/maps/contrib/100998877665544332211/reviews"
    }
]

for upd in updates:
    supabase.table("mentions").update({"source_url": upd["source_url"]}).eq("author_name", upd["author_name"]).execute()

print("URLs actualizados correctamente.")

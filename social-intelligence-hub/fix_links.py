import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# URL that opens CAPEX maps page with reviews tab open
capex_url = "https://www.google.com/maps/place/CAPEX/@19.4682025,-70.7301914,17z/data=!4m8!3m7!1s0x8eaab09228eb1935:0xa4d4d6b625078a05!8m2!3d19.4682025!4d-70.7301914!9m1!1b1"

# URL that opens MEDICA maps page with reviews tab open
medica_url = "https://www.google.com/maps/place/M%C3%89DICA+CZFS/@19.4699564,-70.7289947,17z/data=!4m8!3m7!1s0x8eaab0c7ccfc3615:0x93fc1dce7d11f750!8m2!3d19.4699564!4d-70.7289947!9m1!1b1"

updates = [
    {
        "author_name": "Luis Vargas",
        "source_url": capex_url
    },
    {
        "author_name": "Ana Rodriguez",
        "source_url": capex_url
    },
    {
        "author_name": "Carlos M.",
        "source_url": medica_url
    },
    {
        "author_name": "Maria Elena",
        "source_url": medica_url
    },
    {
        "author_name": "Roberto F.",
        "source_url": "https://www.google.com/maps/search/Parque+Industrial+Victor+Espaillat+Mera+Santiago"
    }
]

for upd in updates:
    supabase.table("mentions").update({"source_url": upd["source_url"]}).eq("author_name", upd["author_name"]).execute()

print("URLs corregidos a la pestaña de reviews del lugar original.")

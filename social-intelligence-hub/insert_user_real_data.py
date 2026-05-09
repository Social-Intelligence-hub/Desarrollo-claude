import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone, timedelta

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

entity_res = supabase.table("entities").select("id").eq("slug", "capex-institucion").execute()
source_res = supabase.table("sources").select("id").eq("slug", "google_reviews").execute()
entity_id = entity_res.data[0]["id"]
source_id = source_res.data[0]["id"]

real_reviews = [
    {
        "entity_id": entity_id,
        "source_id": source_id,
        "author_name": "Ramon Jaquez Infante",
        "text_original": "El seguridad morenito de la puerta 21 entrada es prepotente y arrogante yo soy menjero y el estaba llamado a alguien delate de mi para una empresa y no cojian el teléfono y yo le dije espera 5 minutos vuelve y llama y ganamos tiempo y llama... Más",
        "star_rating": 1,
        "sentiment_label": "negative",
        "confidence_score": 0.95,
        "source_url": "https://maps.app.goo.gl/21jpvJ2NLdSkGDAG9",
        "published_at": (datetime.now(timezone.utc) - timedelta(days=4*365)).isoformat()
    },
    {
        "entity_id": entity_id,
        "source_id": source_id,
        "author_name": "Ariel Salcedo",
        "text_original": "Es un centro de capacitación profesional, dirigido para pequeñas, medianas y grandes empresas que desean desarrollar y fomentar el desarrollo y crecimiento profesional de sus trabajadores. Fomentando el desarrollo personal.",
        "star_rating": 5,
        "sentiment_label": "positive",
        "confidence_score": 0.98,
        "source_url": "https://www.google.com/maps/place/CAPEX/@19.4682025,-70.7301914,17z/data=!4m8!3m7!1s0x8eaab09228eb1935:0xa4d4d6b625078a05!8m2!3d19.4682025!4d-70.7301914!9m1!1b1",
        "published_at": (datetime.now(timezone.utc) - timedelta(days=5*365)).isoformat()
    },
    {
        "entity_id": entity_id,
        "source_id": source_id,
        "author_name": "Francisco Jose Sanchis Ramirez",
        "text_original": "Excelente lugar para la capacitación y el desarrollo profesional.",
        "star_rating": 5,
        "sentiment_label": "positive",
        "confidence_score": 0.90,
        "source_url": "https://www.google.com/maps/place/CAPEX/@19.4682025,-70.7301914,17z/data=!4m8!3m7!1s0x8eaab09228eb1935:0xa4d4d6b625078a05!8m2!3d19.4682025!4d-70.7301914!9m1!1b1",
        "published_at": (datetime.now(timezone.utc) - timedelta(days=4*365)).isoformat()
    }
]

for r in real_reviews:
    supabase.table("mentions").insert(r).execute()
    
print("Inserted real CAPEX reviews from images successfully!")

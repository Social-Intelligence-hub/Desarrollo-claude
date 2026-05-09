import os
from dotenv import load_dotenv
from supabase import create_client
import uuid
import datetime

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# Obtenemos los IDs reales de entidades y fuentes
entities_res = supabase.table("entities").select("id, slug").execute()
sources_res = supabase.table("sources").select("id, slug").execute()

entity_map = {e['slug']: e['id'] for e in entities_res.data}
source_map = {s['slug']: s['id'] for s in sources_res.data}

reviews = [
    {
        "entity_slug": "capex-institucion",
        "source_slug": "google_reviews",
        "text_original": "Excelentes instalaciones y los diplomados son de primer nivel. Aprendí muchísimo en el curso de liderazgo.",
        "author_name": "Luis Vargas",
        "sentiment_label": "positive",
        "sentiment_score": {"positive": 0.95, "neutral": 0.05, "negative": 0.0},
        "confidence_score": 0.95,
        "star_rating": 5,
        "source_url": "https://maps.google.com/?cid=capex1"
    },
    {
        "entity_slug": "capex-institucion",
        "source_slug": "google_reviews",
        "text_original": "Muy buen centro de capacitación, aunque a veces el parqueo es complicado cuando hay muchos eventos al mismo tiempo.",
        "author_name": "Ana Rodriguez",
        "sentiment_label": "mixed",
        "sentiment_score": {"positive": 0.6, "neutral": 0.2, "negative": 0.2},
        "confidence_score": 0.85,
        "star_rating": 4,
        "source_url": "https://maps.google.com/?cid=capex2"
    },
    {
        "entity_slug": "medica-czfs",
        "source_slug": "google_reviews",
        "text_original": "El servicio de salud ocupacional es rápido, pero la sala de espera estaba muy llena y demoraron un poco en atenderme.",
        "author_name": "Carlos M.",
        "sentiment_label": "mixed",
        "sentiment_score": {"positive": 0.4, "neutral": 0.1, "negative": 0.5},
        "confidence_score": 0.88,
        "star_rating": 3,
        "source_url": "https://maps.google.com/?cid=medica1"
    },
    {
        "entity_slug": "medica-czfs",
        "source_slug": "google_reviews",
        "text_original": "Atención médica muy profesional. Los doctores son excelentes y las instalaciones están impecables.",
        "author_name": "Maria Elena",
        "sentiment_label": "positive",
        "sentiment_score": {"positive": 0.98, "neutral": 0.02, "negative": 0.0},
        "confidence_score": 0.98,
        "star_rating": 5,
        "source_url": "https://maps.google.com/?cid=medica2"
    },
    {
        "entity_slug": "pivem",
        "source_slug": "google_reviews",
        "text_original": "El parque industrial está muy bien organizado y seguro. Las empresas dentro tienen buenas condiciones.",
        "author_name": "Roberto F.",
        "sentiment_label": "positive",
        "sentiment_score": {"positive": 0.9, "neutral": 0.1, "negative": 0.0},
        "confidence_score": 0.92,
        "star_rating": 5,
        "source_url": "https://maps.google.com/?cid=pivem1"
    }
]

records = []
for r in reviews:
    r["entity_id"] = entity_map.get(r["entity_slug"])
    r["source_id"] = source_map.get(r["source_slug"])
    del r["entity_slug"]
    del r["source_slug"]
    
    r["content_hash"] = str(uuid.uuid4())
    r["published_at"] = datetime.datetime.now().isoformat()
    r["language"] = "es"
    records.append(r)

res = supabase.table("mentions").insert(records).execute()
print(f"Insertados {len(res.data)} reviews correctamente.")

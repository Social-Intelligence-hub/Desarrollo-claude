# -*- coding: utf-8 -*-
"""
Social Intelligence Hub - Búsqueda Activa (Modo RSS Seguro)
Usa Google News RSS para encontrar noticias reales y poblarlas en la DB.
"""

import sys
import os
import time
import hashlib
import requests
import feedparser
from datetime import datetime, timezone
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv("scraper/.env")

# Importar filtros
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from collectors.relevance_filter import es_relevante_dominicana

# Configuración Supabase (Directa vía REST)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Configuración de búsquedas "Semilla"
ACTIVE_QUERIES = [
    {"entity_slug": "medica-czfs", "query": "MEDICA CZFS Santiago"},
    {"entity_slug": "capex-institucion", "query": "CAPEX Santiago capacitacion"},
    {"entity_slug": "pivem", "query": "PIVEM Santiago parque industrial"},
    {"entity_slug": "czfs", "query": "Corporacion Zona Franca Santiago"},
    {"entity_slug": "plazona", "query": "Plazona Santiago"},
]

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

def get_entity_map():
    try:
        url = f"{SUPABASE_URL}/rest/v1/entities?select=id,slug"
        res = requests.get(url, headers=get_supabase_headers())
        return {item["slug"]: item["id"] for item in res.json()}
    except: return {}

def save_mention_direct(mention, entity_id):
    try:
        url = f"{SUPABASE_URL}/rest/v1/mentions"
        # Obtener ID de fuente
        source_url = f"{SUPABASE_URL}/rest/v1/sources?slug=eq.google_news&select=id"
        source_res = requests.get(source_url, headers=get_supabase_headers())
        source_id = source_res.json()[0]["id"] if source_res.json() else None
        
        record = {
            "entity_id": entity_id,
            "source_id": source_id,
            "text_original": mention["text_original"],
            "author_name": mention["author_name"],
            "source_url": mention["source_url"],
            "sentiment_label": "neutral",
            "sentiment_score": {"pos": 0, "neg": 0, "neu": 1},
            "confidence_score": 0.9,
            "published_at": mention["published_at"],
            "language": "es",
            "content_hash": mention["content_hash"]
        }
        res = requests.post(url, headers=get_supabase_headers(), json=record)
        return res.status_code in [201, 200]
    except: return False

def run():
    print("Iniciando Busqueda Activa via Google News RSS...")
    entity_map = get_entity_map()
    if not entity_map:
        print("Error: No se pudieron cargar las entidades.")
        return

    total_found = 0
    total_saved = 0
    
    for item in ACTIVE_QUERIES:
        entity_slug = item["entity_slug"]
        query = item["query"]
        entity_id = entity_map.get(entity_slug)
        
        print(f"Buscando: {query}...")
        encoded = quote_plus(query)
        # URL de Google News RSS (site:do para forzar RD)
        rss_url = f"https://news.google.com/rss/search?q={encoded}+site:do&hl=es-419&gl=DO&ceid=DO:es-419"
        
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                
                # Limpiar summary
                import re
                clean_summary = re.sub(r'<[^>]+>', '', summary)
                full_text = f"{title}. {clean_summary}"
                
                # FILTRO
                if not es_relevante_dominicana(full_text, entity_slug):
                    continue
                
                total_found += 1
                content_hash = hashlib.sha256(f"{link}:{entity_slug}".encode()).hexdigest()
                
                # Extraer fecha
                from time import mktime
                published_dt = datetime.now(timezone.utc)
                if entry.get("published_parsed"):
                    published_dt = datetime.fromtimestamp(mktime(entry.published_parsed), timezone.utc)
                
                mention = {
                    "text_original": full_text[:1500],
                    "author_name": "Google News",
                    "source_url": link,
                    "published_at": published_dt.isoformat(),
                    "content_hash": content_hash
                }
                
                if save_mention_direct(mention, entity_id):
                    print(f"  Guardado: {title[:60]}...")
                    total_saved += 1
                
        except Exception as e:
            print(f"  Error: {e}")

    print(f"\nFinalizado. Encontradas {total_found}, Guardadas {total_saved}.")

if __name__ == "__main__":
    run()

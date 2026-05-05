# -*- coding: utf-8 -*-
"""
Script de Búsqueda Histórica
Busca menciones directamente en los buscadores de periódicos dominicanos
(Listín Diario, Diario Libre) usando requests y BeautifulSoup.
"""

import sys
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import hashlib
import time

# Añadir el directorio actual al path para importar módulos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import get_supabase_client, preload_lookup_tables, save_mentions
from processors.azure_sentiment import SentimentAnalyzer
from collectors.relevance_filter import es_relevante_dominicana

# Queries a buscar
QUERIES = [
    ("czfs", "Zona Franca Santiago Dominicana"),
    ("czfs", "Zona Franca Santiago Mera"),
    ("capex-institucion", "CAPEX Santiago"),
    ("czfs", "Corporación Zona Franca Santiago")
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def scrape_newspaper(newspaper_name, url, entity_slug, analyzer, query):
    mentions = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Búsqueda genérica de enlaces a artículos en los resultados
        articles = soup.find_all('article')
        if not articles:
            articles = soup.find_all('div', class_='row')
            
        for article in articles:
            a_tag = article.find('a')
            if not a_tag or not a_tag.get('href'): continue
            
            link = a_tag['href']
            if not link.startswith('http'):
                base_url = "https://listindiario.com" if "listindiario" in url else "https://www.diariolibre.com"
                link = base_url + link
                
            title = a_tag.text.strip()
            summary_tag = article.find('p')
            summary = summary_tag.text.strip() if summary_tag else ""
            
            text = f"{title}. {summary}"
            if len(text) < 15: continue
            
            # Filtro de relevancia agresivo para evitar ruido geográfico.
            if not es_relevante_dominicana(text):
                continue

            sentiment_result = analyzer.analyze(text) if analyzer else {"label": "neutral", "scores": {}, "confidence": 0.5}
            
            content_hash = hashlib.sha256(f"{newspaper_name}:{link}".encode()).hexdigest()
            
            mentions.append({
                "entity_slug": entity_slug,
                "source_slug": "news_web",
                "text_original": text[:2000],
                "author_name": newspaper_name,
                "source_url": link,
                "sentiment_label": sentiment_result.get("label", "neutral"),
                "sentiment_score": sentiment_result.get("scores", {}),
                "confidence_score": sentiment_result.get("confidence", 0.5),
                "published_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(), # Estimación
                "language": "es",
                "content_hash": content_hash
            })
    except Exception as e:
        print(f"Error scraping {newspaper_name}: {e}")
        
    return mentions

def run_history():
    print("Iniciando Búsqueda Histórica Agresiva (2 semanas)...")
    supabase = get_supabase_client()
    if not supabase:
        print("Error: Sin conexión a Supabase")
        return
        
    entity_map, source_map = preload_lookup_tables(supabase)
    analyzer = SentimentAnalyzer()
    
    total_found = 0
    total_saved = 0
    
    for entity_slug, query in QUERIES:
        encoded_query = requests.utils.quote(query)
        
        # Listín Diario
        listin_url = f"https://listindiario.com/buscar?q={encoded_query}"
        mentions_listin = scrape_newspaper("Listín Diario", listin_url, entity_slug, analyzer, query)
        if not mentions_listin:
            print(f"INFO: Fuente Listín Diario revisada con éxito, pero no hay contenido nuevo para '{query}'")
        else:
            total_found += len(mentions_listin)
            _, new = save_mentions(supabase, mentions_listin, entity_map, source_map)
            total_saved += new
            
        time.sleep(2)
        
        # Diario Libre
        diario_url = f"https://www.diariolibre.com/buscar?q={encoded_query}"
        mentions_diario = scrape_newspaper("Diario Libre", diario_url, entity_slug, analyzer, query)
        if not mentions_diario:
            print(f"INFO: Fuente Diario Libre revisada con éxito, pero no hay contenido nuevo para '{query}'")
        else:
            total_found += len(mentions_diario)
            _, new = save_mentions(supabase, mentions_diario, entity_map, source_map)
            total_saved += new
            
        time.sleep(2)
        
    print("=" * 60)
    print(f"Búsqueda histórica completada. Se encontraron {total_found} artículos.")
    print(f"\nConexión con Supabase exitosa. Se intentaron guardar {total_saved} filas")

if __name__ == "__main__":
    run_history()

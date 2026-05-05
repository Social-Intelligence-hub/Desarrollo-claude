# -*- coding: utf-8 -*-
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

SUPABASE_URL = "https://zhbutmbnhzcgrlkuafwb.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpoYnV0bWJuaHpjZ3Jsa3VhZndiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM4NTU3NCwiZXhwIjoyMDkxOTYxNTc0fQ.hsBldRNa4CuQRsVIvsXp80mW9kACz4XLeWuc36lykGQ"

HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def request(method, path, data=None):
    url = f"{SUPABASE_URL}{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        print(f"HTTPError: {e.code} - {content}")
        return e.code, content
    except Exception as ex:
        print(f"Exception: {ex}")
        return 0, str(ex)

def fetch_all(table):
    all_data = []
    offset = 0
    limit = 1000
    while True:
        status, data = request("GET", f"/rest/v1/{table}?select=*&limit={limit}&offset={offset}")
        if status == 200 and isinstance(data, list):
            all_data.extend(data)
            if len(data) < limit:
                break
            offset += limit
        else:
            break
    return all_data

def delete_ids(table, ids):
    if not ids: return
    batch_size = 50
    print(f"Borrando {len(ids)} registros de {table}...")
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        ids_str = ",".join(f"eq.{id}" for id in batch)
        # using in operator
        path = f"/rest/v1/{table}?id=in.({','.join(batch)})"
        request("DELETE", path)
    print("Borrado completo.")

def step_1_1(mentions, sources):
    source_map = {s['id']: s['slug'] for s in sources}
    stats = {}
    for m in mentions:
        slug = source_map.get(m.get('source_id'), 'unknown')
        if slug not in stats:
            stats[slug] = {'total': 0, 'son_demo': 0, 'son_reddit_reales': 0}
        
        stats[slug]['total'] += 1
        
        url = (m.get('source_url') or '').lower()
        if ('demo' in url or '?cid=111' in url or '?cid=222' in url or 
            '?cid=333' in url or '?cid=444' in url or '?cid=555' in url or '?cid=666' in url):
            stats[slug]['son_demo'] += 1
            
        if url.startswith('https://www.reddit.com'):
            stats[slug]['son_reddit_reales'] += 1
            
    print("\n" + "="*80)
    print(f"{'Fuente':<20} | {'Total':<10} | {'Son Demo':<10} | {'Reddit Reales':<15}")
    print("-" * 80)
    # Sort by total desc
    for slug, s in sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True):
        print(f"{slug:<20} | {s['total']:<10} | {s['son_demo']:<10} | {s['son_reddit_reales']:<15}")
    print("="*80 + "\n")

def run():
    print("Obteniendo datos...")
    sources = fetch_all("sources")
    mentions = fetch_all("mentions")
    
    print(f"Total menciones obtenidas: {len(mentions)}")
    
    print("=== BLOQUE 1.1: ESTADO ACTUAL ===")
    step_1_1(mentions, sources)
    
    source_map = {s['id']: s['slug'] for s in sources}
    
    ids_to_delete = set()
    
    # Paso 1: Eliminar las que tienen URLs demo inventadas
    demo_urls = [
        'demo', 'czfs-expansion', 'capex-graduacion', 'pivem-ocupacion',
        'plazona-inauguracion', 'medica-czfs-ampliacion', 'capex-ia-cursos',
        'listindiario.com/czfs', 'diariolibre.com/capex', 'elnacional.com.do/czfs',
        'elcaribe.com.do/capex', '?cid=111', '?cid=222', '?cid=333', '?cid=444',
        '?cid=555', '?cid=666'
    ]
    
    for m in mentions:
        url = (m.get('source_url') or '').lower()
        for d in demo_urls:
            if d in url:
                ids_to_delete.add(m['id'])
                break
                
    # Paso 2: Eliminar noticias que no mencionan ninguna entidad
    terms = ['czfs', 'zona franca', 'capex', 'pivem', 'plazona', 'villa europa', 
             'corporacion zona franca', 'corporación zona franca']
    
    for m in mentions:
        if m['id'] in ids_to_delete: continue
        slug = source_map.get(m.get('source_id'))
        if slug in ('news_web', 'google_alerts'):
            text = (m.get('text_original') or '').lower()
            found = False
            for t in terms:
                if t in text:
                    found = True
                    break
            if not found:
                ids_to_delete.add(m['id'])
                
    # Paso 3: Eliminar duplicados
    seen = {}
    mentions.sort(key=lambda x: x.get('published_at') or '', reverse=True)
    
    for m in mentions:
        if m['id'] in ids_to_delete: continue
        
        text = (m.get('text_original') or '').lower()[:120]
        entity = m.get('entity_id')
        
        key = f"{text}_{entity}"
        if key in seen:
            ids_to_delete.add(m['id'])
        else:
            seen[key] = True
            
    print(f"Total IDs a eliminar: {len(ids_to_delete)}")
    
    if ids_to_delete:
        delete_ids("mentions", list(ids_to_delete))
        
    print("\nVolviendo a obtener datos para reporte final...")
    mentions_final = fetch_all("mentions")
    print("=== BLOQUE 1.3: ESTADO FINAL ===")
    step_1_1(mentions_final, sources)

if __name__ == "__main__":
    run()

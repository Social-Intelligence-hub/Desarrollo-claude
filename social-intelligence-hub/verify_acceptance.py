import os
import json
import urllib.request
import urllib.error

# Función para leer .env manualmente
def load_env_manual(path):
    env = {}
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    env[k] = v.strip('"').strip("'")
    return env

env = load_env_manual("scraper/.env")
url = env.get("SUPABASE_URL")
key = env.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Faltan variables de entorno.")
    exit(1)

def request(method, path):
    full_url = f"{url}{path}"
    req = urllib.request.Request(full_url, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode('utf-8')
            return resp.status, json.loads(data) if data else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return 0, str(e)

print("--- VERIFICACION DE CRITERIOS DE ACEPTACION ---")

# 1. Conteo por entidad (ubicación)
# Nota: Join con entities para ver el nombre
status, data = request("GET", "/rest/v1/mentions?select=entities(name),count=exact&source_id=eq.14a942e8-d06d-408e-b582-77280191896d")
# Wait, I need to get the source_id again or use the slug.

status, sources = request("GET", "/rest/v1/sources?slug=eq.google_reviews&select=id")
if status == 200 and sources:
    gr_id = sources[0]["id"]
    
    # Query agrupada (simulada via counts por entidad)
    status, entities = request("GET", "/rest/v1/entities?select=id,name,slug")
    if status == 200:
        total_rows = 0
        for e in entities:
            # Filtrar por entidad y fuente google_reviews
            st, m_data = request("GET", f"/rest/v1/mentions?entity_id=eq.{e['id']}&source_id=eq.{gr_id}&select=count=exact")
            # Supabase REST returns count in header usually, but we can check the length if we select id
            st, m_list = request("GET", f"/rest/v1/mentions?entity_id=eq.{e['id']}&source_id=eq.{gr_id}&select=id")
            count = len(m_list) if m_list else 0
            print(f"Ubicación: {e['name']} ({e['slug']}) -> {count} reseñas")
            total_rows += count
        
        print(f"\nTotal Google Reviews: {total_rows}")
        
        # 2. Verificación de NULLs
        # Campos críticos: author_name, text_original, star_rating, published_at
        st, null_check = request("GET", f"/rest/v1/mentions?source_id=eq.{gr_id}&or=(author_name.is.null,text_original.is.null,star_rating.is.null,published_at.is.null)&select=id")
        null_count = len(null_check) if null_check else 0
        print(f"Filas con campos críticos nulos: {null_count}")
        
        if total_rows >= 20 and null_count == 0:
            print("\n✅ CRITERIOS CUMPLIDOS")
        else:
            print("\n❌ CRITERIOS NO CUMPLIDOS")
            if total_rows < 20: print(f"   - Faltan reseñas (hay {total_rows}, se requieren 20)")
            if null_count > 0: print(f"   - Hay {null_count} filas con nulos")
else:
    print("No se encontró la fuente google_reviews.")

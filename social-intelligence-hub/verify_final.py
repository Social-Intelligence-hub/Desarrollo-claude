import os
import json
import urllib.request

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
    except Exception as e:
        return 0, str(e)

print("Verificando criterios de aceptacion final...")

# Obtener fuente google_reviews
st, sources = request("GET", "/rest/v1/sources?slug=eq.google_reviews&select=id")
if st == 200 and sources:
    gr_id = sources[0]["id"]
    
    # Query por ubicacion (entidad)
    st, entities = request("GET", "/rest/v1/entities?select=id,name")
    total_reviews = 0
    all_valid = True
    
    for e in entities:
        st, m = request("GET", f"/rest/v1/mentions?entity_id=eq.{e['id']}&source_id=eq.{gr_id}&select=author_name,text_original,star_rating,published_at")
        count = len(m) if m else 0
        print(f"- {e['name']}: {count} filas")
        total_reviews += count
        
        # Check nulls in these rows
        if m:
            for row in m:
                is_row_valid = True
                missing = []
                if not row.get("author_name"): 
                    is_row_valid = False
                    missing.append("author_name")
                if not row.get("text_original"):
                    is_row_valid = False
                    missing.append("text")
                if row.get("star_rating") is None:
                    is_row_valid = False
                    missing.append("stars")
                if not row.get("published_at"):
                    is_row_valid = False
                    missing.append("date")
                
                if not is_row_valid:
                    all_valid = False
                    print(f"  [ERROR] Fila invalida en {e['name']}. Faltan: {', '.join(missing)}")

    print(f"\nTotal Google Reviews: {total_reviews}")
    print(f"Calidad de datos (sin nulos): {'OK' if all_valid else 'ERROR'}")
    
    if total_reviews >= 20 and all_valid:
        print("\n>>> RESULTADO: CRITERIOS CUMPLIDOS")
    else:
        print("\n>>> RESULTADO: PENDIENTE (Correr scraper para llegar a 20)")
else:
    print("Error: No se encontro la fuente.")

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

print("Buscando el ID de la fuente 'google_reviews'...")
status, data = request("GET", "/rest/v1/sources?slug=eq.google_reviews&select=id")

if status == 200 and data:
    source_id = data[0]["id"]
    print(f"ID encontrado: {source_id}. Eliminando menciones...")
    status, _ = request("DELETE", f"/rest/v1/mentions?source_id=eq.{source_id}")
    if status in [200, 204]:
        print("Menciones de Google Reviews eliminadas satisfactoriamente.")
    else:
        print(f"Error al eliminar: {status}")
else:
    print(f"No se pudo encontrar la fuente o error: {status}")

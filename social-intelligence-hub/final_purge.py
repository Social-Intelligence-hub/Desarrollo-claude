import os
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

# Purge google_reviews
gr_id = "14a942e8-d06d-408e-b582-77280191896d"
url_full = f"{url}/rest/v1/mentions?source_id=eq.{gr_id}"
req = urllib.request.Request(url_full, method="DELETE")
req.add_header("apikey", key)
req.add_header("Authorization", f"Bearer {key}")

try:
    with urllib.request.urlopen(req) as resp:
        print(f"Purged Google Reviews. Status: {resp.status}")
except Exception as e:
    print(f"Error purging: {e}")

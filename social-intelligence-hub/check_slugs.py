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

url_full = f"{url}/rest/v1/entities?select=slug"
req = urllib.request.Request(url_full)
req.add_header("apikey", key)
req.add_header("Authorization", f"Bearer {key}")

with urllib.request.urlopen(req) as resp:
    print(resp.read().decode())

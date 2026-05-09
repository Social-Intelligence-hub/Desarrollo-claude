import os
from dotenv import load_dotenv
from supabase import create_client
import requests

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# Get a mention to delete
res = supabase.table("mentions").select("id").limit(1).execute()
if not res.data:
    print("No mentions to test with.")
    exit(0)

mention_id = res.data[0]["id"]
print(f"Testing rejection of mention {mention_id}")

# Hit the local Next.js API
payload = {
    "id": mention_id,
    "reason": "Spam o Promoción"
}

try:
    response = requests.delete("http://localhost:3000/api/mentions/reject", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")

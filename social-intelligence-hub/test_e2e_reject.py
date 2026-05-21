import os
from dotenv import load_dotenv
from supabase import create_client
import requests
import uuid

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# Insert dummy mention
dummy_id = str(uuid.uuid4())
# Find a valid entity and source id
res_e = supabase.table("entities").select("id").limit(1).execute()
res_s = supabase.table("sources").select("id").limit(1).execute()
e_id = res_e.data[0]["id"]
s_id = res_s.data[0]["id"]

supabase.table("mentions").insert({
    "id": dummy_id,
    "text_original": "This is a dummy test mention",
    "entity_id": e_id,
    "source_id": s_id,
    "author_name": "Test",
    "source_url": "http://test",
}).execute()

print(f"Created dummy mention: {dummy_id}")

payload = {
    "id": dummy_id,
    "reason": "Spam o Promoción"
}
resp = requests.post("http://localhost:3000/api/mentions/refine", json=payload)
print(resp.status_code, resp.text)

print(supabase.table("relevance_feedback").select("*").eq("mention_id", dummy_id).execute())

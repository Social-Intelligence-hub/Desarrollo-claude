import os
from supabase import create_client

url = "https://ejivsqgumonogddiftvq.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqaXZzcWd1bW9ub2dkZGlmdHZxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTExODcyMCwiZXhwIjoyMDk2Njk0NzIwfQ.nJTXJyNK6X5jEujHiyTzFfxoTSTR4TD7Qjt75H50lXE"

try:
    print("Connecting...")
    client = create_client(url, key)
    # try writing to mentions
    test_mention = {
        "entity_id": "00000000-0000-0000-0000-000000000000",
        "source_id": "00000000-0000-0000-0000-000000000000",
        "text_original": "Test mention",
        "content_hash": "test12345"
    }
    res = client.table("mentions").insert(test_mention).execute()
    print("Insert response:", res)
except Exception as e:
    print(f"Error: {e}")

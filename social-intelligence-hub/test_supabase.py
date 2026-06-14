import os
from supabase import create_client

url = "https://ejivsqgumonogddiftvq.supabase.co"
key = "sb_publishable_iS3ecatM1xzNBaDJfNVz2A_Ri2oRYVl"

try:
    print("Connecting...")
    client = create_client(url, key)
    # try reading conglomerates
    res = client.table("conglomerates").select("*").execute()
    print("Conglomerates count:", len(res.data))
    
    # try reading mentions
    res = client.table("mentions").select("*").limit(1).execute()
    print("Mentions count:", len(res.data))
except Exception as e:
    print(f"Error: {e}")

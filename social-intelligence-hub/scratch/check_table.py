import os
from dotenv import load_dotenv
from supabase import create_client

# Try both locations for .env
load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    load_dotenv("frontend/.env.local")
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

try:
    res = supabase.table("relevance_feedback").select("id").limit(1).execute()
    print("Table relevance_feedback exists.")
except Exception as e:
    print(f"Table relevance_feedback might not exist or error: {e}")

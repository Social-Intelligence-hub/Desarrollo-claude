import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

sql = """
CREATE TABLE IF NOT EXISTS relevance_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mention_id UUID,
    entity_slug TEXT,
    text_original TEXT,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);
"""

# Since we don't have direct SQL execution via python client easily without rpc, 
# we can just use the supabase API to insert or we can create it using the UI.
# Wait, the user has Supabase CLI or SQL editor. We can run a raw query or just use postgrest.

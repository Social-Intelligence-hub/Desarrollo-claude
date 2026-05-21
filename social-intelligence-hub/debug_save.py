import os
import json
import urllib.request
import sys

# Add scraper to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper"))

from main import get_supabase_client, preload_lookup_tables, save_mentions_rest

def debug():
    env = {}
    with open('scraper/.env') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k] = v.strip('"').strip("'")
    
    os.environ.update(env)
    
    # Simular reviews
    test_reviews = [
        {
            "entity_slug": "capex-institucion",
            "source_slug": "google_reviews",
            "text_original": "Test review robustness 1",
            "author_name": "Tester 1",
            "star_rating": 5,
            "published_at": "2024-01-01T00:00:00Z",
            "content_hash": "abc1"
        }
    ]
    
    from main import get_supabase_client, preload_lookup_tables
    supabase = get_supabase_client()
    entity_map, source_map = preload_lookup_tables(supabase)
    
    print(f"Entity Map: {entity_map}")
    print(f"Source Map: {source_map}")
    
    collected, saved = save_mentions_rest(test_reviews, entity_map, source_map)
    print(f"Collected: {collected}, Saved: {saved}")

if __name__ == "__main__":
    debug()

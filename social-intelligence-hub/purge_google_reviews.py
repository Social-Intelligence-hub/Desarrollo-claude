import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv("scraper/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

def purge_google_reviews():
    print("Buscando el ID de la fuente 'google_reviews'...")
    res = requests.get(f"{url}/rest/v1/sources?slug=eq.google_reviews&select=id", headers=headers)
    if not res.json():
        print("No se encontró la fuente google_reviews.")
        return
    
    source_id = res.json()[0]["id"]
    print(f"ID encontrado: {source_id}. Procediendo a eliminar menciones...")
    
    # Eliminar menciones de esta fuente
    del_res = requests.delete(f"{url}/rest/v1/mentions?source_id=eq.{source_id}", headers=headers)
    
    if del_res.status_code in [200, 204]:
        print("Menciones de Google Reviews eliminadas satisfactoriamente.")
    else:
        print(f"Error al eliminar: {del_res.status_code} - {del_res.text}")

if __name__ == "__main__":
    purge_google_reviews()

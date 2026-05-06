# -*- coding: utf-8 -*-
import os
import requests
import logging
from dotenv import load_dotenv
from collectors.relevance_filter import es_relevante_dominicana

load_dotenv("scraper/.env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cleanup_light")

def run_deep_cleanup():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        logger.error("Faltan credenciales de Supabase")
        return

    # Preparar headers para PostgREST
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    try:
        # 1. Obtener mapeo de entidades
        entity_url = f"{url}/rest/v1/entities?select=id,slug"
        entity_res = requests.get(entity_url, headers=headers)
        entity_res.raise_for_status()
        entity_map = {e["id"]: e["slug"] for e in entity_res.json()}

        # 2. Obtener menciones
        mentions_url = f"{url}/rest/v1/mentions?select=id,text_original,entity_id"
        mentions_res = requests.get(mentions_url, headers=headers)
        mentions_res.raise_for_status()
        mentions = mentions_res.json()

        logger.info(f"Analizando {len(mentions)} menciones...")

        to_delete = []
        for m in mentions:
            text = m.get("text_original", "")
            entity_slug = entity_map.get(m.get("entity_id"))
            
            if not es_relevante_dominicana(text, entity_slug):
                to_delete.append(m["id"])

        logger.info(f"Eliminando {len(to_delete)} menciones irrelevantes...")

        # 3. Eliminar
        if to_delete:
            for i in range(0, len(to_delete), 50):
                chunk = to_delete[i:i+50]
                ids_param = ",".join([f'"{id}"' for id in chunk])
                delete_url = f"{url}/rest/v1/mentions?id=in.({ids_param})"
                requests.delete(delete_url, headers=headers).raise_for_status()
            logger.info("Limpieza completada satisfactoriamente.")
        else:
            logger.info("No hay nada que eliminar.")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    run_deep_cleanup()

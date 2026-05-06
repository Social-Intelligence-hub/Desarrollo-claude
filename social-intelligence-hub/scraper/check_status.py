# -*- coding: utf-8 -*-
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv("scraper/.env")

def check_runs():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    
    print(f"--- Verificando Ejecuciones (Hora actual UTC: {datetime.now(timezone.utc).strftime('%H:%M:%S')}) ---\n")
    
    try:
        # 1. Consultar últimas ejecuciones
        r = requests.get(f"{url}/rest/v1/scraper_runs?select=*&order=finished_at.desc&limit=3", headers=headers)
        runs = r.json()
        
        if not runs:
            print("No se encontraron registros de ejecuciones en la tabla 'scraper_runs'.")
        else:
            for run in runs:
                print(f"Run ID: {run['id']}")
                print(f"Fuente: {run['source_slug']} | Entidad: {run['entity_slug']}")
                print(f"Status: {run['status']} | Nuevas: {run['mentions_new']}")
                print(f"Finalizado: {run['finished_at']}")
                print("-" * 30)

        # 2. Consultar última mención
        r_mentions = requests.get(f"{url}/rest/v1/mentions?select=collected_at&order=collected_at.desc&limit=1", headers=headers)
        mentions = r_mentions.json()
        if mentions:
            print(f"\nUltima mencion recolectada el: {mentions[0]['collected_at']}")
        else:
            print("\nNo hay menciones en la base de datos.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_runs()

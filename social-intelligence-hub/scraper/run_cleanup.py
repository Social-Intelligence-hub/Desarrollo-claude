# -*- coding: utf-8 -*-
"""
Script de limpieza de datos en Supabase.
Resuelve:
1. Menciones irrelevantes (que no mencionan entidades core).
2. Texto sucio (con URLs de imágenes).
3. Duplicados (basado en los primeros 150 caracteres).
"""

import os
import re
import logging
from dotenv import load_dotenv
from supabase import create_client
from collectors.relevance_filter import es_relevante_dominicana

# Cargar variables desde .env
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("cleanup")

def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos en .env")
    return create_client(url, key)

def run_cleanup():
    try:
        supabase = get_supabase_client()
        logger.info("Conectado a Supabase para limpieza.")

        # --- 1. Limpiar Texto (URLs de imágenes y espacios) ---
        logger.info("PASO 1: Limpiando URLs de imágenes y basura HTML en el texto...")
        res = supabase.table("mentions").select("id, text_original").execute()
        mentions = res.data or []
        updated_count = 0

        for m in mentions:
            original = m["text_original"]
            # Remover URLs de imágenes
            clean = re.sub(r'https?://[^\s]+\.(jpg|jpeg|png|gif|webp)[^\s]*', '', original, flags=re.IGNORECASE)
            # Remover espacios extra
            clean = re.sub(r'\s+', ' ', clean).strip()
            
            if clean != original:
                supabase.table("mentions").update({"text_original": clean}).eq("id", m["id"]).execute()
                updated_count += 1
        
        logger.info(f"Texto actualizado en {updated_count} menciones.")

        # --- 2. Eliminar Irrelevantes ---
        logger.info("PASO 2: Identificando menciones irrelevantes...")
        # Volvemos a leer para tener el texto limpio
        res = supabase.table("mentions").select("id, text_original, star_rating").execute()
        mentions = res.data or []
        
        to_delete = []
        
        for m in mentions:
            text = m["text_original"]
            # Si es una reseña de Google (tiene estrellas), la dejamos
            if m.get("star_rating") is not None:
                continue

            if not es_relevante_dominicana(text):
                to_delete.append(m["id"])
        
        if to_delete:
            logger.info(f"Borrando {len(to_delete)} menciones irrelevantes...")
            for i in range(0, len(to_delete), 50):
                chunk = to_delete[i:i+50]
                supabase.table("mentions").delete().in_("id", chunk).execute()
        else:
            logger.info("No se encontraron menciones irrelevantes.")

        # --- 3. Eliminar Duplicados ---
        logger.info("PASO 3: Eliminando duplicados (mismo inicio de texto y entidad)...")
        # Obtenemos todo ordenado por fecha de recolección descendente
        res = supabase.table("mentions").select("id, text_original, entity_id").order("collected_at", desc=True).execute()
        mentions = res.data or []
        
        seen = set()
        to_delete_dup = []
        
        for m in mentions:
            # Clave: Primeros 150 caracteres + ID de entidad
            text_key = m["text_original"][:150].lower().strip()
            content_key = (text_key, m["entity_id"])
            
            if content_key in seen:
                to_delete_dup.append(m["id"])
            else:
                seen.add(content_key)
        
        if to_delete_dup:
            logger.info(f"Borrando {len(to_delete_dup)} menciones duplicadas...")
            for i in range(0, len(to_delete_dup), 50):
                chunk = to_delete_dup[i:i+50]
                supabase.table("mentions").delete().in_("id", chunk).execute()

        # --- 4. Marcar Datos Demo ---
        logger.info("PASO 4: Marcando datos demo basados en patrones de URL...")
        res = supabase.table("mentions").select("id, source_url").execute()
        mentions = res.data or []
        marked_count = 0
        
        demo_patterns = [
            "demo", 
            "?cid=111", "?cid=222", "?cid=333", 
            "?cid=444", "?cid=555", "?cid=666"
        ]
        
        for m in mentions:
            url = m.get("source_url")
            is_demo = False
            
            if not url:
                is_demo = True
            else:
                if any(p in url.lower() for p in demo_patterns):
                    is_demo = True
            
            if is_demo:
                # Nota: Si la columna is_demo no existe, esto fallará silenciosamente o dará error
                try:
                    supabase.table("mentions").update({"is_demo": True}).eq("id", m["id"]).execute()
                    marked_count += 1
                except:
                    pass
        
        logger.info(f"Marcadas {marked_count} menciones como DEMO.")

        logger.info("PROCESO DE LIMPIEZA FINALIZADO.")

    except Exception as e:
        logger.error(f"Error durante la limpieza: {e}")

if __name__ == "__main__":
    run_cleanup()

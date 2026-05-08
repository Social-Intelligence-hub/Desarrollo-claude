import logging
import numpy as np

logger = logging.getLogger("relevance_filter")

class RelevanceFilter:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.model = None
        self.blacklist_embeddings = []
        
    def _init_model(self):
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Usar un modelo multilenguaje ligero optimizado
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            except ImportError:
                logger.error("sentence-transformers no está instalado. Filtro semántico desactivado.")
            except Exception as e:
                logger.error(f"Error inicializando SentenceTransformer: {e}")

    def load_feedback(self):
        """Carga los embeddings de la base de datos, procesando nuevos feedbacks si es necesario."""
        if not self.supabase:
            return
            
        try:
            # 1. Buscar menciones descartadas que no tengan embedding aún
            # (Asumimos que el script principal llamará a esto cada noche)
            self._process_new_feedback()
            
            # 2. Cargar todos los embeddings de la blacklist en memoria para comparación rápida
            res = self.supabase.table("embeddings_blacklist").select("embedding").execute()
            if res.data:
                self.blacklist_embeddings = [np.array(row["embedding"]) for row in res.data]
                logger.info(f"Filtro Semántico cargado con {len(self.blacklist_embeddings)} vectores de ruido.")
            else:
                logger.info("Filtro Semántico: No hay datos en la lista negra todavía.")
        except Exception as e:
            logger.error(f"Error cargando feedback para el filtro semántico: {e}")

    def _process_new_feedback(self):
        """Procesa el feedback reciente y genera sus embeddings."""
        try:
            # Seleccionar feedback reciente (idealmente solo los no procesados, aquí tomamos todos para simplificar)
            res = self.supabase.table("relevance_feedback").select("id, text_original").execute()
            feedbacks = res.data
            
            if not feedbacks:
                return
                
            # Verificar qué textos ya están en la blacklist
            res_bl = self.supabase.table("embeddings_blacklist").select("content_hash").execute()
            existing_hashes = {row["content_hash"] for row in res_bl.data} if res_bl.data else set()
            
            import hashlib
            new_texts = []
            
            for fb in feedbacks:
                text = fb.get("text_original", "")
                if not text:
                    continue
                content_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
                
                if content_hash not in existing_hashes:
                    new_texts.append({"text": text, "hash": content_hash})
                    
            if new_texts:
                self._init_model()
                if not self.model:
                    return
                
                logger.info(f"Generando embeddings para {len(new_texts)} nuevos feedbacks de usuario...")
                texts_only = [item["text"] for item in new_texts]
                embeddings = self.model.encode(texts_only).tolist()
                
                for item, emb in zip(new_texts, embeddings):
                    self.supabase.table("embeddings_blacklist").insert({
                        "content_hash": item["hash"],
                        "content": item["text"],
                        "embedding": emb
                    }).execute()
                    
                logger.info(f"Embeddings de feedback guardados exitosamente.")
                
        except Exception as e:
            logger.error(f"Error procesando nuevo feedback para embeddings: {e}")

    def is_relevant(self, text: str, threshold: float = 0.75) -> bool:
        """Determina si un texto es relevante comparando contra la blacklist semántica."""
        if not text or not self.blacklist_embeddings:
            return True
            
        self._init_model()
        if not self.model:
            return True # Fallback: permitir todo si el modelo no carga
            
        new_embedding = self.model.encode([text])[0]
        new_norm = np.linalg.norm(new_embedding)
        
        for bl_embedding in self.blacklist_embeddings:
            bl_norm = np.linalg.norm(bl_embedding)
            if new_norm == 0 or bl_norm == 0:
                continue
                
            similarity = np.dot(new_embedding, bl_embedding) / (new_norm * bl_norm)
            
            if similarity > threshold:
                logger.info(f"Mención bloqueada por similitud semántica ({similarity:.2f} > {threshold})")
                return False
                
        return True

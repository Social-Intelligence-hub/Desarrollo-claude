# -*- coding: utf-8 -*-
"""
Juez de Relevancia con Groq — Social Intelligence Hub v3.

Determina si un texto recolectado de internet realmente habla de
una empresa específica de la Zona Franca de Santiago, o si es ruido
(clasificados, bienes raíces, homónimos geográficos, deportes, etc.).

Posición en el pipeline:
    Recolectar → Heurístico (sin API) → Groq Relevancia → Groq Sentimiento

La cascada heurística ya elimina lo obviamente irrelevante. Este módulo
evalúa los candidatos que pasaron el heurístico pero podrían ser falsos
positivos por coincidencia de keyword.

API pública:
    check(text, entity_name, entity_config, conglomerate) -> dict
    check_batch(texts, entity_name, entity_config, conglomerate) -> list[dict]

Cada respuesta: {relevant: bool, confidence: float, reason: str}
"""

import json
import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
BATCH_SIZE = 10

_SYSTEM_PROMPT_TEMPLATE = """Eres un experto en inteligencia corporativa para la Corporación Zona Franca de Santiago (CZFS), República Dominicana.

EMPRESA QUE ESTÁS MONITOREANDO: {entity_name}
{context_block}

TU ÚNICA TAREA: determinar si cada texto encontrado en internet es RELEVANTE para el monitoreo de reputación de esa empresa específica.

━━━ RELEVANTE (relevant: true) ━━━
✓ Habla directamente de la empresa: operaciones, empleados, productos, servicios
✓ Noticias, artículos o reportajes sobre la empresa
✓ Opiniones de clientes, empleados o proveedores sobre la empresa
✓ Eventos corporativos: alianzas, inauguraciones, certificaciones, exportaciones
✓ Problemas o controversias: huelgas, accidentes, quejas laborales, multas
✓ Menciones en rankings, premios o reportes del sector

━━━ NO RELEVANTE (relevant: false) ━━━
✗ Avisos de bienes raíces: "se alquila", "en venta", "m2", solares, apartamentos
✗ El nombre aparece solo como referencia geográfica ("cerca de la zona franca")
✗ Clasificados de productos, servicios o empleos sin relación con la empresa
✗ Noticias de otra empresa u organización con nombre similar
✗ Contenido de otro país (aunque mencione el nombre)
✗ Resultados deportivos, entretenimiento u otros contextos irrelevantes
✗ Spam, listas de precios o contenido autogenerado sin valor informativo

Responde SOLO con JSON válido:
- Para un texto: {{"relevant": true/false, "confidence": 0.0-1.0, "reason": "1 oración"}}
- Para múltiples textos numerados: {{"results": [{{"i": 0, "relevant": true/false, "confidence": 0.0-1.0, "reason": "breve"}}]}}
"""


class RelevanceChecker:
    """Juez de relevancia corporativa usando Groq Llama 4 Scout."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if GROQ_AVAILABLE and self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info("RelevanceChecker Groq inicializado.")
            except Exception as e:
                logger.error("No se pudo inicializar RelevanceChecker: %s", e)
        else:
            logger.warning("GROQ_API_KEY ausente — relevancia solo heurística.")

    # ─────────────────────────────────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────────────────────────────────
    def check(self, text: str, entity_name: str,
              entity_config: dict | None = None,
              conglomerate: dict | None = None) -> dict:
        """Evalúa un solo texto. Devuelve siempre un dict con relevant, confidence, reason."""
        if not text or not text.strip():
            return self._irrelevant("texto vacío")
        if not self.client:
            return self._pass_through("Groq no disponible — asumiendo relevante")

        system = _SYSTEM_PROMPT_TEMPLATE.format(
            entity_name=entity_name,
            context_block=self._context_block(entity_config, conglomerate),
        )
        try:
            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"TEXTO: {text}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=150,
            )
            data = json.loads(resp.choices[0].message.content)
            return self._normalize(data)
        except Exception as e:
            logger.warning("Groq relevance (single) falló: %s", e)
            return self._pass_through(f"error Groq: {e}")

    def check_batch(self, texts: list[str], entity_name: str,
                    entity_config: dict | None = None,
                    conglomerate: dict | None = None) -> list[dict]:
        """Evalúa una lista de textos. Devuelve lista en el mismo orden."""
        if not texts:
            return []
        if not self.client:
            return [self._pass_through("Groq no disponible") for _ in texts]

        results: list[dict | None] = [None] * len(texts)
        system = _SYSTEM_PROMPT_TEMPLATE.format(
            entity_name=entity_name,
            context_block=self._context_block(entity_config, conglomerate),
        )

        for start in range(0, len(texts), BATCH_SIZE):
            chunk = texts[start:start + BATCH_SIZE]
            numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(chunk))
            user_msg = (
                "Evalúa si cada texto es relevante para la empresa. "
                "Responde SOLO con JSON: "
                '{"results": [{"i": 0, "relevant": true/false, "confidence": 0.0, "reason": "breve"}]}\n\n'
                f"TEXTOS:\n{numbered}"
            )
            chunk_results = [None] * len(chunk)
            try:
                resp = self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=800,
                )
                raw = json.loads(resp.choices[0].message.content)
                arr = raw if isinstance(raw, list) else raw.get("results", raw.get("items", []))
                if isinstance(arr, list):
                    for obj in arr:
                        idx = obj.get("i")
                        if isinstance(idx, int) and 0 <= idx < len(chunk):
                            chunk_results[idx] = self._normalize(obj)
            except Exception as e:
                logger.warning("Groq relevance (batch start=%d) falló: %s", start, e)

            for j, r in enumerate(chunk_results):
                results[start + j] = r if r is not None else self._pass_through("sin respuesta Groq")

        return results  # type: ignore

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _context_block(self, entity_config: dict | None, conglomerate: dict | None) -> str:
        parts = []
        if conglomerate:
            parts.append(
                f"Conglomerado: {conglomerate.get('name', 'Zona Franca de Santiago')} — "
                f"{conglomerate.get('context_description', 'parque industrial, Santiago RD')}"
            )
        if entity_config:
            kw = entity_config.get("required_terms") or []
            if kw:
                parts.append(f"Keywords de la empresa: {', '.join(kw[:8])}")
            dis = entity_config.get("disambiguation") or {}
            if isinstance(dis, str):
                try:
                    dis = json.loads(dis)
                except Exception:
                    dis = {}
            neg = dis.get("negative_signals", [])
            pos = dis.get("positive_signals", [])
            if neg:
                parts.append(f"Señales de contexto EQUIVOCADO (descartar): {', '.join(neg)}")
            if pos:
                parts.append(f"Señales que CONFIRMAN contexto correcto: {', '.join(pos)}")
        return "\n".join(parts) if parts else "Parque industrial, Santiago, República Dominicana."

    def _normalize(self, data: dict) -> dict:
        relevant = bool(data.get("relevant", True))
        confidence = float(data.get("confidence", 0.7 if relevant else 0.8))
        reason = str(data.get("reason", ""))
        return {"relevant": relevant, "confidence": confidence, "reason": reason}

    def _irrelevant(self, reason: str) -> dict:
        return {"relevant": False, "confidence": 1.0, "reason": reason}

    def _pass_through(self, reason: str) -> dict:
        return {"relevant": True, "confidence": 0.5, "reason": reason}

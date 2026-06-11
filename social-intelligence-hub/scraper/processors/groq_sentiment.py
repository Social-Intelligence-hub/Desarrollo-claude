# -*- coding: utf-8 -*-
"""
Motor de Análisis de Sentimiento — Groq / Llama 4 Scout (reemplaza Gemini).

Cascada de 3 niveles:
  1. Léxico Dominicano  → override prioritario (sin API)
  2. Groq Llama 4 Scout → analizador principal con contexto del conglomerado
  3. Heurístico         → red de seguridad (nunca falla)

Mantiene la misma firma de salida que gemini_sentiment.py:
  analyze(text, language, entity_config, conglomerate) -> dict
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

from processors.dominican_lexicon import detect_dominican_sentiment

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("groq SDK no instalado. pip install groq")

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
BATCH_SIZE = 10

# ─────────────────────────────────────────────────────────────────────────────
# Bloque de léxico dominicano — inyectado en el prompt de Groq
# ─────────────────────────────────────────────────────────────────────────────
_DOMINICAN_LEXICON_BLOCK = """
## LÉXICO DOMINICANO — reglas de interpretación

POSITIVOS (sin negación): jevi/jevy/nítido, chévere/bacano/vacano, ta' durísimo, rulay,
me la robó/me la roban (="me encanta"), ta' movidú, ta' guay, ta' topú, no tiene pierde,
candela (calidad), saca chispa, matatán/montro, de ley, tato, yala, e' pa' lante.

NEGATIVOS: brigandina (mal hecho), al garete (arruinado), juidero (caos),
boche (crítica severa), la macó (error), mojonear (engañar), ni en pato (rechazo total),
ta' fuera (descartado), me tumbaron/me dejaron a palo/me comieron el coco (estafa),
corcho (oportunista), picao (ofendido), emberracao (furioso), manganzón (perezoso),
pachá (lento), desmadre (caos), prendío (fuera de control), quedao (obsoleto).

AMBIGUOS — requieren contexto:
- tiguere: positivo=inteligente/sagaz; negativo=tramposo.
- vaina (comodín): el modificador decide ("jevi vaina"=pos, "mala vaina"=neg).
- dique/dizque: casi siempre ironía o escepticismo.

Reglas: (1) Negación invierte: "no está jevi"=negativo. (2) pos+neg="mixed".
(3) El sentimiento es hacia la EMPRESA analizada, no el texto en sí.
""".strip()


class SentimentAnalyzer:
    """Analizador de sentimiento en cascada con Groq Llama 4 Scout."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if GROQ_AVAILABLE and self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info("Cliente Groq inicializado (modelo %s).", GROQ_MODEL)
            except Exception as e:
                logger.error("No se pudo inicializar Groq: %s", e)
        else:
            logger.warning("GROQ_API_KEY ausente o SDK no disponible: léxico + heurístico.")

    # ─────────────────────────────────────────────────────────────────────────
    # API pública — misma firma que gemini_sentiment.py
    # ─────────────────────────────────────────────────────────────────────────
    def analyze(self, text: str, language: str = "auto",
                entity_config: dict | None = None,
                conglomerate: dict | None = None) -> dict:
        if not text or not text.strip():
            return self._empty_result()

        # 1) Léxico dominicano (override prioritario)
        dom = detect_dominican_sentiment(text)
        if dom["override"]:
            s = dom["sentiment"]
            return {
                "label": s,
                "scores": self._scores_for_label(s),
                "confidence": 0.90,
                "dominican_override": True,
                "dominican_term": dom["term_found"],
                "method": "dominican_lexicon",
                "reasoning": f"Léxico dominicano: '{dom['term_found']}' ({dom['term_meaning']}).",
            }

        # 2) Groq con contexto del conglomerado
        if self.client:
            result = self._analyze_groq(text, entity_config, conglomerate,
                                         dom.get("ambiguous_hints"))
            if result:
                return result

        # 3) Heurístico
        return self._analyze_heuristic(text)

    def analyze_batch(self, texts: list[str], language: str = "auto",
                      entity_config: dict | None = None,
                      conglomerate: dict | None = None) -> list[dict]:
        """Pre-resuelve léxico localmente; el resto va a Groq en lotes."""
        results: list[dict | None] = [None] * len(texts)
        pending_idx, pending_txt = [], []

        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = self._empty_result()
                continue
            dom = detect_dominican_sentiment(text)
            if dom["override"]:
                s = dom["sentiment"]
                results[i] = {
                    "label": s, "scores": self._scores_for_label(s), "confidence": 0.90,
                    "dominican_override": True, "dominican_term": dom["term_found"],
                    "method": "dominican_lexicon",
                    "reasoning": f"Léxico dominicano: '{dom['term_found']}'.",
                }
            else:
                pending_idx.append(i)
                pending_txt.append(text)

        if self.client and pending_txt:
            for start in range(0, len(pending_txt), BATCH_SIZE):
                chunk_idx = pending_idx[start:start + BATCH_SIZE]
                chunk_txt = pending_txt[start:start + BATCH_SIZE]
                batch = self._analyze_groq_batch(chunk_txt, entity_config, conglomerate)
                for j, idx in enumerate(chunk_idx):
                    results[idx] = batch[j] if batch and batch[j] else \
                        self._analyze_heuristic(chunk_txt[j])
        else:
            for i, idx in enumerate(pending_idx):
                results[idx] = self._analyze_heuristic(pending_txt[i])

        return results  # type: ignore

    # ─────────────────────────────────────────────────────────────────────────
    # Groq internals
    # ─────────────────────────────────────────────────────────────────────────
    def _context_block(self, entity_config, conglomerate) -> str:
        parts = []
        if conglomerate:
            parts.append(
                f"Conglomerado: {conglomerate.get('name', '')} — "
                f"{conglomerate.get('context_description', '')}"
            )
        if entity_config and entity_config.get("disambiguation"):
            dis = entity_config["disambiguation"]
            if isinstance(dis, str):
                try:
                    dis = json.loads(dis)
                except Exception:
                    dis = {}
            pos = ", ".join(dis.get("positive_signals", []))
            neg = ", ".join(dis.get("negative_signals", []))
            if pos:
                parts.append(f"Señales que CONFIRMAN contexto correcto: {pos}.")
            if neg:
                parts.append(f"Señales de contexto EQUIVOCADO (ignorar): {neg}.")
        return "\n".join(parts) if parts else "Contexto: empresa de zona franca, Santiago RD."

    def _build_system_prompt(self, entity_config, conglomerate,
                              ambiguous_hints: list | None = None) -> str:
        hints_block = ""
        if ambiguous_hints:
            lines = [
                f'  - "{h["term"]}": {h["meaning"]}. '
                f'Positivo si: {h["positive_ctx"]}. Negativo si: {h["negative_ctx"]}.'
                for h in ambiguous_hints
            ]
            hints_block = "\n## TÉRMINOS AMBIGUOS DETECTADOS\n" + "\n".join(lines)

        return (
            "Eres un analista experto en reputación corporativa para empresas de la "
            "Corporación Zona Franca de Santiago, República Dominicana. "
            "Clasifica el SENTIMIENTO del texto hacia la empresa analizada (no hacia el narrador).\n\n"
            f"## CONTEXTO\n{self._context_block(entity_config, conglomerate)}\n\n"
            f"{_DOMINICAN_LEXICON_BLOCK}"
            f"{hints_block}\n\n"
            'Responde SOLO con JSON: '
            '{"label":"positive|negative|neutral|mixed",'
            '"scores":{"positive":0.0,"negative":0.0,"neutral":0.0},'
            '"confidence":0.0,'
            '"reasoning":"1-2 oraciones mencionando contexto dominicano o del conglomerado"}'
        )

    def _analyze_groq(self, text, entity_config, conglomerate,
                      ambiguous_hints=None) -> dict | None:
        system = self._build_system_prompt(entity_config, conglomerate, ambiguous_hints)
        try:
            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"TEXTO: {text}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            data = json.loads(resp.choices[0].message.content)
            return self._normalize(data)
        except Exception as e:
            logger.warning("Groq falló (single): %s", e)
            return None

    def _analyze_groq_batch(self, texts: list[str], entity_config,
                             conglomerate) -> list[dict] | None:
        system = self._build_system_prompt(entity_config, conglomerate)
        numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(texts))
        user_msg = (
            "Analiza CADA texto numerado. "
            'Devuelve SOLO un arreglo JSON en el MISMO orden:\n'
            '[{"i":0,"label":"positive|negative|neutral|mixed",'
            '"scores":{"positive":0.0,"negative":0.0,"neutral":0.0},'
            '"confidence":0.0,"reasoning":"breve"}]\n\n'
            f"TEXTOS:\n{numbered}"
        )
        try:
            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1500,
            )
            raw = json.loads(resp.choices[0].message.content)
            # Groq puede devolver {"results": [...]} o directamente [...]
            arr = raw if isinstance(raw, list) else raw.get("results", raw.get("items", []))
            if not isinstance(arr, list):
                return None
            out = [None] * len(texts)
            for obj in arr:
                i = obj.get("i")
                if isinstance(i, int) and 0 <= i < len(texts):
                    out[i] = self._normalize(obj)
            return out  # type: ignore
        except Exception as e:
            logger.warning("Groq falló (batch): %s", e)
            return None

    def _normalize(self, data: dict) -> dict:
        label = data.get("label", "neutral")
        if label not in ("positive", "negative", "neutral", "mixed"):
            label = "neutral"
        scores = data.get("scores") or self._scores_for_label(label)
        scores = {k: float(scores.get(k, 0.0)) for k in ("positive", "negative", "neutral")}
        return {
            "label": label,
            "scores": scores,
            "confidence": float(data.get("confidence", max(scores.values()))),
            "dominican_override": False,
            "dominican_term": None,
            "method": "groq",
            "reasoning": data.get("reasoning", ""),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Heurístico
    # ─────────────────────────────────────────────────────────────────────────
    def _analyze_heuristic(self, text: str) -> dict:
        t = text.lower()
        institutional = [
            "alianza", "convenio", "acuerdo", "graduación", "graduacion", "éxito", "exito",
            "reconocimiento", "premia", "mejora", "innovación", "innovacion", "lanzamiento",
            "certificación", "certificacion", "aprobado", "colaboración", "colaboracion",
            "inauguración", "inauguracion", "crecimiento", "desarrollo", "fortalece", "exporta",
        ]
        positive = ["excelente", "bueno", "genial", "increíble", "recomiendo", "profesional",
                    "satisfecho", "feliz", "gracias", "perfecto", "bien", "rápido", "eficiente",
                    "calidad", "empleo", "empleos", "inversión"]
        negative = ["malo", "pésimo", "terrible", "horrible", "decepcionante", "problema",
                    "error", "falla", "tarde", "lento", "caro", "espera", "mal", "peor",
                    "nunca", "jamás", "crisis", "queja", "despido", "protesta"]

        inst = sum(2 for w in institutional if w in t)
        pos = sum(1 for w in positive if w in t) + inst
        neg = sum(1.5 for w in negative if w in t)

        if pos > neg:
            label, conf = "positive", (0.85 if inst else 0.70)
            scores = {"positive": 0.80 if inst else 0.65, "negative": 0.05, "neutral": 0.15}
        elif neg > pos:
            label, conf = "negative", 0.78
            scores = {"positive": 0.05, "negative": 0.80, "neutral": 0.15}
        else:
            label, conf = "neutral", 0.55
            scores = {"positive": 0.20, "negative": 0.20, "neutral": 0.60}

        return {
            "label": label, "scores": scores, "confidence": conf,
            "dominican_override": False, "dominican_term": None,
            "method": "heuristic",
            "reasoning": "Heurístico de respaldo (Groq no disponible).",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _scores_for_label(self, label: str) -> dict:
        if label == "positive":
            return {"positive": 0.90, "negative": 0.05, "neutral": 0.05}
        if label == "negative":
            return {"positive": 0.05, "negative": 0.90, "neutral": 0.05}
        if label == "mixed":
            return {"positive": 0.45, "negative": 0.45, "neutral": 0.10}
        return {"positive": 0.20, "negative": 0.20, "neutral": 0.60}

    def _empty_result(self) -> dict:
        return {
            "label": "neutral", "scores": {"positive": 0.33, "negative": 0.33, "neutral": 0.34},
            "confidence": 0.0, "dominican_override": False, "dominican_term": None,
            "method": "empty", "reasoning": "",
        }

# -*- coding: utf-8 -*-
"""
Motor de Análisis de Sentimiento — Gemini 2.0 Flash (reemplaza Azure).

Cascada de 3 niveles (PROYECTO.md §8):
  1. Léxico Dominicano  → override prioritario (sin consultar IA)
  2. Gemini 2.0 Flash   → analizador principal, con CONTEXTO del conglomerado
  3. Heurístico         → red de seguridad (nunca falla)

Mantiene la MISMA firma de salida que el analizador anterior para no romper
colectores: analyze(text, language) -> dict con
  {label, scores, confidence, dominican_override, dominican_term, method}
Se añade `reasoning` (criterio de éxito #3) y parámetros OPCIONALES de contexto
(entity_config / conglomerate) que, si se pasan, contextualizan el prompt de Gemini.
Los parámetros opcionales preservan la compatibilidad con las llamadas existentes.
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
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-genai no instalado. La cascada usará léxico + heurístico.")

GEMINI_MODEL = "gemini-3.5-flash"
BATCH_SIZE = 10  # menciones por request de Gemini (control de cuota: 1500 req/día free)

# ────────────────────────────────────────────────────────────────────────────
# PROMPT BASE — incrustado aquí para que sea fácil de iterar sin tocar lógica
# ────────────────────────────────────────────────────────────────────────────
_DOMINICAN_LEXICON_BLOCK = """
## LÉXICO DOMINICANO — reglas de interpretación

### Términos POSITIVOS (sin negación previa)
jevi/jevy/nítido, chévere/bacano/vacano, ta' durísimo, rulay, hevi-nais,
me la robó/me la roban (="me encanta"), ta' movidú, ta' guay, ta' topú,
no tiene pierde, candela (calidad), saca chispa, matatán/montro (respeto genuino),
de ley, tato, yala, e' pa' lante, bien montao, enchulao, de primera.

### Términos NEGATIVOS (inequívocos)
brigandina (mal hecho), al garete (arruinado), juidero (caos), pariguayo (neg. en corp.),
boche (crítica severa), la macó (error grave), mojonear/mojoneo (engañar),
ni en pato (rechazo total), ta' fuera (descartado), me tumbaron/me dejaron a palo/
me comieron el coco/fue un rata (engaño o estafa), corcho (oportunista no confiable),
boca-agua (no cumple), picao (ofendido, molesto), emberracao (furioso), desmadre/juidero
(caos), prendío (fuera de control), manganzón (perezoso), pachá (lento e ineficiente),
ta pisao (problemas legales), arrebatao/juquiao (descontrolado), en olla (en problemas),
armao de excusas (lleno de pretextos), quedao (obsoleto), una barbaridad (exagerado/abusivo).

### Términos AMBIGUOS — requieren contexto
- **tiguere**: positivo si = inteligente/sagaz; negativo si = tramposo/aprovechador.
- **vaina**: neutro (comodín); el modificador decide: "jevi vaina"=pos, "brigandina vaina"=neg.
- **dique/dizque**: casi siempre ironía o escepticismo → negativo o neutral leve.
- **bregar**: neutral (trabajar/lidiar con algo).
- **janguear**: ocio inocente → neutral; callejear con connotación neg. → negativo.

### Reglas de composición
1. **Negación** → invierte polaridad: "no está jevi" = NEGATIVO; "ni en pato lo recomiendo" = MUY NEGATIVO.
2. **Combinación pos+neg** → "mixed": "me la robó pero la macó" = mixed.
3. **Ironía con dique**: "dique llegaron temprano" = escepticismo → neutral/negativo.
4. **Intensificadores**: "to' el mundo se queja" amplifica el negativo; "en bola recomienda" amplifica el positivo.
5. **El sentimiento es HACIA LA EMPRESA analizada**, no hacia el narrador ni el texto en sí.
""".strip()


class SentimentAnalyzer:
    """Analizador de sentimiento en cascada con Gemini 2.0 Flash."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Cliente Gemini inicializado (modelo %s).", GEMINI_MODEL)
            except Exception as e:
                logger.error("No se pudo inicializar Gemini: %s", e)
        else:
            logger.warning(
                "GEMINI_API_KEY ausente o SDK no disponible: se usa léxico + heurístico."
            )

    # ------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------
    def analyze(self, text: str, language: str = "auto",
                entity_config: dict | None = None,
                conglomerate: dict | None = None) -> dict:
        """Analiza un texto con la cascada de 3 niveles."""
        if not text or not text.strip():
            return self._empty_result()

        # 1) Léxico dominicano (override prioritario)
        dom = detect_dominican_sentiment(text)
        if dom["override"]:
            sentiment = dom["sentiment"]
            return {
                "label": sentiment,
                "scores": self._scores_for_label(sentiment),
                "confidence": 0.90,
                "dominican_override": True,
                "dominican_term": dom["term_found"],
                "method": "dominican_lexicon",
                "reasoning": f"Detectado vía léxico dominicano: '{dom['term_found']}' ({dom['term_meaning']}).",
            }

        # 2) Gemini con contexto del conglomerado + hints de términos ambiguos
        if self.client:
            result = self._analyze_gemini(
                text, entity_config, conglomerate,
                ambiguous_hints=dom.get("ambiguous_hints"),
            )
            if result:
                return result

        # 3) Heurístico (red de seguridad)
        return self._analyze_heuristic(text)

    def analyze_batch(self, texts: list[str], language: str = "auto",
                      entity_config: dict | None = None,
                      conglomerate: dict | None = None) -> list[dict]:
        """
        Analiza múltiples textos minimizando requests a Gemini.
        Pre-resuelve el léxico dominicano localmente y envía el resto en lotes.
        """
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

        # Lotes a Gemini
        if self.client and pending_txt:
            for start in range(0, len(pending_txt), BATCH_SIZE):
                chunk_idx = pending_idx[start:start + BATCH_SIZE]
                chunk_txt = pending_txt[start:start + BATCH_SIZE]
                batch = self._analyze_gemini_batch(chunk_txt, entity_config, conglomerate)
                for j, idx in enumerate(chunk_idx):
                    results[idx] = batch[j] if batch and batch[j] else self._analyze_heuristic(chunk_txt[j])
        else:
            for idx in pending_idx:
                results[idx] = self._analyze_heuristic(texts[idx])

        return results  # type: ignore

    # ------------------------------------------------------------
    # Gemini
    # ------------------------------------------------------------
    def _context_block(self, entity_config, conglomerate) -> str:
        parts = []
        if conglomerate:
            parts.append(
                f"Conglomerado: {conglomerate.get('name','')} — "
                f"{conglomerate.get('context_description','')}"
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
                parts.append(f"Señales que CONFIRMAN el contexto correcto: {pos}.")
            if neg:
                parts.append(f"Señales de contexto EQUIVOCADO (homónimos a ignorar): {neg}.")
        return "\n".join(parts) if parts else "Contexto: empresa de zona franca en Santiago, RD."

    def _build_prompt_single(self, text: str, entity_config, conglomerate,
                              ambiguous_hints: list | None = None) -> str:
        hints_block = ""
        if ambiguous_hints:
            lines = [
                f'  - "{h["term"]}": {h["meaning"]}. '
                f'Positivo si: {h["positive_ctx"]}. '
                f'Negativo si: {h["negative_ctx"]}.'
                for h in ambiguous_hints
            ]
            hints_block = (
                "\n## TÉRMINOS AMBIGUOS DETECTADOS EN ESTE TEXTO (analiza con cuidado)\n"
                + "\n".join(lines)
            )

        return f"""Eres un analista experto en reputación corporativa para empresas de la Corporación \
Zona Franca de Santiago, República Dominicana. Tu tarea es clasificar el SENTIMIENTO del texto \
hacia la empresa analizada (no hacia el narrador).

## CONTEXTO DE LA ENTIDAD
{self._context_block(entity_config, conglomerate)}

{_DOMINICAN_LEXICON_BLOCK}
{hints_block}

## TEXTO A ANALIZAR
{text}

Responde SOLO con JSON válido (sin texto adicional):
{{"label":"positive|negative|neutral|mixed","scores":{{"positive":0.0,"negative":0.0,"neutral":0.0}},\
"confidence":0.0,"reasoning":"1-2 oraciones: menciona término dominicano detectado y/o contexto del conglomerado"}}"""

    def _build_prompt_batch(self, texts: list[str], entity_config, conglomerate) -> str:
        numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(texts))
        return f"""Eres un analista experto en reputación corporativa para empresas de la Corporación \
Zona Franca de Santiago, República Dominicana. Clasifica el SENTIMIENTO de cada texto hacia \
la empresa analizada (no hacia el narrador).

## CONTEXTO DE LA ENTIDAD
{self._context_block(entity_config, conglomerate)}

{_DOMINICAN_LEXICON_BLOCK}

## TEXTOS A ANALIZAR (devuelve un objeto por texto, en el MISMO orden)
{numbered}

Responde SOLO con un arreglo JSON (sin texto adicional):
[{{"i":0,"label":"positive|negative|neutral|mixed","scores":{{"positive":0.0,"negative":0.0,"neutral":0.0}},\
"confidence":0.0,"reasoning":"breve"}}]"""

    def _analyze_gemini(self, text, entity_config, conglomerate,
                        ambiguous_hints: list | None = None) -> dict | None:
        prompt = self._build_prompt_single(text, entity_config, conglomerate, ambiguous_hints)
        try:
            resp = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json", temperature=0.1,
                ),
            )
            data = json.loads(resp.text)
            return self._normalize_gemini(data)
        except Exception as e:
            logger.warning("Gemini falló (single): %s", e)
            return None

    def _analyze_gemini_batch(self, texts, entity_config, conglomerate) -> list[dict] | None:
        prompt = self._build_prompt_batch(texts, entity_config, conglomerate)
        try:
            resp = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json", temperature=0.1,
                ),
            )
            arr = json.loads(resp.text)
            if not isinstance(arr, list):
                return None
            out = [None] * len(texts)
            for obj in arr:
                i = obj.get("i")
                if isinstance(i, int) and 0 <= i < len(texts):
                    out[i] = self._normalize_gemini(obj)
            return out  # type: ignore
        except Exception as e:
            logger.warning("Gemini falló (batch): %s", e)
            return None

    def _normalize_gemini(self, data: dict) -> dict:
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
            "method": "gemini",
            "reasoning": data.get("reasoning", ""),
        }

    # ------------------------------------------------------------
    # Heurístico (red de seguridad) — portado del demo previo
    # ------------------------------------------------------------
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
                    "calidad", "servicio"]
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
            "method": "heuristic", "reasoning": "Heurístico de respaldo (Gemini no disponible).",
        }

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
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

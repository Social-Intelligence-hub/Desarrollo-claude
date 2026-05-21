"""
Motor de Análisis de Sentimiento - Azure AI Language
Con post-procesamiento de Lexicón Dominicano
"""

import os
import logging
from typing import Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

try:
    from azure.ai.textanalytics import TextAnalyticsClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("azure-ai-textanalytics no instalado. Usando modo demo.")

from processors.dominican_lexicon import detect_dominican_sentiment


class SentimentAnalyzer:
    """
    Wrapper para Azure AI Language con soporte de lexicón dominicano.
    Capa gratuita: 5,000 registros/mes.
    """

    def __init__(self):
        self.endpoint = os.getenv("AZURE_LANGUAGE_ENDPOINT")
        self.key = os.getenv("AZURE_LANGUAGE_KEY")
        self.client = None

        if AZURE_AVAILABLE and self.endpoint and self.key:
            try:
                credential = AzureKeyCredential(self.key)
                self.client = TextAnalyticsClient(
                    endpoint=self.endpoint,
                    credential=credential
                )
                logger.info("Azure AI Language client inicializado correctamente.")
            except Exception as e:
                logger.error(f"Error inicializando Azure client: {e}")
        else:
            logger.warning(
                "Azure AI Language no configurado. "
                "Set AZURE_LANGUAGE_ENDPOINT y AZURE_LANGUAGE_KEY en .env"
            )

    def analyze(self, text: str, language: str = "auto") -> dict:
        """
        Analiza el sentimiento de un texto con:
        1. Post-procesamiento dominicano (prioridad alta)
        2. Azure AI Language (si disponible)
        3. Fallback demo

        Returns:
            {
                "label": "positive" | "negative" | "neutral" | "mixed",
                "scores": {"positive": float, "negative": float, "neutral": float},
                "confidence": float,
                "dominican_override": bool,
                "dominican_term": str | None,
                "method": "dominican_lexicon" | "azure" | "demo"
            }
        """
        if not text or not text.strip():
            return self._empty_result()

        # PASO 1: Detección de términos dominicanos (máxima prioridad)
        dominican_result = detect_dominican_sentiment(text)
        if dominican_result["override"]:
            sentiment = dominican_result["sentiment"]
            scores = self._generate_scores_for_label(sentiment)
            return {
                "label": sentiment,
                "scores": scores,
                "confidence": 0.90,
                "dominican_override": True,
                "dominican_term": dominican_result["term_found"],
                "method": "dominican_lexicon",
            }

        # PASO 2: Azure AI Language (auto-detecta idioma: ES, EN, PT, etc.)
        if self.client:
            # "auto" → Azure detecta el idioma automáticamente
            azure_lang = None if language == "auto" else language
            return self._analyze_with_azure(text, azure_lang)

        # PASO 3: Fallback demo (para desarrollo sin credenciales)
        return self._analyze_demo(text)

    def analyze_batch(self, texts: list[str], language: str = "es") -> list[dict]:
        """
        Analiza múltiples textos. Azure permite hasta 10 por batch.
        """
        results = []

        # Pre-filtrar con lexicón dominicano
        azure_batch = []
        azure_indices = []

        for i, text in enumerate(texts):
            dominican = detect_dominican_sentiment(text)
            if dominican["override"]:
                sentiment = dominican["sentiment"]
                results.append({
                    "index": i,
                    "label": sentiment,
                    "scores": self._generate_scores_for_label(sentiment),
                    "confidence": 0.90,
                    "dominican_override": True,
                    "dominican_term": dominican["term_found"],
                    "method": "dominican_lexicon",
                })
            else:
                azure_batch.append(text)
                azure_indices.append(i)
                results.append(None)  # placeholder

        # Procesar resto con Azure en batches de 10
        if self.client and azure_batch:
            for batch_start in range(0, len(azure_batch), 10):
                batch = azure_batch[batch_start:batch_start + 10]
                batch_indices = azure_indices[batch_start:batch_start + 10]
                try:
                    azure_results = self.client.analyze_sentiment(
                        documents=batch,
                        language=language
                    )
                    for j, doc in enumerate(azure_results):
                        if not doc.is_error:
                            result = {
                                "index": batch_indices[j],
                                "label": doc.sentiment,
                                "scores": {
                                    "positive": doc.confidence_scores.positive,
                                    "negative": doc.confidence_scores.negative,
                                    "neutral": doc.confidence_scores.neutral,
                                },
                                "confidence": max(
                                    doc.confidence_scores.positive,
                                    doc.confidence_scores.negative,
                                    doc.confidence_scores.neutral,
                                ),
                                "dominican_override": False,
                                "dominican_term": None,
                                "method": "azure",
                            }
                        else:
                            result = self._demo_fallback(azure_batch[batch_start + j])
                            result["index"] = batch_indices[j]
                        results[batch_indices[j]] = result
                except Exception as e:
                    logger.error(f"Error en batch Azure: {e}")
                    for j, idx in enumerate(batch_indices):
                        results[idx] = self._analyze_demo(azure_batch[batch_start + j])
        else:
            for i, idx in enumerate(azure_indices):
                results[idx] = self._analyze_demo(azure_batch[i])

        return results

    def _analyze_with_azure(self, text: str, language: str | None) -> dict:
        try:
            kwargs = {"documents": [text]}
            if language:          # None → Azure auto-detecta
                kwargs["language"] = language
            response = self.client.analyze_sentiment(**kwargs)
            doc = response[0]
            if doc.is_error:
                logger.error(f"Azure error: {doc.error}")
                return self._analyze_demo(text)

            return {
                "label": doc.sentiment,
                "scores": {
                    "positive": doc.confidence_scores.positive,
                    "negative": doc.confidence_scores.negative,
                    "neutral": doc.confidence_scores.neutral,
                },
                "confidence": max(
                    doc.confidence_scores.positive,
                    doc.confidence_scores.negative,
                    doc.confidence_scores.neutral,
                ),
                "dominican_override": False,
                "dominican_term": None,
                "method": "azure",
            }
        except Exception as e:
            logger.error(f"Error Azure analyze_sentiment: {e}")
            return self._analyze_demo(text)

    def _analyze_demo(self, text: str) -> dict:
        """
        Análisis demo basado en heurísticas avanzadas:
        1. Sentimiento Institucional Positivo (Alianzas, Logros)
        2. Palabras clave estándar
        """
        text_lower = text.lower()
        
        # Heurística: Positivo Institucional
        institutional_positives = [
            "alianza", "convenio", "acuerdo", "graduación", "graduacion", "éxito", "exito", 
            "reconocimiento", "premia", "mejora", "innovación", "innovacion", "lanzamiento", 
            "certificación", "certificacion", "aprobado", "colaboración", "colaboracion",
            "inauguración", "inauguracion", "crecimiento", "desarrollo", "fortalece"
        ]
        
        positive_words = [
            "excelente", "bueno", "genial", "increíble", "recomiendo",
            "profesional", "satisfecho", "feliz", "gracias", "perfecto",
            "bien", "rápido", "eficiente", "calidad", "servicio"
        ]
        
        negative_words = [
            "malo", "pésimo", "terrible", "horrible", "decepcionante",
            "problema", "error", "falla", "tarde", "lento", "caro",
            "espera", "mal", "peor", "nunca", "jamás", "crisis", "queja"
        ]

        # Puntuar
        inst_score = sum(2 for w in institutional_positives if w in text_lower)
        pos_score = sum(1 for w in positive_words if w in text_lower) + inst_score
        neg_score = sum(1.5 for w in negative_words if w in text_lower) # Penalizar negativo más fuerte

        if pos_score > neg_score:
            label = "positive"
            # Si es por institucional, dar mucha confianza
            conf = 0.85 if inst_score > 0 else 0.75
            scores = {"positive": 0.85 if inst_score > 0 else 0.70, "negative": 0.05, "neutral": 0.10 if inst_score > 0 else 0.25}
        elif neg_score > pos_score:
            label = "negative"
            conf = 0.80
            scores = {"positive": 0.05, "negative": 0.80, "neutral": 0.15}
        else:
            label = "neutral"
            conf = 0.60
            scores = {"positive": 0.20, "negative": 0.20, "neutral": 0.60}

        return {
            "label": label,
            "scores": scores,
            "confidence": conf,
            "dominican_override": False,
            "dominican_term": None,
            "method": "heuristic_demo",
        }

    def _generate_scores_for_label(self, label: str) -> dict:
        if label == "positive":
            return {"positive": 0.90, "negative": 0.05, "neutral": 0.05}
        elif label == "negative":
            return {"positive": 0.05, "negative": 0.90, "neutral": 0.05}
        else:
            return {"positive": 0.20, "negative": 0.20, "neutral": 0.60}

    def _empty_result(self) -> dict:
        return {
            "label": "neutral",
            "scores": {"positive": 0.33, "negative": 0.33, "neutral": 0.34},
            "confidence": 0.0,
            "dominican_override": False,
            "dominican_term": None,
            "method": "empty",
        }

    def _demo_fallback(self, text: str) -> dict:
        return self._analyze_demo(text)

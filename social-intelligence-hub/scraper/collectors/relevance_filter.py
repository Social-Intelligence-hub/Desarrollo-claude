# -*- coding: utf-8 -*-
"""
Filtro de Relevancia v3 — DECLARATIVO.

Recibe la `entity_config` desde la BD y aplica reglas. Sin if/elif por slug,
sin hardcode. Agregar una entidad nueva = INSERT, nunca cambiar este archivo.

API principal:
    is_relevant(text: str, config: dict) -> bool
    is_relevant_detailed(text: str, config: dict) -> dict  # con motivo

`config` (de la tabla entity_configs) usa estas claves:
    required_terms    : list[str]  — al menos uno debe aparecer
    required_context  : list[str]  — todos deben aparecer (si no está vacío)
    forbidden_terms   : list[str]  — ninguno puede aparecer
    forbidden_domains : list[str]  — ej ['.cl']; descartado si el texto contiene un dominio así
    geo_requirement   : str | None — 'santiago_rd' | 'dominicana' | None
    disambiguation    : dict       — {positive_signals[], negative_signals[]}

Sobre la lista negra global (Chile/deportes/etc.): se conserva como red base
porque aplica a TODOS los conglomerados dominicanos; no es lógica por entidad.

Compatibilidad: se mantiene `es_relevante_dominicana(text, entity_slug)` para
los colectores legados que aún no leen `entity_configs`, delegando a la versión
declarativa con una config sintética derivada del slug.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


# ============================================================
# Lista negra global (no por-entidad — aplica a todo el conglomerado)
# ============================================================
GLOBAL_BLACKLIST = [
    # Ruido internacional
    "mets", "mlb", "maradona", "messi", "shakira", "marco rubio",
    "irán", "iran", "hormuz", "ormuz",
    "rusia", "ucrania", "putin", "zelensky", "israel", "gaza", "palestina",
    # Chile (homónimo con Santiago)
    "santiago de chile", "scl", "carabineros", "arriendos",
    "pesos chilenos", "audax", "vasco",
    "santiago metro", "región metropolitana", "las condes", "providencia",
    # Otros países LatAm que no son RD
    "argentina", "buenos aires", "méxico", "mexico", "colombia",
    "bogotá", "bogota", "venezuela",
    # Deportes (alto volumen de falsos positivos)
    "yankees", "red sox", "grandes ligas", "beisbol", "baseball",
    "copa américa", "copa america",
]

CHILE_STRONG_SIGNALS = frozenset([
    "santiago de chile", "región metropolitana", "las condes", "providencia",
    "audax", "vasco", "valparaiso", "carabineros", "pesos chilenos",
    "scl", "santiago metro",
])

DOMINICAN_SIGNALS = frozenset([
    "dominicana", "república dominicana", "republica dominicana",
    "rd ", "santiago de los caballeros", "cibao", "tamboril",
])

DOMAIN_PATTERN = re.compile(
    r"\b(?:https?://)?(?:www\.)?([a-z0-9.-]+\.(?:cl|do|com|net|org|info|biz|edu))\b"
)


# ============================================================
# Helpers (puros, sin estado)
# ============================================================
def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _extract_domains(text: str) -> list[str]:
    return [m.group(1).lower().rstrip("/") for m in DOMAIN_PATTERN.finditer(text)]


def _has_any(text: str, terms) -> bool:
    return any(t and t.lower() in text for t in terms)


def _has_all(text: str, terms) -> bool:
    return all(t.lower() in text for t in terms if t)


def _is_santiago_rd(text: str) -> bool:
    """Santiago RD = aparece 'santiago' + alguna señal dominicana."""
    if "santiago" not in text:
        return True  # No menciona Santiago: nada que desambiguar
    return any(s in text for s in DOMINICAN_SIGNALS) or any(
        d.endswith(".do") for d in _extract_domains(text)
    )


# ============================================================
# Filtro declarativo (v3)
# ============================================================
def is_relevant_detailed(text: str, config: dict | None) -> dict:
    """
    Devuelve {accepted: bool, reason: str}. Útil para logs y depuración.
    Si config es None o {}, solo se aplica la lista negra global + santiago_rd.
    """
    if not text or len(text.strip()) < 10:
        return {"accepted": False, "reason": "texto vacío/muy corto"}

    t = _normalize(text)
    cfg = config or {}

    # 1) Lista negra global (aplica siempre)
    for term in GLOBAL_BLACKLIST:
        if term in t:
            return {"accepted": False, "reason": f"blacklist global: '{term}'"}

    # "comuna" es muy chileno; solo bloqueamos cuando hay otro signal chileno
    if ("comuna" in t or "comunas" in t) and any(s in t for s in CHILE_STRONG_SIGNALS):
        return {"accepted": False, "reason": "comuna+contexto chileno"}

    # 2) forbidden_domains de la config (ej ['.cl'])
    domains = _extract_domains(t)
    for fd in cfg.get("forbidden_domains") or []:
        if any(d.endswith(fd.lower()) for d in domains):
            return {"accepted": False, "reason": f"dominio bloqueado: '{fd}'"}

    # 3) forbidden_terms de la config (ej CAPEX financiero)
    if _has_any(t, cfg.get("forbidden_terms") or []):
        bad = next(x for x in cfg["forbidden_terms"] if x.lower() in t)
        return {"accepted": False, "reason": f"forbidden_terms: '{bad}'"}

    # 4) Señales negativas de desambiguación (homónimos)
    dis = cfg.get("disambiguation") or {}
    if isinstance(dis, str):
        try:
            import json as _json
            dis = _json.loads(dis)
        except Exception:
            dis = {}
    neg = dis.get("negative_signals", [])
    pos = dis.get("positive_signals", [])

    # Si abundan negativas y no hay positivas que las balanceen → fuera
    neg_hits = sum(1 for s in neg if s.lower() in t)
    pos_hits = sum(1 for s in pos if s.lower() in t)
    if neg_hits >= 2 and neg_hits > pos_hits:
        return {"accepted": False, "reason": f"{neg_hits} señales negativas vs {pos_hits} positivas"}

    # 5) geo_requirement (santiago_rd / dominicana)
    geo = (cfg.get("geo_requirement") or "").strip().lower()
    if geo == "santiago_rd" and not _is_santiago_rd(t):
        return {"accepted": False, "reason": "geo_requirement=santiago_rd no satisfecho"}
    if geo == "dominicana" and not (
        any(s in t for s in DOMINICAN_SIGNALS) or
        any(d.endswith(".do") for d in domains)
    ):
        return {"accepted": False, "reason": "geo_requirement=dominicana no satisfecho"}

    # 6) required_terms (al menos uno) — usar keywords de la entidad
    req = cfg.get("required_terms") or []
    if req and not _has_any(t, req):
        return {"accepted": False, "reason": "ningún required_term presente"}

    # 7) required_context (todos)
    if (cfg.get("required_context") or []) and not _has_all(t, cfg["required_context"]):
        return {"accepted": False, "reason": "falta algún required_context"}

    return {"accepted": True, "reason": "ok"}


def is_relevant(text: str, config: dict | None) -> bool:
    return is_relevant_detailed(text, config)["accepted"]


# ============================================================
# Compatibilidad con colectores legados (los que pasan slug en vez de config)
# Conserva el contrato es_relevante_dominicana(text, entity_slug) usado por
# google_alerts.py y reddit_collector.py. Internamente delega al filtro v3
# con una config mínima sintética. Cuando esos colectores reciban la config
# real desde BD, esta función se eliminará.
# ============================================================
_LEGACY_SLUG_CONFIGS = {
    "capex-institucion": {
        "required_terms": ["capex"],
        "required_context": [],
        "forbidden_terms": ["capital expenditure", "gasto de capital", "capex ratio"],
        "forbidden_domains": [".cl"],
        "geo_requirement": "santiago_rd",
        "disambiguation": {
            "positive_signals": ["capacitación", "curso", "taller", "egresados", "formación", "zona franca"],
            "negative_signals": ["capital expenditure", "balance general", "depreciación"],
        },
    },
    "capex": {
        "required_terms": ["capex"],
        "forbidden_terms": ["capital expenditure", "gasto de capital", "capex ratio"],
        "forbidden_domains": [".cl"],
        "geo_requirement": "santiago_rd",
        "disambiguation": {
            "positive_signals": ["capacitación", "curso", "taller", "egresados", "formación"],
            "negative_signals": ["capital expenditure", "balance general", "depreciación"],
        },
    },
}


def es_relevante_dominicana(text: str, entity_slug: str | None = None) -> bool:
    """Wrapper legacy: convierte slug→config sintética y delega al filtro v3."""
    if not text:
        return False
    cfg = _LEGACY_SLUG_CONFIGS.get(entity_slug or "", {
        "forbidden_domains": [".cl"],
        "geo_requirement": "santiago_rd",
    })
    return is_relevant(text, cfg)

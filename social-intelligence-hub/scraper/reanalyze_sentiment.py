# -*- coding: utf-8 -*-
"""
Re-analiza el sentimiento de menciones ya guardadas en Supabase.

Útil cuando:
- Gemini estuvo caído durante la corrida original y todo cayó al heurístico.
- Se quiere actualizar el léxico/prompt y reanalizar lo viejo.
- Se quiere validar criterio #3 del DEPLOY (% de menciones via Gemini).

Uso:
    py -3.13 reanalyze_sentiment.py --conglomerate zona-franca
    py -3.13 reanalyze_sentiment.py --conglomerate zona-franca --only-heuristic
    py -3.13 reanalyze_sentiment.py --entity-slug capex
    py -3.13 reanalyze_sentiment.py --limit 20 --dry-run
"""
import argparse
import logging
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client
from processors.gemini_sentiment import SentimentAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reanalyze")


def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY.")
        sys.exit(1)
    return create_client(url, key)


def fetch_mentions(supabase, conglomerate_slug, entity_slug, only_heuristic, limit):
    q = supabase.table("mentions").select(
        "id, text_original, entity_id, sentiment_label, sentiment_score, "
        "entities(slug, name, conglomerate_id, entity_configs(*))"
    )
    if limit:
        q = q.limit(limit)
    rows = q.execute().data or []

    # Filtros en cliente (más simple que JOINs raros vía PostgREST)
    filtered = []
    for r in rows:
        ent = r.get("entities") or {}
        if entity_slug and ent.get("slug") != entity_slug:
            continue
        if only_heuristic:
            score = r.get("sentiment_score") or {}
            method = score.get("method") if isinstance(score, dict) else None
            if method == "gemini":
                continue
        filtered.append(r)
    return filtered


def fetch_conglomerate(supabase, slug):
    res = supabase.table("conglomerates").select("*").eq("slug", slug).limit(1).execute()
    return res.data[0] if res.data else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--conglomerate", default="zona-franca")
    p.add_argument("--entity-slug", default=None, help="Solo una entidad")
    p.add_argument("--only-heuristic", action="store_true",
                   help="Solo re-analiza menciones que NO fueron por Gemini")
    p.add_argument("--limit", type=int, default=None, help="Tope de menciones")
    p.add_argument("--dry-run", action="store_true", help="No actualiza la BD")
    args = p.parse_args()

    supabase = get_supabase()
    conglomerate = fetch_conglomerate(supabase, args.conglomerate)
    if not conglomerate:
        logger.error("Conglomerado '%s' no existe.", args.conglomerate)
        sys.exit(1)

    mentions = fetch_mentions(
        supabase, args.conglomerate, args.entity_slug,
        args.only_heuristic, args.limit
    )
    if not mentions:
        logger.info("No hay menciones que re-analizar.")
        return

    analyzer = SentimentAnalyzer()
    if not analyzer.client:
        logger.error("Gemini no disponible — el script no aporta valor sin el LLM.")
        sys.exit(1)

    logger.info("Re-analizando %d menciones (only_heuristic=%s, dry_run=%s)",
                len(mentions), args.only_heuristic, args.dry_run)

    stats = {"updated": 0, "via_gemini": 0, "via_lexico": 0, "via_heuristico": 0, "skipped": 0}

    for i, m in enumerate(mentions, 1):
        text = m.get("text_original") or ""
        if not text.strip():
            stats["skipped"] += 1
            continue

        ent = m.get("entities") or {}
        cfg_raw = ent.get("entity_configs")
        if isinstance(cfg_raw, list):
            entity_config = cfg_raw[0] if cfg_raw else {}
        elif isinstance(cfg_raw, dict):
            entity_config = cfg_raw
        else:
            entity_config = {}

        s = analyzer.analyze(text, entity_config=entity_config, conglomerate=conglomerate)
        method = s.get("method", "unknown")
        stats[f"via_{ {'gemini':'gemini','dominican_lexicon':'lexico','heuristic':'heuristico'}.get(method, 'heuristico') }"] += 1

        new_score = {
            **s.get("scores", {}),
            "reasoning": s.get("reasoning", ""),
            "method": method,
            "dominican_term": s.get("dominican_term"),
        }
        update = {
            "sentiment_label": s["label"],
            "sentiment_score": new_score,
            "confidence_score": s.get("confidence", 0.5),
            "dominican_override": s.get("dominican_override", False),
        }

        if not args.dry_run:
            supabase.table("mentions").update(update).eq("id", m["id"]).execute()
        stats["updated"] += 1

        if i % 20 == 0:
            logger.info("  ... %d/%d (gemini=%d léxico=%d heur=%d)",
                        i, len(mentions), stats["via_gemini"],
                        stats["via_lexico"], stats["via_heuristico"])

    logger.info("=" * 60)
    logger.info("FIN re-análisis: %s", stats)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

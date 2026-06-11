# -*- coding: utf-8 -*-
"""
Léxico Dominicano para Análisis de Sentimiento — v2
Nivel 1 de la cascada NLP: override prioritario antes de Gemini.

REGLA DE ORO: solo entran aquí términos con polaridad inequívoca en CUALQUIER contexto.
Términos ambiguos (vaina, tiguere, bregar) van en AMBIGUOUS_TERMS para
ser pasados como HINTS a Gemini, no como overrides.
"""

# ============================================================
# NEGACIÓN — ventana de 5 palabras antes del término
# ============================================================
NEGATION_WORDS = {"no", "ni", "nunca", "jamás", "jamas", "tampoco", "sin"}


# ============================================================
# POSITIVOS (override seguro en cualquier contexto)
# ============================================================
POSITIVE_TERMS = {
    # Calidad / Excelencia
    "jevi": "excelente, de alta calidad",
    "jevy": "excelente, de alta calidad",
    "nítido": "perfecto, excelente",
    "nitido": "perfecto, excelente",
    "brutal": "increíble, muy bueno (uso coloquial positivo RD)",
    "chévere": "genial, bueno",
    "chevere": "genial, bueno",
    "vacano": "excelente, genial",
    "bacano": "excelente, cool",
    "ta durísimo": "muy bueno, impresionante",
    "ta' durísimo": "muy bueno, impresionante",
    "rulay": "sentirse/estar muy bien, excelente",
    "hevi-nais": "muy bien, excelente",
    "hevinais": "muy bien, excelente",
    "me la robó": "me encanta, me gusta mucho (positivo idiomático)",
    "me la roban": "me encanta, me gusta mucho (positivo idiomático)",
    "ta' movidú": "excelente, impresionante",
    "ta movidú": "excelente, impresionante",
    "ta' guay": "excelente, moderno, atractivo",
    "ta guay": "excelente, moderno, atractivo",
    "ta topú": "excelente, lo mejor",
    "ta' topú": "excelente, lo mejor",
    "no tiene pierde": "confiable, seguro, excelente",
    "candela": "excelente calidad (en contexto de elogio)",
    "saca chispa": "espectacular, destaca positivamente",
    "e' lujo": "muy bueno, de calidad",
    "es lujo": "muy bueno, de calidad",
    "de lo mío": "muy cercano, muy apreciado, de confianza",
    "matatán": "muy respetado y efectivo",
    "montro": "muy respetado, de gran autoridad positiva",
    "de primera": "de primera calidad",
    "de ley": "de confianza, legítimo",
    "tato": "todo bien, en orden",
    "yala": "de acuerdo, OK, perfecto",
    "e' pa' lante": "avanzando, progresando positivamente",
    "e pa lante": "avanzando, progresando positivamente",
    "bien montao": "bien organizado, de calidad",
    "bien montado": "bien organizado, de calidad",
    "pa' arriba": "en alza, mejorando",
    "pa arriba": "en alza, mejorando",
    "dando pa' lante": "progresando",
    "dando pa lante": "progresando",
    "tremendo": "impresionante (positivo cuando elogio)",
    "metío": "comprometido, dedicado",
    "metio": "comprometido, dedicado",
    "enchulao": "bien equipado, moderno",
    "enchulado": "bien equipado, moderno",
    "lo máximo": "lo mejor",
    "lo maximo": "lo mejor",
    "eso no tiene pierde": "absolutamente confiable",
    "eso tiene su punto": "tiene mérito, buena propuesta",
    "e' de primera": "excelente calidad",
    "ta' bien": "aprobación, satisfacción",
    "dale dale": "aprobación entusiasta",
    "e' pa lante": "avanzando positivamente",
    "empujando": "trabajando duro con resultado positivo",
    "efectivo": "eficiente (en contexto de elogio)",
}

# ============================================================
# NEGATIVOS (override seguro en cualquier contexto)
# ============================================================
NEGATIVE_TERMS = {
    # Estado malo / Falla
    "en olla": "en problemas, funcionando mal",
    "al garete": "arruinado, sin rumbo, descontrolado",
    "brigandina": "mal hecho, de baja calidad, chapucero",
    "juidero": "desorden total, caos",
    "desmadre": "desorden total, caos",
    "dando carpeta": "actuando de forma negligente, fallando",
    "en la luna": "desconectado, irresponsable",
    "arranca'o": "sin recursos, en mal estado",
    "arrancao": "sin recursos, en mal estado",
    "prendio": "en caos, fuera de control",
    "prendío": "en caos, fuera de control",
    "manganzón": "perezoso, ineficiente",
    "manganzon": "perezoso, ineficiente",
    # Enojo / Conflicto
    "emberracado": "muy molesto, furioso",
    "emberracao": "muy molesto, furioso",
    "jodido": "en problemas graves",
    "jodio": "en problemas graves",
    "picao": "molesto, ofendido",
    "picado": "molesto, ofendido",
    "boche": "llamada de atención severa, crítica fuerte",
    "la macó": "cometió un error grave, la pifió",
    # Engaño / Estafa
    "mojonear": "burlar, engañar, tomar el pelo",
    "mojoneo": "burla, engaño sistemático",
    "me tumbaron": "me engañaron, me estafaron",
    "lo tumbaron": "lo engañaron, lo estafaron",
    "me dejaron a palo": "abandonado sin solución, servicio fallido",
    "me comieron el coco": "me engañaron, me manipularon",
    "fue un rata": "fue una estafa descarada",
    "es un rata": "es una estafa descarada",
    "me hicieron queso": "me defraudaron, se burlaron",
    "eso es un chisme": "producto/servicio falso o inútil",
    # Rechazo / Negación fuerte
    "ni en pato": "de ninguna manera, rechazo absoluto",
    "ta' fuera": "descartado totalmente, rechazado",
    "ta fuera": "descartado totalmente, rechazado",
    "qué va": "negación enfática, no funciona",
    # Personas negativas
    "pariguayo": "persona aburrida, que no participa, negativo en contexto empresarial",
    "corcho": "oportunista, no confiable, dice lo que convenga",
    "boca-agua": "persona que solo habla pero no cumple",
    "besa nalga": "adulador sin criterio",
    "jalabola": "adulador sin criterio",
    # Estado crítico
    "desamparado": "sin apoyo, abandonado",
    "botao": "abandonado, descuidado",
    "botado": "abandonado, descuidado",
    "en crisis": "situación crítica",
    "caído": "sin funcionar, caído (sistema/servicio)",
    "caido": "sin funcionar, caído",
    "peor que antes": "ha empeorado visiblemente",
    "complicao": "con muchos problemas, en dificultades",
    "embarrarse": "meterse en líos graves",
    "fumando cable": "perdiendo tiempo, ocioso de manera negativa",
    "atrancado": "bloqueado, atascado en problema",
    "pachá": "lento, ineficiente",
    "pacha": "lento, ineficiente",
    "juquiao": "fuera de control",
    "arrebatao": "fuera de control",
    "ta pisao": "con problemas legales serios, preso",
    "armao de excusas": "lleno de pretextos, sin responsabilidad",
    # Costos / Abusos
    "una barbaridad": "precio/situación exagerada e injusta",
    "pa' sencillo": "irónicamente fácil → con consecuencia negativa",
    "se volvió todo un guiso": "se convirtió en un desorden total",
    "se volvió un guiso": "desorden total",
    "flojo de papeles": "poco profesional, mal manejado",
    "quedao": "obsoleto, fuera de moda, anticuado",
    "quedado": "obsoleto, fuera de moda",
    "no me hagas cocote": "no me des esperanzas falsas",
}

# ============================================================
# AMBIGUOS — hints para Gemini, NO override
# Estructura: {término: {meaning, positive_ctx, negative_ctx}}
# ============================================================
AMBIGUOUS_TERMS = {
    "tiguere": {
        "meaning": "persona astuta de la calle",
        "positive_ctx": "inteligente, sagaz, resuelve problemas",
        "negative_ctx": "tramposo, aprovechador, poco confiable",
    },
    "vaina": {
        "meaning": "comodín para cualquier cosa/situación",
        "positive_ctx": "jevi, buena, genial + vaina",
        "negative_ctx": "mala, brigandina, no sirve + vaina",
    },
    "dique": {
        "meaning": "supuestamente (a menudo irónico)",
        "positive_ctx": "raramente positivo",
        "negative_ctx": "duda, ironía, sospecha, desconfianza",
    },
    "dizque": {
        "meaning": "supuestamente (variante de dique)",
        "positive_ctx": "raramente positivo",
        "negative_ctx": "duda, ironía",
    },
    "janguear": {
        "meaning": "callejear, pasar tiempo informal",
        "positive_ctx": "diversión entre amigos, tiempo libre positivo",
        "negative_ctx": "perder tiempo, actividades cuestionables",
    },
    "bregar": {
        "meaning": "trabajar, lidiar con algo",
        "positive_ctx": "trabajando duro, esforzándose",
        "negative_ctx": "lidiando con problemas, en dificultades",
    },
    "florearse": {
        "meaning": "exhibirse, darse a ver",
        "positive_ctx": "mostrando logros legítimos",
        "negative_ctx": "ostentando de manera molesta",
    },
    "matatán": {
        "meaning": "persona muy respetada",
        "positive_ctx": "respeto genuino por méritos",
        "negative_ctx": "respeto por intimidación o poder negativo",
    },
}

# ============================================================
# SEÑALES PARA DESAMBIGUACIÓN CAPEX
# ============================================================
CAPEX_INSTITUTION_SIGNALS = [
    "capex", "santiago", "capacitación", "capacitacion", "taller",
    "curso", "egresado", "egresados", "formación", "formacion",
    "técnico", "tecnico", "instructor", "estudiante", "centro",
    "capex santiago", "capex rd", "capex dominicana",
]

CAPEX_FINANCIAL_SIGNALS = [
    "capital expenditure", "gastos de capital", "inversión de capital",
    "capex ratio", "capex total", "capex budget", "financial", "finanzas",
    "contabilidad", "balance sheet", "balance general", "activos fijos",
    "depreciación", "depreciacion", "amortización",
]


# ============================================================
# FUNCIONES PÚBLICAS
# ============================================================

def _has_negation_before(words: list[str], term_start_idx: int, window: int = 5) -> bool:
    """Detecta si hay una negación en las N palabras anteriores al término."""
    start = max(0, term_start_idx - window)
    return any(w in NEGATION_WORDS for w in words[start:term_start_idx])


def detect_dominican_sentiment(text: str) -> dict:
    """
    Analiza el texto buscando términos dominicanos con polaridad definida.

    Incluye detección de negación: "no está jevi" → no hace override positivo.
    Los términos ambiguos se devuelven como hints (override=False).

    Returns:
        {
            "override": bool,
            "sentiment": "positive" | "negative" | None,
            "term_found": str | None,
            "term_meaning": str | None,
            "ambiguous_hints": list[dict],   # hints para Gemini
        }
    """
    text_lower = text.lower()
    words = text_lower.split()
    ambiguous_hints = []

    # Buscar términos ambiguos como hints para Gemini
    for term, meta in AMBIGUOUS_TERMS.items():
        if term in text_lower:
            ambiguous_hints.append({
                "term": term,
                "meaning": meta["meaning"],
                "positive_ctx": meta["positive_ctx"],
                "negative_ctx": meta["negative_ctx"],
            })

    # Verificar términos positivos (con detección de negación)
    for term, meaning in POSITIVE_TERMS.items():
        pos = text_lower.find(term)
        if pos == -1:
            continue
        # Calcular índice de palabra aproximado para ventana de negación
        words_before = text_lower[:pos].split()
        if _has_negation_before(words_before, len(words_before), window=5):
            # Negación encontrada: convertir a negativo
            return {
                "override": True,
                "sentiment": "negative",
                "term_found": f"no {term}",
                "term_meaning": f"Negación de: {meaning}",
                "ambiguous_hints": ambiguous_hints,
            }
        return {
            "override": True,
            "sentiment": "positive",
            "term_found": term,
            "term_meaning": meaning,
            "ambiguous_hints": ambiguous_hints,
        }

    # Verificar términos negativos
    for term, meaning in NEGATIVE_TERMS.items():
        if term in text_lower:
            return {
                "override": True,
                "sentiment": "negative",
                "term_found": term,
                "term_meaning": meaning,
                "ambiguous_hints": ambiguous_hints,
            }

    return {
        "override": False,
        "sentiment": None,
        "term_found": None,
        "term_meaning": None,
        "ambiguous_hints": ambiguous_hints,
    }


def disambiguate_capex(text: str) -> str:
    """
    Determina si 'CAPEX' en el texto se refiere a la institución educativa
    o al término financiero.

    Returns:
        "institution" | "financial" | "ambiguous"
    """
    text_lower = text.lower()
    institution_score = sum(1 for s in CAPEX_INSTITUTION_SIGNALS if s in text_lower)
    financial_score = sum(1 for s in CAPEX_FINANCIAL_SIGNALS if s in text_lower)

    if institution_score > financial_score:
        return "institution"
    elif financial_score > institution_score:
        return "financial"
    return "ambiguous"


def normalize_dominican_text(text: str) -> str:
    """Reservado para normalización futura. No modifica el texto en esta versión."""
    return text

import logging
import re

logger = logging.getLogger(__name__)

BLACK_LIST_KEYWORDS = [
    # SUPER_BLACKLIST (Ruido Internacional Crítico)
    "mets", "mlb", "maradona", "messi", "irán", "iran", "hormuz", "ormuz", "rusia", "ucrania", "putin", "chile", "scl", "carabineros", "arriendos",
    # Geográficos adicionales
    "valparaiso", "santiago de chile", "pesos chilenos", "audax", "vasco",
    "santiago metro", "región metropolitana", "las condes", "providencia", "san isidro",
    "santo domingo este", "santo domingo", "distrito nacional", "hainamosa",
    "argentina", "buenos aires", "méxico", "mexico", "colombia", "bogotá", "bogota", "venezuela",
    # Deportes y otros ruidos
    "fútbol", "futbol", "gol", "fifa", "copa américa", "copa america",
    "yankees", "red sox", "grandes ligas", "beisbol", "baseball",
    # Política Internacional
    "zelensky", "israel", "gaza", "palestina",
    # Términos Genéricos de Salud (Ruido para MÉDICA)
    "junta médica", "seguro médico", "atención médica", "facultad de medicina", "médica forense",
]

CHILE_STRONG_SIGNALS = [
    "santiago de chile",
    "región metropolitana",
    "las condes",
    "providencia",
    "audax",
    "vasco",
    "valparaiso",
    "carabineros",
    "pesos chilenos",
    "scl",
    "santiago metro",
]

DOMAIN_CL_SUFFIX = ".cl"
DOMAIN_DO_SUFFIX = ".do"

DOMINICAN_POSITIVE_TERMS = [
    "dominicana",
    "república dominicana",
    "republica dominicana",
    "rd",
    "santiago de los caballeros",
]

CZFS_TERMS = [
    "czfs",
    "corporación zona franca",
    "corporacion zona franca",
    "zona franca santiago",
    "parque industrial victor espaillat",
    "parque industrial víctor espaillat",
    "pivem",
    "mera",
    "vvm",
    "capex",
    "plazona",
    "médica czfs",
    "medica czfs",
    "villa europa",
]


# Empresas clave en el PIVEM
PIVEM_COMPANIES = [
    "grupo m", "codevi", "bojs tanning", "swisher", "swedish match", 
    "general cigar", "hanesbrands", "hanes", "timberland", "vf corporation",
    "insight", "grand island", "cooperativa san miguel",
]

CAPEX_CONTEXT_TERMS = [
    "capacitación", "capacitacion", "curso", "taller", "formacion", "formación",
    "diplomado", "educacion", "educación", "infotep", "enseñanza", "aprendizaje",
]

CAPEX_TERMS = [
    "capex",
    "capacitación",
    "capacitacion",
    "curso",
    "taller",
    "formacion",
    "formación",
]

PIVEM_TERMS = [
    "pivem",
    "parque industrial villa europa",
    "villa europa",
]

GENERIC_ENTITY_TERMS = list({
    *CZFS_TERMS,
    *CAPEX_TERMS,
    *PIVEM_TERMS,
})

DOMAIN_PATTERN = re.compile(r"\b(?:https?://)?(?:www\.)?([a-z0-9.-]+\.(?:cl|do|com|net|org|info|biz|edu))\b")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_domains(text: str) -> list[str]:
    domains = []
    for match in DOMAIN_PATTERN.finditer(text):
        domain = match.group(1).lower().rstrip("/")
        domains.append(domain)
    return domains


def has_chile_domain(text: str) -> bool:
    return any(domain.endswith(DOMAIN_CL_SUFFIX) for domain in extract_domains(text))


def has_dominican_domain(text: str) -> bool:
    return any(domain.endswith(DOMAIN_DO_SUFFIX) for domain in extract_domains(text))


def has_santiago(text: str) -> bool:
    return "santiago" in text or "santiago de los caballeros" in text


def has_dominican_signal(text: str) -> bool:
    return any(term in text for term in DOMINICAN_POSITIVE_TERMS)


def has_blacklist_signal(text: str) -> bool:
    if any(phrase in text for phrase in BLACK_LIST_KEYWORDS):
        return True

    # Las menciones de "comuna" son comunes en Chile; solo bloqueamos cuando hay contexto chileno.
    if "comuna" in text or "comunas" in text:
        if any(signal in text for signal in CHILE_STRONG_SIGNALS):
            return True

    return False


def has_entity_term(text: str, entity_slug: str) -> bool:
    if entity_slug == "czfs":
        return any(term in text for term in CZFS_TERMS)
    if entity_slug == "capex-institucion":
        return any(term in text for term in CAPEX_TERMS)
    if entity_slug == "pivem":
        return any(term in text for term in PIVEM_TERMS)
    if entity_slug == "plazona":
        return "plazona" in text or "centro comercial" in text
    if entity_slug == "medica-czfs":
        return any(term in text for term in ["médica czfs", "medica czfs", "centro de salud czfs"])
    return any(term in text for term in GENERAL_RELEVANT_TERMS)


def es_relevante_dominicana(texto: str, entity_slug: str | None = None) -> bool:
    """
    Filtro estricto de relevancia para RD/CZFS/CAPEX.
    Retorna True solo si:
    - NO tiene palabras clave de ruido (Chile, sports, etc.)
    - Si menciona Santiago, DEBE confirmar contexto RD (Dominicana/RD/Caballeros)
    - Si es CAPEX, DEBE tener contexto educativo
    - Si es MÉDICA, DEBE confirmar ser de CZFS Santiago
    - Si es PIVEM, DEBE mencionar el parque en RD
    """
    if not texto:
        return False

    text = normalize_text(texto)
    
    # 1. Filtro CRÍTICO: Lista Negra (Inmediato)
    if has_blacklist_signal(text):
        logger.debug(f"[DESCARTADO] Blacklist: {texto[:80]}...")
        return False
    if has_chile_domain(text):
        logger.debug(f"[DESCARTADO] Dominio Chile (.cl): {texto[:80]}...")
        return False

    # 2. Desambiguación Geográfica para Santiago GENÉRICO (sin entidad específica)
    # Si no estamos buscando una entidad específica y menciona Santiago, DEBE confirmar RD
    if entity_slug is None and "santiago" in text:
        has_rd_signal = has_dominican_signal(text) or has_dominican_domain(text)
        if not has_rd_signal:
            logger.debug(f"[DESCARTADO] Santiago sin contexto RD: {texto[:80]}...")
            return False

    is_santiago_rd = has_dominican_signal(text) or has_dominican_domain(text)
    
    # 3. Lógica ESTRICTA por Entidad
    
    if entity_slug == "capex-institucion":
        # CAPEX SOLO se acepta si es educativo
        has_capex = "capex" in text
        if not has_capex:
            logger.debug(f"[DESCARTADO] CAPEX sin mención directa: {texto[:80]}...")
            return False
        
        # CAPEX DEBE estar en contexto educativo
        edu_keywords = ["curso", "taller", "diplomado", "capacitacion", "capacitación", 
                       "formacion", "formación", "certificacion", "certificación",
                       "programa", "infotep", "estudiante", "alumno", "egresado", 
                       "entrenamiento", "adiestramiento"]
        has_edu_context = any(kw in text for kw in edu_keywords)
        if not has_edu_context:
            logger.debug(f"[DESCARTADO] CAPEX sin contexto educativo: {texto[:80]}...")
            return False
        
        # Si menciona Santiago Y contexto chileno, rechazar
        if "santiago" in text and has_chile_domain(text):
            logger.debug(f"[DESCARTADO] CAPEX en contexto Chile: {texto[:80]}...")
            return False
        
        logger.debug(f"[ACEPTADO] CAPEX educativo: {texto[:80]}...")
        return True

    if entity_slug == "medica-czfs":
        # MÉDICA CZFS DEBE confirmar ser médica
        has_medica = ("médica" in text or "medica" in text or 
                     "centro médico" in text or "centro medico" in text or
                     "clínica" in text or "clinica" in text)
        if not has_medica:
            logger.debug(f"[DESCARTADO] No es MÉDICA: {texto[:80]}...")
            return False
        
        # MÉDICA en CZFS/PIVEM/zona franca es suficiente (contexto claro)
        czfs_context_terms = ["czfs", "zona franca", "pivem", "parque industrial", 
                             "el parque", "santiaguero", "santiago de los caballeros"]
        has_czfs_context = any(term in text for term in czfs_context_terms)
        
        # O MÉDICA con Santiago + contexto RD
        explicit_rd = is_santiago_rd or ("santiago" in text and has_dominican_signal(text))
        
        if not (has_czfs_context or explicit_rd):
            logger.debug(f"[DESCARTADO] MÉDICA sin contexto CZFS/RD: {texto[:80]}...")
            return False
        
        # Rechazar si está explícitamente en Chile
        if has_chile_domain(text):
            logger.debug(f"[DESCARTADO] MÉDICA en contexto Chile: {texto[:80]}...")
            return False
        
        logger.debug(f"[ACEPTADO] MÉDICA CZFS: {texto[:80]}...")
        return True

    if entity_slug == "pivem":
        # PIVEM o empresas del parque
        has_pivem_term = "pivem" in text or "villa europa" in text or "parque industrial" in text or "el parque" in text
        has_company = any(term in text for term in PIVEM_COMPANIES)
        has_zona_franca = "zona franca" in text  # Zona franca es contexto implícitamente RD
        
        if not (has_pivem_term or has_company or (has_zona_franca and "pivem" in text)):
            logger.debug(f"[DESCARTADO] No PIVEM ni empresas: {texto[:80]}...")
            return False
        
        # Rechazar si está explícitamente en Chile
        if has_chile_domain(text):
            logger.debug(f"[DESCARTADO] PIVEM en contexto Chile: {texto[:80]}...")
            return False
        
        # Si menciona Santiago, DEBE ser Santiago RD (no Chile)
        if "santiago" in text and not is_santiago_rd and not has_zona_franca:
            logger.debug(f"[DESCARTADO] PIVEM Santiago sin contexto RD: {texto[:80]}...")
            return False
        
        logger.debug(f"[ACEPTADO] PIVEM: {texto[:80]}...")
        return True

    if entity_slug == "czfs":
        # CZFS o zona franca
        has_czfs = any(term in text for term in CZFS_TERMS)
        if not has_czfs:
            logger.debug(f"[DESCARTADO] No CZFS/zona franca: {texto[:80]}...")
            return False
        
        # Rechazar si está explícitamente en Chile
        if has_chile_domain(text):
            logger.debug(f"[DESCARTADO] CZFS en contexto Chile: {texto[:80]}...")
            return False
        
        # Si menciona "Zona franca Santiago" sin contrasentido (Chile), es RD por defecto
        # Si menciona Santiago, DEBE ser Santiago RD (no Chile) a menos que ya lo es implícitamente
        if "santiago" in text and not is_santiago_rd:
            # Solo rechazar si hay una contrasentido explícito (no lo hay si es "zona franca santiago")
            # porque zona franca santiago es por defecto CZFS RD
            if "zona franca santiago" not in text:
                logger.debug(f"[DESCARTADO] CZFS Santiago sin contexto RD: {texto[:80]}...")
                return False
        
        logger.debug(f"[ACEPTADO] CZFS: {texto[:80]}...")
        return True

    if entity_slug == "plazona":
        # PLAZONA DEBE mencionar plazona
        has_plazona = "plazona" in text
        if not has_plazona:
            logger.debug(f"[DESCARTADO] No Plazona: {texto[:80]}...")
            return False
        
        # Rechazar si está en Chile
        if has_chile_domain(text):
            logger.debug(f"[DESCARTADO] Plazona en contexto Chile: {texto[:80]}...")
            return False
        
        logger.debug(f"[ACEPTADO] Plazona: {texto[:80]}...")
        return True

    # 4. Filtro Genérico (Si no se especifica entidad)
    all_positive_terms = GENERIC_ENTITY_TERMS + PIVEM_COMPANIES
    if any(term in text for term in all_positive_terms):
        if is_santiago_rd or has_dominican_domain(text):
            logger.debug(f"[ACEPTADO] Genérico RD: {texto[:80]}...")
            return True
        logger.debug(f"[DESCARTADO] Genérico sin RD: {texto[:80]}...")
        return False

    logger.debug(f"[DESCARTADO] Sin coincidencia de términos: {texto[:80]}...")
    return False


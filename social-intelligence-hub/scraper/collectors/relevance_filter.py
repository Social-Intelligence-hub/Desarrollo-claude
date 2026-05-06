import re

BLACK_LIST_KEYWORDS = [
    # Geográficos (Fuera de Santiago RD)
    "chile", "scl", "valparaiso", "santiago de chile", "carabineros", "pesos chilenos", "audax", "vasco",
    "santiago metro", "región metropolitana", "las condes", "providencia", "san isidro",
    "santo domingo este", "santo domingo", "distrito nacional", "hainamosa",
    "argentina", "buenos aires", "méxico", "mexico", "colombia", "bogotá", "bogota", "venezuela",
    # Deportes y otros ruidos
    "messi", "maradona", "fútbol", "futbol", "gol", "fifa", "copa américa", "copa america",
    "mets", "yankees", "red sox", "mlb", "grandes ligas", "beisbol", "baseball",
    # Política Internacional y Conflictos
    "irán", "iran", "hormuz", "ormuz", "estrecho", "rusia", "ucrania", "putin", "zelensky",
    "israel", "gaza", "palestina",
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
    if not texto:
        return False

    text = normalize_text(texto)
    
    # 1. Filtro de Lista Negra (Inmediato)
    if has_blacklist_signal(text):
        return False
    if has_chile_domain(text):
        return False

    # 2. Desambiguación Geográfica Positiva
    is_santiago_rd = has_santiago(text) and (has_dominican_signal(text) or has_dominican_domain(text))
    
    # 3. Lógica por Entidad
    if entity_slug == "capex-institucion":
        # Requiere "capex" Y contexto educativo O Santiago RD
        has_capex = "capex" in text
        has_edu_context = any(term in text for term in CAPEX_CONTEXT_TERMS)
        return has_capex and (has_edu_context or is_santiago_rd)

    if entity_slug == "medica-czfs":
        # Requiere "médica" Y contexto institucional de Santiago
        has_medica = "médica" in text or "medica" in text
        has_medica_context = any(term in text for term in ["czfs", "pivem", "zona franca", "santiago"])
        return has_medica and has_medica_context

    if entity_slug == "pivem":
        # PIVEM o empresas del parque
        has_pivem = "pivem" in text or "parque industrial" in text
        has_company = any(term in text for term in PIVEM_COMPANIES)
        return (has_pivem or has_company) and (is_santiago_rd or "santiago" in text)

    if entity_slug == "czfs":
        has_czfs = any(term in text for term in CZFS_TERMS)
        return has_czfs and (is_santiago_rd or "santiago" in text)

    # 4. Filtro Genérico (Si no se especifica entidad)
    all_positive_terms = GENERIC_ENTITY_TERMS + PIVEM_COMPANIES
    if any(term in text for term in all_positive_terms):
        if is_santiago_rd:
            return True
        # Si menciona una empresa específica y Santiago, lo damos por bueno
        if any(term in text for term in PIVEM_COMPANIES) and "santiago" in text:
            return True

    return False

import re

BLACK_LIST_KEYWORDS = [
    "chile",
    "scl",
    "valparaiso",
    "santiago de chile",
    "carabineros",
    "pesos chilenos",
    "audax",
    "vasco",
    "las américas",
    "las americas",
    "santo domingo este",
    "santo domingo",
    "santiago metro",
    "región metropolitana",
    "región metropolitana",
    "las condes",
    "providencia",
    "san isidro",
    "hainamosa",
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
    "zona franca",
    "mera",
    "vvm",
    "capex",
    "pivem",
    "plazona",
    "médica czfs",
    "medica czfs",
    "villa europa",
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
    if has_blacklist_signal(text):
        return False
    if has_chile_domain(text):
        return False

    if entity_slug:
        if not has_entity_term(text, entity_slug):
            return False
    else:
        if not any(term in text for term in GENERIC_ENTITY_TERMS):
            return False

    if has_dominican_domain(text):
        return True

    if "santiago de los caballeros" in text:
        return True

    if has_dominican_signal(text) and any(term in text for term in GENERIC_ENTITY_TERMS):
        return True

    if entity_slug == "czfs":
        return has_santiago(text) and any(term in text for term in [
            "czfs", "corporación zona franca", "corporacion zona franca", "mera", "vvm", "capex"
        ])

    if entity_slug == "capex-institucion":
        return has_santiago(text) and "capex" in text

    if entity_slug == "pivem":
        return has_santiago(text) and any(term in text for term in ["pivem", "parque industrial"])

    if entity_slug == "plazona":
        return has_santiago(text) and "plazona" in text

    if entity_slug == "medica-czfs":
        return has_santiago(text) and any(term in text for term in ["médica czfs", "medica czfs"])

    return False

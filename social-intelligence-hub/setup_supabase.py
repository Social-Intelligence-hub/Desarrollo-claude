# -*- coding: utf-8 -*-
"""
Script de setup automático para Supabase.
Ejecuta el schema SQL y los datos demo usando la REST API de Supabase.
Uso: python setup_supabase.py
"""

import os
import sys
import json
import urllib.request
import urllib.error
try:
    from dotenv import load_dotenv
    load_dotenv("scraper/.env")
except ImportError:
    pass

# ── Configuración ─────────────────────────────────────────────
# SINCRONIZADO CON frontend/lib/supabase.ts
SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

HEADERS = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# ── Helper: llamada HTTP ──────────────────────────────────────
def request(method, path, data=None):
    url = f"{SUPABASE_URL}{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return e.code, content
    except Exception as ex:
        return 0, str(ex)

# ── Paso 1: Verificar conexión ────────────────────────────────
def test_connection():
    print("\n[Paso 1] Verificando conexion a Supabase...")
    status, data = request("GET", "/rest/v1/")
    if status in (200, 404):  # 404 normal si no hay tablas aún
        print(f"   OK - Conectado (status {status})")
        return True
    print(f"   ERROR - Error de conexion: status {status}")
    print(f"   Detalle: {data}")
    return False

# ── Paso 2: Insertar entidades ────────────────────────────────
def insert_entities():
    print("\n[Paso 2] Insertando entidades...")
    entities = [
        {
            "slug": "czfs",
            "name": "Corporacion Zona Franca Santiago",
            "category": "industrial",
            "keywords": ["czfs", "zona franca", "zona franca santiago", "parque industrial", "pivem", "plazona", "médica", "medica", "corporacion"],
            "anti_keywords": ["ciudad", "parque nacional"],
            "description": "Conglomerado industrial lider en la region norte de Republica Dominicana",
            "active": True,
        },
        {
            "slug": "capex-institucion",
            "name": "CAPEX Institucion Educativa",
            "category": "educacion",
            "keywords": ["capex", "capacitacion", "taller", "curso", "egresado", "egresados", "formacion", "tecnico", "centro capacitacion", "capex santiago"],
            "anti_keywords": ["capital expenditure", "gastos de capital", "inversion de capital", "capex ratio", "financial", "finanzas", "contabilidad"],
            "description": "Centro de Innovacion y Capacitacion Profesional - brazo educativo de CZFS",
            "active": True,
        },
        {
            "slug": "pivem",
            "name": "PIVEM (Parque Industrial)",
            "category": "industrial",
            "keywords": ["pivem", "parque industrial villa europa", "inquilino", "empresa parque", "zona franca"],
            "anti_keywords": [],
            "description": "Parque Industrial Villa Europa Mediterraneo",
            "active": True,
        },
        {
            "slug": "plazona",
            "name": "PlaZona",
            "category": "comercial",
            "keywords": ["plazona", "plaza zona franca", "comercial plazona"],
            "anti_keywords": [],
            "description": "Centro comercial y de servicios del ecosistema CZFS",
            "active": True,
        },
        {
            "slug": "medica-czfs",
            "name": "MEDICA CZFS",
            "category": "comercial",
            "keywords": ["medica czfs", "medica czfs", "clinica zona franca", "clinica zona franca"],
            "anti_keywords": [],
            "description": "Centro de salud del ecosistema CZFS",
            "active": True,
        },
    ]

    # Upsert (insert or ignore if slug exists)
    headers_upsert = dict(HEADERS)
    headers_upsert["Prefer"] = "resolution=ignore-duplicates,return=minimal"
    url = f"{SUPABASE_URL}/rest/v1/entities"
    body = json.dumps(entities).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers_upsert, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"   OK - Entidades insertadas (status {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        print(f"   ERROR - Error {e.code}: {content[:300]}")
        return False

# ── Paso 3: Insertar fuentes ──────────────────────────────────
def insert_sources():
    print("\n[Paso 3] Insertando fuentes...")
    sources = [
        {"slug": "google_reviews", "name": "Google Reviews",    "base_url": "https://maps.google.com",     "active": True},
        {"slug": "reddit",         "name": "Reddit",            "base_url": "https://reddit.com",          "active": True},
        {"slug": "google_alerts",  "name": "Google Alerts RSS", "base_url": "https://google.com/alerts",   "active": True},
        {"slug": "twitter_x",      "name": "X (Twitter)",        "base_url": "https://x.com",              "active": True},
        {"slug": "facebook",       "name": "Facebook",          "base_url": "https://facebook.com",        "active": True},
        {"slug": "news_web",       "name": "Noticias Web",      "base_url": None,                          "active": True},
    ]
    headers_upsert = dict(HEADERS)
    headers_upsert["Prefer"] = "resolution=ignore-duplicates,return=minimal"
    url = f"{SUPABASE_URL}/rest/v1/sources"
    body = json.dumps(sources).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers_upsert, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"   OK - Fuentes insertadas (status {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        print(f"   ERROR - Error {e.code}: {content[:300]}")
        return False

# ── Paso 4: Obtener IDs ───────────────────────────────────────
def get_ids():
    print("\n[Paso 4] Obteniendo IDs de entidades y fuentes...")
    status, entities = request("GET", "/rest/v1/entities?select=id,slug")
    if status != 200 or not isinstance(entities, list):
        print(f"   ERROR - No se pudieron obtener entidades: {entities}")
        return None, None
    status, sources = request("GET", "/rest/v1/sources?select=id,slug")
    if status != 200 or not isinstance(sources, list):
        print(f"   ERROR - No se pudieron obtener fuentes: {sources}")
        return None, None

    entity_map = {e["slug"]: e["id"] for e in entities}
    source_map = {s["slug"]: s["id"] for s in sources}
    print(f"   OK - Entidades: {list(entity_map.keys())}")
    print(f"   OK - Fuentes:   {list(source_map.keys())}")
    return entity_map, source_map

# ── Paso 5: Insertar menciones demo ──────────────────────────
def insert_mentions(entity_map, source_map):
    print("\n[Paso 5] Insertando menciones de demostracion...")
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    def ago(days): return (now - timedelta(days=days)).isoformat()

    czfs   = entity_map.get("czfs")
    capex  = entity_map.get("capex-institucion")
    gr     = source_map.get("google_reviews")
    reddit = source_map.get("reddit")

    if not czfs or not capex or not gr or not reddit:
        print("   ERROR - No se encontraron todos los IDs necesarios")
        return False

    import hashlib
    def md5(s): return hashlib.md5(s.encode()).hexdigest()

    # Todos los objetos deben tener las mismas llaves para el bulk insert de Supabase
    mentions = [
        {
            "entity_id": czfs, "source_id": gr,
            "text_original": "Excelente parque industrial. Las instalaciones estan en perfectas condiciones y el personal de seguridad es muy profesional. Definitivamente un referente en la region norte.",
            "author_name": "Carlos Rodriguez",
            "source_url": "https://maps.google.com/?cid=123456789",
            "sentiment_label": "positive",
            "sentiment_score": {"positive": 0.92, "negative": 0.03, "neutral": 0.05},
            "confidence_score": 0.92, "star_rating": 5,
            "published_at": ago(2), "language": "es",
            "dominican_override": False,
            "content_hash": md5("google_reviews_czfs_001"),
        },
        {
            "entity_id": czfs, "source_id": gr,
            "text_original": "Jevi el servicio aqui. Llegue a buscar informacion y me atendieron de primera. Todo esta muy bien organizado.",
            "author_name": "Maria Sanchez",
            "source_url": "https://maps.google.com/?cid=123456790",
            "sentiment_label": "positive",
            "sentiment_score": {"positive": 0.88, "negative": 0.05, "neutral": 0.07},
            "confidence_score": 0.88, "star_rating": 5,
            "published_at": ago(5), "language": "es",
            "dominican_override": True,
            "content_hash": md5("google_reviews_czfs_002"),
        },
        {
            "entity_id": czfs, "source_id": gr,
            "text_original": "El parqueo esta en olla. No hay suficiente espacio y el acceso vehicular es un caos todas las maanas.",
            "author_name": "Juan Perez",
            "source_url": "https://maps.google.com/?cid=123456791",
            "sentiment_label": "negative",
            "sentiment_score": {"positive": 0.05, "negative": 0.88, "neutral": 0.07},
            "confidence_score": 0.88, "star_rating": 2,
            "published_at": ago(1), "language": "es",
            "dominican_override": True,
            "content_hash": md5("google_reviews_czfs_003"),
        },
        {
            "entity_id": czfs, "source_id": gr,
            "text_original": "Pesima atencion al cliente en la recepcion. Estuve esperando mas de una hora sin que nadie me atendiera. Dando carpeta con el servicio.",
            "author_name": "Ana Gomez",
            "source_url": "https://maps.google.com/?cid=123456792",
            "sentiment_label": "negative",
            "sentiment_score": {"positive": 0.04, "negative": 0.91, "neutral": 0.05},
            "confidence_score": 0.91, "star_rating": 1,
            "published_at": ago(3), "language": "es",
            "dominican_override": True,
            "content_hash": md5("google_reviews_czfs_004"),
        },
        {
            "entity_id": capex, "source_id": reddit,
            "text_original": "Acabo de terminar el curso de mecatronica en CAPEX Santiago y quede impresionado. Los instructores son profesionales con experiencia real en la industria. Los egresados tienen alta empleabilidad.",
            "author_name": "tecnico_rd",
            "source_url": "https://reddit.com/r/Dominican/comments/abc123",
            "sentiment_label": "positive",
            "sentiment_score": {"positive": 0.95, "negative": 0.02, "neutral": 0.03},
            "confidence_score": 0.95, "star_rating": None,
            "published_at": ago(4), "language": "es",
            "dominican_override": False,
            "content_hash": md5("reddit_capex_001"),
        },
        {
            "entity_id": capex, "source_id": reddit,
            "text_original": "El taller de soldadura en CAPEX es nitido. Aprendi mas en 3 meses que en un ao de teoria. Vale cada peso.",
            "author_name": "soldador_cibao",
            "source_url": "https://reddit.com/r/Dominican/comments/abc124",
            "sentiment_label": "positive",
            "sentiment_score": {"positive": 0.91, "negative": 0.03, "neutral": 0.06},
            "confidence_score": 0.91, "star_rating": None,
            "published_at": ago(7), "language": "es",
            "dominican_override": True,
            "content_hash": md5("reddit_capex_002"),
        },
        {
            "entity_id": capex, "source_id": gr,
            "text_original": "Los horarios son muy inflexibles para quienes trabajamos. Necesitan ofrecer mas opciones nocturnas para los cursos de tecnologia.",
            "author_name": "trabajador_norte",
            "source_url": "https://maps.google.com/?cid=123456793",
            "sentiment_label": "negative",
            "sentiment_score": {"positive": 0.10, "negative": 0.75, "neutral": 0.15},
            "confidence_score": 0.75, "star_rating": 3,
            "published_at": ago(6), "language": "es",
            "dominican_override": False,
            "content_hash": md5("google_reviews_capex_001"),
        },
        {
            "entity_id": czfs, "source_id": reddit,
            "text_original": "Alguien sabe los horarios de atencion de la Corporacion Zona Franca Santiago? Necesito ir a consultar sobre el proceso para instalar una empresa.",
            "author_name": "emprendedor_stgo",
            "source_url": "https://reddit.com/r/Dominican/comments/abc125",
            "sentiment_label": "neutral",
            "sentiment_score": {"positive": 0.15, "negative": 0.10, "neutral": 0.75},
            "confidence_score": 0.75, "star_rating": None,
            "published_at": ago(8), "language": "es",
            "dominican_override": False,
            "content_hash": md5("reddit_czfs_001"),
        },
        {
            "entity_id": capex, "source_id": reddit,
            "text_original": "CAPEX lanzo nuevos cursos de inteligencia artificial para el 2026. Alguien tiene mas informacion sobre los requisitos de admision?",
            "author_name": "futuro_tecnico",
            "source_url": "https://reddit.com/r/Dominican/comments/abc126",
            "sentiment_label": "neutral",
            "sentiment_score": {"positive": 0.20, "negative": 0.05, "neutral": 0.75},
            "confidence_score": 0.75, "star_rating": None,
            "published_at": ago(10), "language": "es",
            "dominican_override": False,
            "content_hash": md5("reddit_capex_003"),
        },
    ]

    headers_upsert = dict(HEADERS)
    headers_upsert["Prefer"] = "resolution=ignore-duplicates,return=minimal"
    url = f"{SUPABASE_URL}/rest/v1/mentions"
    body = json.dumps(mentions).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers_upsert, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"   OK - {len(mentions)} menciones demo insertadas (status {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        print(f"   ERROR - Error {e.code}: {content[:500]}")
        return False

# ── Paso 6: Verificar count final ────────────────────────────
def verify():
    print("\n[Paso 6] Verificando datos en Supabase...")
    status, data = request("GET", "/rest/v1/mentions?select=id&limit=100")
    if status == 200 and isinstance(data, list):
        print(f"   OK - {len(data)} menciones en la base de datos")
    else:
        print(f"   AVISO - No se pudo verificar: {data}")

    status, data = request("GET", "/rest/v1/entities?select=id,name")
    if status == 200 and isinstance(data, list):
        print(f"   OK - {len(data)} entidades encontradas")
    
    status, data = request("GET", "/rest/v1/sources?select=id,name")
    if status == 200 and isinstance(data, list):
        print(f"   OK - {len(data)} fuentes encontradas")

# ── Paso 7: Instrucciones finales ─────────────────────────────
def instructions():
    print("\n[Paso 7] Instrucciones finales")
    print("   La anon key solo esta disponible en el dashboard de Supabase.")
    print("   Copiala desde Settings -> API -> 'anon public' y pegala en .env.local")

# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Social Intelligence Hub - Setup de Supabase")
    print("=" * 60)

    if not test_connection():
        print("\nERROR: No se pudo conectar. Verifica que el proyecto existe.")
        sys.exit(1)

    insert_entities()
    insert_sources()

    entity_map, source_map = get_ids()
    if entity_map and source_map:
        insert_mentions(entity_map, source_map)

    verify()
    instructions()

    print("\n" + "=" * 60)
    print("  Setup completado satisfactoriamente.")
    print("=" * 60)

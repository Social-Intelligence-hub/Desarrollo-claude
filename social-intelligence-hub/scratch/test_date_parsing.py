import re
from datetime import datetime, timedelta, timezone

def _parse_relative_date(text: str) -> str:
    """Convierte fechas relativas ('hace 2 semanas') a ISO timestamp."""
    if not text:
        return datetime.now(timezone.utc).isoformat()
        
    text = text.lower()
    now = datetime.now(timezone.utc)
    
    # Extraer número, asume 1 si dice "un", "una" o no hay número
    match = re.search(r'(\d+)', text)
    val = int(match.group(1)) if match else 1
    
    if "un " in text or "una " in text:
        val = 1
        
    if "minuto" in text:
        delta = timedelta(minutes=val)
    elif "hora" in text:
        delta = timedelta(hours=val)
    elif "día" in text or "dia" in text:
        delta = timedelta(days=val)
    elif "semana" in text:
        delta = timedelta(weeks=val)
    elif "mes" in text:
        delta = timedelta(days=val * 30)
    elif "año" in text or "ano" in text:
        delta = timedelta(days=val * 365)
    else:
        # Aquí es donde fallan las fechas absolutas
        delta = timedelta(0)
        
    return (now - delta).isoformat()

tests = [
    "hace un año",
    "hace 3 meses",
    "hace 5 días",
    "hace una semana",
    "hace 2 horas",
    "hace 2 semanas",
    "15 de enero de 2024",  # Esto debería fallar (devolver ahora)
    "20 de mayo de 2023"
]

print(f"Current time: {datetime.now(timezone.utc).isoformat()}\n")
for t in tests:
    print(f"Input: '{t}' -> Output: {_parse_relative_date(t)}")

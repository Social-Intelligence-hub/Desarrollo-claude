import re
from datetime import datetime, timedelta, timezone

def _parse_relative_date(text: str) -> str:
    """Convierte fechas relativas ('hace 2 semanas') o absolutas a ISO timestamp."""
    if not text:
        return datetime.now(timezone.utc).isoformat()
        
    text = text.lower().strip()
    now = datetime.now(timezone.utc)
    
    # 1. Intentar como fecha absoluta (Ej: "15 de enero de 2024")
    months = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }
    
    abs_match = re.search(r'(\d+)\s+de\s+([a-z]+)\s+de\s+(\d{4})', text)
    if abs_match:
        day = int(abs_match.group(1))
        month_name = abs_match.group(2)
        year = int(abs_match.group(3))
        
        month = months.get(month_name)
        if month:
            try:
                dt = datetime(year, month, day, tzinfo=timezone.utc)
                return dt.isoformat()
            except ValueError:
                pass

    # 2. Intentar como fecha relativa ("hace X ...")
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
        delta = timedelta(0)
        
    return (now - delta).isoformat()

tests = [
    "hace un año",
    "hace 3 meses",
    "hace 5 días",
    "hace una semana",
    "hace 2 horas",
    "hace 2 semanas",
    "15 de enero de 2024",
    "20 de mayo de 2023",
    "1 de diciembre de 2022"
]

print(f"Current time: {datetime.now(timezone.utc).isoformat()}\n")
for t in tests:
    print(f"Input: '{t}' -> Output: {_parse_relative_date(t)}")

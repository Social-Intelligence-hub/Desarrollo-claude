# -*- coding: utf-8 -*-
from collectors.relevance_filter import es_relevante_dominicana

test_cases = [
    # --- DEBERÍAN SER RELEVANTES ---
    ("Gran diplomado en CAPEX Santiago sobre gestión de almacenes", "capex-institucion", True),
    ("El PIVEM anuncia nuevas vacantes en Santiago", "pivem", True),
    ("MÉDICA Zona Franca ofrece servicios de laboratorio", "medica-czfs", True),
    ("Grupo M en Santiago impulsa el empleo en el Cibao", "pivem", True),
    ("Hanesbrands Santiago anuncia expansión en PIVEM", "pivem", True),
    ("La Corporación Zona Franca Santiago celebra su aniversario", "czfs", True),
    ("Capacitación técnica en el Cibao por parte de CAPEX", "capex-institucion", True),
    
    # --- DEBERÍAN SER DESCARTADOS (RUIDO) ---
    ("Capex de la empresa minera en Chile aumentó 20%", "capex-institucion", False),
    ("Lionel Messi anotó un gol en el mundial", None, False),
    ("Diego Maradona es recordado en Argentina", None, False),
    ("El estrecho de Ormuz está en tensión", None, False),
    ("Los New York Mets ganaron anoche", None, False),
    ("Junta médica analiza la salud en España", "medica-czfs", False),
    ("Santiago de Chile es una ciudad hermosa", None, False),
    ("Arriendo de departamentos en Santiago SCL", None, False),
]

print("Iniciando pruebas de filtro de relevancia...\n")
success_count = 0
for text, entity, expected in test_cases:
    result = es_relevante_dominicana(text, entity)
    status = "PASS" if result == expected else "FAIL"
    if status == "PASS": success_count += 1
    print(f"[{status}] Entidad: {entity} | Texto: {text[:50]}... | Resultado: {result}")

print(f"\nPruebas completadas: {success_count}/{len(test_cases)} correctas.")

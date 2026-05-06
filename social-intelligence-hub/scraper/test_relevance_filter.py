"""
Test suite para validar el filtro de relevancia.
Casos de prueba reales para cada entidad.
"""

import sys
from collectors.relevance_filter import es_relevante_dominicana

# Colores para terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def test_case(text: str, entity_slug: str | None, expected: bool, description: str) -> bool:
    """Ejecuta un caso de prueba y reporta el resultado."""
    result = es_relevante_dominicana(text, entity_slug)
    status = GREEN + "✓ PASS" + RESET if result == expected else RED + "✗ FAIL" + RESET
    
    print(f"\n{status} | {description}")
    print(f"  Text: {text[:100]}...")
    print(f"  Entity: {entity_slug}")
    print(f"  Expected: {expected}, Got: {result}")
    
    return result == expected


def run_tests():
    """Suite de pruebas completa."""
    
    passed = 0
    total = 0
    
    print("\n" + "="*80)
    print("TEST SUITE: Filtro de Relevancia para CZFS/CAPEX/PIVEM")
    print("="*80)
    
    # ─────────────────────────────────────────────────────────────────
    # TESTS: CAPEX (Educación)
    # ─────────────────────────────────────────────────────────────────
    print(f"\n{YELLOW}[CAPEX - Educación]{RESET}")
    
    tests_capex = [
        (
            "CAPEX Santiago ofrece nuevos cursos de capacitación en el 2024 para técnicos dominicanos",
            "capex-institucion",
            True,
            "CAPEX + contexto educativo (cursos, técnicos, dominicana)"
        ),
        (
            "Se inauguran nuevas aulas en CAPEX Centro de Innovación y Capacitación Profesional",
            "capex-institucion",
            True,
            "CAPEX + formación directa"
        ),
        (
            "CAPEX anuncia nuevo diplomado en logística para la zona franca Santiago",
            "capex-institucion",
            True,
            "CAPEX + diplomado + zona franca"
        ),
        (
            "CAPEX en Santiago abrió sus puertas el 2023",
            "capex-institucion",
            False,
            "CAPEX sin contexto educativo (debería rechazarse)"
        ),
        (
            "Capital Expenditure (CAPEX) aumentó un 5% en la región",
            "capex-institucion",
            False,
            "CAPEX financiero (no educativo, debe rechazarse)"
        ),
        (
            "El Infotep brinda talleres de formación en CAPEX para empleados de PIVEM",
            "capex-institucion",
            True,
            "CAPEX + Infotep + formación"
        ),
    ]
    
    for text, entity, expected, desc in tests_capex:
        total += 1
        if test_case(text, entity, expected, desc):
            passed += 1
    
    # ─────────────────────────────────────────────────────────────────
    # TESTS: PIVEM (Parque Industrial)
    # ─────────────────────────────────────────────────────────────────
    print(f"\n{YELLOW}[PIVEM - Parque Industrial]{RESET}")
    
    tests_pivem = [
        (
            "PIVEM Santiago de los Caballeros anuncia nuevas empresas exportadoras",
            "pivem",
            True,
            "PIVEM + Santiago de los Caballeros (contextualización geográfica clara)"
        ),
        (
            "Grupo M amplía sus operaciones en el Parque Industrial Víctor Espaillat Mera",
            "pivem",
            True,
            "Empresa PIVEM (Grupo M) sin mencionar PIVEM explícito pero con ubicación"
        ),
        (
            "PIVEM en Chile anuncia nuevas inversiones",
            "pivem",
            False,
            "PIVEM en Chile (debe rechazarse, no es RD)"
        ),
        (
            "Empleos en PIVEM: se buscan operarios en zona franca Santiago",
            "pivem",
            True,
            "PIVEM + contexto de empleos en zona franca"
        ),
        (
            "Swedish Match invierte en el parque industrial de villa europa",
            "pivem",
            True,
            "Empresa PIVEM (Swedish Match) + villa europa"
        ),
    ]
    
    for text, entity, expected, desc in tests_pivem:
        total += 1
        if test_case(text, entity, expected, desc):
            passed += 1
    
    # ─────────────────────────────────────────────────────────────────
    # TESTS: MÉDICA CZFS
    # ─────────────────────────────────────────────────────────────────
    print(f"\n{YELLOW}[MÉDICA CZFS - Centro de Salud]{RESET}")
    
    tests_medica = [
        (
            "MÉDICA CZFS Santiago amplía sus servicios de atención en zona franca",
            "medica-czfs",
            True,
            "MÉDICA + CZFS + zona franca"
        ),
        (
            "Centro médico CZFS en Santiago de los Caballeros inaugura nuevo laboratorio",
            "medica-czfs",
            True,
            "MÉDICA + CZFS + Santiago de los Caballeros"
        ),
        (
            "Se abre nueva clínica médica en el PIVEM para empleados",
            "medica-czfs",
            True,
            "Clínica médica en PIVEM (contexto institucional CZFS)"
        ),
        (
            "Médicos sin fronteras visita Santiago para campaña de vacunación",
            "medica-czfs",
            False,
            "Médica genérica sin contexto CZFS (debe rechazarse)"
        ),
        (
            "Atención médica privada en la capital Santiago, Chile",
            "medica-czfs",
            False,
            "Médica en Santiago de Chile (debe rechazarse)"
        ),
    ]
    
    for text, entity, expected, desc in tests_medica:
        total += 1
        if test_case(text, entity, expected, desc):
            passed += 1
    
    # ─────────────────────────────────────────────────────────────────
    # TESTS: CZFS General
    # ─────────────────────────────────────────────────────────────────
    print(f"\n{YELLOW}[CZFS - Corporación Zona Franca]{RESET}")
    
    tests_czfs = [
        (
            "La Corporación Zona Franca Santiago continúa atrayendo inversión extranjera",
            "czfs",
            True,
            "CZFS explícita + contexto"
        ),
        (
            "Zona franca Santiago anuncia nueva política de empleo para 2024",
            "czfs",
            True,
            "Zona franca + Santiago"
        ),
        (
            "CZFS en Santiago de los Caballeros genera 15,000 empleos directos",
            "czfs",
            True,
            "CZFS + Santiago de los Caballeros + contexto laboral"
        ),
        (
            "Zona franca Santiago, Chile, actualiza sus normas aduanales",
            "czfs",
            False,
            "Zona franca en Chile (debe rechazarse por dominio .cl o contexto)"
        ),
    ]
    
    for text, entity, expected, desc in tests_czfs:
        total += 1
        if test_case(text, entity, expected, desc):
            passed += 1
    
    # ─────────────────────────────────────────────────────────────────
    # TESTS: Ruido (Deberían rechazarse)
    # ─────────────────────────────────────────────────────────────────
    print(f"\n{YELLOW}[RUIDO - Deberían rechazarse]{RESET}")
    
    tests_noise = [
        (
            "Barcelona vs Real Madrid: Messi anotó dos goles en la Champions League",
            None,
            False,
            "Deportes internacionales (Messi, Champions)"
        ),
        (
            "Santiago de Chile experimenta terremoto de magnitud 6.5. Carabineros activa protocolo",
            None,
            False,
            "Contexto de Chile (Carabineros, región metropolitana)"
        ),
        (
            "Las Condes, Santiago: Transantiago sufre retrasos por congestionamiento vehicular",
            None,
            False,
            "Municipio de Santiago de Chile"
        ),
        (
            "Crisis en Gaza: Israel continúa bombardeos en territorio palestino",
            None,
            False,
            "Noticias internacionales/políticas"
        ),
        (
            "Trump declara nuevas sanciones contra Irán y Rusia",
            None,
            False,
            "Política internacional (Trump, Putin)"
        ),
    ]
    
    for text, entity, expected, desc in tests_noise:
        total += 1
        if test_case(text, entity, expected, desc):
            passed += 1
    
    # ─────────────────────────────────────────────────────────────────
    # TESTS: Casos Límite
    # ─────────────────────────────────────────────────────────────────
    print(f"\n{YELLOW}[CASOS LÍMITE]{RESET}")
    
    tests_edge = [
        (
            "PIVEM abre sucursal en Santiago, Chile",
            "pivem",
            False,
            "Menciona PIVEM pero en contexto de Chile (debe rechazarse)"
        ),
        (
            "Plazona, el nuevo centro comercial de la Zona Franca Santiago en la Dominicana",
            "czfs",
            True,
            "Plazona + RD + zona franca (contexto claro)"
        ),
        (
            "santiago ... dominicana",
            None,
            False,
            "Texto muy corto sin términos positivos"
        ),
        (
            "Excelentes empleos disponibles en PIVEM, parque industrial de villa europa santiago rd",
            "pivem",
            True,
            "PIVEM explícito + villa europa + santiago + rd"
        ),
    ]
    
    for text, entity, expected, desc in tests_edge:
        total += 1
        if test_case(text, entity, expected, desc):
            passed += 1
    
    # ─────────────────────────────────────────────────────────────────
    # REPORTE FINAL
    # ─────────────────────────────────────────────────────────────────
    print("\n" + "="*80)
    percentage = (passed / total * 100) if total > 0 else 0
    
    if passed == total:
        print(f"{GREEN}✓ TODAS LAS PRUEBAS PASARON ({passed}/{total})  {percentage:.0f}%{RESET}")
    elif percentage >= 80:
        print(f"{YELLOW}⚠ MAYORÍA PASARON ({passed}/{total})  {percentage:.0f}%{RESET}")
    else:
        print(f"{RED}✗ MUCHAS FALLAS ({passed}/{total})  {percentage:.0f}%{RESET}")
    
    print("="*80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

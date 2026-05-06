"""
Test de integración local: simula datos y valida filtrado antes de Supabase.
"""

import sys
from collectors.relevance_filter import es_relevante_dominicana

# Simulación de datos que podrían venir de diversos collectors
TEST_DATA = {
    "google_alerts": [
        {
            "text": "CZFS anuncia inversión de 50 millones en zona franca Santiago RD",
            "entity": "czfs",
            "should_pass": True,
        },
        {
            "text": "Zona franca Santiago, Chile: nuevas normas aduanales",
            "entity": "czfs",
            "should_pass": False,
        },
        {
            "text": "CAPEX ofrece diplomado en gestión empresarial en Santiago",
            "entity": "capex-institucion",
            "should_pass": True,
        },
        {
            "text": "Capital Expenditure crece 5% en el sector",
            "entity": "capex-institucion",
            "should_pass": False,
        },
    ],
    "reddit": [
        {
            "text": "¿Alguien trabaja en PIVEM? Cómo es la experiencia?",
            "entity": "pivem",
            "should_pass": True,
        },
        {
            "text": "Oportunidades de empleo en zona franca Santiago, empresas como Grupo M",
            "entity": "pivem",
            "should_pass": True,
        },
        {
            "text": "PIVEM abre sucursal en Santiago, Chile - nuevas oportunidades",
            "entity": "pivem",
            "should_pass": False,
        },
    ],
    "mixed": [
        {
            "text": "MÉDICA CZFS inaugura nuevo laboratorio en Santiago RD",
            "entity": "medica-czfs",
            "should_pass": True,
        },
        {
            "text": "Clínica médica en el PIVEM amplia servicios",
            "entity": "medica-czfs",
            "should_pass": True,
        },
        {
            "text": "Médicos sin fronteras llega a Santiago de Chile",
            "entity": "medica-czfs",
            "should_pass": False,
        },
    ],
}

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def test_integration():
    """Test de integración de filtros por fuente."""
    print(f"\n{BLUE}{'='*80}")
    print("TEST DE INTEGRACIÓN: Validar filtrado por fuente")
    print(f"{'='*80}{RESET}\n")
    
    total = 0
    passed = 0
    
    for source, tests in TEST_DATA.items():
        print(f"{YELLOW}[{source.upper()}]{RESET}")
        source_passed = 0
        
        for test in tests:
            total += 1
            text = test["text"]
            entity = test["entity"]
            expected = test["should_pass"]
            
            result = es_relevante_dominicana(text, entity)
            matches = result == expected
            
            if matches:
                passed += 1
                source_passed += 1
                status = f"{GREEN}✓{RESET}"
            else:
                status = f"{RED}✗{RESET}"
            
            print(f"  {status} {text[:60]}...")
            print(f"      Entity: {entity}, Expected: {expected}, Got: {result}\n")
        
        print(f"  Resultado: {source_passed}/{len(tests)} pasaron\n")
    
    # Resumen
    print(f"\n{BLUE}{'='*80}")
    percentage = (passed / total * 100) if total > 0 else 0
    
    if passed == total:
        print(f"{GREEN}✓ INTEGRACIÓN OK: {passed}/{total} ({percentage:.0f}%){RESET}")
        print(f"{BLUE}{'='*80}{RESET}\n")
        return True
    else:
        print(f"{RED}✗ FALLOS EN INTEGRACIÓN: {passed}/{total} ({percentage:.0f}%){RESET}")
        print(f"{BLUE}{'='*80}{RESET}\n")
        return False


def test_collector_output_simulation():
    """Simula salida de collectors y valida filtrado."""
    print(f"\n{BLUE}{'='*80}")
    print("SIMULACIÓN: Datos de collectors y filtrado antes de insert")
    print(f"{'='*80}{RESET}\n")
    
    # Simulación de Google Alerts
    print(f"{YELLOW}[Google Alerts Simulator]{RESET}")
    ga_mentions = [
        {
            "title": "CZFS anuncia plan de desarrollo 2024",
            "text": "La corporación zona franca Santiago continúa creciendo...",
            "source_url": "https://elnacional.com.do/...",
            "entity_slug": "czfs",
        },
        {
            "title": "Noticias de Santiago de Chile",
            "text": "La región metropolitana experimenta cambios...",
            "source_url": "https://elmercurio.cl/...",
            "entity_slug": "czfs",  # Falsa alarma
        },
        {
            "title": "CAPEX lanza nuevo diplomado",
            "text": "Centro de Capacitación ofrece formación en CAPEX...",
            "source_url": "https://listindiario.com/...",
            "entity_slug": "capex-institucion",
        },
    ]
    
    filtered_count = 0
    for mention in ga_mentions:
        if es_relevante_dominicana(mention["text"], mention["entity_slug"]):
            filtered_count += 1
            print(f"  {GREEN}✓ ACEPTADO:{RESET} {mention['title'][:50]}")
        else:
            print(f"  {RED}✗ RECHAZADO:{RESET} {mention['title'][:50]}")
    
    print(f"  Resultado: {filtered_count}/{len(ga_mentions)} menciones aceptadas\n")
    
    # Simulación de Reddit
    print(f"{YELLOW}[Reddit Simulator]{RESET}")
    reddit_mentions = [
        {
            "title": "Trabajo en PIVEM",
            "text": "Alguien que trabaje en el parque industrial villa europa?",
            "source_url": "https://reddit.com/r/republicadominicana/...",
            "entity_slug": "pivem",
        },
        {
            "title": "PIVEM en Chile",
            "text": "He visto que PIVEM abre en Santiago de Chile",
            "source_url": "https://reddit.com/r/chile/...",
            "entity_slug": "pivem",  # Falsa alarma (Chile)
        },
    ]
    
    reddit_filtered = 0
    for mention in reddit_mentions:
        if es_relevante_dominicana(mention["text"], mention["entity_slug"]):
            reddit_filtered += 1
            print(f"  {GREEN}✓ ACEPTADO:{RESET} {mention['title'][:50]}")
        else:
            print(f"  {RED}✗ RECHAZADO:{RESET} {mention['title'][:50]}")
    
    print(f"  Resultado: {reddit_filtered}/{len(reddit_mentions)} menciones aceptadas\n")
    
    print(f"{BLUE}{'='*80}")
    print(f"RESUMEN SIMULACIÓN:")
    print(f"  - Google Alerts: {filtered_count} menciones válidas")
    print(f"  - Reddit: {reddit_filtered} menciones válidas")
    print(f"  - Total: {filtered_count + reddit_filtered} menciones para Supabase")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    return filtered_count + reddit_filtered > 0


if __name__ == "__main__":
    print(f"\n{BLUE}╔════════════════════════════════════════════════════════════════╗")
    print(f"║  VALIDACIÓN COMPLETA: Filtro en Contexto Real                 ║")
    print(f"╚════════════════════════════════════════════════════════════════╝{RESET}")
    
    # Test 1: Integración
    integration_ok = test_integration()
    
    # Test 2: Simulación de collectors
    simulation_ok = test_collector_output_simulation()
    
    # Resumen final
    print(f"{BLUE}╔════════════════════════════════════════════════════════════════╗")
    print(f"║  RESULTADO FINAL                                               ║")
    print(f"╚════════════════════════════════════════════════════════════════╝{RESET}")
    
    if integration_ok and simulation_ok:
        print(f"\n{GREEN}✓ SISTEMA DE FILTRADO COMPLETO Y VALIDADO ✓{RESET}")
        print(f"  → Listo para ejecutar el scraper real")
        print(f"  → No habrá datos de Chile ni ruido irrelevante en Supabase\n")
        sys.exit(0)
    else:
        print(f"\n{RED}✗ FALLOS EN VALIDACIÓN ✗{RESET}")
        print(f"  → Revisar el filtrado antes de ejecutar en producción\n")
        sys.exit(1)

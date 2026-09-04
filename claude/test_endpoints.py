"""
Test Script - Valida que todos los endpoints funcionan
========================================================

Ejecuta este script DESPUÉS de que app.py esté corriendo en otro terminal.

Uso:
    python claude/test_endpoints.py

Requisitos:
    - app.py ejecutándose en http://127.0.0.1:5000
    - requests instalado (pip install requests)
"""

import requests
import json
from colorama import Fore, Style, init

init(autoreset=True)

BASE_URL = "http://127.0.0.1:5000"

# Estilos de colores
SUCCESS = Fore.GREEN
ERROR = Fore.RED
INFO = Fore.BLUE
WARNING = Fore.YELLOW


def print_header(title):
    """Imprime encabezado de test"""
    print(f"\n{'='*70}")
    print(f"{INFO}🧪 {title}")
    print(f"{'='*70}")


def print_test(test_name, passed, response=None, error=None):
    """Imprime resultado de un test"""
    if passed:
        print(f"{SUCCESS}✓ PASSED{Style.RESET_ALL} — {test_name}")
        if response:
            print(f"  Response: {json.dumps(response, indent=2)[:200]}...")
    else:
        print(f"{ERROR}✗ FAILED{Style.RESET_ALL} — {test_name}")
        if error:
            print(f"  Error: {error}")


def test_health():
    """Test 1: Verificar que servidor está activo"""
    print_header("TEST 1: Health Check")

    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()

        passed = response.status_code == 200
        print_test("Server is running", passed, data)

        if passed:
            print(f"\n  📊 Datos cargados:")
            for key, value in data.get('data_loaded', {}).items():
                print(f"     • {key}: {value}")

        return passed
    except Exception as e:
        print_test("Server is running", False, error=str(e))
        return False


def test_parse_cv():
    """Test 2: Parse CV"""
    print_header("TEST 2: Parse CV (Simula extracción de datos)")

    try:
        payload = {
            "cv_id": "USER_001"
        }
        response = requests.post(f"{BASE_URL}/api/parse-cv", json=payload)
        data = response.json()

        passed = response.status_code == 200 and 'ocupacion_actual' in data
        print_test("Parse CV endpoint", passed, data)

        if passed:
            print(f"\n  Datos extraídos del CV:")
            print(f"     • Nombre: {data.get('nombre')}")
            print(f"     • Ocupación actual: {data.get('ocupacion_actual')}")
            print(f"     • Skills: {', '.join(data.get('skills_identificadas', [])[:3])}...")
            print(f"     • Experiencia: {data.get('experiencia_años')} años")
            print(f"     • Salario actual: ${data.get('salario_actual_usd')}")

        return passed, data
    except Exception as e:
        print_test("Parse CV endpoint", False, error=str(e))
        return False, None


def test_matching(ocupacion_actual, skills_actuales):
    """Test 3: Matching - Encontrar ocupaciones objetivo"""
    print_header("TEST 3: Matching - Ocupaciones objetivo + Cursos")

    try:
        payload = {
            "ocupacion_actual": ocupacion_actual,
            "skills_actuales": skills_actuales
        }
        response = requests.post(f"{BASE_URL}/api/matching", json=payload)
        data = response.json()

        passed = response.status_code == 200 and 'ocupaciones_objetivo' in data
        print_test("Matching endpoint", passed)

        if passed:
            ocupaciones = data.get('ocupaciones_objetivo', [])
            print(f"\n  ✓ Encontradas {len(ocupaciones)} ocupaciones posibles")
            print(f"  ✓ Total posibilidades: {data.get('total_posibilidades')}")

            print(f"\n  🏆 TOP 3 OCUPACIONES OBJETIVO:")
            for i, ocu in enumerate(ocupaciones[:3], 1):
                print(f"\n     {i}. {ocu['ocupacion_objetivo']}")
                print(f"        Dificultad: {ocu['difficulty_score']}%")
                print(f"        Skills faltantes: {len(ocu['skills_faltantes'])} ({', '.join(ocu['skills_faltantes'][:2])}...)")
                print(f"        Cursos recomendados: {len(ocu['cursos_recomendados'])}")
                if ocu['cursos_recomendados']:
                    print(f"          • {ocu['cursos_recomendados'][0]['nombre']} ({ocu['cursos_recomendados'][0]['duracion_horas']}h)")

        return passed, data
    except Exception as e:
        print_test("Matching endpoint", False, error=str(e))
        return False, None


def test_wellness():
    """Test 4: Wellness - Apoyo emocional"""
    print_header("TEST 4: Wellness - Apoyo emocional + Cohorts")

    try:
        payload = {
            "stress_level": 8,
            "confidence_level": 4,
            "ocupacion_objetivo": "Data Analyst"
        }
        response = requests.post(f"{BASE_URL}/api/wellness", json=payload)
        data = response.json()

        passed = response.status_code == 200 and 'mensaje' in data
        print_test("Wellness endpoint", passed)

        if passed:
            print(f"\n  Estado emocional:")
            print(f"     • Estrés: {data.get('stress_level')}/10")
            print(f"     • Confianza: {data.get('confidence_level')}/10")
            print(f"     • Categoría: {data.get('wellness_category')}")

            print(f"\n  💬 Mensaje de bienestar:")
            print(f"     \"{data.get('mensaje')}\"")

            print(f"\n  ✅ Acción sugerida:")
            print(f"     {data.get('accion_sugerida')}")

            cohort = data.get('cohort_recommendation')
            if cohort:
                print(f"\n  👥 Cohort recomendado:")
                print(f"     • {cohort.get('nombre')}")
                print(f"     • Ubicación: {cohort.get('ubicacion')}")
                print(f"     • Tasa de finalización: {cohort.get('tasa_finalizacion')*100:.0f}%")
                print(f"     • Próxima fecha: {cohort.get('proximidad_fecha')}")

        return passed, data
    except Exception as e:
        print_test("Wellness endpoint", False, error=str(e))
        return False, None


def test_cursos():
    """Test 5: Catálogo de cursos"""
    print_header("TEST 5: Catálogo de cursos")

    try:
        response = requests.get(f"{BASE_URL}/api/cursos")
        data = response.json()

        passed = response.status_code == 200 and 'cursos' in data
        print_test("Cursos endpoint", passed)

        if passed:
            total = data.get('total_cursos', 0)
            print(f"\n  Total cursos disponibles: {total}")

            cursos = data.get('cursos', [])[:3]
            print(f"\n  📚 Primeros 3 cursos:")
            for i, curso in enumerate(cursos, 1):
                print(f"\n     {i}. {curso['nombre']}")
                print(f"        Duración: {curso['duracion_horas']}h")
                print(f"        Dificultad: {curso['dificultad']}")
                print(f"        Certificación: {'Sí' if curso['certificacion'] else 'No'}")
                print(f"        Skills: {', '.join(curso['skills'][:2])}")

        return passed, data
    except Exception as e:
        print_test("Cursos endpoint", False, error=str(e))
        return False, None


def test_ocupaciones():
    """Test 6: Lista de ocupaciones"""
    print_header("TEST 6: Lista de ocupaciones disponibles")

    try:
        response = requests.get(f"{BASE_URL}/api/ocupaciones")
        data = response.json()

        passed = response.status_code == 200 and 'ocupaciones' in data
        print_test("Ocupaciones endpoint", passed)

        if passed:
            total = data.get('total_ocupaciones', 0)
            print(f"\n  Total ocupaciones en el sistema: {total}")

            ocupaciones = data.get('ocupaciones', [])[:5]
            print(f"\n  💼 Primeras 5 ocupaciones:")
            for i, ocu in enumerate(ocupaciones, 1):
                skills_count = len(ocu['skills_requeridos'])
                print(f"     {i}. {ocu['nombre']} ({skills_count} skills requeridos)")

        return passed, data
    except Exception as e:
        print_test("Ocupaciones endpoint", False, error=str(e))
        return False, None


def test_cohorts():
    """Test 7: Cohorts de peer support"""
    print_header("TEST 7: Cohorts de peer support")

    try:
        response = requests.get(f"{BASE_URL}/api/cohorts")
        data = response.json()

        passed = response.status_code == 200 and 'cohorts' in data
        print_test("Cohorts endpoint", passed)

        if passed:
            total = data.get('total_cohorts', 0)
            print(f"\n  Total cohorts disponibles: {total}")

            cohorts = data.get('cohorts', [])[:3]
            print(f"\n  👥 Primeros 3 cohorts:")
            for i, cohort in enumerate(cohorts, 1):
                print(f"\n     {i}. {cohort['nombre']}")
                print(f"        Ubicación: {cohort['ubicacion']}")
                print(f"        Tamaño: {cohort['tamaño_actual']}/{cohort['tamaño_maximo']}")
                print(f"        Tasa finalización: {cohort['tasa_finalizacion']*100:.0f}%")

        return passed, data
    except Exception as e:
        print_test("Cohorts endpoint", False, error=str(e))
        return False, None


def test_full_flow():
    """Test 8: Flujo completo (CV → Matching → Wellness)"""
    print_header("TEST 8: Flujo completo de usuario")

    print(f"{INFO}Simulando: Usuario sube CV → obtiene recomendaciones → ve bienestar{Style.RESET_ALL}")

    # Paso 1: Parse CV
    print(f"\n  Paso 1: Extrayendo datos del CV...")
    parse_ok, cv_data = test_parse_cv()
    if not parse_ok or not cv_data:
        print(f"{ERROR}✗ No se pudo extraer CV{Style.RESET_ALL}")
        return False

    ocupacion_actual = cv_data.get('ocupacion_actual')
    skills = cv_data.get('skills_identificadas', [])

    # Paso 2: Matching
    print(f"\n  Paso 2: Buscando ocupaciones objetivo...")
    matching_ok, matching_data = test_matching(ocupacion_actual, skills)
    if not matching_ok:
        print(f"{ERROR}✗ No se pudo calcular matching{Style.RESET_ALL}")
        return False

    ocupacion_objetivo = matching_data['ocupaciones_objetivo'][0]['ocupacion_objetivo'] if matching_data.get('ocupaciones_objetivo') else "Data Analyst"

    # Paso 3: Wellness
    print(f"\n  Paso 3: Obteniendo apoyo emocional...")
    wellness_ok, wellness_data = test_wellness()
    if not wellness_ok:
        print(f"{ERROR}✗ No se pudo obtener wellness{Style.RESET_ALL}")
        return False

    print(f"\n{SUCCESS}✓ FLUJO COMPLETO EXITOSO{Style.RESET_ALL}")
    return True


def main():
    """Ejecuta todos los tests"""
    print(f"\n{INFO}{'='*70}")
    print(f"TRANSITION RADAR - TEST SUITE")
    print(f"{'='*70}{Style.RESET_ALL}")

    results = {}

    # Test 1: Health
    results['health'] = test_health()
    if not results['health']:
        print(f"\n{ERROR}⚠️  SERVIDOR NO ESTÁ ACTIVO{Style.RESET_ALL}")
        print(f"{WARNING}Asegúrate de ejecutar: python claude/app.py{Style.RESET_ALL}")
        return

    # Test 2-7: Endpoints individuales
    test_parse_ok, cv_data = test_parse_cv()
    results['parse_cv'] = test_parse_ok

    if test_parse_ok and cv_data:
        ocupacion = cv_data.get('ocupacion_actual')
        skills = cv_data.get('skills_identificadas', [])

        test_matching_ok, _ = test_matching(ocupacion, skills)
        results['matching'] = test_matching_ok

    results['wellness'] = test_wellness()[0]
    results['cursos'] = test_cursos()[0]
    results['ocupaciones'] = test_ocupaciones()[0]
    results['cohorts'] = test_cohorts()[0]

    # Test 8: Flujo completo
    results['full_flow'] = test_full_flow()

    # Resumen
    print(f"\n\n{'='*70}")
    print(f"{INFO}📊 RESUMEN DE TESTS{Style.RESET_ALL}")
    print(f"{'='*70}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{SUCCESS}✓ PASS{Style.RESET_ALL}" if result else f"{ERROR}✗ FAIL{Style.RESET_ALL}"
        print(f"{status} — {test_name}")

    print(f"\n{INFO}Total: {passed}/{total} tests pasados{Style.RESET_ALL}")

    if passed == total:
        print(f"\n{SUCCESS}🎉 TODOS LOS TESTS PASARON - BACKEND FUNCIONA CORRECTAMENTE{Style.RESET_ALL}")
    else:
        print(f"\n{ERROR}⚠️  {total - passed} tests fallaron - revisa los errores arriba{Style.RESET_ALL}")

    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()

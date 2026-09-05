"""
Matching Module - Funciones de lógica de transición de carrera
================================================================

Este módulo contiene las funciones auxiliares para:
1. Calcular similitud entre skills
2. Generar embeddings (preparado para Gemini API)
3. Ranking de ocupaciones objetivo
4. Cálculo de "difficulty score"

Nota: La lógica de matching está integrada en app.py.
Este módulo puede extenderse para usar embeddings con Gemini en el futuro.
"""

from typing import List, Dict, Set, Tuple
import json

import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class SkillMatcher:
    """
    Clase para manejar lógica de matching de skills.

    Proporciona métodos para:
    - Calcular overlap entre sets de skills
    - Generar scores de dificultad
    - Crear rankings de transiciones
    """

    def __init__(self, skills_mapping: Dict[str, List[str]]):
        """
        Inicializa el matcher con un mapeo de ocupaciones a skills.

        Args:
            skills_mapping: Dict donde key=ocupación, value=lista de skills

        Ejemplo:
            skills_mapping = {
                "Data Analyst": ["SQL", "Python", "Excel"],
                "Sales Manager": ["Leadership", "Communication", "Excel"]
            }
        """
        self.skills_mapping = skills_mapping
        self.ocupaciones = list(skills_mapping.keys())

    def calcular_overlap(self,
                        skills_actuales: List[str],
                        skills_objetivo: List[str]) -> Dict[str, any]:
        """
        Calcula el overlap entre skills actuales y objetivo.

        Args:
            skills_actuales: Lista de skills que ya tiene el usuario
            skills_objetivo: Lista de skills requeridos para la ocupación objetivo

        Returns:
            Dict con:
                - skills_comunes: skills que ya tiene
                - skills_faltantes: skills que necesita aprender
                - num_comunes: cantidad de skills comunes
                - num_faltantes: cantidad de skills a aprender

        Ejemplo:
            >>> matcher = SkillMatcher(...)
            >>> result = matcher.calcular_overlap(
            ...     ["Communication", "Sales"],
            ...     ["Communication", "Leadership", "Excel"]
            ... )
            >>> result['skills_faltantes']
            ["Leadership", "Excel"]
        """
        set_actual = set(skills_actuales)
        set_objetivo = set(skills_objetivo)

        skills_comunes = set_actual & set_objetivo
        skills_faltantes = set_objetivo - set_actual

        return {
            'skills_comunes': list(skills_comunes),
            'skills_faltantes': list(skills_faltantes),
            'num_comunes': len(skills_comunes),
            'num_faltantes': len(skills_faltantes),
            'total_requeridos': len(set_objetivo)
        }

    def calcular_difficulty_score(self,
                                 skills_actuales: List[str],
                                 skills_objetivo: List[str]) -> float:
        """
        Calcula score de dificultad de transición (0-100).

        Fórmula: (skills_faltantes / skills_totales) * 100

        Args:
            skills_actuales: Skills que ya tiene
            skills_objetivo: Skills requeridos para ocupación objetivo

        Returns:
            float entre 0-100:
                - 0: ya tiene todos los skills (transición fácil)
                - 100: no tiene ninguno (transición difícil)
                - 50: tiene la mitad

        Ejemplo:
            >>> matcher.calcular_difficulty_score(
            ...     ["Communication", "Sales"],
            ...     ["Communication", "Leadership", "Excel"]
            ... )
            66.67  # faltantes 2, totales 3 = 2/3 * 100
        """
        overlap = self.calcular_overlap(skills_actuales, skills_objetivo)

        if overlap['total_requeridos'] == 0:
            return 0.0

        difficulty = (overlap['num_faltantes'] / overlap['total_requeridos']) * 100
        return round(difficulty, 2)

    def rankear_transiciones(self,
                            ocupacion_actual: str,
                            skills_actuales: List[str] = None,
                            top_n: int = 5) -> List[Dict]:
        """
        Ranquea todas las ocupaciones objetivo por dificultad.

        Args:
            ocupacion_actual: Ocupación del usuario ahora
            skills_actuales: Lista de skills actuales (si no, usa los de ocupación actual)
            top_n: Número de ocupaciones a devolver (default: 5)

        Returns:
            Lista ordenada de dicts con estructura:
            {
                'ocupacion_objetivo': str,
                'difficulty_score': float (0-100),
                'skills_faltantes': List[str],
                'num_skills_faltantes': int
            }

        Ejemplo:
            >>> ranking = matcher.rankear_transiciones(
            ...     "Retail Sales Associate",
            ...     top_n=3
            ... )
            >>> ranking[0]
            {
                'ocupacion_objetivo': 'Customer Service Manager',
                'difficulty_score': 25.0,
                'skills_faltantes': ['Management', 'Excel'],
                'num_skills_faltantes': 2
            }
        """
        # Si no especifica skills, usar los de la ocupación actual
        if skills_actuales is None:
            if ocupacion_actual not in self.skills_mapping:
                raise ValueError(f"Ocupación '{ocupacion_actual}' no encontrada")
            skills_actuales = self.skills_mapping[ocupacion_actual]

        resultados = []

        for ocu_objetivo, skills_req in self.skills_mapping.items():
            # No considerar la misma ocupación
            if ocu_objetivo == ocupacion_actual:
                continue

            overlap = self.calcular_overlap(skills_actuales, skills_req)
            difficulty = self.calcular_difficulty_score(skills_actuales, skills_req)

            resultados.append({
                'ocupacion_objetivo': ocu_objetivo,
                'difficulty_score': difficulty,
                'skills_faltantes': overlap['skills_faltantes'],
                'skills_comunes': overlap['skills_comunes'],
                'num_skills_faltantes': overlap['num_faltantes'],
                'num_skills_comunes': overlap['num_comunes']
            })

        # Ordenar por difficulty (menor primero = más fácil)
        resultados_ordenados = sorted(resultados, key=lambda x: x['difficulty_score'])

        return resultados_ordenados[:top_n]

    def sugerir_camino_aprendizaje(self,
                                  ocupacion_actual: str,
                                  ocupacion_objetivo: str,
                                  skills_actuales: List[str] = None) -> Dict:
        """
        Genera un "learning path" sugerido entre dos ocupaciones.

        Args:
            ocupacion_actual: Ocupación de inicio
            ocupacion_objetivo: Ocupación destino
            skills_actuales: Skills del usuario (si no, usa los de ocu_actual)

        Returns:
            Dict con:
                - difficulty_score: qué tan difícil es la transición
                - skills_faltantes: qué debe aprender
                - skills_comunes: qué ya tiene útil
                - pasos_sugeridos: orden en que aprender (futura feature)

        Ejemplo:
            >>> path = matcher.sugerir_camino_aprendizaje(
            ...     "Retail Sales",
            ...     "Sales Manager"
            ... )
        """

        if skills_actuales is None:
            skills_actuales = self.skills_mapping.get(ocupacion_actual, [])

        skills_objetivo = self.skills_mapping.get(ocupacion_objetivo, [])

        if not skills_objetivo:
            raise ValueError(f"Ocupación '{ocupacion_objetivo}' no encontrada")

        overlap = self.calcular_overlap(skills_actuales, skills_objetivo)
        difficulty = self.calcular_difficulty_score(skills_actuales, skills_objetivo)

        return {
            'ocupacion_actual': ocupacion_actual,
            'ocupacion_objetivo': ocupacion_objetivo,
            'difficulty_score': difficulty,
            'skills_comunes': overlap['skills_comunes'],
            'skills_faltantes': overlap['skills_faltantes'],
            'num_skills_a_aprender': overlap['num_faltantes'],
            'estimado_meses': self._estimar_duracion(overlap['num_faltantes']),
            'evaluacion': self._evaluar_viabilidad(difficulty)
        }

    def _estimar_duracion(self, num_skills: int) -> str:
        """
        Estima duración aproximada del aprendizaje en meses.
        Heurística: ~1-2 meses por skill.
        """
        if num_skills == 0:
            return "0 (ya tienes los skills)"
        elif num_skills <= 2:
            return "1-2 meses"
        elif num_skills <= 5:
            return "2-4 meses"
        else:
            return "4-8 meses"

    def _evaluar_viabilidad(self, difficulty_score: float) -> str:
        """Categoriza la viabilidad de la transición"""
        if difficulty_score < 25:
            return "Muy viable - ya tienes la mayoría de skills"
        elif difficulty_score < 50:
            return "Viable - necesitas aprender algunos skills"
        elif difficulty_score < 75:
            return "Desafiante - requiere aprendizaje significativo"
        else:
            return "Muy desafiante - transición importante, requiere dedicación"


# ============================================================================
# FUNCIONES AUXILIARES (preparadas para Gemini API en el futuro)
# ============================================================================

def generar_embedding(texto: str) -> List[float]:
    """
    Genera un embedding real con la API de Gemini (text-embedding-004).
    Si no hay API key configurada, cae a un vector dummy (para no romper
    el resto del pipeline en desarrollo local sin key).
    """
    if not GEMINI_API_KEY:
        print("[matching] GEMINI_API_KEY no configurada, usando embedding dummy.")
        return [0.0] * 768

    try:
        resultado = genai.embed_content(
            model="models/text-embedding-004",
            content=texto,
            task_type="semantic_similarity"
        )
        return resultado["embedding"]
    except Exception as e:
        print(f"[matching] Error generando embedding con Gemini: {e}")
        return [0.0] * 768


def matching_semantico(puesto_texto: str, candidatos: List[Dict], top_n: int = 5) -> List[Dict]:
    """
    Dado el texto libre de un puesto y una lista de candidatos (cada uno con
    su texto de perfil/CV), rankea los más similares usando embeddings de Gemini.

    candidatos: [{"candidato_id": ..., "texto_perfil": "..."}, ...]
    """
    embedding_puesto = generar_embedding(puesto_texto)

    resultados = []
    for candidato in candidatos:
        embedding_candidato = generar_embedding(candidato["texto_perfil"])
        score = similaridad_coseno(embedding_puesto, embedding_candidato)
        resultados.append({
            "candidato_id": candidato["candidato_id"],
            "similitud": round(score, 4)
        })

    return sorted(resultados, key=lambda r: r["similitud"], reverse=True)[:top_n]

def similaridad_coseno(vec1: List[float], vec2: List[float]) -> float:
    """
    Calcula similaridad coseno entre dos vectores.

    Usado en el futuro cuando tengamos embeddings reales.

    Args:
        vec1: Vector 1 (embedding)
        vec2: Vector 2 (embedding)

    Returns:
        float entre 0-1 (1 = muy similar, 0 = no similar)
    """
    from math import sqrt

    # Producto punto
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Normas
    norm1 = sqrt(sum(a * a for a in vec1))
    norm2 = sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == '__main__':
    # Cargar skills mapping
    with open('data/skills_por_ocupacion.json') as f:
        skills_data = json.load(f)

    skills_mapping = skills_data['skills_mapping']

    # Crear matcher
    matcher = SkillMatcher(skills_mapping)

    # Ejemplo 1: Rankear transiciones desde "Retail Sales Associate"
    print("\n" + "="*60)
    print("EJEMPLO 1: Ocupaciones objetivo desde Retail Sales")
    print("="*60)
    ranking = matcher.rankear_transiciones("Retail Sales Associate", top_n=5)
    for i, ocu in enumerate(ranking, 1):
        print(f"\n{i}. {ocu['ocupacion_objetivo']}")
        print(f"   Difficulty: {ocu['difficulty_score']}%")
        print(f"   Skills a aprender: {', '.join(ocu['skills_faltantes'][:3])}...")

    # Ejemplo 2: Generar camino de aprendizaje específico
    print("\n" + "="*60)
    print("EJEMPLO 2: Camino de Retail Sales → Sales Manager")
    print("="*60)
    path = matcher.sugerir_camino_aprendizaje("Retail Sales Associate", "Sales Manager")
    print(f"Dificultad: {path['difficulty_score']}%")
    print(f"Evaluación: {path['evaluacion']}")
    print(f"Tiempo estimado: {path['estimado_meses']}")
    print(f"Skills a aprender: {', '.join(path['skills_faltantes'])}")

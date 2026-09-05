import json
import os

RUTA_INEI = "data/inei_consolidado.json"
RUTA_SALIDA = "data/processed/datos_historicos.json"

def cargar_json(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_json(datos, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def serie_ordenada(diccionario_anios: dict) -> list:
    return [valor for _, valor in sorted(diccionario_anios.items(), key=lambda x: int(x[0]))]

def construir_historico(registros: list) -> dict:
    historico = {}
    for r in registros:
        tipo = r.get("tipo")
        if tipo == "salarios":
            region = r.get("region")
            industria = r.get("rama_actividad")
            serie = serie_ordenada(r.get("salarios_por_año", {}))
            if region and industria and serie:
                historico.setdefault(region, {}).setdefault(industria, []).extend(serie)
        elif tipo == "ocupados_rama_lima":
            region = "Lima"
            industria = r.get("categoria")
            serie = serie_ordenada(r.get("poblacion_miles", {}))
            if industria and serie:
                historico.setdefault(region, {}).setdefault(industria, []).extend(serie)
    return historico

if __name__ == "__main__":
    registros = cargar_json(RUTA_INEI)
    historico = construir_historico(registros)
    guardar_json(historico, RUTA_SALIDA)
    print(f"Listo: {RUTA_SALIDA} generado con {len(historico)} regiones.")
    for region, industrias in historico.items():
        print(f"  {region}: {list(industrias.keys())}")

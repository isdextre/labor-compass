import json
import pandas as pd
from pmdarima import auto_arima

def cargar_datos_json(ruta_archivo: str) -> dict:
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo en: {ruta_archivo}.")
        return {}

def obtener_tendencia(region_nombre: str, industria_nombre: str, datos_totales: dict) -> dict:
    datos_region = datos_totales.get(region_nombre, {})
    lista_datos = datos_region.get(industria_nombre, [])
    if len(lista_datos) < 12:
        return {"error": "No hay suficientes datos históricos para realizar una predicción"}
    serie_datos = pd.Series(lista_datos)
    modelo = auto_arima(
        serie_datos,
        start_p=0, max_p=3,
        start_q=0, max_q=3,
        d=None,
        seasonal=False,
        suppress_warnings=True,
        stepwise=True
    )
    modelo_predict6m = modelo.predict(n_periods=6)
    return {
        "region": region_nombre,
        "industria": industria_nombre,
        "ultimo_dato": lista_datos[-1],
        "prediccion_6m": round(float(modelo_predict6m.iloc[-1]), 2)
    }

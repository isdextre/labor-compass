# Workforce Shift - INEI Data Pipeline

Extracción y procesamiento de datos de ocupación y salarios del Perú desde el INEI para hackathon Software Week DTHN.

## 📊 Datos incluidos

### 1. Salarios por rama de actividad (2009-2021)
**Archivo:** `ingcuad5_4_1.xlsx`
- Salario promedio mensual en soles corrientes
- 4 ámbitos: Total nacional, Costa urbana, Sierra urbana, Selva urbana
- 5 ramas: Manufactura, Construcción, Comercio, Servicios, Otros
- **Output:** `inei_salarios_por_rama.json` (12 registros)

### 2. Población ocupada en Lima (2006-2023)
**Archivo:** `limacuad3_5.xlsx`
- Población en miles de personas
- Por rama de actividad
- Por tamaño de empresa
- Por categoría ocupacional (empleador, independiente, empleado, etc.)
- **Output:** `inei_ocupados_lima.json` (6 registros)

### 3. Población ocupada nacional (2009-2021)
**Archivo:** `ingcuad1_3_1.xlsx`
- Ingresos promedios nacionales
- Por área de residencia (Urbana, Rural)
- Por región natural (Costa, Sierra, Selva)
- Por departamento (24 departamentos)
- **Output:** `inei_ocupados_nacional.json` (30 registros)

## 🚀 Instalación y uso

### 1. Descargar archivos INEI

Los archivos Excel se descargan automáticamente desde INEI, pero también pueden descargarse manualmente:
https://m.inei.gob.pe/media/MenuRecursivo/indices_tematicos/

Guardar en `data/raw/`:
- `ingcuad5_4_1.xlsx`
- `limacuad3_5.xlsx`
- `ingcuad1_3_1.xlsx`

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar pipeline

```bash
python3 run_pipeline.py
```

Genera archivos JSON en `data/processed/`:
- `inei_salarios_por_rama.json` - 12 registros
- `inei_ocupados_lima.json` - 6 registros
- `inei_ocupados_nacional.json` - 30 registros
- `inei_consolidado.json` - 48 registros totales

## 📁 Estructura del proyecto

```
workforce-shift/
├── run_pipeline.py           # Script maestro
├── parse_all_inei.py         # 3 parsers específicos (Salarios, Lima, Nacional)
├── config.py                 # Configuración global
├── requirements.txt          # Dependencias
├── .gitignore
├── README.md
├── logs/
│   └── pipeline.log
└── data/
    ├── raw/
    │   ├── ingcuad5_4_1.xlsx
    │   ├── limacuad3_5.xlsx
    │   └── ingcuad1_3_1.xlsx
    └── processed/
        ├── inei_salarios_por_rama.json
        ├── inei_ocupados_lima.json
        ├── inei_ocupados_nacional.json
        └── inei_consolidado.json
```

## 🔍 Estructura de datos

### Salarios por rama
```json
{
  "tipo": "salarios",
  "rama_actividad": "Construcción",
  "region": "Total",
  "salarios_por_año": {
    "2009": 1202.86,
    "2010": 1277.53,
    ...
    "2021": 1549.57
  },
  "salario_2009": 1202.86,
  "salario_2021": 1549.57,
  "variacion_pct": 28.82
}
```

### Ocupados nacional
```json
{
  "tipo": "ingreso_nacional",
  "ambito": "Total nacional",
  "ingresos_por_año": {
    "2009": 810.53,
    ...
    "2021": 1443.08
  },
  "ingreso_2009": 810.53,
  "ingreso_2021": 1443.08,
  "unidad": "soles corrientes"
}
```

## 📈 Insights principales

1. **Variación salarial 2009-2021:**
   - Servicios: +38.0% (mayor crecimiento)
   - Comercio: +29.4%
   - Construcción: +28.8%

2. **Población ocupada Lima 2006-2023:**
   - Comercio: mayor empleador (~1.1M personas)
   - Servicios: en crecimiento
   - Construcción: volatilidad por ciclos económicos

3. **Geografía:**
   - Ingresos urbanos vs rurales: 1.9x (1595 vs 815 soles)
   - Costa genera ~35% de ingresos nacionales
   - Sierra y Selva con brecha salarial de 40%+

## 🛠️ Próximos pasos para el hackathon

- [ ] Validación manual de estructuras de cada parser
- [ ] Integración con datos WEF (Future of Jobs)
- [ ] Análisis de transiciones laborales (minería → energías renovables)
- [ ] Visualización de tendencias (Plotly/Altair)
- [ ] API REST para servir datos
- [ ] Dashboard interactivo

## 📝 Notas técnicas

- Los parsers usan estructura específica para cada archivo INEI (no son genéricos)
- Maneja años como columnas numéricas, no como headers
- Convierte tipos de datos automáticamente
- Exporta solo datos con valores numéricos válidos
- Mantiene variaciones porcentuales para análisis de tendencias

## 🔗 Fuentes

- INEI (Instituto Nacional de Estadística e Informática): https://www.inei.gob.pe/
- Datos públicos: https://datosabiertos.gob.pe/
- Índices de empleo: https://m.inei.gob.pe/sistema-estadistico-nacional/

---

**Proyecto:** Workforce Shift - Software Week DTHN
**Equipo:** [Tu nombre aquí]
**Estado:** En desarrollo para hackathon 24-48h

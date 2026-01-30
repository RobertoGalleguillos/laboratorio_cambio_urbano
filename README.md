# Laboratorio Cambio Urbano

## Aplicacion Streamlit

### Flujo recomendado (si no tienes datos generados)
1. Ejecuta el notebook `notebooks/01_descarga_datos.ipynb` para descargar insumos base.
2. Ejecuta los demas notebooks en orden (`02_...` a `05_...`) para generar los resultados.
3. Cuando existan los archivos de salida, ejecuta la app.

### Flujo rapido (si ya tienes todos los datos)
Si ya cuentas con los archivos generados por los notebooks, puedes correr la app directamente.

### Requisitos
- Python 3.9+
- Dependencias en `requirements.txt`

### Instalacion
```powershell
pip install -r requirements.txt
```

### Ejecucion
```powershell
streamlit run app/app.py
```

### Datos utilizados
- `data/processed/estadisticas_cambio.csv`
- `data/processed/estadisticas_indices.csv`
- `data/processed/indices_*.tif`
- `data/vector/manzanas_censales.shp`
- `data/vector/limite_comuna.gpkg`

### Funcionalidades
- Mapa interactivo con capas de cambio.
- Estadisticas resumidas y grafico de top 10 zonas.
- Comparador visual antes/despues de NDVI.
- Evolucion temporal de indices espectrales.
- Descarga de resultados en CSV.

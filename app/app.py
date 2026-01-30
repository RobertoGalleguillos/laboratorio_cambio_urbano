from __future__ import annotations

from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from config import APP_ICON, APP_TITLE, PROCESSED_DIR
from utils import DataPaths, detect_join_column, join_stats, list_index_years, load_indices_stats, load_stats, raster_to_rgb, read_zones


page_config = {"page_title": APP_TITLE, "layout": "wide"}
if APP_ICON:
    page_config["page_icon"] = APP_ICON
st.set_page_config(**page_config)
st.title(APP_TITLE)
st.markdown("### Detección de cambios mediante imágenes satelitales")

paths = DataPaths()


@st.cache_data
def _cached_stats():
    return load_stats(paths)


@st.cache_data
def _cached_indices_stats():
    return load_indices_stats(paths)


@st.cache_data
def _cached_zones():
    return read_zones(paths)


stats = _cached_stats()
indices_stats = _cached_indices_stats()
zones, boundary = _cached_zones()

available_years = list_index_years(PROCESSED_DIR)
if not available_years:
    available_years = [2018, 2020, 2022, 2024]

# Si el CSV trae la columna de años como índice 0..n, reemplázalo por los años reales disponibles.
if indices_stats is not None and not indices_stats.empty and "fecha" in indices_stats.columns:
    fecha_vals = pd.to_numeric(indices_stats["fecha"], errors="coerce")
    if fecha_vals.notna().all():
        unique_vals = sorted(fecha_vals.unique().tolist())
        expected = list(range(len(indices_stats)))
        if unique_vals == expected and len(available_years) == len(indices_stats):
            indices_stats = indices_stats.copy()
            indices_stats["fecha"] = [str(y) for y in sorted(available_years)]

st.sidebar.header("Configuración")
fecha_inicio = st.sidebar.selectbox("Fecha inicial", available_years, index=0)
valid_end_years = [y for y in available_years if y >= fecha_inicio]
fecha_fin = st.sidebar.selectbox("Fecha final", valid_end_years, index=len(valid_end_years) - 1)

change_options = {
    "Urbanizacion": "urbanizacion_ha",
    "Pérdida vegetación": "perdida_veg_ha",
    "Ganancia vegetación": "ganancia_veg_ha",
}
tipos_cambio = st.sidebar.multiselect(
    "Tipos de cambio a mostrar",
    list(change_options.keys()),
    default=list(change_options.keys()),
)
st.sidebar.caption("ha = hectáreas. Selecciona una o más capas para el mapa.")

if zones is not None and zones.crs is not None:
    zones = zones.to_crs(epsg=4326)
if boundary is not None and boundary.crs is not None:
    boundary = boundary.to_crs(epsg=4326)

join_col = detect_join_column(stats, zones)
zones_joined = join_stats(zones, stats, join_col)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Mapa de cambios")
    st.caption("Mapa de cambio total (no depende del año seleccionado).")
    if zones_joined is None or zones_joined.empty:
        st.info("No se encontraron zonas para mostrar en el mapa.")
    else:
        center = [
            zones_joined.geometry.centroid.y.mean(),
            zones_joined.geometry.centroid.x.mean(),
        ]
        mapa = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")

        if boundary is not None and not boundary.empty:
            folium.GeoJson(
                boundary,
                name="Límite comunal",
                style_function=lambda _: {"color": "#1f4e79", "weight": 2, "fillOpacity": 0},
            ).add_to(mapa)

        for label in tipos_cambio:
            col_name = change_options[label]
            if col_name not in zones_joined.columns:
                continue
            values = zones_joined[col_name].fillna(0)
            vmin, vmax = float(values.min()), float(values.max())
            if vmin == vmax:
                vmin, vmax = 0.0, max(vmax, 1.0)

            def _style(feat, column=col_name, vmin=vmin, vmax=vmax):
                value = feat["properties"].get(column)
                if value is None:
                    return {"fillColor": "#dddddd", "color": "#333333", "weight": 0.5, "fillOpacity": 0.2}
                scaled = (float(value) - vmin) / (vmax - vmin) if vmax != vmin else 0
                idx = int(max(0, min(8, round(scaled * 8))))
                color = px.colors.sequential.YlOrRd[idx]
                return {"fillColor": color, "color": "#333333", "weight": 0.5, "fillOpacity": 0.6}

            tooltip = None
            tooltip_fields = []
            tooltip_aliases = []
            if join_col:
                tooltip_fields.append(join_col)
                tooltip_aliases.append("Zona")
            for alias, col_name in change_options.items():
                if col_name in zones_joined.columns:
                    tooltip_fields.append(col_name)
                    tooltip_aliases.append(f"{alias} (ha)")
            if tooltip_fields:
                tooltip = folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases)

            folium.GeoJson(zones_joined, name=label, style_function=_style, tooltip=tooltip).add_to(mapa)

        folium.LayerControl().add_to(mapa)
        st_folium(mapa, width=700, height=500)

with col2:
    st.subheader("Estadísticas")
    if stats is None or stats.empty:
        st.info("No hay estadísticas disponibles.")
    else:
        total_urb = stats["urbanizacion_ha"].sum() if "urbanizacion_ha" in stats.columns else 0
        total_perd = stats["perdida_veg_ha"].sum() if "perdida_veg_ha" in stats.columns else 0
        total_gan = stats["ganancia_veg_ha"].sum() if "ganancia_veg_ha" in stats.columns else 0

        st.metric("Total urbanización", f"{total_urb:.2f} ha")
        st.metric("Pérdida vegetación", f"{total_perd:.2f} ha")
        st.metric("Ganancia vegetación", f"{total_gan:.2f} ha")
        st.caption("ha = hectáreas. Valores agregados para todas las zonas.")

        metric_label = st.selectbox(
            "Variable para gráfico",
            list(change_options.keys()),
            index=list(change_options.keys()).index(tipos_cambio[0]) if tipos_cambio else 0,
        )
        selected_metric = change_options.get(metric_label, "urbanizacion_ha")
        if selected_metric in stats.columns:
            stats_plot = stats.copy()
            stats_plot["zona"] = stats_plot["zona"].astype(str)
            stats_plot["zona_label"] = stats_plot["zona"].str[-6:]
            fig = px.bar(
                stats_plot.nlargest(10, selected_metric),
                x="zona_label",
                y=selected_metric,
                title=f"Top 10 zonas con más {metric_label.lower()}",
                labels={
                    "zona_label": "Zona (últimos 6 dígitos del ID)",
                    selected_metric: "Hectáreas (ha)",
                },
                hover_data={"zona": True},
            )
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

st.subheader("Comparación temporal")
col3, col4 = st.columns(2)

with col3:
    img_path = PROCESSED_DIR / f"indices_{fecha_inicio}.tif"
    rgb = raster_to_rgb(img_path)
    if rgb is not None:
        st.image(rgb, caption=f"NDVI {fecha_inicio}")
    else:
        st.info(f"No se pudo cargar la imagen NDVI {fecha_inicio}.")

with col4:
    img_path = PROCESSED_DIR / f"indices_{fecha_fin}.tif"
    rgb = raster_to_rgb(img_path)
    if rgb is not None:
        st.image(rgb, caption=f"NDVI {fecha_fin}")
    else:
        st.info(f"No se pudo cargar la imagen NDVI {fecha_fin}.")

st.subheader("Evolución temporal")
if indices_stats is not None and not indices_stats.empty:
    indices_plot = indices_stats.copy()
    indices_plot["fecha"] = indices_plot["fecha"].astype(str)
    ordered_years = sorted(indices_plot["fecha"].unique())
    indices_long = indices_plot.melt(
        id_vars="fecha",
        value_vars=["ndvi_mean", "ndbi_mean", "ndwi_mean"],
        var_name="indice",
        value_name="valor",
    )
    indice_labels = {
        "ndvi_mean": "NDVI (vegetacion)",
        "ndbi_mean": "NDBI (urbano)",
        "ndwi_mean": "NDWI (agua)",
    }
    indices_long["indice"] = indices_long["indice"].map(indice_labels).fillna(indices_long["indice"])

    fig_temporal = px.line(
        indices_long,
        x="fecha",
        y="valor",
        color="indice",
        title="Evolución de índices espectrales (promedio)",
        labels={"valor": "Valor promedio", "fecha": "Año", "indice": "Índice"},
    )
    fig_temporal.update_layout(legend_title_text="Índice")
    fig_temporal.update_xaxes(type="category", categoryorder="array", categoryarray=ordered_years)
    st.plotly_chart(fig_temporal, use_container_width=True)
    st.caption(
        "El eje X muestra los años disponibles (por ejemplo, 2018, 2020, 2022, 2024). "
        "Cada punto es el promedio del índice en toda el área de estudio para ese año. "
        "NDVI: vegetación, NDBI: zonas urbanas, NDWI: agua."
    )
else:
    st.info("No hay datos de evolución temporal disponibles.")

st.sidebar.markdown("---")
st.sidebar.subheader("Descargar datos")
if stats is not None and not stats.empty:
    csv = stats.to_csv(index=False)
    st.sidebar.download_button(
        "Descargar estadísticas (CSV)",
        csv,
        "estadisticas_cambio.csv",
        "text/csv",
    )

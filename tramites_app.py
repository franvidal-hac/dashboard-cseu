"""
Dashboard de Trámites — Sistema CSEU
=====================================
Calidad de Servicio y Experiencia Usuaria · Secretaría de Modernización · Ministerio de Hacienda

Este dashboard se enfoca exclusivamente en el módulo de Trámites del Sistema CSEU.
Permite:
  - Comparar el desempeño de las instituciones (ranking, scatter, tabla).
  - Hacer drill-down en una institución para ver el detalle de sus trámites individuales.

Para ejecutar localmente:
    python3 -m streamlit run tramites_app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from pathlib import Path


# ══════════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CSEU · Trámites",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; }
.block-container { padding-top: 1.5rem; }
[data-testid="stTabs"] { margin-top: 0.5rem; }
.stTabs [data-baseweb="tab-list"] {
    position: sticky;
    top: 3rem;
    background-color: white;
    z-index: 99;
    padding-top: 0.5rem;
    border-bottom: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

YEARS = ["2022", "2023", "2024", "2025"]

# Paleta semáforo (idéntica al dashboard principal streamlit_app.py)
C_OK   = "#1e8449"   # verde  — bueno
C_WARN = "#d35400"   # naranja — regular
C_BAD  = "#c0392b"   # rojo   — malo
C_BLUE = "#1a5276"   # azul   — neutro / referencia
C_GOLD = "#d4ac0d"   # dorado — comparación
C_GRAY = "#aab7b8"   # gris   — sin datos

# Colores por categoría funcional (para el scatter)
COLORES_CAT = {
    "SERVICIOS PÚBLICOS GENERALES": "#1a5276",
    "FOMENTO PRODUCTIVO":           "#1e8449",
    "REGULACIÓN":                   "#d35400",
    "FISCALIZACIÓN":                "#922b21",
    "PREVISIÓN Y SEGURIDAD SOCIAL": "#7d6608",
}

# Umbrales semáforo para % fuera de plazo:
#   verde ≤ 10%  |  naranja ≤ 30%  |  rojo > 30%
UMBRAL_FP_OK   = 10
UMBRAL_FP_WARN = 30

# Directorio con los archivos de datos
DATA_DIR = Path(__file__).parent / "Información Sistema"


# ══════════════════════════════════════════════════════════════════════════════
# 3. FUNCIONES AUXILIARES
# ══════════════════════════════════════════════════════════════════════════════

def color_fp(v: float) -> str:
    """Devuelve el color semáforo para % fuera de plazo (lower is better).
    Verde ≤ 10%  |  naranja ≤ 30%  |  rojo > 30%  |  gris si no hay datos.
    """
    if pd.isna(v):
        return C_GRAY
    if v <= UMBRAL_FP_OK:
        return C_OK
    if v <= UMBRAL_FP_WARN:
        return C_WARN
    return C_BAD


def color_fp_css(v) -> str:
    """Para Styler.map — devuelve estilo CSS de fondo para % fuera de plazo."""
    if not isinstance(v, (int, float)) or pd.isna(v):
        return ""
    if v <= UMBRAL_FP_OK:
        return f"background-color: {C_OK}22"
    if v <= UMBRAL_FP_WARN:
        return f"background-color: {C_WARN}22"
    return f"background-color: {C_BAD}22"


def fmt_pct(v) -> str:
    """Formatea como porcentaje con 1 decimal, o 'N/D' si el valor falta."""
    return f"{v:.1f}%" if pd.notna(v) else "N/D"


def fmt_n(v) -> str:
    """Formatea como entero con separador de miles, o 'N/D' si el valor falta."""
    return f"{int(v):,}" if pd.notna(v) else "N/D"


# ══════════════════════════════════════════════════════════════════════════════
# 4. CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Cargando datos de trámites…")
def load_data():
    """Lee los archivos Excel y construye dos DataFrames listos para visualizar.

    Retorna:
        tram_inst (DataFrame): un registro por institución con métricas
                               agregadas (promedio simple de sus trámites).
                               Incluye columnas de ministerio, categoría y etapa.
        tram_raw  (DataFrame): un registro por trámite, con métricas individuales
                               por año. Usado en la ficha de institución.
    """

    # ── Maestro de instituciones ──────────────────────────────────────────────
    maestro = pd.read_excel(DATA_DIR / "Categorización Sistema CSEU 2025 1.xlsx")
    maestro = maestro.rename(columns={
        "codigo_interno_SCSEU": "cod",
        "MINISTERIO":           "ministerio",
        "SERVICIO":             "nombre_maestro",
        "Categoría funcional":  "categoria",
        "ETAPA":                "etapa",
    })
    maestro["cod"] = maestro["cod"].astype(str)

    # Excluir servicios en etapa SAIP y filas sin etapa válida
    maestro = maestro[maestro["etapa"].isin(["Etapa 1", "Etapa 2", "Etapa 3"])].copy()
    maestro = maestro[["cod", "ministerio", "nombre_maestro", "categoria", "etapa"]]

    # ── Trámites (un registro por trámite reportado) ──────────────────────────
    tram = pd.read_excel(DATA_DIR / "tramites_consolidado_2025.xlsx")
    tram["cod"] = tram["codigo_interno_SCSEU"].astype(str)

    # Calcular métricas por año para cada trámite
    for yr in YEARS:
        col_n     = f"{yr}_n_transacciones_gestionadas_en_el_ano"
        col_fuera = f"{yr}_n_transacciones_gestionadas_en_un_plazo_mayor_al_esperado"
        tram[f"n_{yr}"]      = pd.to_numeric(tram[col_n],        errors="coerce")
        tram[f"fuera_{yr}"]  = pd.to_numeric(tram[col_fuera],    errors="coerce")
        tram[f"prom_{yr}"]   = pd.to_numeric(tram[f"{yr}_promedio"], errors="coerce")

        # % fuera de plazo para este trámite en este año
        tram[f"fp_pct_{yr}"] = np.where(
            tram[f"n_{yr}"] > 0,
            tram[f"fuera_{yr}"] / tram[f"n_{yr}"] * 100,
            np.nan,
        )

    # ── tram_raw: tabla de trámites individuales (para la ficha) ─────────────
    columnas_raw = [
        "cod",
        "nombre_institucion",
        "nombre_del_tramite_y_o_servicio_relevante",
        "tiempo_esperado_para_la_gestion_del_servicio_relevante",
        "periodo_de_tiempo_dias_habiles_dias_corridos_horas_minutos",
        "hito_de_inicio",
        "hito_final",
    ] + [f"{m}_{yr}" for yr in YEARS for m in ("n", "fuera", "fp_pct", "prom")]

    tram_raw = tram[[c for c in columnas_raw if c in tram.columns]].copy()
    tram_raw = tram_raw.rename(columns={
        "nombre_del_tramite_y_o_servicio_relevante":              "nombre_tramite",
        "tiempo_esperado_para_la_gestion_del_servicio_relevante": "plazo_esperado",
        "periodo_de_tiempo_dias_habiles_dias_corridos_horas_minutos": "unidad_plazo",
    })

    # Agregar datos del maestro a tram_raw para uso en la ficha
    tram_raw = tram_raw.merge(
        maestro[["cod", "ministerio", "categoria", "etapa"]],
        on="cod", how="left"
    )

    # ── tram_inst: tabla agregada por institución (para comparación) ──────────
    # Cada trámite pesa igual en el promedio (independiente de su volumen)
    agg_dict = {"nombre_institucion": "first"}
    for yr in YEARS:
        agg_dict[f"fp_pct_{yr}"] = "mean"   # % fuera de plazo: promedio simple
        agg_dict[f"n_{yr}"]      = "sum"    # total transacciones de la institución
        agg_dict[f"fuera_{yr}"]  = "sum"    # total transacciones fuera de plazo

    tram_inst = tram.groupby("cod").agg(agg_dict).reset_index()

    # Agregar el número de trámites reportados por institución
    conteo_tramites = tram.groupby("cod").size().reset_index(name="n_tramites")
    tram_inst = tram_inst.merge(conteo_tramites, on="cod", how="left")

    # Nombre normalizado de la institución (desde el archivo de trámites)
    tram_inst["nombre_tram"] = (
        tram_inst["nombre_institucion"].str.strip().str.title()
    )

    # Cruzar con el maestro para obtener ministerio, categoría, etapa
    tram_inst = maestro.merge(tram_inst, on="cod", how="left")
    tram_inst["nombre"] = (
        tram_inst["nombre_tram"]
        .fillna(tram_inst["nombre_maestro"].str.strip().str.title())
    )

    return tram_inst, tram_raw


# Carga inicial de datos (cacheada)
tram_inst, tram_raw = load_data()


# ══════════════════════════════════════════════════════════════════════════════
# 5. SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

# inst_cod: código interno de la institución seleccionada para drill-down.
# None → Vista A (comparación entre instituciones).
# str  → Vista B (ficha de detalle de esa institución).
if "inst_cod" not in st.session_state:
    st.session_state.inst_cod = None


# ══════════════════════════════════════════════════════════════════════════════
# 6. SIDEBAR: FILTROS Y CONTROLES
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ⏱️ CSEU · Trámites")
    st.caption(
        "Calidad de Servicio y Experiencia Usuaria  \n"
        "Secretaría de Modernización · Ministerio de Hacienda"
    )
    st.caption("Datos autodeclarados por los servicios participantes en el Sistema CSEU.")
    st.caption("ℹ️ Los datos de 2025 corresponden al período enero–junio 2025.")
    st.divider()

    # ── Filtros ───────────────────────────────────────────────────────────────
    ministerios = ["Todos"] + sorted(tram_inst["ministerio"].dropna().unique())
    min_sel = st.selectbox("Ministerio", ministerios)

    categorias = ["Todas"] + sorted(tram_inst["categoria"].dropna().unique())
    cat_sel = st.selectbox("Categoría funcional", categorias)

    st.divider()

    # ── Año de análisis ───────────────────────────────────────────────────────
    yr_sel = st.select_slider("Año de análisis", options=YEARS, value="2025")
    yr_prev = str(int(yr_sel) - 1)   # año anterior para mostrar variación

    st.divider()

    # ── Leyenda semáforo ──────────────────────────────────────────────────────
    st.markdown("**Semáforo % fuera de plazo**")
    st.markdown(
        f"🟢 ≤ {UMBRAL_FP_OK}% &nbsp;&nbsp; "
        f"🟠 ≤ {UMBRAL_FP_WARN}% &nbsp;&nbsp; "
        f"🔴 > {UMBRAL_FP_WARN}%",
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption(
        "⚠️ Los plazos de gestión son definidos por cada institución — "
        "no son directamente comparables entre ellas.  \n\n"
        "% fuera de plazo = promedio simple entre los trámites reportados "
        "(cada trámite pesa igual, sin ponderar por su volumen de transacciones)."
    )


# ══════════════════════════════════════════════════════════════════════════════
# FILTRO GLOBAL: aplicar sidebar a la tabla de instituciones
# ══════════════════════════════════════════════════════════════════════════════

df_inst = tram_inst.copy()
if min_sel != "Todos":
    df_inst = df_inst[df_inst["ministerio"] == min_sel]
if cat_sel != "Todas":
    df_inst = df_inst[df_inst["categoria"] == cat_sel]

# Solo instituciones con al menos una transacción en el año seleccionado
fp_col = f"fp_pct_{yr_sel}"
n_col  = f"n_{yr_sel}"
df_inst = df_inst[df_inst[n_col].fillna(0) > 0].copy()


# ══════════════════════════════════════════════════════════════════════════════
# 7A. VISTA COMPARACIÓN (inst_cod is None)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.inst_cod is None:

    st.title("⏱️ Trámites — Comparación entre instituciones")
    st.caption(
        f"Año: **{yr_sel}** · "
        f"Ministerio: **{min_sel}** · "
        f"Categoría: **{cat_sel}** · "
        f"**{len(df_inst)} instituciones** con datos  \n"
        "👆 Haz clic en una barra del ranking para abrir la ficha de esa institución."
    )

    # ── KPIs ──────────────────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Instituciones con datos", len(df_inst))
    with k2:
        st.metric("Total transacciones", fmt_n(df_inst[n_col].sum()))
    with k3:
        avg_fp = df_inst[fp_col].mean()
        st.metric(
            "% promedio fuera de plazo",
            fmt_pct(avg_fp),
            help="Promedio simple entre instituciones (cada institución pesa igual).",
        )

    st.divider()

    # ── Ranking bar chart (interactivo) ───────────────────────────────────────
    st.subheader(f"Ranking — % fuera de plazo ({yr_sel})")

    ctrl1, ctrl2 = st.columns([3, 1])
    with ctrl1:
        orden_sel = st.radio(
            "Orden", ["Mayor → menor % fuera de plazo", "Menor → mayor % fuera de plazo"],
            horizontal=True, index=0,
        )
    with ctrl2:
        n_total = df_inst[fp_col].notna().sum()
        n_show = st.number_input(
            "Mostrar", min_value=1, max_value=max(1, n_total),
            value=min(40, n_total), step=5,
        )

    sort_asc = (orden_sel == "Menor → mayor % fuera de plazo")
    df_rank = (
        df_inst[df_inst[fp_col].notna()]
        .sort_values(fp_col, ascending=sort_asc)
        .head(n_show)
        .reset_index(drop=True)
    )

    st.caption(
        f"Mostrando **{len(df_rank)}** de {n_total} instituciones con datos."
    )

    # Colores semáforo por barra (verde ≤10%, naranja ≤30%, rojo >30%)
    bar_colors = [color_fp(v) for v in df_rank[fp_col]]

    # customdata[0] = cod → permite recuperar la institución al hacer clic
    customdata = np.column_stack([
        df_rank["cod"].values,
        df_rank["ministerio"].values,
        df_rank["categoria"].values,
        df_rank[n_col].values,
        df_rank["n_tramites"].fillna(0).astype(int).values,
    ])

    fig_rank = go.Figure(go.Bar(
        x=df_rank[fp_col],
        y=df_rank["nombre"].str[:55],           # nombre truncado para el eje
        orientation="h",
        marker_color=bar_colors,
        text=[fmt_pct(v) for v in df_rank[fp_col]],
        textposition="outside",
        customdata=customdata,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Ministerio: %{customdata[1]}<br>"
            "Categoría: %{customdata[2]}<br>"
            f"% fuera de plazo ({yr_sel}): %{{x:.1f}}%<br>"
            "Transacciones: %{customdata[3]:,.0f}<br>"
            "N° trámites: %{customdata[4]}<extra></extra>"
        ),
    ))

    # Líneas de referencia en los dos umbrales semáforo
    fig_rank.add_vline(
        x=UMBRAL_FP_OK,
        line_dash="dash", line_color=C_OK, opacity=0.7,
        annotation_text=f"{UMBRAL_FP_OK}%", annotation_position="top right",
    )
    fig_rank.add_vline(
        x=UMBRAL_FP_WARN,
        line_dash="dash", line_color=C_WARN, opacity=0.7,
        annotation_text=f"{UMBRAL_FP_WARN}%", annotation_position="top right",
    )

    x_max = max(df_rank[fp_col].max() * 1.2, UMBRAL_FP_WARN * 1.5) if len(df_rank) > 0 else 40
    fig_rank.update_layout(
        height=max(500, len(df_rank) * 24),
        margin=dict(t=10, b=40, l=10, r=80),
        xaxis=dict(range=[0, min(100, x_max)], ticksuffix="%", title="% fuera de plazo"),
        yaxis=dict(autorange="reversed", title=""),
        showlegend=False,
    )

    # on_select="rerun": al hacer clic en una barra se guarda la selección
    # y la app se rerenderiza con los datos del punto seleccionado disponibles.
    sel_ranking = st.plotly_chart(
        fig_rank,
        use_container_width=True,
        on_select="rerun",
        key="chart_ranking",
    )

    # Detectar clic y activar la ficha de la institución seleccionada
    puntos = getattr(getattr(sel_ranking, "selection", None), "points", [])
    if puntos:
        cod_clickeado = str(puntos[0]["customdata"][0])
        st.session_state.inst_cod = cod_clickeado
        st.rerun()

    st.divider()

    # ── Scatter: volumen vs. % fuera de plazo ─────────────────────────────────
    st.subheader(f"Volumen de transacciones vs. % fuera de plazo ({yr_sel})")

    df_sc = df_inst[["nombre", "ministerio", "categoria", n_col, fp_col, "n_tramites"]].dropna(
        subset=[n_col, fp_col]
    ).copy()

    # Slider para acotar el eje X — valores en miles para que los números sean legibles
    # select_slider permite mostrar etiquetas legibles (50 mil, 1 millón, etc.)
    opciones_slider = {
        "1.000":        1_000,
        "5.000":        5_000,
        "10.000":      10_000,
        "50 mil":      50_000,
        "100 mil":    100_000,
        "200 mil":    200_000,
        "500 mil":    500_000,
        "1 millón":   1_000_000,
        "1,5 millones": 1_500_000,
        "2 millones": 2_000_000,
        "2,5 millones": 2_500_000,
        "3 millones": 3_000_000,
    }
    etiqueta_sel = st.select_slider(
        "Límite eje X — transacciones",
        options=list(opciones_slider.keys()),
        value="3 millones",
        help=(
            "Ajusta el encuadre del gráfico. Las instituciones fuera del límite "
            "siguen estando en los datos — solo quedan fuera del área visible."
        ),
    )
    x_limite = opciones_slider[etiqueta_sel]
    n_ocultas = (df_sc[n_col] > x_limite).sum()
    if n_ocultas > 0:
        st.caption(
            f"⚠️ {n_ocultas} institución(es) con más de {etiqueta_sel} transacciones "
            "quedan fuera del encuadre (aparecen al pasar el cursor si están en el borde)."
        )

    fig_sc = px.scatter(
        df_sc,
        x=n_col,
        y=fp_col,
        color="categoria",
        color_discrete_map=COLORES_CAT,
        hover_name="nombre",
        hover_data={
            "ministerio":  True,
            "n_tramites":  True,
            n_col:         ":,.0f",
            fp_col:        ":.1f",
            "categoria":   False,
        },
        labels={
            n_col:        "Total transacciones",
            fp_col:       "% fuera de plazo",
            "n_tramites": "N° trámites",
        },
    )
    # Líneas de referencia en los dos umbrales
    for umbral, color in [(UMBRAL_FP_OK, C_OK), (UMBRAL_FP_WARN, C_WARN)]:
        fig_sc.add_hline(
            y=umbral, line_dash="dash", line_color=color, opacity=0.5,
            annotation_text=f"{umbral}%",
        )
    fig_sc.update_layout(
        height=420,
        margin=dict(t=10, b=60, l=60, r=20),
        yaxis=dict(ticksuffix="%", title="% fuera de plazo"),
        xaxis=dict(title="Total transacciones", range=[0, x_limite]),
        legend=dict(title="Categoría", orientation="h", y=-0.35),
    )
    st.plotly_chart(fig_sc, use_container_width=True)
    st.caption("Eje X: total de transacciones gestionadas por la institución en el año (suma de todos sus trámites reportados).")

    st.divider()

    # ── Tabla comparativa ─────────────────────────────────────────────────────
    st.subheader("Tabla comparativa")

    # Agregar columna de año anterior si existe
    fp_prev_col = f"fp_pct_{yr_prev}" if yr_prev in YEARS else None
    n_prev_col  = f"n_{yr_prev}"      if yr_prev in YEARS else None

    cols_tabla = ["nombre", "ministerio", "categoria", "n_tramites", n_col, fp_col]
    if fp_prev_col and fp_prev_col in df_inst.columns:
        cols_tabla.append(fp_prev_col)

    df_tabla = (
        df_inst[cols_tabla]
        .copy()
        .sort_values(fp_col, ascending=False)
        .reset_index(drop=True)
    )

    # Calcular variación respecto al año anterior (en puntos porcentuales)
    if fp_prev_col and fp_prev_col in df_tabla.columns:
        df_tabla["Δ pp"] = df_tabla[fp_col] - df_tabla[fp_prev_col]

    # Renombrar columnas para la tabla final
    rename_cols = {
        "nombre":     "Institución",
        "ministerio": "Ministerio",
        "categoria":  "Categoría",
        "n_tramites": "N° trámites",
        n_col:        f"Transacciones {yr_sel}",
        fp_col:       f"% fuera plazo {yr_sel}",
    }
    if fp_prev_col and fp_prev_col in df_tabla.columns:
        rename_cols[fp_prev_col] = f"% fuera plazo {yr_prev}"

    df_tabla = df_tabla.rename(columns=rename_cols)

    # Aplicar semáforo a las columnas de % fuera de plazo
    fp_display_cols = [rename_cols[fp_col]]
    if fp_prev_col and fp_prev_col in rename_cols:
        fp_display_cols.append(rename_cols[fp_prev_col])

    styled_tabla = df_tabla.style.map(color_fp_css, subset=fp_display_cols)
    st.dataframe(styled_tabla, use_container_width=True, hide_index=True)

    # Selector directo de institución (alternativa al clic en el gráfico)
    st.caption("O selecciona una institución directamente:")
    nombres_inst = sorted(df_inst["nombre"].dropna().tolist())
    inst_directa = st.selectbox(
        "Ir a ficha", ["— selecciona —"] + nombres_inst, label_visibility="collapsed"
    )
    if inst_directa != "— selecciona —":
        match = df_inst[df_inst["nombre"] == inst_directa]
        if not match.empty:
            st.session_state.inst_cod = match.iloc[0]["cod"]
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# 7B. VISTA FICHA DE INSTITUCIÓN (inst_cod is not None)
# ══════════════════════════════════════════════════════════════════════════════

else:
    cod_sel = st.session_state.inst_cod

    # Obtener datos de la institución (sin filtros de sidebar para asegurar que aparezca)
    inst_row     = tram_inst[tram_inst["cod"] == cod_sel]
    tramites_inst = tram_raw[tram_raw["cod"] == cod_sel].copy()

    # Validar que existan datos
    if inst_row.empty or tramites_inst.empty:
        st.warning("No se encontraron datos para la institución seleccionada.")
        if st.button("← Volver a comparación"):
            st.session_state.inst_cod = None
            st.rerun()
        st.stop()

    inst        = inst_row.iloc[0]
    nombre_inst = inst["nombre"]

    # ── Header ────────────────────────────────────────────────────────────────
    if st.button("← Volver a comparación"):
        st.session_state.inst_cod = None
        st.rerun()

    st.title(nombre_inst)
    st.markdown(
        f"**Ministerio:** {inst['ministerio']} &nbsp;|&nbsp; "
        f"**Categoría:** {inst['categoria']} &nbsp;|&nbsp; "
        f"**Etapa CSEU:** {inst['etapa']} &nbsp;|&nbsp; "
        f"Año: **{yr_sel}**",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    # Calcular promedio de la categoría para comparar
    promedio_cat = (
        tram_inst[
            (tram_inst["categoria"] == inst["categoria"]) &
            (tram_inst[n_col].fillna(0) > 0)
        ][fp_col].mean()
    )
    fp_inst   = inst[fp_col]
    delta_cat = fp_inst - promedio_cat if (pd.notna(fp_inst) and pd.notna(promedio_cat)) else None

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        n_tram = int(inst["n_tramites"]) if pd.notna(inst.get("n_tramites")) else "N/D"
        st.metric("N° trámites reportados", n_tram)
    with k2:
        st.metric(f"Transacciones ({yr_sel})", fmt_n(inst[n_col]))
    with k3:
        st.metric(f"% fuera de plazo ({yr_sel})", fmt_pct(fp_inst))
    with k4:
        # Delta positivo = peor que el promedio de la categoría (más % fuera de plazo)
        delta_str   = f"{delta_cat:+.1f} pp vs. promedio categoría" if delta_cat is not None else None
        delta_color = "inverse" if (delta_cat is not None and delta_cat > 0) else "normal"
        st.metric(
            f"Promedio categoría ({yr_sel})",
            fmt_pct(promedio_cat),
            delta=delta_str,
            delta_color=delta_color,
            help="Diferencia en puntos porcentuales respecto al promedio de las instituciones "
                 "de la misma categoría funcional. Positivo = peor que el promedio.",
        )

    st.divider()

    # ── Tabs internas de la ficha ─────────────────────────────────────────────
    tab_tabla, tab_barras, tab_evol = st.tabs([
        "📋 Trámites individuales",
        "📊 Comparación entre trámites",
        "📈 Evolución 2022→2025",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1 — Tabla de trámites individuales
    # ─────────────────────────────────────────────────────────────────────────
    with tab_tabla:
        st.subheader(f"Detalle de trámites — {nombre_inst} ({yr_sel})")

        cols_detalle = [
            "nombre_tramite",
            "plazo_esperado",
            "unidad_plazo",
            f"n_{yr_sel}",
            f"fuera_{yr_sel}",
            f"fp_pct_{yr_sel}",
            f"prom_{yr_sel}",
        ]
        cols_presentes = [c for c in cols_detalle if c in tramites_inst.columns]
        df_detalle = tramites_inst[cols_presentes].copy()

        # Convertir a entero las columnas de conteo (se muestran sin decimales)
        for c in [f"n_{yr_sel}", f"fuera_{yr_sel}"]:
            if c in df_detalle.columns:
                df_detalle[c] = df_detalle[c].apply(lambda v: int(v) if pd.notna(v) else None)

        df_detalle = df_detalle.rename(columns={
            "nombre_tramite":    "Trámite",
            "plazo_esperado":    "Plazo esperado",
            "unidad_plazo":      "Unidad",
            f"n_{yr_sel}":       "Transacciones",
            f"fuera_{yr_sel}":   "Fuera de plazo (N°)",
            f"fp_pct_{yr_sel}":  "% fuera de plazo",
            f"prom_{yr_sel}":    "Tiempo promedio real",
        })

        semaf_cols = [c for c in ["% fuera de plazo"] if c in df_detalle.columns]
        styled_det = df_detalle.style.map(color_fp_css, subset=semaf_cols)
        st.dataframe(styled_det, use_container_width=True, hide_index=True)

        st.caption(
            "Plazo esperado: definido por la propia institución — "
            "no comparable directamente entre instituciones."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2 — Comparación visual entre trámites de la institución
    # ─────────────────────────────────────────────────────────────────────────
    with tab_barras:
        st.subheader(f"% fuera de plazo por trámite — {yr_sel}")

        df_bar = tramites_inst[["nombre_tramite", f"fp_pct_{yr_sel}", f"n_{yr_sel}"]].dropna(
            subset=[f"fp_pct_{yr_sel}"]
        ).copy()

        if df_bar.empty:
            st.info("Sin datos de % fuera de plazo para el año seleccionado.")
        else:
            promedio_inst = df_bar[f"fp_pct_{yr_sel}"].mean()

            fig_bar = go.Figure(go.Bar(
                x=df_bar[f"fp_pct_{yr_sel}"],
                y=df_bar["nombre_tramite"].str[:60],    # nombre truncado para el eje
                orientation="h",
                marker_color=[color_fp(v) for v in df_bar[f"fp_pct_{yr_sel}"]],
                text=[fmt_pct(v) for v in df_bar[f"fp_pct_{yr_sel}"]],
                textposition="outside",
                customdata=df_bar[[f"n_{yr_sel}"]].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"% fuera de plazo ({yr_sel}): %{{x:.1f}}%<br>"
                    "Transacciones: %{customdata[0]:,.0f}<extra></extra>"
                ),
            ))

            # Promedio de la institución (línea punteada azul)
            fig_bar.add_vline(
                x=promedio_inst,
                line_dash="dot",
                line_color=C_BLUE,
                opacity=0.8,
                annotation_text=f"Promedio institución: {promedio_inst:.1f}%",
                annotation_position="top right",
            )
            # Umbral semáforo (línea roja)
            for umbral_b, col_b in [(UMBRAL_FP_OK, C_OK), (UMBRAL_FP_WARN, C_WARN)]:
                fig_bar.add_vline(
                    x=umbral_b, line_dash="dash", line_color=col_b, opacity=0.5,
                    annotation_text=f"{umbral_b}%",
                )

            x_max_bar = max(df_bar[f"fp_pct_{yr_sel}"].max() * 1.3, UMBRAL_FP_WARN * 1.5)
            fig_bar.update_layout(
                height=max(300, len(df_bar) * 80),
                margin=dict(t=10, b=40, l=10, r=140),
                xaxis=dict(range=[0, min(100, x_max_bar)], ticksuffix="%"),
                yaxis=dict(autorange="reversed", title=""),
                showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3 — Evolución 2022→2025
    # ─────────────────────────────────────────────────────────────────────────
    with tab_evol:
        st.subheader(f"Evolución % fuera de plazo — {nombre_inst}")

        # Construir tabla larga: una fila por (trámite, año)
        filas_evol = []
        for _, row in tramites_inst.iterrows():
            for yr in YEARS:
                val_fp = row.get(f"fp_pct_{yr}")
                val_n  = row.get(f"n_{yr}")
                if pd.notna(val_fp):
                    filas_evol.append({
                        "Trámite": row["nombre_tramite"],
                        "Año":     int(yr),
                        "fp_pct":  val_fp,
                        "n_trans": val_n,
                    })

        df_evol = pd.DataFrame(filas_evol)

        if df_evol.empty:
            st.info("Sin datos históricos disponibles para esta institución.")
        else:
            fig_evol = px.line(
                df_evol,
                x="Año",
                y="fp_pct",
                color="Trámite",
                markers=True,
                labels={"fp_pct": "% fuera de plazo", "n_trans": "Transacciones"},
                hover_data={"n_trans": ":,.0f"},
            )
            for umbral_e, col_e in [(UMBRAL_FP_OK, C_OK), (UMBRAL_FP_WARN, C_WARN)]:
                fig_evol.add_hline(
                    y=umbral_e, line_dash="dash", line_color=col_e, opacity=0.5,
                    annotation_text=f"{umbral_e}%",
                )
            fig_evol.update_layout(
                height=400,
                margin=dict(t=10, b=80, l=60, r=20),
                yaxis=dict(range=[0, 105], ticksuffix="%", title="% fuera de plazo"),
                xaxis=dict(tickvals=[2022, 2023, 2024, 2025], title=""),
                legend=dict(title="", orientation="h", y=-0.4, font=dict(size=11)),
            )
            st.plotly_chart(fig_evol, use_container_width=True)

        # Tabla resumen de evolución
        st.subheader("Tabla de evolución por trámite")
        cols_evol = ["nombre_tramite"] + [
            f"fp_pct_{yr}" for yr in YEARS if f"fp_pct_{yr}" in tramites_inst.columns
        ]
        df_evol_tabla = tramites_inst[cols_evol].copy().rename(columns={
            "nombre_tramite": "Trámite",
            **{f"fp_pct_{yr}": yr for yr in YEARS},
        })
        yr_cols_tabla = [yr for yr in YEARS if yr in df_evol_tabla.columns]
        styled_evol = df_evol_tabla.style.map(color_fp_css, subset=yr_cols_tabla)
        st.dataframe(styled_evol, use_container_width=True, hide_index=True)

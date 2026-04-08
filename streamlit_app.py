"""
Dashboard CSEU · Benchmarking Institucional
Calidad de Servicio y Experiencia Usuaria — DIPRES
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from pathlib import Path

st.set_page_config(
    page_title="CSEU · Benchmarking Institucional",
    page_icon="🏛️",
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

# ─── Paleta ────────────────────────────────────────────────
C_OK   = "#1e8449"
C_WARN = "#d35400"
C_BAD  = "#c0392b"
C_BLUE = "#1a5276"
C_GOLD = "#d4ac0d"
C_GRAY = "#aab7b8"

YEARS = ["2022", "2023", "2024", "2025"]

# (col, n_col, n_min, lower_is_better, suffix)
MODULOS = {
    "📋 Reclamos — % respondidos":    ("rec_pct_2025",  "rec_n_2025",   10, False, "%"),
    "📋 Reclamos — días promedio":     ("rec_prom_2025", "rec_n_2025",   10, True,  "d"),
    "📄 SAIP — % respondidas":         ("saip_pct_2025", "saip_n_2025",  10, False, "%"),
    "📄 SAIP — días promedio":          ("saip_prom_2025","saip_n_2025",  10, True,  "d"),
    "⏱️ Trámites en plazo":            ("tram_pct_2025", "tram_n_2025",  50, False, "%"),
}

def sem_color(v, ok=90, warn=70):
    if pd.isna(v): return C_GRAY
    return C_OK if v >= ok else (C_WARN if v >= warn else C_BAD)

def sem_emoji(v, ok=90, warn=70):
    if pd.isna(v): return "⚫"
    return "🟢" if v >= ok else ("🟡" if v >= warn else "🔴")

def fmt(v):
    return f"{v:.1f}%" if pd.notna(v) else "N/D"

def bg_color(v):
    """Para Styler.map — devuelve CSS según valor."""
    if not isinstance(v, (int, float)) or pd.isna(v):
        return ""
    if v >= 90: return f"background-color: {C_OK}22"
    if v >= 70: return f"background-color: {C_WARN}22"
    return f"background-color: {C_BAD}22"

# ─── Carga de datos ────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "Información Sistema"

@st.cache_data(show_spinner="Cargando datos…")
def load_data():
    # Maestro instituciones
    cat = pd.read_excel(DATA_DIR / "Categorización Sistema CSEU 2025 1.xlsx")
    cat = cat.rename(columns={
        "codigo_interno_SCSEU": "cod",
        "MINISTERIO":           "ministerio",
        "SERVICIO":             "servicio_maestro",
        "Categoría funcional":  "categoria",
        "ETAPA":                "etapa",
        "COMPROMETE SISTEMA CON MESU (final)": "aplica_mesu",
    })
    cat["cod"] = cat["cod"].astype(str)

    # Reclamos
    rec = pd.read_excel(DATA_DIR / "reclamos_consolidado_2025.xlsx")
    rec["cod"] = rec["codigo_interno_SCSEU"].astype(str)
    for yr in YEARS:
        rec[f"rec_n_{yr}"]      = pd.to_numeric(rec[f"{yr}_n_de_reclamos_recibidos_al_ano"], errors="coerce")
        rec[f"rec_resp_{yr}"]   = pd.to_numeric(rec[f"{yr}_n_de_reclamos_respondidos_en_el_ano"], errors="coerce")
        rec[f"rec_pct_{yr}"]    = pd.to_numeric(rec[f"{yr}_respondidos"], errors="coerce")
        rec[f"rec_prom_{yr}"]   = pd.to_numeric(rec[f"{yr}_promedio_tiempo_de_respuesta"], errors="coerce")
        rec[f"rec_fp_n_{yr}"]   = pd.to_numeric(rec[f"{yr}_n_de_reclamos_respondidos_en_mas_de_20_dias_habiles_en_el_ano"], errors="coerce")
        rec[f"rec_fp_pct_{yr}"] = pd.to_numeric(rec[f"{yr}_respondidos_en_mas_de_20_dias_habiles"], errors="coerce")
    rec = rec[["cod", "nombre_institucion"] + [
        f"{m}_{yr}" for yr in YEARS for m in ("rec_n", "rec_resp", "rec_pct", "rec_prom", "rec_fp_n", "rec_fp_pct")
    ]]

    # SAIP
    saip = pd.read_excel(DATA_DIR / "saip_consolidado_2025.xlsx")
    saip["cod"] = saip["codigo_interno_SCSEU"].astype(str)
    for yr in YEARS:
        saip[f"saip_n_{yr}"]      = pd.to_numeric(saip[f"{yr}_n_de_saip_recibidas_al_ano"], errors="coerce")
        saip[f"saip_resp_{yr}"]   = pd.to_numeric(saip[f"{yr}_n_de_saip_respondidas_en_el_ano"], errors="coerce")
        saip[f"saip_pct_{yr}"]    = pd.to_numeric(saip[f"{yr}_respondidas"], errors="coerce")
        saip[f"saip_prom_{yr}"]   = pd.to_numeric(saip[f"{yr}_promedio_tiempo_de_respuesta"], errors="coerce")
        saip[f"saip_fp_n_{yr}"]   = pd.to_numeric(saip[f"{yr}_n_de_saip_respondidas_en_mas_de_20_dias_habiles"], errors="coerce")
        saip[f"saip_fp_pct_{yr}"] = pd.to_numeric(saip[f"{yr}_respondidas_en_mas_de_20_dias_habiles"], errors="coerce")
    saip_cols = ["cod", "nombre_institucion"] + [
        f"{m}_{yr}" for yr in YEARS for m in ("saip_n", "saip_resp", "saip_pct", "saip_prom", "saip_fp_n", "saip_fp_pct")
    ]
    saip = saip[[c for c in saip_cols if c in saip.columns]]

    # Trámites → % en plazo por trámite, luego promedio simple por institución
    # (cada trámite pesa igual, independiente de su volumen de transacciones)
    tram = pd.read_excel(DATA_DIR / "tramites_consolidado_2025.xlsx")
    tram["cod"] = tram["codigo_interno_SCSEU"].astype(str)
    for yr in YEARS:
        tram[f"t_n_{yr}"]     = pd.to_numeric(tram[f"{yr}_n_transacciones_gestionadas_en_el_ano"], errors="coerce")
        tram[f"t_fuera_{yr}"] = pd.to_numeric(tram[f"{yr}_n_transacciones_gestionadas_en_un_plazo_mayor_al_esperado"], errors="coerce")
        # % en plazo de cada trámite individualmente
        tram[f"t_pct_{yr}"] = np.where(
            tram[f"t_n_{yr}"] > 0,
            100 - tram[f"t_fuera_{yr}"] / tram[f"t_n_{yr}"] * 100,
            np.nan,
        )

    agg_fns = {"nombre_institucion": "first"}
    for yr in YEARS:
        agg_fns[f"t_pct_{yr}"] = "mean"   # promedio simple: cada trámite pesa igual
        agg_fns[f"t_n_{yr}"]   = "sum"    # total transacciones (referencia)

    tram_agg = tram.groupby("cod").agg(agg_fns).reset_index()
    for yr in YEARS:
        tram_agg[f"tram_pct_{yr}"] = tram_agg[f"t_pct_{yr}"]
        tram_agg[f"tram_n_{yr}"]   = tram_agg[f"t_n_{yr}"]
    tram_cols = ["cod"] + [f"{m}_{yr}" for yr in YEARS for m in ("tram_pct", "tram_n")]
    tram_agg = tram_agg[tram_cols]

    # Join maestro
    master = (
        cat
        .merge(rec,      on="cod", how="left")
        .merge(saip,     on="cod", how="left", suffixes=("", "_saip"))
        .merge(tram_agg, on="cod", how="left")
    )
    master["nombre"] = (
        master["nombre_institucion"].fillna(master["servicio_maestro"])
        .str.strip().str.title()
    )

    # Mantener solo etapas válidas del sistema (excluye SAIP y filas basura del Excel)
    master = master[master["etapa"].isin(["Etapa 1", "Etapa 2", "Etapa 3"])].copy()

    # Máscara de datos suficientes por módulo (2025)
    master["tiene_rec"]  = master["rec_n_2025"].fillna(0)  > 10
    master["tiene_saip"] = master["saip_n_2025"].fillna(0) > 10
    master["tiene_tram"] = master["tram_n_2025"].fillna(0) > 50
    master["n_mods"]     = master[["tiene_rec","tiene_saip","tiene_tram"]].sum(axis=1)

    return master, tram


master, tram_raw = load_data()

# ─── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏛️ CSEU · Benchmarking")
    st.caption("Calidad de Servicio y Experiencia Usuaria  \nSecretaría de Modernización · Ministerio de Hacienda")
    st.divider()

    ministerios = ["Todos"] + sorted(master["ministerio"].dropna().unique())
    min_sel = st.selectbox("Ministerio", ministerios)

    categorias = ["Todas"] + sorted(master["categoria"].dropna().unique())
    cat_sel = st.selectbox("Categoría funcional", categorias)

    st.divider()
    st.caption("ℹ️ 2025 = enero–junio (parcial)  \nUmbral: ≥11 reclamos/SAIP · ≥51 trámites")

# ─── Filtro global ─────────────────────────────────────────
df = master.copy()
if min_sel != "Todos":
    df = df[df["ministerio"] == min_sel]
if cat_sel != "Todas":
    df = df[df["categoria"] == cat_sel]

# ─── Tabs ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Resumen Ejecutivo",
    "🏆 Ranking",
    "📈 Evolución Temporal",
    "🔍 Por Categoría",
])


# ══════════════════════════════════════════════════════════
# TAB 1 — RESUMEN EJECUTIVO
# ══════════════════════════════════════════════════════════
with tab1:
    st.title("Panorama 2025 — Desempeño institucional")
    st.caption(
        f"Filtros activos: Ministerio = **{min_sel}** · Categoría = **{cat_sel}**"
    )

    # ── KPI bloques por módulo ─────────────────────────────
    col_r, col_s, col_t = st.columns(3)

    def kpi_modulo(col, label, n_col, resp_col, pct_col, n_min, vol_label):
        sub = df[df[n_col].fillna(0) > n_min]
        tot_n    = int(sub[n_col].sum())
        tot_resp = int(sub[resp_col].sum()) if resp_col in sub.columns else None
        pct_nac  = tot_resp / tot_n * 100 if (tot_resp and tot_n > 0) else None
        n_inst   = sub[pct_col].notna().sum()
        buenos   = (sub[pct_col] >= 90).sum()
        regulares= ((sub[pct_col] >= 70) & (sub[pct_col] < 90)).sum()
        criticos = (sub[pct_col] < 70).sum()

        with col:
            st.markdown(f"### {label}")
            st.metric(vol_label, f"{tot_n:,.0f}")
            if pct_nac is not None:
                st.metric("% respondidos (nacional)", f"{pct_nac:.1f}%")
            st.markdown(
                f"🟢 **{buenos}** buenas &nbsp;·&nbsp; "
                f"🟡 **{regulares}** regulares &nbsp;·&nbsp; "
                f"🔴 **{criticos}** críticas  \n"
                f"<small>({n_inst} instituciones con datos)</small>",
                unsafe_allow_html=True,
            )
            st.divider()
            st.caption("**Peores (mínimo de datos):**")
            worst = sub[sub[pct_col].notna()].nsmallest(4, pct_col)
            for _, r in worst.iterrows():
                st.caption(
                    f"{sem_emoji(r[pct_col])} {r['nombre'][:44]}  \n"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;**{fmt(r[pct_col])}**"
                )

    def kpi_fuera_plazo(col, modulo, fp_n_col, fp_pct_col, n_col, n_min):
        """Métricas de respondidos fuera de plazo (>20 días hábiles)."""
        sub = df[df[n_col].fillna(0) > n_min]
        tot_fp_n   = sub[fp_n_col].sum()
        avg_fp_pct = sub[fp_pct_col].mean()
        with col:
            st.metric(f"Respondidos >20 días hábiles", f"{tot_fp_n:,.0f}")
            st.metric("% fuera de plazo (promedio)", f"{avg_fp_pct:.1f}%" if pd.notna(avg_fp_pct) else "N/D")
            st.caption("**Peores (mayor % fuera de plazo):**")
            worst_fp = sub[sub[fp_pct_col].notna()].nlargest(4, fp_pct_col)
            for _, r in worst_fp.iterrows():
                st.caption(
                    f"🔴 {r['nombre'][:44]}  \n"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;**{fmt(r[fp_pct_col])}** fuera de plazo"
                )

    kpi_modulo(col_r, "📋 Reclamos",
               "rec_n_2025", "rec_resp_2025", "rec_pct_2025", 10, "Recibidos (2025)")
    kpi_fuera_plazo(col_r, "rec", "rec_fp_n_2025", "rec_fp_pct_2025", "rec_n_2025", 10)

    kpi_modulo(col_s, "📄 SAIP — Transparencia",
               "saip_n_2025", "saip_resp_2025", "saip_pct_2025", 10, "Recibidas (2025)")
    kpi_fuera_plazo(col_s, "saip", "saip_fp_n_2025", "saip_fp_pct_2025", "saip_n_2025", 10)

    with col_t:
        sub_t = df[df["tram_n_2025"].fillna(0) > 50]
        tot_trans  = int(sub_t["tram_n_2025"].sum())
        pct_plazo  = sub_t["tram_pct_2025"].mean()
        n_inst_t   = sub_t["tram_pct_2025"].notna().sum()
        buenos_t   = (sub_t["tram_pct_2025"] >= 90).sum()
        regulares_t= ((sub_t["tram_pct_2025"] >= 70) & (sub_t["tram_pct_2025"] < 90)).sum()
        criticos_t = (sub_t["tram_pct_2025"] < 70).sum()

        st.markdown("### ⏱️ Trámites en plazo")
        st.caption("Promedio simple del % en plazo de cada trámite reportado — cada trámite pesa igual, independiente de su volumen de transacciones.")
        st.metric("Transacciones (2025)", f"{tot_trans:,.0f}")
        st.metric("% en plazo (promedio)", f"{pct_plazo:.1f}%")
        st.markdown(
            f"🟢 **{buenos_t}** buenas &nbsp;·&nbsp; "
            f"🟡 **{regulares_t}** regulares &nbsp;·&nbsp; "
            f"🔴 **{criticos_t}** críticas  \n"
            f"<small>({n_inst_t} instituciones con datos)</small>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption("**Peores (mínimo 50 trans.):**")
        worst_t = sub_t[sub_t["tram_pct_2025"].notna()].nsmallest(4, "tram_pct_2025")
        for _, r in worst_t.iterrows():
            st.caption(
                f"{sem_emoji(r['tram_pct_2025'])} {r['nombre'][:44]}  \n"
                f"&nbsp;&nbsp;&nbsp;&nbsp;**{fmt(r['tram_pct_2025'])}**"
            )

    # ── Distribuciones por módulo ──────────────────────────
    st.divider()
    st.subheader("Distribución de instituciones por módulo")

    def dist_chart(data_col, n_col, n_min, titulo, height=270):
        sub = master[master[n_col].fillna(0) > n_min][[data_col]].dropna()
        bins = [0, 50, 70, 80, 90, 95, 100.01]
        labels = ["<50%", "50–69%", "70–79%", "80–89%", "90–94%", "95–100%"]
        colores = [C_BAD, C_BAD, C_WARN, C_WARN, C_OK, C_OK]
        sub["rango"] = pd.cut(sub[data_col], bins=bins, labels=labels, right=False)
        conteo = sub["rango"].value_counts().reindex(labels, fill_value=0).reset_index()
        conteo.columns = ["rango", "n"]
        fig = go.Figure(go.Bar(
            x=conteo["rango"], y=conteo["n"],
            marker_color=colores,
            text=conteo["n"], textposition="outside",
        ))
        y_max = conteo["n"].max()
        fig.update_layout(
            title=titulo, height=height,
            margin=dict(t=35, b=20, l=20, r=20),
            yaxis=dict(title="N° instituciones", range=[0, y_max * 1.2]),
            xaxis=dict(title=""),
            showlegend=False,
        )
        return fig

    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        st.plotly_chart(dist_chart("rec_pct_2025",  "rec_n_2025",  10,
                                    "📋 Reclamos — % respondidos"),
                         use_container_width=True)
    with dc2:
        st.plotly_chart(dist_chart("saip_pct_2025", "saip_n_2025", 10,
                                    "📄 SAIP — % respondidas"),
                         use_container_width=True)
    with dc3:
        st.plotly_chart(dist_chart("tram_pct_2025", "tram_n_2025", 50,
                                    "⏱️ Trámites — % en plazo"),
                         use_container_width=True)
        st.caption("Promedio simple por institución: cada trámite pesa igual.")

    # ── Por categoría funcional ────────────────────────────
    st.divider()
    st.subheader("Promedio por categoría funcional")

    cat_avg = (
        master.groupby("categoria")
        .agg(
            rec_prom  = ("rec_pct_2025",  lambda x: x[master.loc[x.index,"rec_n_2025"].fillna(0)  > 10].mean()),
            saip_prom = ("saip_pct_2025", lambda x: x[master.loc[x.index,"saip_n_2025"].fillna(0) > 10].mean()),
            tram_prom = ("tram_pct_2025", lambda x: x[master.loc[x.index,"tram_n_2025"].fillna(0) > 50].mean()),
        )
        .reset_index()
        .sort_values("rec_prom", ascending=True)
    )

    fig_cat = go.Figure()
    for col, label, color in [
        ("rec_prom",  "📋 Reclamos",  C_BLUE),
        ("saip_prom", "📄 SAIP",      C_GOLD),
        ("tram_prom", "⏱️ Trámites",  C_OK),
    ]:
        fig_cat.add_trace(go.Bar(
            x=cat_avg[col],
            y=cat_avg["categoria"],
            name=label,
            orientation="h",
            marker_color=color,
            opacity=0.85,
            text=[f"{v:.1f}%" if pd.notna(v) else "" for v in cat_avg[col]],
            textposition="outside",
        ))
    fig_cat.update_layout(
        barmode="group", height=320,
        margin=dict(t=10, b=30, l=200, r=90),
        xaxis=dict(range=[0, 115], ticksuffix="%", title=""),
        yaxis=dict(title=""),
        legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig_cat, use_container_width=True)


# ══════════════════════════════════════════════════════════
# TAB 2 — RANKING
# ══════════════════════════════════════════════════════════
with tab2:
    st.title("Ranking de Instituciones 2025")

    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    with ctrl1:
        modulo_sel = st.radio(
            "Ordenar por módulo",
            list(MODULOS.keys()),
            horizontal=True,
        )
    with ctrl2:
        orden = st.radio("Orden", ["Mejor → Peor", "Peor → Mejor"], horizontal=True)
    with ctrl3:
        n_max = max(1, len(df))
        n_show = st.number_input("Mostrar", min_value=1,
                                  max_value=n_max, value=min(40, n_max), step=5)

    val_col, n_col, n_min, lower_better, suffix = MODULOS[modulo_sel]

    # Para tiempo (lower_better): "Mejor → Peor" = ascendente; invertir lógica
    sort_asc = (orden == "Mejor → Peor") if lower_better else (orden == "Peor → Mejor")

    df_rank = df[df[n_col].fillna(0) > n_min].copy()
    df_rank = df_rank.sort_values(val_col, ascending=sort_asc).head(n_show)
    df_rank["#"] = range(1, len(df_rank) + 1)

    st.caption(
        f"Mostrando **{len(df_rank)}** instituciones con datos en **{modulo_sel}**"
        f" (de {len(df)} totales con filtros activos)"
        + ("  \n⚠️ Para tiempos: **menor = mejor**." if lower_better else "")
    )

    # Colores: para tiempos invertir umbrales (≤5d verde, ≤15d naranja, >15d rojo)
    if lower_better:
        bar_colors = [
            C_GRAY if pd.isna(v) else C_OK if v <= 5 else C_WARN if v <= 15 else C_BAD
            for v in df_rank[val_col]
        ]
        fmt_val = lambda v: f"{v:.1f}d" if pd.notna(v) else "N/D"
        x_range = [0, df_rank[val_col].max() * 1.2 if len(df_rank) > 0 else 30]
        x_title = "Días hábiles promedio"
        vlines   = []
    else:
        bar_colors = [sem_color(v) for v in df_rank[val_col]]
        fmt_val = fmt
        x_range = [0, 118]
        x_title = modulo_sel
        vlines   = [(90, C_OK, "90%"), (70, C_WARN, "70%")]

    fig_rank = go.Figure(go.Bar(
        x=df_rank[val_col],
        y=df_rank["nombre"].str[:50],
        orientation="h",
        marker_color=bar_colors,
        text=[fmt_val(v) for v in df_rank[val_col]],
        textposition="outside",
        customdata=df_rank[["ministerio", "categoria",
                             "rec_pct_2025", "rec_prom_2025",
                             "saip_pct_2025", "saip_prom_2025",
                             "tram_pct_2025"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Ministerio: %{customdata[0]}<br>"
            "Categoría: %{customdata[1]}<br>"
            "📋 Reclamos: %{customdata[2]:.1f}% · %{customdata[3]:.1f}d<br>"
            "📄 SAIP: %{customdata[4]:.1f}% · %{customdata[5]:.1f}d<br>"
            "⏱️ Trámites: %{customdata[6]:.1f}%<extra></extra>"
        ),
    ))
    for x_val, color, label in vlines:
        fig_rank.add_vline(x=x_val, line_dash="dash", line_color=color,
                           opacity=0.5, annotation_text=label)
    fig_rank.update_layout(
        height=max(450, len(df_rank) * 22),
        margin=dict(t=10, b=40, l=10, r=80),
        xaxis=dict(range=x_range, ticksuffix=suffix, title=x_title),
        yaxis=dict(autorange="reversed", title=""),
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    # Tabla comparativa (los 3 módulos juntos)
    with st.expander("📋 Ver tabla completa (los 3 módulos)", expanded=True):
        df_tabla = df[df["n_mods"] >= 1][
            ["nombre", "ministerio", "categoria",
             "rec_pct_2025", "rec_prom_2025", "rec_fp_pct_2025", "rec_n_2025",
             "saip_pct_2025", "saip_prom_2025", "saip_fp_pct_2025", "saip_n_2025",
             "tram_pct_2025", "tram_n_2025"]
        ].copy()

        df_tabla = df_tabla.sort_values(val_col, ascending=sort_asc)

        df_tabla = df_tabla.rename(columns={
            "nombre":            "Institución",
            "ministerio":        "Ministerio",
            "categoria":         "Categoría",
            "rec_pct_2025":      "📋 Resp. %",
            "rec_prom_2025":     "📋 Días prom.",
            "rec_fp_pct_2025":   "📋 >20d %",
            "rec_n_2025":        "N rec.",
            "saip_pct_2025":     "📄 Resp. %",
            "saip_prom_2025":    "📄 Días prom.",
            "saip_fp_pct_2025":  "📄 >20d %",
            "saip_n_2025":       "N SAIP",
            "tram_pct_2025":     "⏱️ Trámites %",
            "tram_n_2025":       "N trans.",
        })

        pct_cols  = ["📋 Resp. %", "📄 Resp. %", "⏱️ Trámites %"]
        fp_cols   = ["📋 >20d %", "📄 >20d %"]
        dias_cols = ["📋 Días prom.", "📄 Días prom."]
        int_cols  = ["N rec.", "N SAIP", "N trans."]

        def bg_dias(v):
            """Para días de respuesta: verde si ≤5, naranja si ≤15, rojo si >15."""
            if not isinstance(v, (int, float)) or pd.isna(v): return ""
            if v <= 5:  return f"background-color: {C_OK}22"
            if v <= 15: return f"background-color: {C_WARN}22"
            return f"background-color: {C_BAD}22"

        def bg_fp(v):
            """Para columnas de fuera de plazo: rojo si alto, verde si bajo."""
            if not isinstance(v, (int, float)) or pd.isna(v): return ""
            if v <= 5:  return f"background-color: {C_OK}22"
            if v <= 20: return f"background-color: {C_WARN}22"
            return f"background-color: {C_BAD}22"

        styled = (
            df_tabla.style
            .map(bg_color, subset=pct_cols)
            .map(bg_fp,    subset=fp_cols)
            .map(bg_dias,  subset=dias_cols)
            .format({c: fmt for c in pct_cols + fp_cols})
            .format({c: lambda v: f"{v:.1f}d" if pd.notna(v) else "N/D" for c in dias_cols})
            .format({c: lambda v: f"{int(v):,}" if pd.notna(v) else "N/D" for c in int_cols})
        )
        st.dataframe(styled, use_container_width=True, height=480)


# ══════════════════════════════════════════════════════════
# TAB 3 — EVOLUCIÓN TEMPORAL
# ══════════════════════════════════════════════════════════
with tab3:
    st.title("Evolución Temporal 2022–2025")

    # ── Helpers reutilizables ──────────────────────────────
    def evol_volumen(n_col, resp_col, label_n, label_r, title):
        """Barras recibidos/respondidos + línea % por año."""
        rows = []
        for yr in YEARS:
            sub = df[df[f"{n_col}_{yr}"].fillna(0) > 0]
            tot_n    = sub[f"{n_col}_{yr}"].sum()
            tot_resp = sub[f"{resp_col}_{yr}"].sum()
            pct      = tot_resp / tot_n * 100 if tot_n > 0 else None
            rows.append({"Año": yr, "n": tot_n, "resp": tot_resp, "pct": pct})
        dfev = pd.DataFrame(rows)
        fig = go.Figure()
        fig.add_bar(x=dfev["Año"], y=dfev["n"],    name=label_n,
                    marker_color="#2e86c1", opacity=0.85)
        fig.add_bar(x=dfev["Año"], y=dfev["resp"],  name=label_r,
                    marker_color=C_OK, opacity=0.9)
        fig.add_trace(go.Scatter(
            x=dfev["Año"], y=dfev["pct"], name="% respondidos",
            yaxis="y2", mode="lines+markers",
            line=dict(color=C_GOLD, width=3), marker=dict(size=10),
        ))
        fig.update_layout(
            title=title, barmode="group", height=320,
            yaxis2=dict(overlaying="y", side="right", ticksuffix="%",
                        range=[70, 105], showgrid=False),
            legend=dict(orientation="h", y=-0.28),
            margin=dict(t=40, b=70, r=70),
        )
        return fig

    def evol_tiempo(prom_col, n_col, n_min, title):
        """Boxplot de tiempo promedio de respuesta por año (mediana nacional)."""
        rows = []
        for yr in YEARS:
            sub = df[df[f"{n_col}_{yr}"].fillna(0) > n_min][f"{prom_col}_{yr}"].dropna()
            if len(sub) == 0:
                continue
            rows.append({
                "Año": yr,
                "mediana": sub.median(),
                "p25":     sub.quantile(0.25),
                "p75":     sub.quantile(0.75),
                "min":     sub.min(),
                "max":     sub.max(),
                "n":       len(sub),
            })
        dfev = pd.DataFrame(rows)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dfev["Año"], y=dfev["mediana"],
            name="Mediana",
            marker_color=C_BLUE, opacity=0.85,
            text=[f"{v:.1f}d" for v in dfev["mediana"]],
            textposition="outside",
            error_y=dict(
                type="data",
                symmetric=False,
                array=       (dfev["p75"] - dfev["mediana"]).tolist(),
                arrayminus=  (dfev["mediana"] - dfev["p25"]).tolist(),
                visible=True,
                color="#888",
                thickness=2,
            ),
        ))
        fig.update_layout(
            title=title, height=300,
            yaxis=dict(title="Días hábiles", rangemode="tozero"),
            margin=dict(t=40, b=30, r=20),
            showlegend=False,
        )
        return fig

    def scatter_cambio(pct_col, n_col, n_min, xlab, ylab, titulo, caption_txt):
        """Scatter 2022 vs 2025 con diagonal de referencia."""
        d = df[df[f"{n_col}_2022"].fillna(0) > n_min][
            ["nombre", "ministerio", "categoria",
             f"{pct_col}_2022", f"{pct_col}_2025"]
        ].dropna().copy()
        d["delta"] = d[f"{pct_col}_2025"] - d[f"{pct_col}_2022"]
        return d

    # ── Sección 1: Volumen y % respondidos ────────────────
    st.subheader("Volumen y % respondidos")
    col_rv, col_sv = st.columns(2)
    with col_rv:
        st.plotly_chart(
            evol_volumen("rec_n", "rec_resp", "Recibidos", "Respondidos", "📋 Reclamos"),
            use_container_width=True)
    with col_sv:
        st.plotly_chart(
            evol_volumen("saip_n", "saip_resp", "Recibidas", "Respondidas", "📄 SAIP"),
            use_container_width=True)

    # ── Sección 2: Tiempos de respuesta ───────────────────
    st.divider()
    st.subheader("Tiempo de respuesta")
    st.caption("Mediana entre instituciones (barras) con rango intercuartil P25–P75 (bigotes). Solo instituciones con datos suficientes.")

    col_rt, col_st = st.columns(2)
    with col_rt:
        st.plotly_chart(
            evol_tiempo("rec_prom", "rec_n", 10, "📋 Reclamos — días promedio de respuesta"),
            use_container_width=True)
    with col_st:
        st.plotly_chart(
            evol_tiempo("saip_prom", "saip_n", 10, "📄 SAIP — días promedio de respuesta"),
            use_container_width=True)

    # ── Sección 3: Fuera de plazo >20 días hábiles ────────
    st.divider()
    st.subheader("Respondidos fuera de plazo (>20 días hábiles)")

    def evol_fp(fp_pct_col, n_col, n_min, title):
        """Línea de % promedio fuera de plazo por año."""
        rows = []
        for yr in YEARS:
            sub = df[df[f"{n_col}_{yr}"].fillna(0) > n_min]
            avg_pct = sub[f"{fp_pct_col}_{yr}"].mean()
            rows.append({"Año": yr, "pct_prom": avg_pct})
        dfev = pd.DataFrame(rows)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dfev["Año"], y=dfev["pct_prom"],
            name="% promedio fuera de plazo",
            mode="lines+markers",
            line=dict(color=C_BAD, width=3), marker=dict(size=10),
            text=[f"{v:.1f}%" if pd.notna(v) else "" for v in dfev["pct_prom"]],
            textposition="top center",
        ))
        fig.update_layout(
            title=title, height=300,
            yaxis=dict(title="% fuera de plazo (promedio)", ticksuffix="%", rangemode="tozero"),
            showlegend=False,
            margin=dict(t=40, b=30, r=20),
        )
        return fig

    st.caption(
        "Promedio simple del % de casos respondidos fuera de plazo por institución — "
        "cada institución pesa igual independiente de su volumen. "
        "Solo se incluyen instituciones con datos suficientes en cada año."
    )
    col_rfp, col_sfp = st.columns(2)
    with col_rfp:
        st.plotly_chart(
            evol_fp("rec_fp_pct", "rec_n", 10, "📋 Reclamos — % respondidos >20 días hábiles"),
            use_container_width=True)
    with col_sfp:
        st.plotly_chart(
            evol_fp("saip_fp_pct", "saip_n", 10, "📄 SAIP — % respondidas >20 días hábiles"),
            use_container_width=True)

    # ── Sección 4: Scatterplots 2022 → 2025 ──────────────
    st.divider()
    st.subheader("Cambio individual 2022 → 2025 — % respondidos")
    st.caption("Puntos **sobre** la diagonal = mejoraron · **bajo** la diagonal = empeoraron · tamaño proporcional al cambio absoluto.")

    def render_scatter(pct_col, n_col, n_min, xlab, ylab, titulo):
        d = scatter_cambio(pct_col, n_col, n_min, xlab, ylab, titulo, "")
        if len(d) == 0:
            st.info("Sin datos suficientes.")
            return
        vmin = max(0, d[[f"{pct_col}_2022", f"{pct_col}_2025"]].min().min() - 5)
        vmax = min(100, d[[f"{pct_col}_2022", f"{pct_col}_2025"]].max().max() + 3)
        fig = px.scatter(
            d,
            x=f"{pct_col}_2022", y=f"{pct_col}_2025",
            color="delta",
            color_continuous_scale=[[0, C_BAD], [0.4, C_WARN], [0.6, C_WARN], [1, C_OK]],
            range_color=[-45, 45],
            size=d["delta"].abs().clip(lower=2),
            size_max=18,
            hover_name="nombre",
            hover_data={"delta": ":.1f", "ministerio": True,
                        f"{pct_col}_2022": ":.1f", f"{pct_col}_2025": ":.1f"},
            labels={
                f"{pct_col}_2022": xlab,
                f"{pct_col}_2025": ylab,
                "delta": "Cambio (pp)",
            },
        )
        fig.add_shape(type="line", x0=vmin, y0=vmin, x1=vmax, y1=vmax,
                      line=dict(color="gray", dash="dot", width=1))
        fig.update_layout(
            title=titulo, height=380,
            margin=dict(t=40, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

        col_m, col_e = st.columns(2)
        with col_m:
            st.markdown("🟢 **Mejoraron más**")
            for _, r in d.nlargest(6, "delta").iterrows():
                st.caption(
                    f"**{r['nombre'][:46]}**  \n"
                    f"{r[f'{pct_col}_2022']:.1f}% → {r[f'{pct_col}_2025']:.1f}%  "
                    f"(**{r['delta']:+.1f} pp**)"
                )
        with col_e:
            st.markdown("🔴 **Empeoraron más**")
            for _, r in d.nsmallest(6, "delta").iterrows():
                st.caption(
                    f"**{r['nombre'][:46]}**  \n"
                    f"{r[f'{pct_col}_2022']:.1f}% → {r[f'{pct_col}_2025']:.1f}%  "
                    f"(**{r['delta']:+.1f} pp**)"
                )

    sc1, sc2, sc3 = st.tabs([
        "📋 Reclamos — % respondidos",
        "📄 SAIP — % respondidas",
        "⏱️ Trámites — % en plazo",
    ])
    with sc1:
        render_scatter("rec_pct",  "rec_n",  50,
                       "% respondidos 2022", "% respondidos 2025",
                       "📋 Reclamos: % respondidos 2022 vs 2025")
    with sc2:
        render_scatter("saip_pct", "saip_n", 20,
                       "% respondidas 2022", "% respondidas 2025",
                       "📄 SAIP: % respondidas 2022 vs 2025")
    with sc3:
        render_scatter("tram_pct", "tram_n", 50,
                       "% en plazo 2022", "% en plazo 2025",
                       "⏱️ Trámites: % en plazo 2022 vs 2025")


# ══════════════════════════════════════════════════════════
# TAB 4 — POR CATEGORÍA
# ══════════════════════════════════════════════════════════
with tab4:
    st.title("Comparación por Categoría Funcional")

    cat_det = st.selectbox(
        "Seleccionar categoría",
        sorted(master["categoria"].dropna().unique()),
    )

    df_det = master[master["categoria"] == cat_det].copy()

    # KPIs de la categoría
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Instituciones en categoría", len(df_det))
    for col, label, n_col, n_min, dest in [
        ("rec_pct_2025",  "📋 Reclamos (prom.)",  "rec_n_2025",  10, c2),
        ("saip_pct_2025", "📄 SAIP (prom.)",       "saip_n_2025", 10, c3),
        ("tram_pct_2025", "⏱️ Trámites (prom.)",   "tram_n_2025", 50, c4),
    ]:
        sub = df_det[df_det[n_col].fillna(0) > n_min][col].dropna()
        val = sub.mean() if len(sub) > 0 else None
        dest.metric(label, fmt(val))

    # Heatmap — vista principal
    st.subheader(f"Desempeño por institución — {cat_det}")
    st.caption("Colores: 🟢 ≥90% · 🟡 70–89% · 🔴 <70% · ⚫ sin datos suficientes")

    hm_data = df_det.set_index("nombre")[
        ["rec_pct_2025", "saip_pct_2025", "tram_pct_2025"]
    ].copy()
    hm_data.columns = ["📋 Reclamos", "📄 SAIP", "⏱️ Trámites en plazo"]
    hm_data.index   = hm_data.index.str[:48]
    hm_data = hm_data.sort_values("📋 Reclamos", ascending=False, na_position="last")

    z    = hm_data.values.astype(float)
    text = [[fmt(v) for v in row] for row in z]

    fig_hm = go.Figure(go.Heatmap(
        z=z,
        x=hm_data.columns.tolist(),
        y=hm_data.index.tolist(),
        colorscale=[[0, C_BAD], [0.4, C_WARN], [0.55, C_WARN], [1, C_OK]],
        zmin=0, zmax=100,
        text=text, texttemplate="%{text}",
        showscale=True,
        colorbar=dict(ticksuffix="%", title=""),
    ))
    fig_hm.update_layout(
        height=max(320, len(df_det) * 30),
        margin=dict(t=10, b=40, l=10, r=20),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

    # Ranking por módulo dentro de categoría
    st.subheader("Ranking dentro de la categoría")
    mod_cat = st.radio(
        "Ver ranking por",
        list(MODULOS.keys()),
        horizontal=True,
        key="mod_cat",
    )
    val_col_cat, n_col_cat, n_min_cat, lower_cat, _ = MODULOS[mod_cat]

    df_cat_rank = df_det[df_det[n_col_cat].fillna(0) > n_min_cat].copy()
    df_cat_rank = df_cat_rank.sort_values(val_col_cat, ascending=False)

    if len(df_cat_rank) == 0:
        st.info("No hay instituciones con datos suficientes en este módulo para esta categoría.")
    else:
        avg_cat = df_cat_rank[val_col_cat].mean()
        colors_cat = [sem_color(v) for v in df_cat_rank[val_col_cat]]

        fig_cat_r = go.Figure(go.Bar(
            x=df_cat_rank[val_col_cat],
            y=df_cat_rank["nombre"].str[:48],
            orientation="h",
            marker_color=colors_cat,
            text=[fmt(v) for v in df_cat_rank[val_col_cat]],
            textposition="outside",
        ))
        fig_cat_r.add_vline(x=avg_cat, line_dash="dot", line_color=C_BLUE,
                             annotation_text=f"Prom. {avg_cat:.1f}%",
                             annotation_position="top right")
        fig_cat_r.add_vline(x=90, line_dash="dash", line_color=C_OK,  opacity=0.4)
        fig_cat_r.add_vline(x=70, line_dash="dash", line_color=C_WARN, opacity=0.4)
        fig_cat_r.update_layout(
            height=max(300, len(df_cat_rank) * 26),
            margin=dict(t=20, b=30, l=10, r=80),
            xaxis=dict(range=[0, 118], ticksuffix="%", title=mod_cat),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_cat_r, use_container_width=True)

    # Por ministerio dentro de la categoría
    if df_det["ministerio"].nunique() > 1:
        st.subheader("Por ministerio (dentro de la categoría)")
        min_avg = (
            df_det.groupby("ministerio")
            .agg(
                rec=("rec_pct_2025",  "mean"),
                saip=("saip_pct_2025", "mean"),
                tram=("tram_pct_2025", "mean"),
            )
            .reset_index()
            .sort_values("rec", ascending=True)
        )
        fig_min = go.Figure()
        for col_m, label_m, color_m in [
            ("rec",  "📋 Reclamos",  C_BLUE),
            ("saip", "📄 SAIP",      C_GOLD),
            ("tram", "⏱️ Trámites",  C_OK),
        ]:
            fig_min.add_trace(go.Bar(
                x=min_avg[col_m], y=min_avg["ministerio"],
                name=label_m, orientation="h",
                marker_color=color_m, opacity=0.85,
            ))
        fig_min.update_layout(
            barmode="group", height=max(250, len(min_avg) * 50),
            margin=dict(t=10, b=30, l=10, r=60),
            xaxis=dict(range=[0, 115], ticksuffix="%"),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_min, use_container_width=True)

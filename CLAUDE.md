# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

Dashboard interactivo en **Streamlit (Python)** para el sistema CSEU (Calidad de Servicio y Experiencia Usuaria), Secretaría de Modernización, Ministerio de Hacienda. Permite evaluar el desempeño de 145 instituciones públicas en reclamos, transparencia (SAIP) y trámites, con análisis 2022–2025 y vista evolutiva.

**URL producción:** https://dashboard-cseu.streamlit.app/
**Repositorio:** https://github.com/franvidal-hac/dashboard-cseu

## Cómo ejecutar localmente

```bash
cd "/Users/fran/Desktop/Dashboard Sistema CSEU"
python3 -m streamlit run streamlit_app.py   # dashboard principal
python3 -m streamlit run tramites_app.py    # dashboard de trámites (puerto 8502 si el principal ya está corriendo)
```

## Cómo publicar cambios

```bash
git add streamlit_app.py tramites_app.py   # agregar los archivos modificados
git commit -m "descripción del cambio"
git push https://franvidal-hac:TOKEN@github.com/franvidal-hac/dashboard-cseu.git main
```

Streamlit Community Cloud detecta el push y actualiza la app automáticamente en ~2 minutos. El TOKEN es un Personal Access Token (classic) con scope `repo`, generado en GitHub → Settings → Developer settings → Personal access tokens.

## Estructura de archivos

```
Dashboard Sistema CSEU/
├── streamlit_app.py                               # Dashboard principal (benchmarking general)
├── tramites_app.py                                # Dashboard de trámites (comparación + ficha por institución)
├── requirements.txt                               # Dependencias Python
├── CLAUDE.md                                      # Este archivo
├── app.R                                          # Dashboard anterior en R Shiny (no tocar)
├── Reporte consolidado CSEU 2024.xlsx             # Datos principales 2024 (no usados en Streamlit)
├── Reporte consolidado_SistemaCSEU2025.xlsx       # Datos principales 2025 (no usados en Streamlit)
└── Información Sistema/                           # Fuentes de datos del dashboard Streamlit
    ├── Categorización Sistema CSEU 2025 1.xlsx    # Maestro de instituciones
    ├── reclamos_consolidado_2025.xlsx             # Reclamos 2022–2025
    ├── saip_consolidado_2025.xlsx                 # SAIP (transparencia) 2022–2025
    ├── tramites_consolidado_2025.xlsx             # Trámites 2022–2025
    └── indicadores-proyectos-inversion-2025.xlsx  # Metas de trámites de inversión (aún no integrado)
```

## Arquitectura de datos

**ID de unión:** `codigo_interno_SCSEU` (= `cod` tras renombrar en carga).

**Instituciones incluidas:** 145 — solo etapas válidas (`Etapa 1`, `Etapa 2`, `Etapa 3`). Se excluyen los 21 servicios en etapa `SAIP` y 2 filas basura del Excel maestro.

**Columnas clave tras carga:**

| Prefijo | Módulo | Métricas por año (2022–2025) |
|---|---|---|
| `rec_*` | Reclamos | `rec_n` (recibidos), `rec_resp` (respondidos), `rec_pct` (% respondidos), `rec_prom` (días promedio), `rec_fp_n` / `rec_fp_pct` (respondidos >20 días hábiles) |
| `saip_*` | SAIP | mismo esquema que reclamos (`saip_n`, `saip_resp`, `saip_pct`, `saip_prom`, `saip_fp_n`, `saip_fp_pct`) |
| `tram_*` | Trámites | `tram_pct` (% en plazo, promedio simple por trámite), `tram_n` (total transacciones) |

**Umbrales mínimos de datos para incluir una institución:**
- Reclamos / SAIP: ≥ 11 casos recibidos en el año
- Trámites: ≥ 51 transacciones totales en el año

## Decisiones metodológicas importantes

- **% en plazo de trámites:** promedio simple del % en plazo de cada trámite reportado por la institución. Cada trámite pesa igual, independiente de su volumen de transacciones. El plazo esperado lo define cada institución, por lo que no es directamente comparable entre ellas.
- **% fuera de plazo (reclamos/SAIP):** promedio simple entre instituciones (cada institución pesa igual, sin ponderar por volumen).
- **Sin score compuesto:** los tres módulos (reclamos, SAIP, trámites) se muestran siempre como columnas separadas. No se agrega en un único número.
- **Tiempos (días promedio):** menor = mejor. Umbrales semáforo: ≤5d verde, ≤15d naranja, >15d rojo.
- **Porcentajes (% respondidos, % en plazo):** mayor = mejor. Umbrales: ≥90% verde, ≥70% naranja, <70% rojo.
- **% fuera de plazo en tramites_app.py:** menor = mejor. Umbrales: ≤10% verde, ≤30% naranja, >30% rojo.

## Arquitectura de streamlit_app.py

```
1. Configuración de página y CSS global
2. Constantes: YEARS, MODULOS (dict con 5 campos por módulo)
3. Funciones auxiliares: sem_color, sem_emoji, fmt, bg_color, bg_fp, bg_dias
4. load_data() — @st.cache_data
   ├── Lee 4 archivos Excel de Información Sistema/
   ├── Calcula métricas derivadas (% fp, % en plazo por trámite)
   ├── Agrega trámites por institución (promedio simple)
   ├── Join maestro → master DataFrame (145 filas)
   └── Filtra etapas inválidas
5. Sidebar: filtros de ministerio y categoría funcional → df (subconjunto de master)
6. Tabs:
   ├── Tab 1: Resumen Ejecutivo — KPIs por módulo, distribuciones, por categoría
   ├── Tab 2: Ranking — bar chart + tabla ordenables por cualquier módulo/métrica
   ├── Tab 3: Evolución Temporal — volumen, tiempos, fuera de plazo, scatterplots 2022→2025
   └── Tab 4: Por Categoría — heatmap, ranking dentro de categoría, por ministerio
```

**MODULOS dict:** cada entrada es `(col, n_col, n_min, lower_is_better, suffix)`. Se usa en Ranking (Tab 2) y Por Categoría (Tab 4) para determinar ordenamiento, colores y formato de ejes.

**Filtros globales:** `df` es el DataFrame filtrado por sidebar. Todos los tabs usan `df` excepto los selectores del sidebar (que usan `master` para listar todas las opciones).

## Arquitectura de tramites_app.py

```
1. Configuración de página y CSS global
2. Constantes: YEARS, colores, COLORES_CAT (por categoría), UMBRAL_FP_OK=10, UMBRAL_FP_WARN=30
3. Funciones auxiliares: color_fp, color_fp_css, fmt_pct, fmt_n
4. load_data() — @st.cache_data
   ├── Lee maestro + tramites_consolidado_2025.xlsx
   ├── Calcula fp_pct_{yr} por trámite (fuera/n * 100)
   ├── tram_raw: una fila por trámite con métricas individuales por año
   └── tram_inst: una fila por institución (promedio simple de fp_pct, suma de n)
       → join con maestro (ministerio, categoría, etapa)
5. Session state: inst_cod (None = comparación, str = ficha de institución)
6. Sidebar: filtros ministerio + categoría + selector de año
7. Router:
   ├── Vista A (inst_cod=None): KPIs · Ranking interactivo · Scatter · Tabla comparativa
   └── Vista B (inst_cod=str): Header · KPIs vs. promedio categoría · 3 tabs internos
       ├── Tab 1: Tabla de trámites individuales
       ├── Tab 2: Bar chart comparando trámites de la institución
       └── Tab 3: Líneas de evolución 2022→2025 por trámite
```

**Navegación drill-down:** clic en barra del ranking → `on_select="rerun"` captura `customdata[0]` (cod) → guarda en `st.session_state.inst_cod` → rerenderiza en Vista B. Botón "← Volver" limpia `inst_cod`.

## Pendiente / próximas mejoras

- Integrar `indicadores-proyectos-inversion-2025.xlsx` (metas de trámites de autorización de proyectos de inversión)
- Exportar tabla a Excel desde el dashboard

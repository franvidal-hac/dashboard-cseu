# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

Dashboard interactivo en **R Shiny** para el sistema CSEU (Calidad de Servicio y Experiencia Usuaria) de DIPRES, orientado a las autoridades del Ministerio de Hacienda. Permite evaluar el desempeño de instituciones públicas en reclamos, transparencia (SAIP), trámites y metas de proyectos de inversión, con análisis 2022–2025 y vista evolutiva.

## Cómo ejecutar

```r
# Desde R o RStudio, estando en el directorio del proyecto:
shiny::runApp("app.R")

# O directamente desde la terminal:
Rscript -e "shiny::runApp('app.R')"
```

El dashboard se despliega en ShinyApps.io (ver carpeta `rsconnect/`).

```r
# Para desplegar:
rsconnect::deployApp()
```

## Estructura de archivos

```
Dashboard Sistema CSEU/
├── app.R                                      # App completa (UI + Server en un solo archivo)
├── Reporte consolidado CSEU 2024.xlsx         # Datos principales 2024 (skip=4, sin nombres de columna)
├── Reporte consolidado_SistemaCSEU2025.xlsx   # Datos principales 2025 (skip=6)
├── rsconnect/                                 # Config de despliegue ShinyApps.io
└── Información Sistema/                       # Datos desagregados por módulo
    ├── Categorización Sistema CSEU 2025 1.xlsx        # Maestro de instituciones y categoría funcional
    ├── reclamos_consolidado_2025.xlsx                  # Reclamos 2022–2025 por institución
    ├── saip_consolidado_2025.xlsx                      # SAIP (transparencia) 2022–2025
    ├── tramites_consolidado_2025.xlsx                  # Trámites relevantes 2022–2025
    └── indicadores-proyectos-inversion-2025.xlsx       # Metas de trámites de autorización de inversión
```

## Arquitectura de datos

**ID de unión principal:** `codigo_interno_SCSEU` (equivalente a `cod_servicio` en los reportes consolidados). Todas las fuentes se pueden unir por este código.

**Fuentes de datos:**

| Archivo | Contenido | Cobertura |
|---|---|---|
| `Reporte consolidado*.xlsx` | Resumen agregado por institución: reclamos, SAIP, trámites, satisfacción (MESU), plan de actividades | 2024 y 2025 |
| `reclamos_consolidado_2025.xlsx` | Serie anual: n° recibidos, respondidos, tiempos (promedio/mediana/min/max), plazo >20 días hábiles, metas | 2022–2025 |
| `saip_consolidado_2025.xlsx` | Serie anual: n° recibidas, respondidas, tiempos, % por tramo (≤10, ≤15, ≤20, >20 días hábiles), metas | 2022–2025 |
| `tramites_consolidado_2025.xlsx` | Por trámite: tiempo esperado, promedio/mediana/min/max, n° transacciones, % fuera de plazo | 2022–2025 |
| `indicadores-proyectos-inversion-2025.xlsx` | Metas de 3 indicadores por trámite de autorización de inversión | 2025 |
| `Categorización*.xlsx` | Maestro de 169 instituciones: ministerio, etapa, si aplica MESU, categoría funcional | 2025 |

**Porcentajes en Excel:** los archivos de reportes consolidados almacenan porcentajes como decimales (0.87 = 87%). La función `norm_pct()` normaliza esto automáticamente. Los archivos de `Información Sistema/` almacenan porcentajes ya en escala 0–100.

## Arquitectura de app.R

El archivo sigue esta secuencia:

1. **Helpers** (`safe_num`, `norm_pct`, `fmt_pct`, `fmt_num`, `norm_nombre`) — funciones de limpieza y formato usadas en todo el código.
2. **Carga de datos** — lee los dos reportes consolidados (2024 y 2025), asigna nombres de columna manualmente (los archivos Excel no tienen cabeceras usables), normaliza tipos.
3. **Clasificación de instituciones** — separa entre instituciones presentes en ambos años (para comparación evolutiva) vs. solo en 2025 (instituciones nuevas). El join entre años se hace por **nombre normalizado** (`join_key`) porque los códigos cambian. Hay una tabla de equivalencias `equiv_2024` para instituciones que cambiaron de nombre entre años.
4. **Paleta de colores y funciones de gráficos** — `plot_reclamos()`, `plot_saip()`, `plot_sat_canal()`, `plot_atributos()`, etc. Todos retornan objetos `plotly`.
5. **UI** — definida con `bslib::page_navbar()`, organizada en pestañas por módulo.
6. **Server** — reactivos filtrados por institución seleccionada; cada módulo (reclamos, SAIP, trámites, satisfacción, inversión) tiene su propia sección en el server.

## Convenciones clave

- **Colores semáforo:** `col_ok` (#1e8449 verde) ≥75%, `col_warn` (#d35400 naranja) ≥50%, `col_bad` (#c0392b rojo) <50%. Aplicar con `bar_color(pct)`.
- **Valores faltantes:** mostrar como `"N/D"` usando `fmt_pct()` / `fmt_num()`.
- **Institución "nueva en 2025":** listada en `nuevas_2025`; no tiene datos 2024 para comparación, mostrar solo la vista 2025.
- **Módulo MESU (satisfacción):** solo aplica a instituciones donde `mesu_aplica == "Sí"` en los datos consolidados.
- **Indicadores de inversión:** solo aplican a instituciones y trámites presentes en `indicadores-proyectos-inversion-2025.xlsx`.

## Nuevas funcionalidades planificadas

El proyecto está en fase inicial de expansión. Los objetivos son:

1. **Análisis comparativo entre instituciones** — ranking y benchmarking por categoría funcional y ministerio.
2. **Vista evolutiva 2022–2025** usando los archivos desagregados de `Información Sistema/`.
3. **Dashboard para autoridades** — presentación ejecutiva con foco en "quién lo hace mejor" y "mayores oportunidades de mejora".

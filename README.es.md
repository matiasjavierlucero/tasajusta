# TasaJusta

**Estimador de precio justo para vehículos usados en Argentina.**

TasaJusta analiza publicaciones reales del mercado para decirte cuánto debería valer tu auto — en pesos y en dólares blue. No usa precios de lista ni tablas estáticas: aprende directamente de lo que la gente publica hoy.

---

## ¿Qué hace?

- **Cotizador**: ingresás marca, modelo, año, kilómetros y provincia — el modelo te devuelve el precio estimado según el mercado actual.
- **Cruce con el dólar blue**: cada estimación se expresa también en USD al tipo de cambio informal vigente.
- **Datos frescos**: el pipeline corre semanalmente y reentrena el modelo con las publicaciones más recientes.

---

## Fuente de datos y cumplimiento

Los datos de vehículos provienen de [DeRuedas](https://www.deruedas.com.ar), portal argentino de compraventa de autos usados.

El scraper respeta íntegramente las directivas publicadas en `robots.txt`:

| Directiva | Valor | Cómo la respetamos |
|-----------|-------|-------------------|
| `User-agent: *` / `Allow: /` | Acceso permitido a todas las rutas | No accedemos a rutas privadas ni áreas restringidas |
| `Crawl-delay: 5` | 5 segundos entre requests | Hardcodeado en el scraper (`CRAWL_DELAY = 5`) |
| `ai-train: no` | No usar para entrenar modelos generativos | No usamos los datos para generar texto ni imágenes |

El uso que hacemos es **análisis de mercado de precios** — equivalente a lo que hace cualquier comparador de precios. Extraemos únicamente datos públicos (marca, modelo, año, kilómetros, precio, provincia) de listings ya publicados por los propios usuarios de la plataforma.

La cotización del dólar blue se obtiene de [bluelytics.com.ar](https://api.bluelytics.com.ar/v2/latest), API pública y gratuita.

---

## Arquitectura

```
DeRuedas ──────────────────────────────────────────────────────────────────┐
                                                                           │
                    ETL Pipeline (GitHub Actions — semanal)                │
                                                                           │
  scrape_deruedas.py ──► bronze/ (JSON crudo)                             │
         │                    │                                            │
         │            transform_autos.py ──► silver/ (Parquet limpio)      │
         │                    │                                            │
         │             load_autos.py ──► Supabase (PostgreSQL)             │
         │                    │                                            │
         │              gold_autos.py ──► gold/ (features para ML)         │
         │                    │                                            │
         │             train_lgbm.py ──► S3 tasajusta-models/              │
                                               │                           │
                                               ▼                           │
                                        AWS Lambda                         │
                                     (FastAPI + LightGBM)                  │
                                               │                           │
                                               ▼                           │
                                     Next.js (Vercel)                      │
                                      [frontend]                           │
                                                                           │
bluelytics.com.ar ──► extract_dolar.py ──► S3 bronze ──► Supabase ────────┘
(diario, GitHub Actions)
```

---

## Pipeline de datos — capas medallion

### Bronze — datos crudos

El scraper recorre los tres segmentos de DeRuedas para toda Argentina:

| Segmento | Descripción |
|----------|-------------|
| `0` | Autos |
| `1` | Utilitarios y Camionetas |
| `2` | Motos |

Cada run genera un archivo JSON en `s3://tasajusta-datalake/vehiculos_usados/YYYY-MM-DD.json` con todos los campos tal cual vienen del sitio.

### Silver — datos limpios

`transform_autos.py` aplica las siguientes reglas y escribe Parquet:

- `precio_ars = 0` → `null` (publicaciones sin precio cargado)
- `anio` fuera de `[1990, año_actual]` → `null`
- `km = 0` en un vehículo que no es 0km → `null`
- Duplicados por `cod` (ID único de DeRuedas) → se conserva uno solo

### Gold — features para ML

`gold_autos.py` construye las variables de entrada del modelo:

| Feature | Descripción |
|---------|-------------|
| `antiguedad` | `año_scraping − anio` |
| `km_valido` | `True` si el km es real, `False` si fue imputado |
| `km_por_anio` | `km / max(antiguedad, 1)` |
| `dolar_blue_venta` | Cotización blue del día de scraping (join con tabla dólar) |

---

## Modelo de Machine Learning

### LightGBM (modelo en producción)

| Parámetro | Valor |
|-----------|-------|
| Algoritmo | Gradient Boosting (LightGBM) |
| Target | `precio_ars` |
| Features numéricas | `anio`, `antiguedad`, `km`, `km_valido`, `km_por_anio`, `dolar_blue_venta` |
| Features categóricas | `marca`, `modelo`, `provincia` (nativas — sin OHE) |
| `n_estimators` | 300 |
| `num_leaves` | 15 (árbol poco profundo para controlar overfitting) |
| `learning_rate` | 0.05 |

El modelo se serializa con `pickle` y se sube a `s3://tasajusta-models/lgbm/model_lgbm_YYYY-MM-DD.pkl`. La Lambda siempre carga el archivo más reciente disponible.

### MLP PyTorch (en desarrollo)

`train_mlp.py` entrena una red neuronal para comparar performance contra LightGBM. Objetivo: evaluar si la complejidad adicional justifica el costo de inferencia.

---

## Infraestructura (AWS + Supabase + Vercel)

```
┌─────────────────────────────────────────────────────────────┐
│  AWS                                                        │
│                                                             │
│  S3 tasajusta-datalake   ← datos bronze/silver/gold         │
│  S3 tasajusta-models     ← modelos ML serializados          │
│  ECR                     ← imagen Docker de la Lambda       │
│  Lambda (container)      ← FastAPI + LightGBM              │
│  API Gateway (HTTP)      ← endpoint público                 │
│  CloudWatch              ← logs de la Lambda               │
│  IAM OIDC                ← autenticación para CI/CD         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Supabase (PostgreSQL)                                      │
│                                                             │
│  autos_usados            ← listings scrapeados              │
│  cotizaciones_dolar      ← histórico de tipo de cambio      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Vercel                                                     │
│                                                             │
│  Next.js 14              ← frontend (SSR + Route Handlers)  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Toda la infraestructura AWS se gestiona con **Terraform**. El estado vive en S3 con lock en DynamoDB.

### CI/CD — GitHub Actions

| Workflow | Trigger | Qué hace |
|----------|---------|----------|
| `etl-dolar.yml` | Diario (09:00 ART) | Descarga cotización blue → Supabase |
| `etl-vehiculos.yml` | Semanal (dom 03:00 ART) | Scrape → Transform → Load → Gold → Retrain |

Autenticación con AWS vía **OIDC** — sin credenciales de larga duración almacenadas como secrets.

---

## Stack técnico

| Capa | Tecnología |
|------|-----------|
| Scraping / ETL | Python 3.11, httpx, Polars |
| Data lake local | MinIO (S3-compatible) |
| Data lake prod | AWS S3 |
| Base de datos | Supabase (PostgreSQL) |
| ML | LightGBM, scikit-learn, PyTorch |
| API | FastAPI, Mangum (AWS Lambda adapter) |
| Frontend | Next.js 14, Tailwind CSS, Vercel |
| IaC | Terraform |
| CI/CD | GitHub Actions |

---

## Desarrollo local

### Requisitos

- Docker y Docker Compose
- Python 3.11+
- AWS CLI (solo si necesitás interactuar con S3/Lambda)

### Setup

```bash
cp env.example .env
# Completar las variables en .env

docker compose up -d
docker compose exec app bash

# Dentro del contenedor:
pip install -r requirements-etl.txt

# Correr el pipeline local (usa MinIO + Postgres del docker-compose)
python -m etl.scrape_deruedas
python -m etl.transform_autos
python -m etl.load_autos
python -m etl.gold_autos
python -m ml.train_lgbm
```

### Variables de entorno

```env
# Postgres (dev local)
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
DATABASE_URL=

# MinIO (dev) / S3 (prod)
MINIO_ENDPOINT=http://localhost:9000
MINIO_ROOT_USER=
MINIO_ROOT_PASSWORD=
MINIO_BUCKET=tasajusta-bronze

# Supabase (prod)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# Modelo
MODELS_BUCKET=tasajusta-models
```

### Levantar la API localmente

```bash
pip install -r requirements-lambda.txt
uvicorn api.main:app --reload
# → http://localhost:8000/docs
```

---

## Estructura del repositorio

```
tasajusta/
├── api/                  # FastAPI — endpoint de predicción
│   ├── main.py           # lifespan: carga modelo + cotización blue
│   ├── routes/predict.py # POST /predict
│   └── schemas.py        # PredictRequest / PredictResponse
├── etl/
│   ├── scrape_deruedas.py  # scraper (3 segmentos, toda Argentina)
│   ├── transform_autos.py  # bronze → silver
│   ├── load_autos.py       # silver → Supabase
│   ├── gold_autos.py       # silver → gold (feature engineering)
│   ├── extract_dolar.py    # fetch cotización blue
│   ├── transform_dolar.py  # limpieza cotizaciones
│   ├── load_dolar.py       # → Supabase
│   └── infra.py            # clientes S3 y Postgres
├── ml/
│   ├── train_lgbm.py    # entrenamiento LightGBM
│   ├── train_mlp.py     # entrenamiento MLP PyTorch
│   └── evaluate.py      # métricas comparativas
├── web/                 # Next.js 14
│   └── app/
│       ├── page.tsx
│       ├── components/PredictForm.tsx
│       └── api/predict/route.ts   # proxy → Lambda (evita CORS)
├── infra/               # Terraform
├── .github/workflows/   # GitHub Actions
├── docker-compose.yml   # dev local: app + postgres + minio
└── Dockerfile           # imagen Lambda
```

---

## Licencia

MIT

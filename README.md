# TasaJusta

**Used car price intelligence platform for Argentina.**

TasaJusta estimates the fair market price of a used vehicle based on real listings, flags underpriced opportunities, and tracks how the used car market moves against the blue-dollar exchange rate.

🔗 **Live demo:** [tasajusta.vercel.app](https://tasajusta.vercel.app)

---

## What it does

- **Price estimator** — Enter make, model, year, mileage, and province. A LightGBM model trained on real listings returns the estimated market price in ARS and USD (blue rate).
- **Opportunity detector** — Listings priced more than 10% below the model's estimate are flagged as buying opportunities.
- **Blue-dollar cross** — Every estimate includes the USD equivalent at the current informal exchange rate — a signal unique to the Argentine market.
- **Dual data source** — Listings from DeRuedas (scraped weekly) and Kavak (scraped daily Mon–Fri).
- **Weekly + daily pipeline** — DeRuedas scrapes every Sunday; Kavak runs every weekday and retrains the model with fresh data.

---

## Architecture

```
DeRuedas (weekly) ──► scrape_deruedas.py ──► S3 bronze
                                                  │
Kavak (daily) ──────► scrape_kavak.py ──────► S3 bronze
                                                  │
                              transform_*.py ──► S3 silver (Parquet)
                                                  │
                               load_autos.py ──► Supabase (source column)
                                                  │
                               gold_autos.py ──► S3 gold (merged features)
                                                  │
                              train_lgbm.py ──► S3 models (.pkl)
                                                  │
                              score_autos.py ──► Supabase (scores)
                                                  │
                                           AWS Lambda
                                        (FastAPI + LightGBM)
                                                  │
                                          Next.js (Vercel)

bluelytics.com.ar ──► extract_dolar.py ──► Supabase (daily)
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Scraping / ETL | Python 3.11, httpx, Polars |
| Data lake (dev) | MinIO (S3-compatible) |
| Data lake (prod) | AWS S3 — medallion pattern (bronze / silver / gold) |
| Database | Supabase (PostgreSQL) |
| ML | LightGBM, scikit-learn, PyTorch (MLP comparison) |
| API | FastAPI + Mangum (Lambda adapter) |
| Infra | AWS Lambda, API Gateway, ECR, IAM — all provisioned with Terraform |
| CI/CD | GitHub Actions with OIDC (no long-lived AWS credentials) |
| Frontend | Next.js 14 App Router, Tailwind CSS, deployed on Vercel |

---

## Data pipeline — medallion layers

| Layer | Location | What it contains |
|-------|----------|-----------------|
| **Bronze** | `s3://…/vehiculos_usados/YYYY-MM-DD.json` | Raw DeRuedas scrape — 3 segments, 23 provinces |
| **Bronze** | `s3://…/kavak_autos/YYYY-MM-DD.json` | Raw Kavak scrape — used cars with certified inspection |
| **Silver** | `s3://…/silver/autos_usados/YYYY-MM-DD.parquet` | Cleaned DeRuedas: nulled zeros, dedup by listing ID |
| **Silver** | `s3://…/silver/kavak_autos/YYYY-MM-DD.parquet` | Cleaned Kavak listings (same schema) |
| **Gold** | `s3://…/gold/autos_usados/YYYY-MM-DD.parquet` | Both sources merged + ML features: `antiguedad`, `km_por_anio`, `dolar_blue_venta` |

---

## ML model

**LightGBM** — gradient boosting on tabular data.

| | Train | Test |
|---|---|---|
| MAE | $1.4M ARS | $4.1M ARS |
| R² | 0.942 | 0.556 |
| MAPE | — | 21% |

Overfitting is expected at ~300 listings — it improves as the weekly pipeline accumulates data. A PyTorch MLP was also trained for comparison (`ml/train_mlp.py`); LightGBM was chosen for production due to better R² and lower RMSE on this dataset size.

**Opportunity score:**
```
score = (precio_estimado − precio_real) / precio_estimado
```
Listings with `score > 0.10` (10%+ below estimated value) are surfaced as opportunities.

### Experiment tracking — MLflow (local)

Each training run logs parameters, metrics, and the model artifact to a local MLflow instance. No server is required — everything is stored in `mlruns/` (gitignored).

```bash
# Instalar (grupo separado — no va a Lambda ni CI)
uv sync --group tracking

# Correr entrenamiento (genera mlflow.db automáticamente)
python -m ml.train_lgbm

# Abrir la UI
mlflow ui --backend-store-uri sqlite:///mlflow.db
# → http://localhost:5000
```

**Why local and not a hosted MLflow server?**
At this stage the model retrains automatically via GitHub Actions — a dedicated tracking server (EC2 or managed Databricks) would add infrastructure cost and operational overhead for a single-developer project. Local tracking lets you inspect every run's R², MAE, and overfitting gap without spending anything. If the project scales to a team, pointing `MLFLOW_TRACKING_URI` at a remote server requires changing one line.

---

## Infrastructure

Everything in AWS is provisioned with Terraform. State lives in S3 with DynamoDB locking.

```
AWS
├── S3 tasajusta-datalake-*     ← bronze / silver / gold data
├── S3 tasajusta-models-*       ← serialized model artifacts (.pkl)
├── ECR tasajusta-api           ← Lambda container image
├── Lambda tasajusta-predict    ← FastAPI inference (512MB, 30s timeout)
├── API Gateway (HTTP v2)       ← public endpoint
├── IAM OIDC                    ← keyless auth for GitHub Actions
└── CloudWatch                  ← Lambda logs (7-day retention)

Supabase
├── autos_usados                ← scraped listings + ML scores
└── cotizaciones_dolar          ← daily blue-dollar history

Vercel
└── Next.js 14                  ← SSR frontend + Route Handler proxy
```

---

## CI/CD workflows

| Workflow | Trigger | Steps |
|----------|---------|-------|
| `etl-dolar.yml` | Daily 09:00 ART | Fetch blue rate → Supabase |
| `etl-vehiculos.yml` | Weekly Sun 03:00 ART | Scrape DeRuedas → Transform → Load → Gold → Train → Score |
| `etl-kavak.yml` | Mon–Fri 07:00 ART + manual | Scrape Kavak → Transform → Load → Gold → Train → Score |
| `retrain.yml` | Manual (`workflow_dispatch`) | Gold → Train → Score (reuses existing S3 data) |
| `deploy-lambda.yml` | Push to `api/**` + manual | Build Docker → Push ECR → Update Lambda |

Authentication uses **OIDC** — GitHub Actions assumes an IAM role via federated identity. No AWS access keys stored as secrets.

---

## Key architectural decisions

**Why Lambda over EC2?**
Lambda is in the always-free tier (1M requests/month forever). An EC2 instance would consume AWS credits that expire in 6 months on new accounts. Cold start (~2s) is acceptable for this use case.

**Why LightGBM over PyTorch for tabular data?**
Both were trained and compared honestly. LightGBM handles high-cardinality categoricals natively (make/model/province without one-hot encoding), trains faster, and achieves better R² on this dataset size. PyTorch MLP is kept in the repo as a comparison baseline.

**Why Supabase REST API instead of direct Postgres from CI?**
GitHub Actions runners have IPv6-only DNS resolution for Supabase's direct connection host. Port 5432 is unreachable. Port 443 (PostgREST HTTPS) works without restriction. The ETL scripts use a dual-strategy pattern: REST API when `SUPABASE_URL` is available, psycopg2 for local dev.

---

## Local development

### Requirements
- Docker and Docker Compose
- Python 3.11+

### Setup

```bash
cp .env.example .env
# Fill in the variables

docker compose up -d
docker compose exec app bash

# Inside the container:
python -m etl.scrape_deruedas
python -m etl.transform_autos
python -m etl.load_autos
python -m etl.gold_autos
python -m ml.train_lgbm
python -m ml.score_autos
```

### Run the API locally

```bash
pip install -r requirements/lambda.txt
uvicorn api.main:app --reload
# → http://localhost:8000/docs
```

---

## Repository structure

```
tasajusta/
├── etl/
│   ├── scrape_deruedas.py    # scraper — 3 segments, 23 provinces, Crawl-delay: 5s
│   ├── scrape_kavak.py       # scraper — Kavak used cars (daily)
│   ├── transform_autos.py    # bronze → silver (clean + deduplicate)
│   ├── transform_kavak.py    # kavak bronze → silver (reuses transform_autos logic)
│   ├── load_autos.py         # silver → Supabase (source-aware upsert)
│   ├── gold_autos.py         # silver → gold (merges DeRuedas + Kavak)
│   ├── extract_dolar.py      # blue-dollar rate fetch
│   ├── transform_dolar.py    # dolar bronze → silver
│   ├── load_dolar.py         # dolar silver → Supabase
│   └── infra.py              # shared S3 + Postgres clients
├── ml/
│   ├── train_lgbm.py         # LightGBM training + S3 artifact upload
│   ├── train_mlp.py          # PyTorch MLP (comparison baseline)
│   ├── evaluate.py           # side-by-side metrics
│   └── score_autos.py        # batch scoring → opportunity detection
├── api/
│   ├── main.py               # FastAPI app + lifespan (model loaded once at startup)
│   ├── routes/predict.py     # POST /predict
│   └── schemas.py            # PredictRequest / PredictResponse
├── web/                      # Next.js 14 frontend
│   └── app/
│       ├── page.tsx
│       ├── components/
│       │   ├── PredictForm.tsx          # client component — estimator form
│       │   ├── DolarSection.tsx         # server component — blue-dollar rates
│       │   ├── OportunidadesSection.tsx # server component — opportunity cards
│       │   └── VehiculosSection.tsx     # server component — full listings table
│       └── api/predict/route.ts         # Route Handler proxy → Lambda (avoids CORS)
├── infra/
│   ├── bootstrap/            # S3 + DynamoDB for Terraform remote state
│   └── main/                 # Lambda, API Gateway, ECR, IAM, S3
├── .github/workflows/        # GitHub Actions (ETL cron + retrain)
├── docker-compose.yml        # dev: app + postgres + minio
├── Dockerfile                # dev image
└── lambda.Dockerfile         # production Lambda image (multi-stage, Python 3.12/AL2023)
```

---

## License

MIT

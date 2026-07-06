# TasaJusta — Plataforma de inteligencia de precios de autos usados (ETL + ML + Deploy)

> Brief de proyecto para portfolio, pensado para levantarlo con **Claude Code CLI**.
> Objetivo: un proyecto que englobe lo que piden las ofertas (ETL, data, ML/PyTorch, cloud, IaC),
> que quede **en producción con URL pública**, y que cueste **~USD 0** durante toda la búsqueda laboral.

---

## 0. Contexto y decisiones de arranque (leer primero)

Dos realidades de 2025/2026 que definen la arquitectura:

1. **AWS Free Tier cambió (julio 2025).** Las cuentas nuevas ya **no** tienen 12 meses gratis de
   EC2/RDS/S3. Reciben ~USD 200 en créditos y un "plan gratuito" que **expira a los 6 meses o al
   agotar los créditos, y luego AWS cierra la cuenta**. Lo único que sobrevive para siempre es la
   capa **"always free"** (Lambda 1M req/mes, DynamoDB 25 GB, S3 ~5 GB/mes, CloudWatch, EventBridge).
   → **Regla de oro:** el demo vive en servicios always-free + plataformas externas gratis.
   AWS se usa para *demostrar* Lambda/S3/DynamoDB/Terraform, no para hostear cosas que se pagan.

2. **La API pública de Mercado Libre está cerrada.** El endpoint `/search` ahora exige token de un
   vendedor autenticado (403 sin auth). Scraping = frágil + riesgo legal. → No basamos el demo en
   datos en vivo de ML. Usamos un **dataset semilla** para entrenar + **señales macro estables** para
   la parte "viva".

**Guardrail de costos ANTES de tocar nada:** crear una cuenta AWS, activar el plan gratuito, y de una
crear un **AWS Budget de USD 1** con alerta por mail + activar **Cost Anomaly Detection**. En AWS,
los sustos vienen de logs sin retención y recursos olvidados (EBS, Elastic IPs, NAT Gateways).

---

## 1. Qué construimos (y por qué destaca)

**Producto:** una plataforma que estima el precio justo de un auto usado en Argentina **y** detecta
publicaciones por debajo de mercado ("detector de oportunidades"), mostrando además cómo se mueve el
mercado del usado frente al **dólar**.

**Por qué no es "otro predictor de precios más":**
- El ángulo es *detección de oportunidades/anomalías*, no solo predicción. Propuesta de valor real.
- Cruza precios con **macro (dólar blue)** — algo muy argentino que casi nadie hace en un tutorial.
- Usa **NLP sobre las descripciones** ("impecable, único dueño, service oficial") para mejorar la
  estimación y para flaggear publicaciones sospechosas. Ahí entra PyTorch/Hugging Face de forma
  genuina, no forzada.
- La ejecución (ETL orquestado + modelo servido + IaC + CI/CD + observabilidad) es lo que separa un
  proyecto de portfolio de un notebook de Kaggle.

**Skills que demuestra (mapa a ofertas laborales):**
`Python` · `ETL / pipelines` · `orquestación (Airflow/serverless)` · `data lake (S3/parquet)` ·
`SQL / warehouse (Postgres/dbt)` · `scikit-learn` · `PyTorch` · `Hugging Face` · `FastAPI` ·
`AWS (Lambda, S3, DynamoDB, EventBridge, CloudWatch)` · `Terraform (IaC)` · `CI/CD (GitHub Actions)` ·
`Next.js` · `observabilidad`.

---

## 2. Estrategia de datos (robusta, legal y gratis)

La clave es que **el demo nunca se rompe**: todo lo que se ingesta se persiste, así la app siempre
tiene datos aunque una fuente falle.

| Fuente | Uso | Estabilidad | Auth |
|---|---|---|---|
| Dataset semilla de autos usados (Kaggle o una colección única propia) | Entrenar el modelo | Alta (es estático) | No |
| **dolarapi.com** (dólar oficial/blue/MEP) | Señal macro "viva", refresca a diario | Alta, sin auth | No |
| Precios de combustibles (datos abiertos oficiales AR) | Enriquecimiento macro opcional | Alta, dataset oficial | No |
| Scrape *respetuoso* de UNA fuente amigable (opcional, ej. Demotores/DeRuedas) | Refrescar muestras nuevas | Baja/frágil | No |

**Reglas del scraping (si lo hacés):** solo como fuente *secundaria y opcional*; con rate-limit alto,
User-Agent claro, respeto de `robots.txt`, y **caché/snapshots en S3** para que el demo funcione aunque
el scrape falle. Nunca lo pongas en el camino crítico de la demo.

**Capas del data lake (patrón medallion):**
- **bronze/** → crudo tal cual llega (JSON/CSV) en S3.
- **silver/** → limpio y normalizado (parquet): tipos, monedas a USD usando el dólar del día, dedup.
- **gold/** → agregados listos para la app y el modelo (features, series de precio vs dólar).

---

## 3. Arquitectura

```
                         ┌───────────────────────────────────────────┐
                         │              INGESTA (ETL)                 │
  Kaggle seed ──────────►│  Extract → S3 bronze                       │
  dolarapi.com ─────────►│  (Lambda + EventBridge cron, o GH Actions) │
  (scrape opcional) ────►│                                            │
                         │  Transform (Pandas/Polars) → S3 silver     │
                         │  Load → Postgres (Supabase/Neon) + S3 gold │
                         └───────────────┬───────────────────────────┘
                                         │
                    ┌────────────────────┴───────────────────┐
                    │                                         │
          ┌─────────▼──────────┐                   ┌──────────▼───────────┐
          │   ENTRENAMIENTO    │                   │   FEATURES NLP       │
          │  (offline/Colab)   │                   │  (batch, PyTorch/HF) │
          │  LightGBM + MLP    │◄──── embeddings ──│  sentence-transformers│
          │  → artefacto a S3  │                   │  sobre descripciones │
          └─────────┬──────────┘                   └──────────────────────┘
                    │ modelo.pkl / .pt
          ┌─────────▼──────────────────────┐
          │   INFERENCIA (API)             │        ┌───────────────────────┐
          │  FastAPI + Mangum en           │◄───────│  FRONTEND             │
          │  AWS Lambda (Function URL)     │        │  Next.js 14 en Vercel │
          │  (modelo liviano, embeddings   │        │  dashboard + buscador │
          │   ya precomputados)            │───────►│  + detector de gangas │
          └────────────────────────────────┘        └───────────────────────┘

  IaC: Terraform provisiona S3, Lambda, DynamoDB, EventBridge, CloudWatch, IAM.
  CI/CD: GitHub Actions (tests, lint, terraform plan/apply, deploy).
  Observabilidad: CloudWatch logs + métricas; página /health y /metrics.
```

**Decisión de diseño clave (buen argumento de entrevista):** todo lo pesado de deep learning
(embeddings de texto) corre en **batch, offline**, y se persiste. La **inferencia en runtime es
liviana** (un modelo tabular + lookup de embeddings), así entra cómoda en Lambda always-free y los
cold starts no duelen. "Puse el DL pesado en batch y dejé la inferencia barata" es exactamente el tipo
de decisión que buscan en un rol backend+data.

---

## 4. Stack y por qué cada cosa

| Capa | Tecnología | Por qué |
|---|---|---|
| Lenguaje ETL/ML | **Python 3.11+** | Estándar del ecosistema data |
| Transformación | **Polars** (o Pandas) | Rápido; Polars suma puntos de "modernidad" |
| Orquestación (cloud) | **AWS EventBridge + Lambda** | Serverless, always-free, cero infra que pagar |
| Orquestación (demo de skill) | **Airflow local (docker-compose)** | Muchas ofertas piden "Airflow". Poné 2-3 DAGs en el repo para *demostrarlo*, pero corré la prod en serverless para no pagar |
| Data lake | **S3** (parquet, medallion) | Barato, estándar de la industria |
| Data lake (dev local) | **MinIO** (en Docker) | S3-compatible; mismo código `boto3`, sin cuenta AWS. Swap a S3 real cambiando el endpoint |
| Entorno de dev | **Docker + docker-compose** (sobre WSL2 en Windows) | Portable entre SO; reproducible; te acerca a Linux desde ya |
| DB / warehouse | **Supabase o Neon (Postgres)** | Always-free de verdad (RDS ahora consume créditos y expira). Ya conocés Supabase |
| Transform SQL (opcional) | **dbt** | Keyword muy pedido; modela silver→gold con SQL versionado |
| Consultas analíticas locales | **DuckDB** | Query directo sobre parquet, cero infra, se ve moderno |
| ML baseline | **scikit-learn + LightGBM** | En datos tabulares suele ganarle a las redes; es tu baseline honesto |
| Deep learning | **PyTorch** | Un MLP tabular (para *mostrar* que sabés armar y entrenar una red) + comparación honesta vs LightGBM |
| NLP | **Hugging Face sentence-transformers** (modelo multilingüe) | Embeddings de descripciones en español; features + detección de anomalías |
| API | **FastAPI + Mangum** | FastAPI es lo que se pide; Mangum lo adapta a Lambda |
| Serving | **Lambda + Function URL** | Function URLs son gratis (no necesitás API Gateway) |
| IaC | **Terraform** | Ya lo sabés y está en tu CV; provisioná TODO con esto |
| CI/CD | **GitHub Actions** | Gratis en repos públicos; tests + terraform + deploy |
| Frontend | **Next.js 14 en Vercel** | Ya lo dominás; Vercel free = URL pública estable |
| ML demo (opcional) | **Hugging Face Spaces** | Hosting gratis para un demo de inferencia, y los reclutadores lo reconocen |

---

## 5. Infra y costos — qué es gratis para siempre y qué NO

**Always free (usalo con confianza):**
- Lambda: 1M requests + 400k GB-s / mes.
- DynamoDB: 25 GB (útil para guardar predicciones/estado sin tocar Postgres).
- S3: ~5 GB, 20k GET, 2k PUT / mes (mantené los parquet chicos y comprimidos).
- CloudWatch: 10 métricas, 10 alarmas, 1M req API.
- EventBridge: reglas programadas de bajo volumen.

**Evitar en el plan gratuito (consumen créditos o expiran):**
- EC2, RDS, NAT Gateway, API Gateway (usá Lambda Function URL en su lugar), App Runner, Fargate.

**Fuera de AWS (always-free reales, ideales para que el demo viva > 6 meses):**
- **Vercel** (frontend + funciones), **Supabase/Neon** (Postgres), **GitHub Actions** (cron + CI),
  **Hugging Face Spaces** (inferencia ML opcional).

**Guardrails obligatorios:**
1. AWS Budget de USD 1 con alerta (además te regala créditos por configurarlo).
2. Retención de logs en 7-30 días en TODOS los log groups (default es "para siempre" = plata).
3. `terraform destroy` documentado para bajar todo cuando no lo necesites.
4. Revisar semanalmente: EBS volumes sueltos, Elastic IPs sin asociar.

---

## 6. Roadmap por fases (con tareas concretas para Claude Code)

> Filosofía: **desplegar temprano, iterar siempre**. Que haya una URL pública desde la semana 1,
> aunque muestre poco. Nunca tener "todo en local hasta el final".

### Fase 0 — Setup (½ día)
> Ver **`setup-inicial.md`** para el paso a paso de cuentas y entorno Docker. Regla: **NO crear la
> cuenta AWS todavía** — recién se crea en la Fase 2 (Lambda), para no gastar el reloj de 6 meses.
- [ ] (Windows) WSL2 + Docker Desktop con backend WSL2; desarrollar DENTRO del filesystem de WSL2.
- [ ] Repo monorepo: `/etl`, `/ml`, `/api`, `/web`, `/infra`, `/dags`.
- [ ] `docker-compose.yml` de desarrollo: servicios `app` (Python), `postgres`, `minio` (S3 local).
- [ ] `CLAUDE.md` con contexto, comandos, convenciones (para Claude Code CLI).
- [ ] `pyproject.toml` (uv o poetry), `ruff`, `pytest`, pre-commit.
- [ ] Proyectos gratis (para la URL viva, cuando toque): Supabase/Neon, Vercel, (opcional HF Space).
- [ ] `.gitignore`: `*.tfstate*`, `.terraform/`, `.env`, credenciales. NADA de secretos en el repo.

### Fase 1 — ETL MVP + URL viva (2-3 días) — TODO local, SIN AWS
- [ ] Extractor `dolarapi` → **MinIO** bronze (JSON con timestamp). Mismo código `boto3` que S3 real.
- [ ] Cargar dataset semilla de autos → MinIO bronze.
- [ ] Transform: normalizar, dedup, convertir precios a USD, escribir parquet a silver.
- [ ] Load a Postgres (local en Docker para dev; Supabase para la versión viva).
- [ ] Scheduler: **GitHub Actions cron** (no requiere AWS todavía).
- [ ] **Deploy del esqueleto del dashboard a Vercel** (aunque solo muestre el dólar). ✅ URL viva.

> Nota: en Fase 2, cuando creemos la cuenta AWS, se cambia el endpoint de MinIO → S3 real (un cambio
> de config, no de código) y se migra el estado de Terraform a un backend S3 + DynamoDB.

### Fase 2 — ML + API en producción (3-4 días) — acá SÍ creamos la cuenta AWS
- [ ] **Crear cuenta AWS personal** (nueva, NO la del trabajo) + Budget USD 1 + Cost Anomaly Detection.
- [ ] Migrar estado de Terraform a backend **S3 + DynamoDB**; cambiar endpoint MinIO → S3 real.
- [ ] Feature engineering sobre gold (año, km, marca/modelo, antigüedad, precio vs dólar).
- [ ] Baseline **LightGBM** (métrica: MAE / MAPE). Guardar artefacto en S3.
- [ ] **MLP en PyTorch** entrenado sobre las mismas features. Comparar honestamente vs LightGBM
      (documentar cuál gana y por qué — madurez técnica).
- [ ] `FastAPI` con `POST /predict` (recibe features → devuelve precio estimado + intervalo).
- [ ] Deploy a **Lambda + Function URL** vía Terraform. Wire del dashboard a la API.

### Fase 3 — NLP + detector de oportunidades (3-4 días)
- [ ] Embeddings de descripciones con sentence-transformers (batch, offline/Colab) → S3.
- [ ] Sumar features de texto al modelo; medir mejora.
- [ ] **Scoring de anomalías:** por cada publicación, `(precio_real - precio_estimado) / precio_estimado`.
      Flaggear "oportunidades" (muy por debajo) y "sospechosas/scam" (imposiblemente baratas + texto raro).
- [ ] Vista "Oportunidades" en el dashboard (el diferenciador del producto).

### Fase 4 — Producción de verdad (2-3 días)
- [ ] Tests (unit ETL + contract test de la API) y CI en GitHub Actions.
- [ ] `terraform plan/apply` en CI (con OIDC, sin claves hardcodeadas).
- [ ] Observabilidad: logs estructurados, `/health`, `/metrics`, dashboard simple en CloudWatch.
- [ ] **README en INGLÉS** (reclutadores internacionales/LATAM), diagrama de arquitectura,
      GIF/demo, y un `WRITEUP.md` corto explicando decisiones y trade-offs.
- [ ] Opcional: DAGs de Airflow en `/dags` + `docker-compose` para demostrar el skill localmente.

---

## 7. El ángulo PyTorch/ML, con honestidad

En datos **tabulares**, gradient boosting (LightGBM) casi siempre le gana a una red neuronal. Entonces,
¿por qué PyTorch? Dos razones legítimas que podés defender en una entrevista:

1. **Mostrar que sabés construir y entrenar una red.** Un MLP tabular en PyTorch (Dataset, DataLoader,
   loop de entrenamiento, early stopping) prueba que entendés el framework que piden. Lo comparás con
   LightGBM y explicás por qué en tabular el boosting suele ser mejor — eso es criterio, no debilidad.
2. **Donde PyTorch SÍ aporta valor real: el texto.** Las descripciones libres tienen señal ("único
   dueño", "service oficial", "permuto", "no anda"). Un modelo de embeddings multilingüe (PyTorch/HF)
   convierte ese texto en features que mejoran la estimación y habilitan la detección de anomalías y
   "publicaciones similares". Ahí el deep learning se gana su lugar.

**Talking point:** "Usé PyTorch donde agrega valor (NLP sobre texto libre) y un baseline de boosting
para lo tabular; comparé ambos y elegí con datos, no por moda. El DL pesado corre en batch y la
inferencia queda liviana y barata."

---

## 8. Qué contar en entrevistas

- **Problema real:** "El precio del usado en Argentina se mueve con el dólar y hay mucha dispersión;
  construí un sistema que estima el precio justo y detecta oportunidades."
- **ETL de punta a punta:** ingesta multi-fuente → data lake medallion en S3 → warehouse en Postgres,
  orquestado y programado.
- **Decisión de costos/arquitectura:** "Diseñé para que viva en capa always-free; el DL pesado va en
  batch y la inferencia es serverless y barata."
- **IaC:** "Todo reproducible con Terraform; `terraform destroy` y vuelvo a levantar en minutos."
- **Trade-offs medidos:** LightGBM vs MLP, con métricas.
- **Está vivo:** les pasás la URL de Vercel en la entrevista. Eso vale más que mil repos.

---

## 9. Checklist de "está en producción de verdad"

- [ ] URL pública que carga y funciona (Vercel).
- [ ] La API responde `/predict` con un ejemplo real.
- [ ] El pipeline corre solo (cron) y se ve la última corrida.
- [ ] Infra provisionada por Terraform (no clicks manuales).
- [ ] CI verde en cada push.
- [ ] README en inglés + diagrama + demo visual.
- [ ] Costo del mes: USD 0 (con el Budget de vigilante).

---

## 10. Plan B (si querés algo aún más original y a prueba de fallos)

Si en algún momento te cansa la fragilidad de los datos de autos, el **mismo stack** se reskinea a un
proyecto con datos 100% oficiales y estables: **análisis y predicción de precios de combustibles en
Argentina** (datos abiertos oficiales, sin auth, se actualizan solos). Menos común que un predictor de
autos → destaca más. La arquitectura, la infra y el roadmap son idénticos; solo cambia la fuente y el
dominio.

---

### Notas para Claude Code
- Arrancá pidiéndole que scaffoldee la estructura de carpetas y el `CLAUDE.md`.
- Trabajá **fase por fase**; no le pidas todo junto. Cada fase termina con algo desplegado.
- Pedile siempre `terraform plan` antes de `apply`, y que setee retención de logs en cada log group.
- El README final va en inglés; este brief y tus notas de trabajo pueden quedar en español.

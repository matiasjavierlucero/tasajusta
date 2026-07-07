# TasaJusta — Web

Next.js 14 App Router frontend for TasaJusta. Deployed automatically on Vercel on every push to `master`.

🔗 **Live:** [tasajusta.vercel.app](https://tasajusta.vercel.app)

---

## Stack

| | |
|---|---|
| Framework | Next.js 14 App Router |
| Styling | Tailwind CSS |
| Deployment | Vercel (auto-deploy on push to `master`) |

---

## Local development

```bash
cd web
npm install
npm run dev
# → http://localhost:3000
```

---

## Architecture notes

- **Server Components** fetch data from Supabase directly at request time (listings, blue-dollar rate, opportunities).
- **`PredictForm`** is a Client Component — it calls `/api/predict`, a Next.js Route Handler that proxies to the Lambda. This avoids exposing the Lambda URL to the browser and sidesteps CORS.
- **Vercel** serves as the edge layer — no Express server, no Docker container. The Route Handler runs as a Vercel Function.

---

## Experiment tracking (MLflow)

The ML model that powers the price estimator is tracked with MLflow locally. Each training run records R², MAE, MAPE, and the trained artifact. Not deployed — the Lambda loads the `.pkl` directly from S3.

```bash
# From the repo root:
uv sync --group tracking
python -m ml.train_lgbm
mlflow ui --backend-store-uri sqlite:///mlflow.db  # → http://localhost:5000
```

MLflow lives in a separate dependency group (`tracking`) so it doesn't bloat the Lambda image or CI installs. A hosted MLflow server would add infra cost and operational overhead for no benefit at this scale — local tracking is enough to catch regressions between weekly retrains.

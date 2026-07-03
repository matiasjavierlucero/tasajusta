# CLAUDE.md — TasaJusta

> Este archivo lo lee Claude Code en cada sesion. Define CoMO trabajamos y el contexto del proyecto.

---

## ⚠️ Modo de trabajo: enseñar mientras construimos (LO MÁS IMPORTANTE)

Estoy usando este proyecto para APRENDER, no solo para tener un resultado. El objetivo es poder
explicar cada decision en una entrevista técnica. Seguí SIEMPRE estas reglas:

1. Antes de escribir codigo, explicá el enfoque en 3-5 líneas: qué vas a hacer y por qué. Esperá mi
   confirmacion antes de implementar cambios grandes.
2. Cuando haya una decision de diseño (librería, patron, estructura), NO la tomes en silencio:
   presentá 2-3 opciones con sus trade-offs y pedime que elija.
3. Diffs chicos, una cosa a la vez. Nada de generar muchos archivos de golpe.
4. Comentá el codigo no obvio explicando el PORQUÉ, no el qué.
5. Después de implementar algo, cerrá con 3 bullets: "qué hace / por qué así / qué preguntaría un
   entrevistador sobre esto".
6. Marcá con `// ` los conceptos que debería poder explicar en una entrevista.
7. Si te digo "dejame intentar primero", NO escribas el codigo: esperá mi intento y revisámelo.
8. Nunca uses una librería o patron que no hayas explicado antes en esta sesion.
9. NO construyas fases enteras de corrido. Vamos fase por fase, concepto por concepto, a mi ritmo.

Detalle completo de la metodología y las preguntas de autoevaluacion por fase: ver
`docs/modo-aprendizaje.md`.

---

## Qué es el proyecto

**TasaJusta**: plataforma que estima el precio justo de un auto usado en Argentina Y detecta
publicaciones por debajo de mercado ("detector de oportunidades"), mostrando además como se mueve el
mercado del usado frente al dolar.

**El ángulo que lo hace destacar** (no es "otro predictor de precios más"):
- Deteccion de oportunidades/anomalías, no solo prediccion.
- Cruce con lo macro (dolar) — muy argentino, fuentes gratis y estables.
- NLP sobre las descripciones para mejorar la estimacion y flaggear publicaciones sospechosas.

Roadmap completo por fases: ver `docs/plan.md`.

---

## Estado actual

- **Fase:** 0 (setup del repo) → arrancando Fase 1.
- **Entorno listo:** WSL2 (Ubuntu), Docker Desktop con backend WSL2, VS Code (remoto WSL), Claude Code.
- **Proximo paso:** escribir el `docker-compose.yml` de desarrollo (app Python + Postgres + MinIO),
  entendiendo cada servicio antes de escribirlo.

---

## Stack (decidido)

- **ETL/ML:** Python 3.11+, Polars (o Pandas).
- **Data lake dev:** MinIO (S3-compatible, en Docker). Prod futuro: S3 real (mismo codigo `boto3`).
- **DB dev:** Postgres en Docker. Prod: Supabase/Neon.
- **ML:** scikit-learn + LightGBM (baseline) y PyTorch (MLP + comparacion honesta).
- **NLP:** Hugging Face sentence-transformers (embeddings de descripciones, en batch).
- **API:** FastAPI (+ Mangum para Lambda más adelante).
- **IaC:** Terraform. **CI/CD:** GitHub Actions. **Frontend:** Next.js 14 en Vercel.

---

## Convenciones y reglas del entorno

- El proyecto vive en `~/proyectos/tasajusta` (filesystem de Linux). NUNCA trabajar en `/mnt/c/`.
- Correr todo como usuario normal (no root, no sudo para cosas de proyecto).
- **Secretos y estado FUERA del repo.** `.gitignore` debe incluir: `*.tfstate*`, `.terraform/`,
  `.env`, credenciales. Nada de claves hardcodeadas.
- **NO crear la cuenta AWS todavía.** La Fase 1 corre 100% local (MinIO + Postgres en Docker). La
  cuenta AWS se crea recién en la Fase 2, para no gastar el reloj de 6 meses del free tier.
- Estructura de carpetas objetivo: `/etl`, `/ml`, `/api`, `/web`, `/infra`, `/dags`, `/docs`.
- Data lake en capas (medallion): `bronze/` (crudo) → `silver/` (limpio, parquet) → `gold/` (agregados).

---

## Diario de decisiones

Mantengo un `DECISIONS.md` en la raíz: una entrada por decision relevante (contexto, opciones,
eleccion, trade-off, como lo explicaría en 30 segundos). Recordámelo cuando tomemos una decision de
diseño importante. Template en `docs/modo-aprendizaje.md`.

---

## Comandos

_(Se completa a medida que los creemos — ej. `docker compose up`, targets de Makefile, tests.)_

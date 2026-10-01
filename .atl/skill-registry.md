# Skill Registry — tasajusta

Generated: 2026-10-01

## User Skills

| Name | Trigger |
|------|---------|
| `branch-pr` | Creating a pull request, opening a PR, preparing changes for review |
| `langfuse` | LLM observability, Langfuse tracing, AI monitoring, evals, prompt management — **auto-load when touching api/routes/agent.py, mcp_server.py, any Langfuse/LangGraph code** |
| `go-testing` | Writing Go tests (not applicable to this project — Python/TS) |
| `skill-creator` | Creating new AI skills |
| `issue-creation` | Creating GitHub issues or tracking work items |
| `judgment-day` | Code review / quality judgement |
| `codebase-memory` | Codebase indexing and graph queries |

## Compact Rules

### branch-pr
- Create GitHub issue FIRST, link it in the PR body
- PR title follows conventional commits format: `type(scope): description`
- Include test evidence in PR description

### langfuse
- Load `~/.claude/skills/langfuse/SKILL.md` before touching any observability code
- Applies to: `api/routes/agent.py`, `mcp_server.py`, any `langfuse.*` import
- Use Langfuse Python SDK v3.x patterns

### issue-creation
- Create issue before starting any non-trivial change
- Use conventional labels: `feature`, `bug`, `chore`, `docs`

## Project Conventions (tasajusta)

### Python (etl/, ml/, api/)
- Formatter: `ruff format` (Black-compatible, 88 chars)
- Linter: `ruff check` with E, F, I rules
- Test runner: `.venv/bin/pytest` — testpaths=["tests"]
- Coverage: `.venv/bin/pytest --cov`
- Data layer: **Polars** (not pandas) for ETL transforms
- Secrets: always via `.env` + `python-dotenv`, never hardcoded

### Frontend (web/)
- Framework: Next.js 14 App Router
- Styling: Tailwind CSS
- Type checking: TypeScript strict
- Linter: ESLint (eslint-config-next)
- DB client: `@supabase/supabase-js`
- No test framework configured yet (web/)

### Architecture Layers
```
S3/MinIO datalake (bronze → silver → gold)
     ↓
ML training (LightGBM) → S3 models bucket
     ↓
FastAPI Lambda (predict + agent endpoints)
     ↓
Next.js frontend → Supabase (postgres + auth)
```

### CI Workflows
- `etl-vehiculos.yml` — scrape + transform + load autos
- `etl-dolar.yml` — fetch dolar rates
- `etl-kavak.yml` — kavak scraper Lambda
- `retrain.yml` — retrain LightGBM (manual trigger)
- `deploy-lambda.yml` — build + push Docker → Lambda

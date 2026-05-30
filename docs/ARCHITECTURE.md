# AtlasLens — Architecture

チーム運営のための Agentic AI Co-pilot。外部 SaaS 連携なしで、日報・1on1・OKR などのテキストデータを Azure 上のマルチエージェントが横断的に参照し、運営側の「見落とし」を減らす。

## System overview

```
Browser (React + Vite + Tailwind)
        │
        │  same-origin fetch (/api/*)
        ▼
Frontend Container App  (nginx 1.27)
        │
        │  reverse proxy /api/* -> backend
        ▼
Backend  Container App  (FastAPI, Python 3.13)
        │
        ├── Azure OpenAI (gpt-4o / gpt-4o-mini / text-embedding-3-large)
        │     └── Function Calling — Chat agentic loop (8 tools, max 4 rounds)
        │
        ├── Azure AI Foundry Agent Service
        │     └── Analyzer Agent (thread + run, App Insights GenAI tracing)
        │
        ├── Foundry Prompt Flow (5-node DAG)
        │     └── Org Impact Simulator (primary path)
        │           └── Critic + Refiner agents (quality loop)
        │
        ├── Azure AI Search (provisioned; hybrid RAG planned)
        ├── Cosmos DB Serverless (profiles, goals, daily, 1on1, org, credentials, ai_artefacts)
        └── Application Insights (OpenTelemetry + AIAgentsInstrumentor)
```

Both the frontend and backend run in the same Azure Container Apps environment. Browsers
only see the frontend's URL; the backend FQDN is private to the environment from the
user's point of view (no CORS preflight in the happy path).

## Modules (M1–M9)

| Module | Purpose | Key API |
|--------|---------|---------|
| M1 Member 360 | Profile, OKR + career canvas, recent daily/1on1, AI insights | `GET /api/members`, `POST …/insights` |
| M2 Daily Pulse | Team daily report rollup + AI summary (Cosmos-persisted) | `GET /api/daily-pulse/team-summary`, `POST .../generate`, `GET .../team-summaries` |
| M3 1on1 Companion | 面談前の資料 (prep), 議事録の下書き, Cosmos save | `GET /api/one-on-ones/packet/{id}` |
| M4 Goal Alignment | OKR vs activity alignment | Chat tool `get_goal_alignment` |
| M5 Org Simulator | Structural change impact (Prompt Flow + Critic/Refiner) | `POST /api/simulator/simulate` |
| M6 Team Health | Behavioral signals only (no emotion inference) | `GET /api/health/team` |
| M7 Admin Dashboard | Org-wide KPIs (members / submission rate / 1on1 / OKR / AI) | `GET /api/admin/dashboard` |
| M8 Career Canvas | Goal schema extended with `career_vision_*`, `skills_to_grow`, `roles_to_explore`, `support_needed` | `POST /api/me/goals` |
| M9 成長サマリー | Per-member AI summary of growing/stuck areas (Cosmos-persisted history) | `POST /api/me/growth-summary`, `GET …/history`, `GET …/{key}` |

## Agentic design

### Chat — autonomous tool use

- **Files**: `backend/app/services/chat.py`, `agent_tools.py`
- **Tools**: `list_team`, `get_member`, `find_blockers`, `get_goal_alignment`, `get_team_health`, `get_org_tree`, `get_meetings_with`, `run_org_simulation`
- **Loop**: Up to 4 tool-call rounds; UI shows tool trace (“AI が N 件の情報を参照しました”)
- **Styles**: 6 presets (`standard`, `concise`, `bullet`, `coaching`, `analytical`, `casual`)

### Simulator — Plan → Act → Critique → Refine

```
simulate_change()
  └─ _plan_act_critique()
       ├─ _execute()   # Prompt Flow (primary) or fallback agent
       ├─ critique()   # Critic — verdict: good / needs_refinement
       └─ refine()     # Refiner when critique requests it
```

UI exposes `_critique`, `_refined`, `_source` and a **SimulatorProgress** step list during execution.

### Analyzer — Foundry Agent Service

- **Files**: `backend/app/agents/analyzer_agent.py`, `core/foundry_agents.py`, `core/tracing.py`
- Creates/reuses `atlaslens-analyzer` on Foundry; `threads` → `messages` → `runs.create_and_process`
- **Tracing**: `azure-core-tracing-opentelemetry` bridge + `AIAgentsInstrumentor` for GenAI spans in App Insights / Foundry Portal

## Security & operations

| Area | Implementation |
|------|----------------|
| Auth | JWT (HS256, 24h); demo accounts + optional per-member bcrypt |
| Production secrets | `JWT_SECRET` rejected if default value when `APP_ENV ∈ {production, container, staging}`; Terraform generates a 48-char random one |
| CORS | Explicit origins only; in container envs the frontend Container App URL is injected via `CORS_ORIGINS` |
| Same-origin frontend | nginx in the frontend Container App proxies `/api/*` to backend, so the browser only sees one origin |
| Persisted AI artefacts | Daily Pulse team summaries are stored in `ai_artefacts` (partition key `/kind`) |
| IaC | Terraform + GitHub Actions (OIDC); `cd-infra` manual dispatch + destroy guard |
| Identity | System-assigned Managed Identity for Azure services |

## Responsible AI (M6)

- Observes **objective** signals only: report cadence, “進められないこと” mentions in dailies, meeting count, days since last 1on1
- Does **not** infer mood or mental health
- Facts are phrased as “確認推奨”, not judgments
- Insights cite evidence IDs (humanized in UI as e.g. 「佐藤 美咲の日報（5/8）」)

## CI/CD

| Workflow | Trigger |
|----------|---------|
| `ci.yml` | PR — lint, pytest smoke, frontend build, terraform plan |
| `cd-backend.yml` | push `main` + backend/data/prompt_flow paths |
| `cd-frontend.yml` | push `main` + frontend paths |
| `cd-infra.yml` | **manual** `workflow_dispatch` only |

## Future work (post-hackathon)

Honest gaps for production hardening:

- Rate limiting on `/api/auth/login` and `/api/chat`
- Credential cache memoization (avoid bcrypt re-hash per login)
- Azure AI Search hybrid RAG wired into Chat (`search_history` tool)
- LLM eval harness (Prompt Flow Eval + golden set)
- Chat SSE streaming for long analytical replies
- ACR pull via Managed Identity (drop admin user)
- Microsoft Graph for calendar/Teams signals

## Related docs

- [RUNBOOK.md](./RUNBOOK.md) — local run and deploy
- [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) — 3-minute demo storyboard
- [ZENN_ARTICLE.md](./ZENN_ARTICLE.md) — hackathon write-up draft

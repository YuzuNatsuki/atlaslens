# AtlasLens — Architecture

EM のための Agentic AI Co-pilot。外部 SaaS 連携なしで、日報・1on1・OKR などのテキストデータを Azure 上のマルチエージェントが横断的に参照し、EM の「見落とし」を減らす。

## System overview

```
Browser (React + Vite + Tailwind)
  └── Azure Static Web Apps
         │
         │  REST (JWT Bearer)
         ▼
  FastAPI (Python 3.11) @ Azure Container Apps (Japan East)
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
         ├── Cosmos DB Serverless (profiles, goals, daily, 1on1, org, credentials)
         └── Application Insights (OpenTelemetry + AIAgentsInstrumentor)
```

## Modules (M1–M6)

| Module | Purpose | Key API |
|--------|---------|---------|
| M1 Member 360 | Profile, OKR, recent daily/1on1, AI insights | `GET /api/members`, `POST …/insights` |
| M2 Daily Pulse | Team daily report rollup + AI summary | `GET /api/daily-pulse/team-summary` |
| M3 1on1 Companion | Prep packet, minutes structuring, Cosmos save | `GET /api/one-on-ones/packet/{id}` |
| M4 Goal Alignment | OKR vs activity alignment | Chat tool `get_goal_alignment` |
| M5 Org Simulator | Structural change impact (Prompt Flow + Critic/Refiner) | `POST /api/simulator/simulate` |
| M6 Team Health | Behavioral signals only (no emotion inference) | `GET /api/health/team` |

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
| Production secrets | `JWT_SECRET` required when `APP_ENV=production` (≥32 chars) |
| CORS | Explicit origins (localhost + production SWA); wildcard `*.azurestaticapps.net` only in `local` |
| IaC | Terraform + GitHub Actions (OIDC); `cd-infra` manual dispatch + destroy guard |
| Identity | System-assigned Managed Identity for Azure services |

## Responsible AI (M6)

- Observes **objective** signals only: report cadence, blocker mentions, meeting count, days since last 1on1
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

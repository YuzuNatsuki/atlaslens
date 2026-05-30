# AtlasLens

> EM のための AI Co-pilot Platform — 見えていないものを、AI が見続ける

Microsoft Agent Hackathon 2026 powered by Tokyo Electron Device への応募作品。

- **Frontend (本番)**: Container Apps — `https://atlaslens-web.<env-suffix>.japaneast.azurecontainerapps.io`（`cd-infra` apply 後に確定）
- **Backend**: https://atlaslens-backend.politeisland-f552e471.japaneast.azurecontainerapps.io
- **旧 Frontend (移行前)**: https://orange-pond-02df6f200.7.azurestaticapps.net
- **Repo**: https://github.com/YuzuNatsuki/atlaslens

> 2026-05-30 にフロントエンドを Static Web Apps から Container Apps（nginx + Vite ビルド）に移行しました。  
> ブラウザは `/api/*` を相対パスで叩き、nginx がバックエンド Container App に reverse proxy します。同オリジンになるので CORS は最小化されています。

## デモアカウント

下記の 6 アカウントが用意されています。**パスワードは申請時に個別にお送りします**（公開リポジトリ・ドキュメントには記載していません）。EM アカウント (`tanaka.ken@atlaslens.dev`) でログインすると全機能を試せます。

| メール | ロール |
|---|---|
| `tanaka.ken@atlaslens.dev` | EM (田中 健) |
| `sato.misaki@atlaslens.dev` | Tech Lead (佐藤 美咲) |
| `suzuki.ryo@atlaslens.dev` | Senior (鈴木 亮) |
| `yamamoto.yuka@atlaslens.dev` | Mid (山本 由香) |
| `watanabe.sho@atlaslens.dev` | Junior (渡辺 翔) |
| `takahashi.yui@atlaslens.dev` | QA / 大阪 (高橋 結衣) |

## Azure 構成

```
atlaslens-rg @ japaneast
├── atlaslens-foundry          AIServices (Foundry) + projects/atlaslens
│   └── gpt-4o (GlobalStandard) + text-embedding-3-large
├── atlaslens-foundry-hub      AML Hub (Prompt Flow ホスト)
├── atlaslens-foundry-proj     AML Project + atlaslens_aoai connection
├── atlaslens-cosmos           Cosmos DB Serverless (6 containers)
├── atlaslensacrb6e5a1         Container Registry
├── atlaslens-logs             Log Analytics
├── atlaslens-appi             Application Insights (OTel 集約)
├── atlaslens-env              Container Apps env
├── atlaslens-backend          Container App (FastAPI + Prompt Flow runtime)
├── atlaslens-web              Container App (nginx + Vite SPA, /api/* → backend)
└── atlaslens-web-legacy       (Static Web App, retained for state continuity)

atlaslens-tfstate-rg @ japaneast
└── atlaslenstfstateb6e5a1     Terraform remote state (Storage Account)
```

## CI/CD パイプライン (GitHub Actions)

| Workflow | Trigger | Does |
|---|---|---|
| `ci.yml` | PR | backend lint + tests, frontend build, `terraform plan` |
| `cd-infra.yml` | **manual** `workflow_dispatch` only | `terraform apply` (production environment, destroy guard) |
| `cd-backend.yml` | push to main, `backend/**` / `data/**` / `infra/prompt_flow/**` | `az acr build` + `containerapp update` |
| `cd-frontend.yml` | push to main, `frontend/**` | `az acr build` (Dockerfile, multi-stage) + `containerapp update` |

すべて **Workload Identity Federation (OIDC)** で Azure に認証。Azure 接続は短命トークンで行い、デモログイン用のパスワードは GitHub Environment Secret `DEMO_PASSWORD` から Azure Container Apps secret として注入します（画面・README・ソースには表示しません）。

## 概要

エンジニアリングマネージャー（EM）の業務を 5 つのモジュールで支援する Agentic AI プラットフォーム。

- **M1. Member 360** — メンバー全方位ビュー
- **M2. Daily Pulse** — 日報 AI（下書き生成 + チーム要約、Cosmos 永続化）
- **M3. 1on1 Companion** — 面談前の資料 + 議事録の下書き + ToDo 管理
- **M4. Goal Alignment Coach** — OKR と日々の活動の整合性
- **M5. Org Impact Simulator** — 体制変更の影響予測
- **M6. Team Health Sensor**（倫理配慮版）— 行動指標による予兆検知
- **M7. Admin Dashboard**（管理者専用）— メンバー数 / 日報提出率 / 1on1 状況 / OKR 進捗 / AI 生成数の KPI 集計
- **M8. Career Canvas**（メンバー側）— OKR と同じフォーマットで「1〜3年後の理想像 / 伸ばしたいスキル / 挑戦したいロール / 必要な支援」を記録
- **M9. 成長サマリー**（メンバー側）— 直近 30 日の自分の日報 + 目標から、AI が「伸びている領域 / 伸び悩む領域 / 次の一歩」を抽出（履歴をクラウドに保存）

## アーキテクチャ

```
Browser (React + Vite)  ──JWT──►  FastAPI @ Container Apps
                                      ├─ Azure OpenAI (Chat: 8 tools, 4 rounds)
                                      ├─ Foundry Agent Service (Analyzer)
                                      ├─ Prompt Flow + Critic/Refiner (Simulator)
                                      ├─ Cosmos DB
                                      └─ Application Insights (GenAI tracing)
```

詳細: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · デモ脚本: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)

## データソース

外部 SaaS API は使わない。次のテキストデータのみ：

- 日報（Markdown）
- 議事録（Markdown / プレーンテキスト）
- 1on1 履歴（Markdown）
- プロフィール（YAML）
- 目標設定 OKR/MBO（YAML）

架空チーム **AtlasCorp**（アトラス株式会社）の 6 メンバー分を seed データとして同梱。

## ディレクトリ構成

```
atlaslens/
├── backend/         # Python + FastAPI + Semantic Kernel
│   └── app/
│       ├── agents/  # Watcher / Analyzer / Coach / Simulator / Reporter
│       ├── api/     # FastAPI ルーター
│       ├── core/    # 設定、Azure クライアント
│       ├── models/  # Pydantic スキーマ
│       └── services/# Knowledge Store, Embedding 等
├── frontend/        # React + Vite + Shadcn/ui + Tailwind
├── data/atlascorp/  # ダミー組織データ
├── infra/           # Bicep / IaC
└── docs/            # ARCHITECTURE, デモ脚本, Zenn 下書き, 提出チェックリスト
```

## ローカル起動（最短）

```bash
cp .env.example .env   # Azure 接続情報を編集
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm install && pnpm dev   # http://localhost:5173
```

初回のみ: `python backend/scripts/seed_atlascorp.py` と `python backend/scripts/seed_credentials.py`  
手順の詳細: [docs/RUNBOOK.md](docs/RUNBOOK.md)

## セットアップ（本番 / Azure）

1. Azure サブスクリプション準備
2. `infra/terraform/` でプロビジョン（`cd-infra.yml` は手動 dispatch）
3. `.env` に接続情報を設定し、Cosmos seed: `python backend/scripts/reseed_cosmos.py`

## ハッカソン情報

- 開催：Microsoft Agent Hackathon 2026 powered by Tokyo Electron Device
- テーマ：業務改革につながる Agentic AI
- 部門：個人部門
- 提出締切：2026/6/1 23:59
- 詳細：https://zenn.dev/hackathons/microsoft-agent-hackathon-2026

## ライセンス

TBD

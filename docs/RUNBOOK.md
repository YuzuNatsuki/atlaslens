# AtlasLens — Runbook

開発・デモ・提出までの実行手順をまとめた集約ガイド。

## ローカル開発

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env
# .env に Azure OpenAI / Cosmos の認証情報を埋める
uvicorn app.main:app --port 8000 --reload
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
# http://localhost:5173 で起動（Vite dev server）
# 同オリジン /api/* は本番では nginx が backend に proxy するが、
# ローカルでは VITE_API_BASE 経由で http://localhost:8000 を叩く。
```

`.env.local` に `VITE_API_BASE=http://localhost:8000` を置くか、デフォルトを変更してください。

### Seed データ生成

```bash
python backend/scripts/seed_atlascorp.py
python backend/scripts/seed_credentials.py     # demo accounts の bcrypt ハッシュ
python backend/scripts/reseed_cosmos.py        # Cosmos 既存環境への一括 upsert
```

### Tests

```bash
cd backend && .venv/bin/pytest -q
# 期待: 全件 pass。CI でも同じコマンドが回ります。
```

## Azure デプロイ

### Infra (Terraform)

```bash
cd infra/terraform
terraform init
terraform apply        # ローカルでは慎重に、原則 GitHub Actions の cd-infra (manual dispatch)
```

`cd-infra` は `workflow_dispatch` のみ（自動 push トリガーなし）。
plan に destroy が含まれると失敗するガードあり。`allow_destroy=true` で解除。

### Backend (Container Apps)

`cd-backend.yml` が `backend/**`, `data/**`, `infra/prompt_flow/**` の push に反応:

1. `az acr build --file backend/Dockerfile .`
2. `az containerapp update --image .../atlaslens-backend:<sha12>`
3. `GET /` で 5 回スモークテスト

### Frontend (Container Apps — 2026-05-30 移行)

`cd-frontend.yml` も Container Apps 化:

1. `az acr build --file frontend/Dockerfile .`（multi-stage: pnpm build → nginx:alpine）
2. `az containerapp update --image .../atlaslens-frontend:<sha12> --set-env-vars BACKEND_URL=...`
3. `GET /healthz` で nginx の生存確認

**初回ブートストラップ**: `atlaslens-web` という名前の Container App を Terraform で先に作っておく必要があります。`cd-infra` を一度 dispatch してから `cd-frontend` を回してください。

#### 旧 Static Web App からの切り替え

- Static Web App (`atlaslens-web` / SWA リソース) は state に残したまま、新しい Container App を `atlaslens-web` 名で並走させると名前衝突します。
- 安全策: SWA のリソース名を Terraform で別名 (`atlaslens-web-legacy`) に変更するか、`module.static_web_app` を削除して `terraform state rm` で外す。
- DNS / 提出 URL は **Container App 側** の `https://atlaslens-web.<env>.<region>.azurecontainerapps.io` に切り替えてください。

#### 同オリジン化の効果

- フロントは `/api/*` を相対パスで叩き、nginx が backend に proxy。
- ブラウザは CORS preflight を出さない。
- backend の `CORS_ORIGINS` には Container App の URL がデフォルトで入る (Terraform `extra_cors_origins`)。

### 環境変数まとめ (production)

| 変数 | 値 |
|------|-----|
| `APP_ENV` | `container` |
| `JWT_SECRET` | Terraform `random_password` 自動生成（32 文字以上）|
| `DEMO_PASSWORD` | GitHub Environment Secret `DEMO_PASSWORD` から Container App secret `demo-password` として注入（ドキュメント・画面には非表示）|
| `CORS_ORIGINS` | フロント Container App URL |
| `BACKEND_URL` (frontend) | バックエンド Container App URL |

## デモ動画撮影

[docs/DEMO_SCRIPT.md](./DEMO_SCRIPT.md) を参照。

## 提出チェックリスト

[docs/SUBMISSION_CHECKLIST.md](./SUBMISSION_CHECKLIST.md) を参照。

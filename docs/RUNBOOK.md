# AtlasLens — Runbook

開発・デモ・提出までの実行手順をまとめた集約ガイド。

## ローカル開発

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp ../.env.example ../.env
# .env に Azure OpenAI / Search / Cosmos の認証情報を埋める
uvicorn app.main:app --port 8000 --reload
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
# http://localhost:5173 で起動
```

### Seed データ生成 (再生成)

```bash
python backend/scripts/seed_atlascorp.py
```

## Azure デプロイ

### Azure OpenAI（先にプロビジョン）
1. Azure ポータルで Azure AI Foundry リソースを作成（リージョン: japaneast or eastus2）
2. デプロイ：`gpt-4o`、`gpt-4o-mini`、`text-embedding-3-large`
3. エンドポイント URL と API キーをメモ

### Bicep でその他リソースをまとめてプロビジョン

```bash
az deployment sub create \
  --location japaneast \
  --template-file infra/main.bicep \
  --parameters namePrefix=atlaslens \
               openAiEndpoint=https://<your>.openai.azure.com/ \
               openAiKey=<your-key>
```

### バックエンドのコンテナ化とデプロイ

```bash
# Dockerfile を backend/ に追加してから
az acr login --name <your-acr>
docker buildx build --platform linux/amd64 -t <your-acr>.azurecr.io/atlaslens-backend:0.1 backend
docker push <your-acr>.azurecr.io/atlaslens-backend:0.1

az containerapp update -n atlaslens-backend -g atlaslens-rg \
  --image <your-acr>.azurecr.io/atlaslens-backend:0.1
```

### Static Web App

```bash
cd frontend
pnpm build
swa deploy ./dist --env production
```

## デモ動画撮影

[docs/DEMO_SCRIPT.md](./DEMO_SCRIPT.md) を参照。

## 提出チェックリスト

- [ ] GitHub リポジトリ public 化
- [ ] README.md に必要な情報をすべて記載
- [ ] Web アプリ URL が動作する状態
- [ ] Zenn 記事公開
- [ ] デモ動画 (3分以内) を YouTube に upload して README から link
- [ ] アーキ図画像を docs/architecture.png として埋め込み
- [ ] 2026/6/1 23:59 までに Zenn 経由で提出

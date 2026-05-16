# AtlasLens

> EM のための AI Co-pilot Platform — 見えていないものを、AI が見続ける

Microsoft Agent Hackathon 2026 powered by Tokyo Electron Device への応募作品。

## 概要

エンジニアリングマネージャー（EM）の業務を 5 つのモジュールで支援する Agentic AI プラットフォーム。

- **M1. Member 360** — メンバー全方位ビュー
- **M2. Daily Pulse** — 日報 AI（下書き生成 + チーム要約）
- **M3. 1on1 Companion** — 事前パケット + 自動議事録 + ToDo tracking
- **M4. Goal Alignment Coach** — OKR と日々の活動の整合性
- **M5. Org Impact Simulator** — 体制変更の影響予測
- **M6. Team Health Sensor**（倫理配慮版）— 行動指標による予兆検知

## アーキテクチャ

```
Frontend (React + Vite)        Backend (Python + FastAPI)
        │                                │
        └─────────── HTTPS ──────────────┤
                                         │
        ┌────────────────────────────────┤
        │                                │
   Multi-Agent Orchestrator (Semantic Kernel)
   Watcher / Analyzer / Coach / Simulator / Reporter
        │
        ├──── Azure OpenAI (GPT-4o, GPT-4o-mini, embeddings)
        ├──── Azure AI Search (Hybrid + Vector)
        ├──── Cosmos DB (時系列ストレージ)
        └──── Azure Container Apps (実行基盤)
```

## データソース

外部 SaaS API は使わない。次のテキストデータのみ：

- 日報（Markdown）
- 議事録（Markdown / プレーンテキスト）
- 1on1 履歴（Markdown）
- プロフィール（YAML）
- 目標設定 OKR/MBO（YAML）

架空チーム **AtlasCorp** の 5 メンバー分を seed データとして同梱。

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
└── docs/            # アーキ図、デモ脚本、Zenn 記事下書き
```

## セットアップ

1. Azure サブスクリプション準備（無料 $200 クレジット推奨）
2. `infra/` の Bicep で OpenAI / AI Search / Cosmos DB をプロビジョン
3. `.env.example` をコピーして `.env` を作成、接続情報を設定
4. `backend/` で `uv sync` または `pip install -r requirements.txt`
5. `frontend/` で `pnpm install`
6. ダミーデータ生成：`python backend/scripts/seed_atlascorp.py`

## ハッカソン情報

- 開催：Microsoft Agent Hackathon 2026 powered by Tokyo Electron Device
- テーマ：業務改革につながる Agentic AI
- 部門：個人部門
- 提出締切：2026/6/1 23:59
- 詳細：https://zenn.dev/hackathons/microsoft-agent-hackathon-2026

## ライセンス

TBD

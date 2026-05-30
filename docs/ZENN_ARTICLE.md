# AtlasLens を作った — EM 向け Agentic AI を Azure Foundry で組む

> **このファイルは Zenn 公開用の下書きです。** 画像（アーキ図・スクリーンショット・Tracing 画面）は公開前に差し込んでください。

## はじめに

エンジニアリングマネージャー（EM）は、日報・1on1・OKR・会議メモなど**散らばったテキスト**からチームの状態を読み取る必要があります。でも現実には「全部は読めない」「見落としが怖い」という構造があります。

**AtlasLens** は、そのギャップを **Agentic AI** で埋める EM Co-pilot です。Microsoft Agent Hackathon 2026（個人部門）への提出作品として、Azure 上に本番デプロイまで行いました。

- デモ: https://orange-pond-02df6f200.7.azurestaticapps.net
- リポジトリ: https://github.com/YuzuNatsuki/atlaslens

## コンセプト

> 見えていないものを、AI が見続ける — あなたは決められる。

外部 SaaS（GitHub / Jira / Slack）には依存せず、**日報・議事録・1on1・プロフィール・OKR** だけを入力にします。架空チーム AtlasCorp（6 名）の seed データで、日本のモダン IT 企業らしい文脈（大阪オフィス・育休復帰など）も再現しています。

## アーキテクチャ

```
React (SWA) ──JWT──► FastAPI (Container Apps)
                         ├─ Azure OpenAI (Function Calling Chat)
                         ├─ Foundry Agent Service (Analyzer)
                         ├─ Prompt Flow DAG (Org Simulator)
                         ├─ Cosmos DB
                         └─ Application Insights (GenAI tracing)
```

詳細はリポジトリの [docs/ARCHITECTURE.md](https://github.com/YuzuNatsuki/atlaslens/blob/main/docs/ARCHITECTURE.md) を参照してください。

## Agentic として設計した 3 本柱

### 1. Chat — 8 ツール × 自律ループ

EM の自然言語質問に対し、GPT-4o が **どのツールを呼ぶか自分で決めます**（最大 4 ラウンド）。

- メンバー一覧 / 詳細、進められないことの抽出、目標の整合、チームの様子、組織ツリー、会議履歴、体制シミュレーション
- UI では `tool_calls` を「AI が N 件の情報を参照しました」として開示
- 6 種類の**回答スタイル**（簡潔・コーチング・分析など）で同じ質問でも文体を変えられる

```python
# 概念: chat.py の agentic loop
response = await chat_complete(messages=..., tools=TOOL_DEFINITIONS, ...)
while msg.tool_calls and iterations < MAX_TOOL_ITERATIONS:
    for tc in msg.tool_calls:
        result = await dispatch(tc.function.name, tc.function.arguments)
        messages.append({"role": "tool", "content": result})
    response = await chat_complete(messages=..., tools=TOOL_DEFINITIONS, ...)
```

審査で伝えたいのは「プロンプト一発」ではなく、**データ取得の意思決定がモデル側にある**点です。

### 2. Org Simulator — Prompt Flow + Critic / Refiner

体制変更案を入力すると:

1. **Prompt Flow**（5 ノード DAG）がコミュニケーション・知識・負荷を並列分析
2. **Critic Agent** が 5 軸（網羅性・一貫性・根拠・トーン・現実性）でレビュー
3. 必要なら **Refiner** が指摘を反映

結果 JSON に `_critique` / `_refined` / `_source` を残し、UI の Critique ブロックと実行中の **SimulatorProgress**（Connector / Knowledge / Load / Schedule / Critic / Refiner）で「複数エージェントが動いた」経路を見せます。

### 3. Analyzer — Foundry Agent Service + GenAI Tracing

メンバー詳細の「AI による状況整理」は Foundry 上の `atlaslens-analyzer` エージェントが担当します。thread / message / run のライフサイクルは Portal の Tracing タブから追えます。

ここでハマったのは **OpenTelemetry ブリッジ** です。`azure-core-tracing-opentelemetry` を登録しないと `AIAgentsInstrumentor` が no-op になり、App Insights に GenAI スパンが出ません。登録後は `create_thread` / `process_thread_run` などが観測できます。

## Responsible AI（M6）

Team Health は**感情推測をしません**。観察するのは:

- 14 日以内の日報件数
- 日報に書かれた「進められないこと」の件数
- 会議参加数
- 前回 1on1 からの日数

フラグ文も「〜の可能性、要確認」のように **事実 + 次アクション** に留めています。Analyzer の出力も evidence ID を付け、UI では「佐藤 美咲の日報（5/8）」のように人間可読化しました。

## 技術スタック（Azure 利用幅）

| サービス | 用途 |
|---------|------|
| Azure OpenAI | Chat, Coach, Reporter, Critic, embeddings |
| AI Foundry | Agent Service, Prompt Flow |
| Cosmos DB | プロファイル・日報・1on1・組織 |
| Container Apps | FastAPI 実行 |
| Static Web Apps | React フロント |
| Application Insights | OTel + GenAI spans |
| Terraform + GitHub Actions OIDC | IaC / CD |

## 正直な Future Work

ハッカソン期間内に **意図的に後回しにした** 項目です（デモ品質には影響しませんが、本番運用には必要）:

| 項目 | 理由 |
|------|------|
| レート制限 | login / chat への brute-force・コスト爆発対策 |
| ログイン時 bcrypt 毎回再計算 | レイテンシ改善（キャッシュ化） |
| AI Search ハイブリッド RAG | README 上の Search は provision 済みだが Chat から未接続 |
| LLM Eval ハーネス | 品質の数値化・回帰検知 |
| Chat SSE | 長文 analytical の待ち時間 |
| ACR admin user 廃止 | MI + AcrPull への移行 |

提出時点では **JWT 本番検証・CORS 厳格化・スモークテスト** まで入れ、最低限の品質ゲートを CI に載せています。

## まとめ

AtlasLens は「EM ツールを増やす」のではなく、**既にあるテキスト資産をエージェントが横断参照し、EM の注意力を補う** プロダクトです。Function Calling・Prompt Flow・Foundry Agent・GenAI Tracing を一つの体験に束ねたことで、ハッカソンの「Agentic AI」要件に正面から応えられる構成にしました。

フィードバックや改善案は GitHub Issues へお願いします。

---

**タグ案**: `Azure`, `OpenAI`, `AgenticAI`, `EM`, `FastAPI`, `Hackathon`

**公開時に差し込む画像**

1. ダッシュボード + チームの様子
2. チャットのツールトレース展開
3. SimulatorProgress + Critic ブロック
4. Foundry Portal Tracing スクショ

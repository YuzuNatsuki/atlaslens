# AtlasLens を作った：チーム運営の「見落とし」を減らす Agentic AI Co-pilot

> **Zenn 公開用の下書きです。**
> 画像は公開前に差し込み想定です。アーキテクチャ図は `docs/architecture.drawio` に drawio 形式で用意しています。

## はじめに

チームを運営する立場にいる人の仕事の一つは、日報、1on1、OKR、会議メモ、組織情報など、散らばったテキストからチームの状態を読み取ることです。

ただ、現実には全部を毎日読むのは難しい。日報の一文にある「ちょっとした違和感」や、1on1 が空いているメンバーのサインを見落とすことがあります。

そこで **AtlasLens** を作りました。

AtlasLens は、チーム運営のための **Agentic AI Co-pilot** です。既存のテキスト資産を Azure 上の AI エージェントが横断的に読み、「今日見るべきこと」「今週声をかけるべき人」「体制変更の影響」を判断しやすくします。

Microsoft Agent Hackathon 2026（個人部門）への提出作品として、Azure Container Apps 上に本番デプロイしました。

- リポジトリ: https://github.com/YuzuNatsuki/atlaslens
- Backend: https://atlaslens-backend.politeisland-f552e471.japaneast.azurecontainerapps.io
- アーキテクチャ詳細: [`docs/ARCHITECTURE.md`](https://github.com/YuzuNatsuki/atlaslens/blob/main/docs/ARCHITECTURE.md)
- drawio アーキ図: [`docs/architecture.drawio`](https://github.com/YuzuNatsuki/atlaslens/blob/main/docs/architecture.drawio)

## コンセプト

> 見えていないものを、AI が見続ける。

AtlasLens が目指したのは「人を AI に置き換える」ことではありません。チームに向き合う側の注意力を補うことです。

今回は外部 SaaS API には依存せず、同梱した架空組織 **AtlasCorp** のデータだけで動くようにしました。

- プロフィール（YAML）
- OKR / Career Canvas（YAML）
- 日報（Markdown）
- 1on1 履歴（Markdown）
- 会議メモ（Markdown）
- 組織ツリー / 認証情報 / AI 生成物（Cosmos DB）

サンプルデータには、SRE テックリードのキャリア停滞、新卒メンターの負荷、フロントエンド専門性の評価不安、時短勤務・大阪オフィス勤務による情報格差など、日本の IT 組織で起きがちな文脈を入れています。

## できること

AtlasLens は M1〜M9 のモジュールで構成しています。

| Module | 機能 |
|---|---|
| M1 Member 360 | メンバーのプロフィール、OKR、Career Canvas、日報、1on1、AI による状況整理 |
| M2 Daily Pulse | 日報の単日サマリー、複数日トレンドサマリー、AI 生成物の永続化 |
| M3 1on1 Companion | 面談前の準備資料、議事録の下書き、ToDo 管理 |
| M4 Goal Alignment | OKR と日々の活動の整合性確認 |
| M5 Org Impact Simulator | 体制変更案の影響予測（Prompt Flow + Critic / Refiner） |
| M6 Team Health | 日報頻度、1on1 間隔、会議参加などの行動指標による予兆検知 |
| M7 Admin Dashboard | メンバー数、日報提出率、1on1 状況、OKR、AI 生成数の管理者 KPI |
| M8 Career Canvas | 1年後 / 3年後の理想像、伸ばしたいスキル、挑戦したいロール |
| M9 成長サマリー | メンバー本人向けに、直近 30 日の日報と目標から成長ポイントを抽出 |

最近の改善として、日報の書きかけは **IndexedDB に自動保存** され、タブを閉じても復元できるようにしました。地味ですが、実用面ではかなり効く機能です。

## アーキテクチャ

構成は Azure に寄せています。

![architecture](./images/architecture.png)

上の画像は `docs/architecture.drawio` から export する想定です。drawio では `mxgraph.azure2019.*` の Azure 公式アイコンセットを使っています。

大まかな流れは次の通りです。

1. ブラウザは `atlaslens-web`（Frontend Container App）にアクセス
2. React SPA は `/api/*` を同一オリジンで呼ぶ
3. nginx が `/api/*` を backend Container App へ reverse proxy
4. FastAPI が Cosmos DB / Azure OpenAI / Foundry Agent Service / Prompt Flow を呼び分ける
5. AI 生成物は `ai_artefacts` として Cosmos DB に保存
6. Foundry Agent / OpenTelemetry のトレースは Application Insights に集約

```text
Browser
  ↓ HTTPS / JWT
Frontend Container App (nginx + React)
  ↓ /api/* reverse proxy
Backend Container App (FastAPI)
  ├─ Azure OpenAI
  ├─ Azure AI Foundry Agent Service
  ├─ Foundry Prompt Flow
  ├─ Cosmos DB Serverless
  └─ Application Insights
```

以前は Static Web Apps でフロントを動かしていましたが、最終的には **Frontend も Container Apps** に移しました。理由はシンプルで、ブラウザからはフロントだけを見せ、`/api/*` を nginx で backend に流すことで CORS を最小化したかったためです。

## Agentic AI として設計したポイント

### 1. AI アシスタント：8 ツール × 自律ループ

AtlasLens の「AI アシスタント」は、単なるチャットではありません。

ユーザーが自然文で質問すると、GPT-4o が必要なツールを選び、最大 4 ラウンドまで自律的に情報を取得します。

使えるツールは次のようなものです。

- チーム一覧取得
- メンバー詳細取得
- 日報から困りごと抽出
- OKR 整合性確認
- Team Health 取得
- 組織ツリー取得
- 会議履歴取得
- 組織シミュレーション実行

UI では、モデルが参照したツールを「AI が N 件の情報を参照しました」として開示します。これにより、ただの作文ではなく「どの情報を根拠に回答したのか」を確認できます。

概念的にはこのようなループです。

```python
response = await chat_complete(
    messages=messages,
    tools=TOOL_DEFINITIONS,
)

while response.tool_calls and iterations < 4:
    for call in response.tool_calls:
        result = await dispatch(call.name, call.arguments)
        messages.append({"role": "tool", "content": result})

    response = await chat_complete(
        messages=messages,
        tools=TOOL_DEFINITIONS,
    )
```

フロントエンドは 2 カラムレイアウトにし、左に回答スタイル・よく聞かれる質問、右に会話スレッドを置きました。会話履歴も Cosmos DB の `ai_artefacts` に保存しています。

### 2. Daily Pulse：単日サマリーと期間トレンド

Daily Pulse は、Reporter Agent が日報を読んでチームの状況を整理する機能です。

単日サマリーでは、朝会前に見るための情報を出します。

- 今日のひと言サマリー
- メンバーごとの動き
- 今日声をかけたい人
- チーム全体の傾向

さらに、複数日にまたがる **期間トレンドサマリー** も追加しました。

期間トレンドでは、1 日だけでは見えない繰り返しを拾います。

- 期間全体のハイライト
- メンバー別トレンド（良化 / 停滞 / 悪化 / 不変）
- 注視すべきシグナル（retention / friction / capacity / engagement / health）
- 根拠日
- 次の一手

たとえばサンプルデータでは、以下のような兆候が出ます。

- 佐藤さん: 次のキャリアステップが描けず停滞、外部求人閲覧
- 鈴木さん: メンタリング負荷と評価制度への不満
- 山本さん: 外部スタートアップからのカジュアル面談
- 渡辺さん: 1on1 未設定、質問しづらさ、放置感
- 高橋さん: 時短勤務・大阪オフィスによる意思決定からの疎外感

単日と期間でプロンプトを分けているのがポイントです。単日サマリーは「今日の朝会前」、期間サマリーは「今週の兆候」を見るためのものなので、出力スキーマも変えています。

### 3. Org Impact Simulator：Prompt Flow + Critic / Refiner

組織シミュレーションでは、「新卒のメンターを変える」「メンバーを別チームに異動する」「チームを分割する」といった変更案を入力できます。

裏側では次の流れで実行します。

1. Prompt Flow の 5 ノード DAG が、コミュニケーション・知識・負荷・スケジュールなどを分析
2. Critic Agent が、網羅性・一貫性・根拠・トーン・現実性の観点でレビュー
3. 必要に応じて Refiner が結果を改善

UI では、実行中ステップと Critic の指摘を見せることで、「AI が 1 回で答えた」のではなく、Plan → Act → Critique → Refine のループが動いていることを表現しています。

### 4. Analyzer：Foundry Agent Service + GenAI Tracing

Member 360 の「AI による状況整理」は、Azure AI Foundry Agent Service 上の `atlaslens-analyzer` が担当します。

Foundry の thread / message / run のライフサイクルを使い、App Insights / Foundry Portal で GenAI tracing を追えるようにしています。

ここで少しハマったのが OpenTelemetry 連携です。`AIAgentsInstrumentor` を使うだけでは十分ではなく、`azure-core-tracing-opentelemetry` の bridge を登録しないと no-op になり、GenAI span が出ませんでした。

登録後は、`create_thread` や `process_thread_run` などの span が Application Insights 側で確認できます。

## データ永続化

この手のデモは、AI が毎回生成して終わりだと実運用に近づきません。AtlasLens では、生成物を Cosmos DB に保存しています。

保存しているものの例:

- Daily Pulse の単日サマリー
- Daily Pulse の期間トレンドサマリー
- メンバー向け成長サマリー
- AI アシスタントの会話履歴

`ai_artefacts` という汎用コンテナを用意し、`kind` と `key` で用途別に扱っています。

```text
kind = team-summary
key  = 2026-05-19

kind = team-summary-range
key  = 2026-05-13_2026-05-19

kind = skill-growth
key  = mem001:2026-05-30

kind = em-chat-session
key  = em001
```

これにより、同じサマリーは次回以降キャッシュから即座に表示されます。再生成したい場合だけ `force=true` で上書きします。

## フロントエンドの工夫

React + Vite + Tailwind で SPA として作っています。

UI は途中で大きく作り直し、現在は左サイドバー + トップバー構成です。チーム運営側 / Admin / Member でナビゲーションが変わります。

実用面で入れた細かい改善:

- 日報の書きかけを IndexedDB に自動保存
- 日報サマリーの単日 / 期間タブ
- AI アシスタントの 2 カラムレイアウト
- AI のツール参照履歴の展開表示
- 管理者ダッシュボード
- Career Canvas 入力 UI
- メンバー本人向けの成長サマリー

IndexedDB の下書き保存は、外部依存を足さずに小さな wrapper を書きました。保存に失敗しても画面を壊さないよう、private browsing や容量超過では no-op にしています。

## セキュリティ / 運用

ハッカソンとはいえ、本番デプロイする前提で最低限の運用まわりを入れました。

- JWT 認証
- bcrypt によるデモアカウント password hash
- `APP_ENV=container` 時は `JWT_SECRET` のデフォルト値を拒否
- GitHub Actions から Container Apps secret を同期
- CORS origins の明示
- Frontend Container App の nginx reverse proxy による same-origin 化
- GitHub Actions OIDC による Azure 認証
- backend / frontend の CD
- smoke test

一度、backend Container App の新 revision が `JWT_SECRET` 未設定で起動失敗する問題がありました。原因は、本番環境で default secret を拒否するようにした一方で、Container App 側に secret binding が渡っていなかったことです。

最終的には `cd-backend.yml` で GitHub Secret → Container App Secret → env var binding を毎回同期するようにして再発防止しました。

## Azure 利用サービス

| Azure サービス | 用途 |
|---|---|
| Azure Container Apps | Frontend / Backend の実行環境 |
| Azure Container Registry | Docker image build / store |
| Azure OpenAI | Chat, Reporter, Coach, Critic, embeddings |
| Azure AI Foundry Agent Service | Analyzer Agent |
| Foundry Prompt Flow | Org Impact Simulator |
| Azure Cosmos DB Serverless | 業務データと AI 生成物の永続化 |
| Application Insights | OpenTelemetry / GenAI tracing |
| Log Analytics | Container Apps / App Insights logs |
| Key Vault | secrets 管理（Terraform 側） |
| Terraform + GitHub Actions OIDC | IaC / CI/CD |

Azure AI Search も provision していますが、今回の提出時点では Chat からの hybrid RAG 連携は Future Work 扱いです。

## 作ってみてよかった点

### Agentic AI は「UI で経路を見せる」と伝わりやすい

内部でツールを呼んでいても、UI がただのチャットだと「プロンプトで答えているだけ」に見えます。

AtlasLens では、AI アシスタントの tool trace、SimulatorProgress、Critic block、Foundry tracing を見せるようにしました。審査やデモでは、Agentic な処理経路を視覚化することが重要だと感じました。

### サンプルデータのリアリティが体験を左右する

最初の seed データは安全すぎて、AI が出すサマリーも薄くなりました。

そこで、直近 1 週間分の日報に、離職リスク、不満、メンバー間の不和につながる兆候を入れました。すると Daily Pulse や AI アシスタントがかなり「それっぽく」なりました。

業務 AI はモデルだけでなく、データ設計が体験を作ると実感しました。

### 生成物の永続化は必須

毎回 LLM を呼ぶと遅いし、デモでも結果が安定しません。Daily Pulse や成長サマリーを Cosmos に保存するようにしたことで、レスポンスも体験も安定しました。

## 今後やりたいこと

実用に近づけるなら、次の順で進めたいです。

| 項目 | 理由 |
|---|---|
| Slack / Teams 通知 | Web を開かなくても朝サマリーが届くようにする |
| Microsoft Graph 連携 | カレンダー / Teams / Entra ID から運用データを取り込む |
| GitHub / Azure DevOps 連携 | PR レビュー遅延や負荷偏りを見たい |
| Line-of-sight RBAC | 利用者が見られる範囲を組織ツリーで厳密に制限する |
| 監査ログ | 誰が誰の情報を見たかを追跡する |
| LLM Eval | プロンプト変更時の品質回帰を検知する |
| Chat SSE | 長い分析回答の待ち時間を改善する |
| AI Search RAG | 過去の日報 / 議事録を横断検索可能にする |

## まとめ

AtlasLens は、チーム運営のための Agentic AI Co-pilot として、以下を 1 つの体験にまとめました。

- Function Calling による自律的なツール利用
- Daily Pulse の単日 / 期間サマリー
- Prompt Flow + Critic / Refiner による組織シミュレーション
- Foundry Agent Service と GenAI tracing
- Cosmos DB による AI 生成物の永続化
- Frontend / Backend ともに Azure Container Apps で本番デプロイ

チームを運営する仕事は、最後は人を見る仕事です。AI が決めるのではなく、AI が散らばった情報を整理し、人が対話に時間を使えるようにする。

その方向性を、Azure の Agentic AI スタックで形にしたのが AtlasLens です。

---

**タグ案**: `Azure`, `AzureOpenAI`, `AIFoundry`, `AgenticAI`, `FastAPI`, `React`, `CosmosDB`, `Hackathon`

## 公開前に差し込む画像

1. `docs/architecture.drawio` から export したアーキテクチャ図
2. SPA ダッシュボード
3. Daily Pulse の期間トレンドサマリー
4. AI アシスタントの tool trace 展開
5. Org Simulator の SimulatorProgress + Critic block
6. Foundry Portal / Application Insights の GenAI tracing

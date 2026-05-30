# EM 向け Agentic AI Co-pilot「AtlasLens」— 設計と実装の解説

> Zenn 公開用の下書き。画像とアーキ図は公開前に差し込む。
> アーキ図の元データは `docs/architecture.drawio`（draw.io / Azure 公式アイコン）。

AtlasLens は、エンジニアリングマネージャー（EM）向けの Agentic AI Co-pilot である。日報・1on1・OKR・会議メモ・組織図といった既存のテキスト資産を Azure 上の AI エージェントが横断的に読み、「今日見るべきこと」「今週声をかける人」「体制変更の影響」を EM が判断しやすい形に整える。フロント・バックエンドとも Azure Container Apps に本番デプロイしている。

- リポジトリ: https://github.com/YuzuNatsuki/atlaslens
- Backend: https://atlaslens-backend.politeisland-f552e471.japaneast.azurecontainerapps.io
- アーキ詳細: `docs/ARCHITECTURE.md`

本記事は、(1) どの業務課題を解くか、(2) なぜ Agentic AI とこのアーキテクチャが有効か、(3) 実務導入を想定してどこまで作り込んだか、の3点を中心に解説する。

---

## 1. ビジネスインパクト：解く業務課題

### 課題

EM の中核業務は「チームの状態を把握し、適切なタイミングで介入する」ことだが、その判断材料は日報・1on1 メモ・OKR・会議メモ・組織情報と、複数のテキストに分散している。

ここには構造的な問題がある。

- **情報量が人手の限界を超える。** メンバーが増えるほど、全員の日報を毎日精読するのは非現実的になる。結果として、日報の一文に出た違和感や、1on1 が長く空いているサインを見落とす。
- **見落としのコストが非対称。** 把握漏れは、離職・燃え尽き・チーム内不和といった、後から取り返しのつきにくい事象に直結する。1人の離職リスクを1週間早く検知できるかどうかで、打てる手の幅が大きく変わる。
- **EM の時間が分析作業に奪われる。** 本来は人に向き合うべき時間が、散らばった情報の収集と突き合わせに消える。

### AtlasLens が生む価値

AtlasLens は、この「分散したテキストの横断的な把握」を AI に肩代わりさせ、EM の判断とアクションに時間を回す。

- **見落としの低減。** 日報・1on1・行動指標を横断し、注視すべきメンバーとシグナル（離職リスク / 不和 / 負荷 / エンゲージメント / 体調）を根拠付きで提示する。
- **意思決定の前倒し。** 単日だけでなく複数日のトレンドで「繰り返し起きている兆候」を拾うため、点ではなく線で予兆を捉えられる。
- **体制変更の事前評価。** 異動・チーム分割・メンター変更などの影響を、実行前にシミュレートできる。

重要なのは、AtlasLens は EM を置き換えるものではないという点である。判断は人が行い、AI は判断材料の整備に徹する。これは評価・人事に関わる領域で AI を使う以上、設計上の前提として固定している。

---

## 2. アプローチの有効性：Agentic AI 設計

「AI が一度の生成で答えを出す」構成ではなく、エージェントが必要な情報を自律的に集め、複数ステップで結論を組み立てる構成にしている。課題が「分散した情報の横断と突き合わせ」である以上、固定パイプラインより、状況に応じてツールを選ぶエージェント型のほうが論理的に適している。

### 2-1. AI アシスタント：Function Calling による自律ツール利用

EM が自然文で質問すると、GPT-4o が必要なツールを選択し、最大4ラウンドまで自律的に情報を取得して回答を組み立てる。

利用できるツールは8種類。

| ツール | 役割 |
|---|---|
| `list_team` | チーム一覧の取得 |
| `get_member` | メンバー詳細の取得 |
| `find_blockers` | 日報からの困りごと抽出 |
| `get_goal_alignment` | OKR と活動の整合性確認 |
| `get_team_health` | 行動指標ベースのヘルス取得 |
| `get_org_tree` | 組織ツリー取得 |
| `get_meetings_with` | 会議履歴取得 |
| `run_org_simulation` | 組織シミュレーション実行 |

ループは Function Calling の結果をメッセージに積み直して再投入する標準的な構成で、上限ラウンドを設けて発散を防いでいる。

```python
response = await chat_complete(messages=messages, tools=TOOL_DEFINITIONS)

while response.tool_calls and iterations < 4:
    for call in response.tool_calls:
        result = await dispatch(call.name, call.arguments)
        messages.append({"role": "tool", "content": result})
    response = await chat_complete(messages=messages, tools=TOOL_DEFINITIONS)
    iterations += 1
```

UI 側では、モデルが参照したツールを「AI が N 件の情報を参照しました」として開示する。回答が作文ではなく、どの情報を根拠にしているかを EM が確認できる。Agentic AI の有効性は、内部でツールを呼ぶこと自体ではなく、その経路を検証可能にすることで初めて実務上の信頼につながる。

### 2-2. Org Impact Simulator：Plan → Act → Critique → Refine

体制変更案の影響予測は、単発生成ではなく品質ループを組んでいる。Azure AI Foundry の Prompt Flow（5ノード DAG）が一次分析を行い、Critic エージェントがレビューし、必要なら Refiner が修正する。

```text
simulate_change()
  └─ _plan_act_critique()
       ├─ _execute()   # Prompt Flow（主経路） / fallback agent
       ├─ critique()   # Critic: good / needs_refinement の判定
       └─ refine()     # 判定が refinement を要求したときのみ
```

Critic は網羅性・一貫性・根拠・トーン・現実性の観点でレビューする。組織変更という誤りの許されない領域では、生成物を一度別のエージェントに検証させるこの構成が、出力品質の担保に直接効く。UI には実行ステップと Critic の指摘を出し、ループが動いていることを可視化している。

### 2-3. Daily Pulse：単日と期間で目的を分けたサマリー

Reporter エージェントが日報を読んでチーム状況を整理する。「朝会前に見る単日サマリー」と「今週の兆候を見る期間トレンド」は目的が異なるため、プロンプトと出力スキーマを分離している。

- 単日: 今日のひと言サマリー / メンバーごとの動き / 今日声をかけたい人 / チーム全体の傾向
- 期間: 期間ハイライト / メンバー別トレンド（良化・停滞・悪化・不変）/ 注視シグナル（retention・friction・capacity・engagement・health）/ 根拠日 / 次の一手

出力中のメンバー表示は、プロンプトで `member_name` をキーに固定したうえで、生成後とキャッシュ読み出しの両方で ID→氏名への決定的な後処理を通している。LLM 出力の表記揺れを後処理でガードすることで、表示の安定性を保証している。

### 2-4. Analyzer：Foundry Agent Service + GenAI tracing

Member 360 の状況整理は、Azure AI Foundry Agent Service 上の `atlaslens-analyzer` が担当する。thread → message → run のライフサイクルで実行し、`azure-core-tracing-opentelemetry` の bridge と `AIAgentsInstrumentor` により、エージェント実行の GenAI span を Application Insights / Foundry Portal で追跡できる。エージェントの挙動を観測可能にしておくことは、実務での運用・デバッグ・品質改善の前提になる。

---

## 3. アーキテクチャ

```text
Browser
  ↓ HTTPS / JWT
Frontend Container App (nginx + React SPA)
  ↓ /api/* を backend へ reverse proxy（same-origin 化）
Backend Container App (FastAPI, Python 3.13)
  ├─ Azure OpenAI (gpt-4o / gpt-4o-mini / text-embedding-3-large)
  ├─ Azure AI Foundry Agent Service (Analyzer)
  ├─ Foundry Prompt Flow (Org Simulator)
  ├─ Cosmos DB Serverless (業務データ + ai_artefacts)
  └─ Application Insights (OpenTelemetry)
```

設計上のポイントは2つ。

- **same-origin 化。** フロントの nginx が `/api/*` を backend に reverse proxy するため、ブラウザから見えるオリジンは1つになり、CORS preflight が happy path で発生しない。設定の単純化と運用負荷の低減が目的。
- **責務分離。** Azure OpenAI（汎用推論）/ Foundry Agent Service（エージェント実行と追跡）/ Prompt Flow（評価ループ付き分析）を用途で使い分け、それぞれの強みに寄せている。

---

## 4. 完成度・実現性

### 安定動作：AI 生成物の永続化

AI の生成物は、毎回 LLM を呼ぶのではなく Cosmos DB の汎用コンテナ `ai_artefacts` に `kind` + `key` で保存し、2回目以降はキャッシュから返す。

```text
kind=team-summary        key=2026-05-19
kind=team-summary-range  key=2026-05-13_2026-05-19
kind=skill-growth        key=mem001:2026-05-30
kind=em-chat-session     key=em001
```

これにより、レスポンスが速くなるだけでなく、同じ問いに対して毎回違う答えが返らない。デモでも実務でも、出力の再現性は信頼性の前提になる。再生成が必要なときのみ `force=true` で上書きする。

### セキュリティ

- JWT 認証（HS256 / 24h）、デモアカウントは bcrypt ハッシュ
- `APP_ENV` が production / container / staging のとき、`JWT_SECRET` のデフォルト値を起動時に拒否（Terraform が48文字のランダム値を生成）
- CORS は明示 origin のみ。container 環境では nginx の same-origin 化で実質不要
- システム割り当て Managed Identity で Azure サービスへアクセス

### 運用性・導入コスト

- **IaC + CI/CD。** Terraform + GitHub Actions（OIDC）。`ci`（lint / pytest / build / terraform plan）、`cd-backend`、`cd-frontend`、`cd-infra`（手動 dispatch + destroy guard）で構成。
- **シークレット同期の自動化。** `cd-backend` で「GitHub Secret → Container App Secret → 環境変数 binding」を毎回同期し、本番のシークレット欠落による起動失敗を構造的に防ぐ。
- **データ投入の運用。** 初期シードはコンテナが空のときのみ自動投入される。運用後にデータを更新する場合に備え、admin 限定の `/api/admin/reseed` で同梱ファイルを強制 upsert できる（既存行は上書き、削除はしない）。
- **サーバーレス構成。** Cosmos DB Serverless と Container Apps により、低トラフィック時のコストを抑えつつスケールできる。

### Responsible AI（M6）

評価・人事に近い領域で動くため、観測対象を行動指標に限定している。

- 日報頻度、「進められないこと」の言及、会議参加数、最終1on1からの経過日数などの客観シグナルのみを観測する
- 感情やメンタル状態の推測はしない
- 出力は判断ではなく「確認推奨」として提示する
- インサイトは根拠 ID を引用し、UI では「佐藤 美咲の日報（5/8）」のように人が辿れる形で示す

---

## 5. 機能一覧（M1–M9）

| Module | 内容 |
|---|---|
| M1 Member 360 | プロフィール / OKR / Career Canvas / 日報 / 1on1 / AI による状況整理 |
| M2 Daily Pulse | 日報の単日サマリー、複数日トレンドサマリー、生成物の永続化 |
| M3 1on1 Companion | 面談前の準備資料、議事録下書き |
| M4 Goal Alignment | OKR と日々の活動の整合性チェック |
| M5 Org Impact Simulator | 体制変更の影響予測（Prompt Flow + Critic / Refiner） |
| M6 Team Health | 行動指標ベースの予兆検知（感情推測なし） |
| M7 Admin Dashboard | 提出率・1on1 状況・OKR・AI 生成数の管理 KPI |
| M8 Career Canvas | 1年後 / 3年後の理想像、伸ばしたいスキル、挑戦したいロール |
| M9 成長サマリー | 本人向けに直近30日の日報と目標から成長ポイントを抽出 |

---

## 6. 使用 Azure サービス

| サービス | 用途 |
|---|---|
| Azure Container Apps | Frontend / Backend 実行環境 |
| Azure Container Registry | image build / store |
| Azure OpenAI | Chat / Reporter / Coach / Critic / embedding |
| Azure AI Foundry Agent Service | Analyzer Agent |
| Foundry Prompt Flow | Org Impact Simulator |
| Azure Cosmos DB Serverless | 業務データ + AI 生成物の永続化 |
| Application Insights | OpenTelemetry / GenAI tracing |
| Log Analytics | logs 集約 |
| Key Vault | secrets 管理（Terraform 側） |

Azure AI Search も provision 済みだが、Chat への hybrid RAG 連携は現時点では未配線（Future Work）。

---

## まとめ

AtlasLens は、EM の「分散したテキストからチーム状態を把握する」という業務課題に対し、

- 業務インパクト: 見落としの低減と意思決定の前倒し
- アプローチ: 自律ツール利用と品質ループ（Critic/Refiner）を持つ Agentic AI
- 完成度・実現性: 生成物の永続化・本番デプロイ・IaC/CI/CD・Responsible AI

をひとつの体験にまとめたものである。判断は人が担い、AI は判断材料の整備に徹する。その役割分担を Azure の Agentic AI スタックで形にした。

---

**タグ案**: `Azure`, `AzureOpenAI`, `AIFoundry`, `AgenticAI`, `FastAPI`, `React`, `CosmosDB`, `Hackathon`

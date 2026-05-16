# AtlasLens — デモ動画 脚本 (3分版)

## 想定視聴者
Microsoft Agent Hackathon 2026 審査員。EM 業務の文脈を10秒で伝え、Agentic AI の効果を視覚的に示す。

## 全体構成

| 時間 | 画面 | ナレーション | 表示テキスト |
|---|---|---|---|
| 0:00-0:10 | 黒画面 → AtlasLens ロゴ | "月曜朝。EM の田中さんがチームを見渡す時間です。" | "Mondays. 5 members. Where do you start?" |
| 0:10-0:30 | Dashboard 画面（チーム一覧 + Team Health） | "AtlasLens は EM のための AI 副操縦士。チーム健康指標を AI が客観的に整理。" | 新人 mem004 のところで "1on1 27 日前" "ブロッカー4件" のフラグを強調 |
| 0:30-0:50 | mem004 のメンバー詳細をクリック | "新卒の渡辺さん。日報・1on1・参加した議事録が一画面に。AI が直近の動きから ハイライト・リスク・成長サイン を抽出。" | Insights カードをハイライト |
| 0:50-1:20 | 1on1 準備ボタン → 事前パケット表示 | "1on1 ボタンを押すと AI が事前パケットを30秒で生成。直近のブロッカー、前回 1on1 のフォローアップ、成長を引き出す質問。" | Discussion topics / Growth questions セクションを順にズーム |
| 1:20-1:50 | 議事録テキストボックスに会話メモを貼る → 整形 | "1on1 中はメモを書くだけ。AI が議事録に整形し、ToDo と担当者を抽出。" | Summary / Decisions / ToDo を順にズーム |
| 1:50-2:20 | Org Simulator 画面 → "新卒のメンターを mem002 から mem001 に変更" を選択 | "体制変更の影響予測。AI が過去30日の会議参加データから コミュニケーション経路の変化 と 知識リスク を予測。" | Communication impacts + Knowledge risks セクションを順に表示 |
| 2:20-2:45 | Daily Pulse 画面 → 5/12 を選択 | "Daily Pulse はチーム全員の日報を AI が要約。EM は TL;DR と "サーフェスすべきブロッカー" だけ確認すれば良い。" | TL;DR セクションを表示 |
| 2:45-3:00 | AtlasLens ロゴ → 締め | "AtlasLens — AI が見続ける。あなたは決められる。" | "AtlasLens. EM Co-pilot powered by Azure AI." |

## 撮影のコツ

- 画面録画は OBS Studio + Audacity（マイク）でローカル収録
- 各セクションの遷移は CMD+CTRL+R などのキーバインドを設定し、画面が静止しないように
- ナレーションは別撮りして編集で合わせる（しゃべりながら操作するとミスが増える）
- 字幕は CapCut で日本語 + 英語の二段
- BGM は YouTube Audio Library から無料素材
- 1回通しで撮るのではなく、シーンごとに撮り直し可能なように分割収録

## 撮影前チェックリスト

- [ ] backend が起動済み (`uvicorn app.main:app --port 8000`)
- [ ] frontend が起動済み (`pnpm dev`)
- [ ] AtlasCorp seed データが反映されている
- [ ] AI 応答が安定している (1回 dry-run して確認)
- [ ] 個人情報が画面に映らないように (Slack 通知 OFF など)
- [ ] 全シーン分の URL を事前にブックマーク

# デモ動画 — 制作ガイド

脚本は [DEMO_SCRIPT.md](./DEMO_SCRIPT.md)。提出前チェックは [SUBMISSION_CHECKLIST.md](./SUBMISSION_CHECKLIST.md)。

## 推奨ワークフロー

1. **本番スモークテスト**（チェックリスト 8 項目）— 失敗したら録画しない
2. **シーン分割録画**（OBS）— チャット・シミュレーターは別テイク
3. **ナレーション録音**（Audacity 等）— 操作と分離するとミスが減る
4. **CapCut で編集** — 字幕（日+英）、BGM（YouTube Audio Library）
5. **5 分試写** — 知人 1 名に Agentic 性が伝わるか確認
6. **リテイク** — ツールトレース or SimulatorProgress が映らなければ再撮
7. **アップロード** — YouTube 限定公開推奨

## 審査員に刺さる 15 秒

- チャット: ツールトレースを **必ず展開**
- シミュレーター: **SimulatorProgress** が動いているクリップを 5 秒以上
- （余力）Foundry Tracing のスクショ 1 枚を 2:35 付近に挿入

## よくある失敗

| 症状 | 対処 |
|------|------|
| Insights がタイムアウト | 再試行 or 別メンバーで dry-run |
| チャットがツールを呼ばない | 質問を「進められないことを書いているメンバーと、1on1 が遅れている人は？」に変更 |
| シミュレーターが即終了 | Progress UI 録画のため、ネットワーク遅い時間帯を避ける |
| CORS エラー after deploy | Container App の `APP_ENV` / `JWT_SECRET` / Actions デプロイ完了を確認 |

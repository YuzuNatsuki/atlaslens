# AtlasLens — 提出チェックリスト（6/1 23:59 締切）

## 本番スモークテスト（録画前に実施）

**URL**: 新フロント Container App URL — `https://atlaslens-web.<env>.<region>.azurecontainerapps.io`（cd-infra apply 後に確定）  
**旧 URL (参考)**: https://orange-pond-02df6f200.7.azurestaticapps.net  
**EM アカウント**: `tanaka.ken@atlaslens.dev` （パスワードは申請時に個別配付）

| # | 操作 | 期待結果 | OK |
|---|------|----------|-----|
| 1 | ログイン | ダッシュボード表示 | [ ] |
| 2 | チームの様子 | 6 名分の行動指標 | [ ] |
| 3 | 渡辺 翔 → メンバー詳細 | プロフィール・OKR・日報 | [ ] |
| 4 | 「AI による状況整理」 | 30s 以内に 3 軸 + 参照元（日本語ラベル） | [ ] |
| 5 | 1on1 準備（1. 面談前の資料） | 面談前の資料を作成 | [ ] |
| 6 | チャット | ツールトレース + Markdown 回答 | [ ] |
| 7 | 組織改編シミュレーション | Progress UI → 結果 + Critic | [ ] |
| 8 | 日報サマリー | TL;DR + 参照件数表示 | [ ] |

### API クイックチェック（任意）

```bash
curl -s https://atlaslens-backend.politeisland-f552e471.japaneast.azurecontainerapps.io/ | jq .
# 期待: {"app":"AtlasLens","version":"0.1.0"}
```

## デモ動画

- [ ] [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) に沿って 3 分版を録画・編集
- [ ] YouTube または Vimeo に **限定公開 or 公開** でアップロード
- [ ] 動画 URL をメモ

## Zenn 記事

- [ ] [ZENN_ARTICLE.md](./ZENN_ARTICLE.md) をベースに Zenn エディタへ貼り付け
- [ ] スクリーンショット 4 枚を挿入
- [ ] 公開 → URL をメモ

## GitHub

- [ ] `main` に最新コミットを push（CI 緑）
- [ ] リポジトリが Public（または審査員が閲覧可能）
- [ ] README のデモ URL・アカウントが最新

## 提出フォーム（6/1 20:00 目標）

| 項目 | 値 |
|------|-----|
| 成果物 URL（アプリ） | 新フロント Container App URL（cd-infra apply 後に確定） |
| GitHub | https://github.com/YuzuNatsuki/atlaslens |
| デモ動画 URL | （記入） |
| Zenn 記事 URL | （記入） |

- [ ] フォーム送信完了（23:59 前）

## デプロイ注意（今回のコミット後）

`fix(security)` で CORS と JWT 検証を変更しています。本番 Container App で:

- `APP_ENV=production` の場合 → **`JWT_SECRET` が 32 文字以上で設定されていること**（未設定だと起動失敗）
- フロントは `https://orange-pond-02df6f200.7.azurestaticapps.net` がデフォルト CORS に含まれています

push 後 `cd-backend.yml` / `cd-frontend.yml` の完了を GitHub Actions で確認してからスモークテストしてください。

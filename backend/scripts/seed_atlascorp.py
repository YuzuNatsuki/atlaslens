"""Seed AtlasCorp data — deterministic, no LLM calls required.

Run from the repo root:
    python backend/scripts/seed_atlascorp.py

Generates members, goals, daily reports, meetings, and 1on1s under
`data/atlascorp/`. Safe to re-run — overwrites existing files.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "atlascorp"


# ---------- members ----------

MEMBERS = [
    {
        "id": "em001",
        "name": "田中 健",
        "role": "em",
        "title": "Engineering Manager",
        "joined_at": "2021-04-01",
        "manager_id": None,
        "skills": ["people management", "backend", "team building"],
        "interests": ["登山", "ジャズ"],
        "bio": "プラットフォームチームの EM。元バックエンドエンジニアで Go と Python。チーム規模拡大期。",
    },
    {
        "id": "mem001",
        "name": "佐藤 美咲",
        "role": "tech_lead",
        "title": "Tech Lead, Platform",
        "joined_at": "2022-10-01",
        "manager_id": "em001",
        "skills": ["sre", "kubernetes", "terraform", "observability"],
        "interests": ["コーヒー焙煎", "推し活"],
        "bio": "SRE 出身のテックリード。プラットフォーム全体の信頼性とアーキの責任者。",
    },
    {
        "id": "mem002",
        "name": "鈴木 亮",
        "role": "senior",
        "title": "Senior Backend Engineer",
        "joined_at": "2023-04-01",
        "manager_id": "em001",
        "skills": ["go", "grpc", "postgres", "distributed systems"],
        "interests": ["ボードゲーム", "ランニング"],
        "bio": "バックエンドの主力。決済とユーザー基盤の API を担当。",
    },
    {
        "id": "mem003",
        "name": "山本 由香",
        "role": "mid",
        "title": "Frontend Engineer",
        "joined_at": "2024-10-01",
        "manager_id": "em001",
        "skills": ["react", "typescript", "design systems", "accessibility"],
        "interests": ["イラスト", "猫"],
        "bio": "フロントエンドのデザインシステム担当。UI コンポーネントの統一を進めている。",
    },
    {
        "id": "mem004",
        "name": "渡辺 翔",
        "role": "junior",
        "title": "Software Engineer (New Grad)",
        "joined_at": "2025-11-01",
        "manager_id": "em001",
        "skills": ["python", "fastapi", "react"],
        "interests": ["音楽制作", "サウナ"],
        "bio": "新卒。オンボーディング途中。バックエンドとフロントエンドの両方に挑戦中。",
    },
]


# ---------- goals (2026 Q2) ----------

GOALS = {
    "em001": [
        {
            "id": "g-em001-1",
            "period": "2026-Q2",
            "objective": "チームの 1on1 サイクルとオンボーディング体験を改善する",
            "key_results": [
                "全メンバーで隔週 1on1 を 90% 以上開催",
                "新卒メンバーのオンボーディング完了率を 6 月末までに 80%",
                "障害ポストモーテムの実施率を 100%(チーム障害)",
            ],
            "progress_pct": 40,
            "status": "on_track",
        }
    ],
    "mem001": [
        {
            "id": "g-mem001-1",
            "period": "2026-Q2",
            "objective": "プラットフォームの SLO を導入し信頼性指標を可視化",
            "key_results": [
                "主要 3 サービスで SLO を定義しダッシュボード化",
                "アラート過多を 40% 削減 (ノイズ削減)",
                "オンコールローテーションを 4 名で確立",
            ],
            "progress_pct": 35,
            "status": "at_risk",
        }
    ],
    "mem002": [
        {
            "id": "g-mem002-1",
            "period": "2026-Q2",
            "objective": "決済 API の信頼性向上",
            "key_results": [
                "p99 レイテンシを 350ms → 200ms",
                "エラーレートを 0.5% → 0.1%",
                "リカバリ Runbook を全障害ケースで整備",
            ],
            "progress_pct": 60,
            "status": "on_track",
        }
    ],
    "mem003": [
        {
            "id": "g-mem003-1",
            "period": "2026-Q2",
            "objective": "デザインシステムをチーム全体に展開",
            "key_results": [
                "コアコンポーネント 30 種を Storybook に公開",
                "プロダクト 3 つで採用率 70%",
                "アクセシビリティ AA 準拠率 90%",
            ],
            "progress_pct": 50,
            "status": "on_track",
        }
    ],
    "mem004": [
        {
            "id": "g-mem004-1",
            "period": "2026-Q2",
            "objective": "新卒オンボーディングを完遂し、初の機能リリースを担う",
            "key_results": [
                "オンボーディング項目 20 件のうち 18 件完了",
                "小規模機能を 1 つ単独リリース",
                "PR 自己レビューチェックリスト習慣化",
            ],
            "progress_pct": 20,
            "status": "at_risk",
        }
    ],
}


# ---------- daily reports (last 10 weekdays) ----------

_today = date(2026, 5, 13)


def _weekdays(end: date, count: int) -> list[date]:
    days: list[date] = []
    d = end
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d)
        d = d - timedelta(days=1)
    return list(reversed(days))


DAILY_DATES = _weekdays(_today - timedelta(days=1), 10)


DAILY_REPORTS = {
    "mem001": [
        ("Kubernetes クラスタのアップグレード検証", "本番反映のリリースノート整理", ""),
        ("Terraform モジュール整理 PR レビュー", "SLO ダッシュボードのワイヤーフレーム", ""),
        ("SLO ダッシュボードのワイヤーフレーム", "Datadog の SLO 機能 PoC", ""),
        ("Datadog の SLO 機能 PoC", "オンコール体制ドラフト", "オンコール候補の合意が取れない"),
        ("オンコール体制ドラフト見直し", "EM と相談、メンバー打診", "アラート過多で集中時間が取れない"),
        ("アラート整理スプリント開始", "誤検知パターンの抽出", ""),
        ("誤検知パターンの抽出と修正", "SLO 定義ワークショップ準備", ""),
        ("SLO 定義ワークショップ", "ワークショップの議事録共有", ""),
        ("障害対応 (DB スパイク)", "ポストモーテム下書き", "障害対応で他タスクが押し気味"),
        ("ポストモーテム提出", "翌週のアラートクリーンアップ計画", ""),
    ],
    "mem002": [
        ("決済 API の負荷試験 設計", "テスト環境の整備", ""),
        ("テスト環境の整備", "p99 計測の初回ラン", ""),
        ("p99 計測 1回目", "ボトルネック箇所の絞り込み", ""),
        ("コネクションプール調整 PR", "ベンチ再計測", ""),
        ("ベンチ再計測 (p99 320ms)", "Index 追加 PR", ""),
        ("Index 追加と本番反映準備", "Runbook ドラフト", ""),
        ("本番反映 + 監視", "Runbook ドラフト続き", ""),
        ("Runbook 共有 (Tech Lead レビュー)", "決済リトライ戦略の再設計", ""),
        ("リトライ戦略の調査", "新人 (mem004) のメンタリング", ""),
        ("mem004 と決済モジュールのペアプロ", "次スプリント計画", ""),
    ],
    "mem003": [
        ("Button コンポーネントの a11y 改善", "Storybook 公開準備", ""),
        ("Storybook で Button/Input 公開", "Modal コンポーネントの仕様議論", ""),
        ("Modal の仕様議論", "Modal 実装着手", ""),
        ("Modal 実装", "Form コンポーネントの設計レビュー", ""),
        ("Form の設計レビュー", "プロダクトA への組込み計画", ""),
        ("プロダクトA で Button を採用 PR", "アクセシビリティ AA チェック", ""),
        ("a11y AA チェック (axe-core)", "改善 PR", ""),
        ("a11y 改善 PR レビュー反映", "Modal の Storybook 化", ""),
        ("Modal 公開", "Form コンポーネント着手", ""),
        ("Form 実装 (50%)", "テストケース整備", ""),
    ],
    "mem004": [
        ("オンボ Day8: ローカル環境構築完了", "決済モジュールのコードリーディング", "Docker のメモリ不足"),
        ("Docker メモリ不足解消、決済コードリーディング", "簡単な PR (typo修正)", ""),
        ("初 PR マージ", "テスト追加の練習", ""),
        ("テスト追加 PR", "Code Review の指摘対応", "TypeScript の型エラー解消に時間"),
        ("型エラー解消", "mem002 とペアプロ", "ペアプロ前の準備不足"),
        ("mem002 とペアプロ (決済 API)", "リトライ処理の小機能 PR", ""),
        ("リトライ処理 PR 提出", "PR レビュー待ち", ""),
        ("レビュー指摘対応", "ドキュメント更新の練習", ""),
        ("ドキュメント PR", "週次振り返り", ""),
        ("週次振り返りで詰まりを共有", "翌週のスプリント計画参加", "1on1 が前回から 4 週空いている"),
    ],
}


# ---------- meetings ----------

MEETINGS = [
    {
        "id": "mtg-2026-05-12-platform-weekly",
        "title": "Platform Weekly",
        "held_at": "2026-05-12T10:00:00",
        "attendees": ["em001", "mem001", "mem002", "mem003", "mem004"],
        "agenda": [
            "先週の障害振り返り",
            "SLO 導入の進捗",
            "決済 API パフォーマンス",
            "デザインシステム展開",
        ],
        "notes": (
            "決済 API の p99 が 320ms まで改善。SLO 導入は来週ワークショップ予定。"
            "デザインシステムは Modal が公開済み、Form 着手中。"
            "新卒 (渡辺) がペアプロを通じて貢献を開始。"
        ),
        "decisions": [
            "SLO ワークショップを 5/14 に開催",
            "決済 API の Index 追加 PR を本日中にマージ",
        ],
        "action_items": [
            "佐藤: SLO ワークショップ準備",
            "鈴木: Index 追加 PR マージ後の本番監視",
            "山本: Form コンポーネント仕様レビュー依頼",
        ],
    },
    {
        "id": "mtg-2026-05-08-incident-postmortem",
        "title": "DB スパイク障害 ポストモーテム",
        "held_at": "2026-05-08T15:00:00",
        "attendees": ["em001", "mem001", "mem002"],
        "agenda": ["タイムライン整理", "根因と要因", "再発防止"],
        "notes": (
            "5/7 14:20 に DB のコネクション枯渇でユーザー機能が 18 分間部分的に停止。"
            "原因は決済 API の長時間トランザクション。決済側の改善と監視強化で合意。"
        ),
        "decisions": [
            "コネクションプール上限を 2 倍に暫定引き上げ",
            "決済 API のトランザクション境界を見直し",
        ],
        "action_items": [
            "鈴木: トランザクション境界の修正 PR",
            "佐藤: 同種アラートのしきい値再調整",
        ],
    },
    {
        "id": "mtg-2026-05-05-design-system-review",
        "title": "デザインシステム展開レビュー",
        "held_at": "2026-05-05T13:00:00",
        "attendees": ["em001", "mem003"],
        "agenda": ["公開済みコンポーネント", "プロダクト採用率", "次の優先順位"],
        "notes": (
            "Button / Input / Modal を公開。プロダクトA で Button 採用率 40%。"
            "Form コンポーネントを次優先。a11y AA チェックの自動化を検討。"
        ),
        "decisions": ["Form を次スプリントで完成"],
        "action_items": ["山本: Form ベータ版を 5/22 までに公開"],
    },
    {
        "id": "mtg-2026-04-30-okr-kickoff",
        "title": "2026 Q2 OKR キックオフ",
        "held_at": "2026-04-30T10:00:00",
        "attendees": ["em001", "mem001", "mem002", "mem003", "mem004"],
        "agenda": ["Q2 OKR 共有", "チーム間の依存関係"],
        "notes": (
            "全員が Q2 OKR をプレゼン。佐藤の SLO 導入と鈴木の決済 API 改善は依存関係あり。"
            "山本のデザインシステムは全プロダクトに影響。新卒 (渡辺) はオンボ最優先。"
        ),
        "decisions": ["佐藤と鈴木で週次同期", "渡辺は週 2 回のペアプロを継続"],
        "action_items": [
            "佐藤: SLO 設計案の初稿",
            "鈴木: 決済 API のベンチ計画",
            "山本: 採用率測定の仕組み導入",
        ],
    },
    {
        "id": "mtg-2026-04-25-architecture-review",
        "title": "アーキテクチャレビュー (オンコール体制)",
        "held_at": "2026-04-25T14:00:00",
        "attendees": ["em001", "mem001", "mem002"],
        "agenda": ["オンコール候補", "アラート整理", "ローテーション"],
        "notes": "オンコール候補で合意が取れず継続協議。アラート整理を先行することで合意。",
        "decisions": ["アラート整理スプリントを 5 月中に開始"],
        "action_items": ["佐藤: アラートインベントリ作成"],
    },
]


# ---------- 1on1s ----------

ONE_ON_ONES = {
    "mem001": [
        {
            "id": "1on1-mem001-2026-05-06",
            "em_id": "em001",
            "held_at": "2026-05-06T11:00:00",
            "topics": ["SLO 導入の進捗", "オンコール候補の壁", "キャリア (技術と人の両方)"],
            "notes": (
                "SLO 定義のドラフトはあるが、合意形成に時間がかかっている。"
                "オンコール候補のメンバー打診で社内政治的な調整が必要。"
                "キャリア的にはマネージメント興味あり、技術リードの次のステップを考えたい。"
            ),
            "todos": [
                "佐藤: ワークショップ準備",
                "EM: オンコール候補のステークホルダー調整支援",
            ],
            "follow_ups": ["6 月の半期評価でキャリア相談", "ワークショップ後の振り返り"],
        }
    ],
    "mem002": [
        {
            "id": "1on1-mem002-2026-05-07",
            "em_id": "em001",
            "held_at": "2026-05-07T15:00:00",
            "topics": ["決済 API 進捗", "新人メンタリング", "次の挑戦"],
            "notes": (
                "p99 改善は順調。新人 (渡辺) のペアプロが効いていると感じている。"
                "次は分散トレーシングの導入か、決済の海外展開対応に挑戦したい。"
            ),
            "todos": ["鈴木: 海外展開の調査ペーパー", "EM: メンタリング工数の評価への反映"],
            "follow_ups": ["分散トレーシング PoC の検討"],
        }
    ],
    "mem003": [
        {
            "id": "1on1-mem003-2026-04-29",
            "em_id": "em001",
            "held_at": "2026-04-29T13:00:00",
            "topics": ["デザインシステム展開", "他チーム連携", "成長軸"],
            "notes": (
                "プロダクトチームとの会話が増えてきた。採用率を可視化したい。"
                "次のステップはコンポーネント設計のリードを取りたい。"
            ),
            "todos": ["山本: 採用率測定のダッシュボード設計"],
            "follow_ups": ["プロダクトチームとの定例参加可否"],
        }
    ],
    "mem004": [
        {
            "id": "1on1-mem004-2026-04-15",
            "em_id": "em001",
            "held_at": "2026-04-15T16:00:00",
            "topics": ["オンボの困りごと", "技術習得の進度", "メンタル状態 (本人発信)"],
            "notes": (
                "ローカル環境構築で 3 日溶けた。質問しづらさを感じている。"
                "TypeScript の型でつまずきが多い。先輩からのレビューは丁寧で助かる。"
            ),
            "todos": ["EM: 質問しやすい仕組み (担当メンター明示)", "渡辺: 型ガイドの読み込み"],
            "follow_ups": ["次回 1on1 を 2 週間後に設定 (実際は 4 週間空いた → 要対応)"],
        }
    ],
}


# ---------- writers ----------


def write_member_yaml(member: dict) -> None:
    path = DATA_DIR / "members" / f"{member['id']}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(member, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_goals_yaml(member_id: str, goals: list[dict]) -> None:
    enriched = []
    for g in goals:
        enriched.append({**g, "member_id": member_id})
    path = DATA_DIR / "goals" / f"{member_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(enriched, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _frontmatter_block(front: dict) -> str:
    return "---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False).rstrip() + "\n---"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def write_daily_report(
    member_id: str,
    report_date: date,
    yesterday: str,
    today: str,
    blockers: str,
) -> None:
    path = DATA_DIR / "daily_reports" / member_id / f"{report_date.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        [
            _frontmatter_block({"date": report_date.isoformat()}),
            "",
            "## 昨日",
            "",
            yesterday,
            "",
            "## 今日",
            "",
            today,
            "",
            "## ブロッカー",
            "",
            blockers,
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")


def write_meeting(meeting: dict) -> None:
    path = DATA_DIR / "meetings" / f"{meeting['id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    front = {
        "id": meeting["id"],
        "title": meeting["title"],
        "held_at": meeting["held_at"],
        "attendees": meeting["attendees"],
        "agenda": meeting["agenda"],
    }
    body = "\n".join(
        [
            _frontmatter_block(front),
            "",
            "## ノート",
            "",
            meeting["notes"],
            "",
            "## 決定",
            "",
            _bullets(meeting["decisions"]),
            "",
            "## アクション",
            "",
            _bullets(meeting["action_items"]),
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")


def write_one_on_one(member_id: str, record: dict) -> None:
    path = (
        DATA_DIR
        / "one_on_ones"
        / member_id
        / f"{record['held_at'][:10]}.md"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    front = {
        "id": record["id"],
        "em_id": record["em_id"],
        "held_at": record["held_at"],
        "topics": record["topics"],
    }
    body = "\n".join(
        [
            _frontmatter_block(front),
            "",
            "## ノート",
            "",
            record["notes"],
            "",
            "## ToDo",
            "",
            _bullets(record["todos"]),
            "",
            "## フォローアップ",
            "",
            _bullets(record["follow_ups"]),
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for member in MEMBERS:
        write_member_yaml(member)

    for member_id, goals in GOALS.items():
        write_goals_yaml(member_id, goals)

    for member_id, entries in DAILY_REPORTS.items():
        for d, (yesterday, today, blockers) in zip(DAILY_DATES, entries):
            write_daily_report(member_id, d, yesterday, today, blockers)

    for meeting in MEETINGS:
        write_meeting(meeting)

    for member_id, records in ONE_ON_ONES.items():
        for record in records:
            write_one_on_one(member_id, record)

    print(f"Seeded AtlasCorp data under {DATA_DIR}")


if __name__ == "__main__":
    main()

"""Daily report storage — Cosmos when configured, file fallback otherwise."""

from __future__ import annotations

from datetime import date

from app.core.config import get_settings
from app.core.cosmos_client import cosmos_configured
from app.models.schemas import DailyReport


def save_daily_report(report: DailyReport) -> None:
    if cosmos_configured():
        from app.services import cosmos_repo

        cosmos_repo.upsert_daily(report)
        return
    _save_file(report)


def existing_report(member_id: str, report_date: date) -> bool:
    if cosmos_configured():
        from app.services import cosmos_repo

        return any(r.report_date == report_date for r in cosmos_repo.list_daily_for(member_id))
    path = get_settings().data_dir / "daily_reports" / member_id / f"{report_date.isoformat()}.md"
    return path.exists()


def _save_file(report: DailyReport) -> None:
    settings = get_settings()
    folder = settings.data_dir / "daily_reports" / report.member_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{report.report_date.isoformat()}.md"
    body = "\n".join(
        [
            "---",
            f"date: {report.report_date.isoformat()}",
            *(f"mood: {report.mood}" for _ in [None] if report.mood is not None),
            "---",
            "",
            "## 昨日",
            "",
            report.yesterday,
            "",
            "## 今日",
            "",
            report.today,
            "",
            "## ブロッカー",
            "",
            report.blockers,
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")

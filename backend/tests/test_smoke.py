"""Smoke tests — minimum CI gate.

These guarantee the API surface and key invariants haven't drifted.
They run in <1s and require no external services.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_tools import TOOL_DEFINITIONS, TOOL_HANDLERS
from app.services.chat import STYLE_PRESETS
from app.services.team_health import _flag_facts

client = TestClient(app)


def test_root_ok():
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["app"] == "AtlasLens"


def test_unauthorized_chat():
    res = client.post("/api/chat", json={"messages": []})
    assert res.status_code == 401


def test_admin_reseed_unauthorized():
    """/api/admin/reseed must require admin auth (not even anonymous)."""
    res = client.post("/api/admin/reseed", json={"scope": "all"})
    assert res.status_code == 401


def test_force_reseed_rejects_unknown_scope(monkeypatch):
    from app.services import seed_migration

    # Stub Cosmos bootstrap so the test can run without a Cosmos account.
    monkeypatch.setattr(seed_migration, "ensure_all_containers", lambda: None)
    monkeypatch.setattr(seed_migration, "_file_profiles", lambda: ["x"])

    with pytest.raises(ValueError):
        seed_migration.force_reseed_from_files("daily_reports,bogus_kind")


def test_unauthorized_chat_history():
    assert client.get("/api/chat/history").status_code == 401
    assert client.delete("/api/chat/history").status_code == 401


def test_chat_history_round_trip_without_cosmos(monkeypatch):
    from app.services import chat_history

    monkeypatch.setattr(chat_history, "cosmos_configured", lambda: False)
    chat_history.clear_session("em001")
    assert chat_history.get_session("em001") is None

    saved = chat_history.save_session(
        "em001",
        messages=[
            {"role": "user", "content": "こんにちは"},
            {
                "role": "assistant",
                "content": "返答です",
                "tool_calls": [{"name": "list_team", "arguments": {}, "result_preview": "x", "elapsed_ms": 1}],
            },
        ],
        style="concise",
    )
    assert len(saved["messages"]) == 2
    assert saved["style"] == "concise"

    loaded = chat_history.get_session("em001")
    assert loaded is not None
    assert loaded["messages"][0]["content"] == "こんにちは"
    assert loaded["messages"][1]["tool_calls"][0]["name"] == "list_team"

    chat_history.clear_session("em001")
    assert chat_history.get_session("em001") is None


def test_unauthorized_team_health():
    res = client.get("/api/health/team")
    assert res.status_code == 401


def test_tool_definitions_match_handlers():
    """Every tool advertised to the LLM must have an implementation."""
    advertised = {t["function"]["name"] for t in TOOL_DEFINITIONS}
    assert advertised == set(TOOL_HANDLERS.keys()), (
        f"Tool surface drift: advertised={advertised} implemented={set(TOOL_HANDLERS.keys())}"
    )


@pytest.mark.parametrize(
    "signals,expected_fact_substr",
    [
        (
            {
                "daily_reports_last_14d": 3,
                "blockers_mentioned_last_14d": 0,
                "meetings_attended_last_14d": 5,
                "days_since_last_one_on_one": 5,
            },
            "日報の提出",
        ),
        (
            {
                "daily_reports_last_14d": 14,
                "blockers_mentioned_last_14d": 5,
                "meetings_attended_last_14d": 5,
                "days_since_last_one_on_one": 5,
            },
            "進められないことの記載",
        ),
        (
            {
                "daily_reports_last_14d": 14,
                "blockers_mentioned_last_14d": 0,
                "meetings_attended_last_14d": 30,
                "days_since_last_one_on_one": 5,
            },
            "会議参加",
        ),
        (
            {
                "daily_reports_last_14d": 14,
                "blockers_mentioned_last_14d": 0,
                "meetings_attended_last_14d": 5,
                "days_since_last_one_on_one": 30,
            },
            "前回1on1から",
        ),
    ],
)
def test_team_health_flags(signals, expected_fact_substr):
    facts = _flag_facts(signals)
    assert any(expected_fact_substr in f for f in facts), facts


def test_chat_style_presets_have_required_keys():
    for _key, preset in STYLE_PRESETS.items():
        assert "label" in preset
        assert "instructions" in preset
        assert "temperature" in preset
        assert 0 <= preset["temperature"] <= 1


def test_artefact_store_round_trip_without_cosmos(monkeypatch):
    """When Cosmos is not configured, get_artefact returns None and save_artefact
    returns a body the API can still echo without crashing."""
    from app.services import artefact_store

    monkeypatch.setattr(artefact_store, "cosmos_configured", lambda: False)
    assert artefact_store.get_artefact("team-summary", "2026-05-12") is None
    res = artefact_store.save_artefact(
        "team-summary",
        "2026-05-12",
        {"tldr": ["x"]},
        extra={"report_count": 1},
    )
    assert res["payload"] == {"tldr": ["x"]}
    assert res["report_count"] == 1
    assert artefact_store.delete_artefact("team-summary", "2026-05-12") is False
    assert artefact_store.list_artefacts("team-summary") == []


def test_goal_schema_accepts_career_canvas():
    """The extended Goal schema must accept and preserve career-canvas fields."""
    from app.models.schemas import Goal

    g = Goal(
        id="g-test-2026-Q2",
        member_id="mem-test",
        period="2026-Q2",
        objective="自分の OKR",
        key_results=["KR-1", "KR-2"],
        progress_pct=40,
        career_vision_1y="リードエンジニアとして 1 つのサブシステムを任される",
        career_vision_3y="プロダクト全体のアーキを牽引する",
        skills_to_grow=["分散システム", "性能設計"],
        roles_to_explore=["Tech Lead"],
        support_needed="月1の設計レビュー",
    )
    body = g.model_dump(mode="json")
    assert body["career_vision_1y"].startswith("リードエンジニア")
    assert body["skills_to_grow"] == ["分散システム", "性能設計"]
    assert Goal.model_validate(body).roles_to_explore == ["Tech Lead"]


def test_goal_schema_backwards_compatible():
    """Old goal payloads without career fields must still validate."""
    from app.models.schemas import Goal

    g = Goal(
        id="g-old",
        member_id="mem-old",
        period="2026-Q1",
        objective="既存目標",
        key_results=["A"],
    )
    assert g.career_vision_1y is None
    assert g.skills_to_grow == []


def test_admin_dashboard_unauthorized():
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 401


def test_growth_summary_unauthorized():
    res = client.post("/api/me/growth-summary", json={})
    assert res.status_code == 401

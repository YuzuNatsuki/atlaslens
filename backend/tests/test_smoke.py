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


def test_audit_events_admin_only():
    """Audit log viewer must reject unauthenticated callers."""
    res = client.get("/api/admin/audit-events")
    assert res.status_code == 401


def test_audit_record_event_in_memory(monkeypatch):
    """Without Cosmos configured, audit events go to the in-memory buffer."""
    from app.core import audit

    monkeypatch.setattr(audit, "cosmos_configured", lambda: False)
    audit.reset_in_memory()
    audit.record_event(
        actor_id="em001",
        actor_email="tanaka@example.com",
        actor_role="em",
        action=audit.ACTION_VIEW,
        target_kind="member",
        target_id="mem001",
        path="/api/members/mem001",
        method="GET",
        status_code=200,
    )
    rows = audit.list_events()
    assert len(rows) == 1
    assert rows[0]["actor_id"] == "em001"
    assert rows[0]["action"] == audit.ACTION_VIEW


def _fake_artefact_store(monkeypatch, *modules):
    """Inject a dict-backed artefact store into the given modules.

    artefact_store deliberately returns None when Cosmos isn't configured, so
    we need a separate fake to test services that round-trip through it.
    """
    from datetime import UTC, datetime

    store: dict[tuple[str, str], dict] = {}

    def fake_get(kind: str, key: str):
        item = store.get((kind, key))
        if item is None:
            return None
        return dict(item)

    def fake_save(kind: str, key: str, payload, *, extra=None):
        doc = {
            "id": f"{kind}:{key}",
            "kind": kind,
            "key": key,
            "payload": payload,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            **(extra or {}),
        }
        store[(kind, key)] = doc
        return dict(doc)

    def fake_delete(kind: str, key: str):
        return store.pop((kind, key), None) is not None

    def fake_list(kind: str, *, limit: int = 50):
        rows = [v for (k, _), v in store.items() if k == kind]
        rows.sort(key=lambda r: r.get("generated_at", ""), reverse=True)
        return rows[:limit]

    for m in modules:
        monkeypatch.setattr(m, "get_artefact", fake_get, raising=False)
        monkeypatch.setattr(m, "save_artefact", fake_save, raising=False)
        monkeypatch.setattr(m, "delete_artefact", fake_delete, raising=False)
        monkeypatch.setattr(m, "list_artefacts", fake_list, raising=False)
    return store


def test_agent_memory_round_trip(monkeypatch):
    """Adding a focus member and a topic must round-trip via the artefact store."""
    from app.services import agent_memory

    _fake_artefact_store(monkeypatch, agent_memory)

    memory = agent_memory.get_memory("em001")
    assert memory["focus_members"] == []

    after_add = agent_memory.add_focus_member(
        "em001", member_id="mem003", reason="退職リスク監視"
    )
    assert any(
        f["member_id"] == "mem003" for f in after_add["focus_members"]
    )

    after_topic = agent_memory.record_topic(
        "em001", topic="渡辺さんの1on1で離職検討を確認"
    )
    assert after_topic["recent_topics"][0]["topic"].startswith("渡辺さん")

    prompt = agent_memory.format_for_prompt(
        "em001", member_index={"mem003": "山本 由香"}
    )
    assert "山本 由香" in prompt
    assert "渡辺さん" in prompt

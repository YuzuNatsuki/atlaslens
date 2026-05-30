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
            "ブロッカー言及",
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
    for key, preset in STYLE_PRESETS.items():
        assert "label" in preset
        assert "instructions" in preset
        assert "temperature" in preset
        assert 0 <= preset["temperature"] <= 1

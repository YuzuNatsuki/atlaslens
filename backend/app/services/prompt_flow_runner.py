"""Run the Org Impact Simulator Prompt Flow inline from the backend.

The DAG (`infra/prompt_flow/org_impact/flow.dag.yaml`) is also deployable as a
Foundry managed online endpoint — we re-use the same files. When the env var
`PROMPT_FLOW_ENDPOINT` is set, we call the deployed endpoint over HTTPS.
Otherwise we execute the flow in-process via the promptflow SDK.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import httpx

from app.core.config import get_settings

FLOW_DIR = Path(
    os.environ.get(
        "PROMPT_FLOW_DIR",
        str(Path(__file__).resolve().parents[2].parent / "infra" / "prompt_flow" / "org_impact"),
    )
)


@lru_cache
def _ensure_local_connection() -> None:
    """Register the `atlaslens_aoai` connection in the local promptflow store.

    Called once when we first run the flow in-process. Reads AOAI creds from
    backend env vars and registers an AzureOpenAI connection promptflow can use.
    """
    from promptflow.client import PFClient
    from promptflow.entities import AzureOpenAIConnection

    settings = get_settings()
    pf = PFClient()
    conn = AzureOpenAIConnection(
        name="atlaslens_aoai",
        api_key=settings.azure_openai_api_key,
        api_base=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        api_type="azure",
    )
    pf.connections.create_or_update(conn)


def _run_inprocess(inputs: dict) -> dict:
    """Run the flow via the local promptflow runtime."""
    _ensure_local_connection()
    from promptflow.client import PFClient

    pf = PFClient()
    result = pf.test(flow=str(FLOW_DIR), inputs=inputs)
    return result.get("result") if isinstance(result, dict) else result


def _run_remote(inputs: dict, endpoint: str, key: str) -> dict:
    response = httpx.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=inputs,
        timeout=120.0,
    )
    response.raise_for_status()
    body = response.json()
    # Endpoints typically wrap the flow output under "outputs"
    if isinstance(body, dict) and "outputs" in body:
        return body["outputs"].get("result", body["outputs"])
    return body.get("result", body) if isinstance(body, dict) else body


def run_org_impact_flow(inputs: dict) -> dict:
    endpoint = os.environ.get("PROMPT_FLOW_ENDPOINT")
    key = os.environ.get("PROMPT_FLOW_KEY")
    if endpoint and key:
        return _run_remote(inputs, endpoint, key)
    return _run_inprocess(inputs)

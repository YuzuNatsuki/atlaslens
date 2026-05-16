"""Placeholder kept for future Foundry Agent Service migration.

We initially attempted to migrate every agent to Foundry Agent Service but the
required data-plane permissions on the AIServices project did not propagate
within the hackathon timebox. The Foundry-native pieces we keep are:

  * Model deployment under `atlaslens-foundry` (kind=AIServices)
  * Prompt Flow for the Org Impact Simulator (separate code path)
  * OpenTelemetry tracing exported to Application Insights, visible in Foundry portal

This module remains so we can re-enable Agent Service paths later by populating
`run_agent_json` again.
"""

from __future__ import annotations


def run_agent_json(*_, **__) -> str:  # pragma: no cover
    raise NotImplementedError(
        "Foundry Agent Service is not currently wired. Use app.core.azure_clients.chat_complete."
    )

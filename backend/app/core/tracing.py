"""OpenTelemetry tracing exporter targeting Application Insights.

Foundry's portal renders these traces under the project's "Tracing" tab as long
as the same Application Insights resource is linked to the Foundry Hub / Project
(it already is — `atlaslens-appi` was created during Foundry provisioning).

Why we trace:
  * Visible record of every LLM call (prompt, response, latency, tokens)
  * Prompt Flow runs auto-trace via the promptflow SDK
  * Foundry Agent Service runs auto-trace via AIAgentsInstrumentor — these
    show up under "Tracing" in the Foundry Portal as GenAI spans (model,
    prompt, completion, tool calls) rather than plain HTTP dependencies
  * FastAPI + httpx instrumentation captures the request lifecycle around them
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

log = logging.getLogger(__name__)


@lru_cache
def setup_tracing(service_name: str = "atlaslens-backend") -> bool:
    """Initialise OpenTelemetry once at process start. Returns True if active."""
    conn_str = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn_str:
        log.info("APPLICATIONINSIGHTS_CONNECTION_STRING not set — tracing disabled.")
        return False

    try:
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: F401
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # promptflow already integrates OTel; we just need a provider.
        provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
        exporter = AzureMonitorTraceExporter.from_connection_string(conn_str)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        HTTPXClientInstrumentor().instrument()

        # azure-core needs an OTel bridge before AIAgentsInstrumentor will
        # emit any spans — without this its `start_span()` silently returns
        # a no-op span. Once registered, every Foundry agent SDK call
        # produces a real OTel span.
        try:
            from azure.core.settings import settings as az_settings
            from azure.core.tracing.ext.opentelemetry_span import OpenTelemetrySpan

            az_settings.tracing_implementation = OpenTelemetrySpan
        except Exception as exc:  # noqa: BLE001
            log.warning("azure-core OTel bridge registration failed: %s", exc)

        # GenAI semantic conventions for Foundry Agent Service runs.
        # `enable_content_recording=True` includes prompts + completions in
        # the span attributes so the Foundry Portal can render them. This is
        # fine for our demo data (no PII); flip to False for any deployment
        # with real customer content.
        try:
            from azure.ai.agents.telemetry import AIAgentsInstrumentor

            AIAgentsInstrumentor().instrument(enable_content_recording=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("AIAgentsInstrumentor.instrument() failed: %s", exc)

        # FastAPI instrumentation is applied per-app in main.py after app creation.
        log.warning("OpenTelemetry tracing → Application Insights enabled (%s).", service_name)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to initialise OpenTelemetry tracing: %s", exc)
        return False


def instrument_fastapi(app) -> None:
    """Attach FastAPI middleware once the app instance exists."""
    if not os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:  # noqa: BLE001
        log.warning("FastAPI tracing instrumentation failed: %s", exc)

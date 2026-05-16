"""OpenTelemetry tracing exporter targeting Application Insights.

Foundry's portal renders these traces under the project's "Tracing" tab as long
as the same Application Insights resource is linked to the Foundry Hub / Project
(it already is — `atlaslens-appi` was created during Foundry provisioning).

Why we trace:
  * Visible record of every LLM call (prompt, response, latency, tokens)
  * Prompt Flow runs auto-trace via the promptflow SDK
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
        # FastAPI instrumentation is applied per-app in main.py after app creation.
        log.info("OpenTelemetry tracing → Application Insights enabled (%s).", service_name)
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

"""Cosmos DB client + container helpers.

Synchronous SDK is fine for AtlasLens — most requests are batched LLM calls,
not high-frequency DB hits, so we keep the data layer simple.

Containers and partition keys:
    members        /id
    goals          /member_id
    daily_reports  /member_id
    one_on_ones    /member_id
    meetings       /id
    prep_notes     /member_id
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy, PartitionKey

from app.core.config import get_settings


CONTAINER_DEFS: dict[str, str] = {
    "members": "/id",
    "goals": "/member_id",
    "daily_reports": "/member_id",
    "one_on_ones": "/member_id",
    "meetings": "/id",
    "prep_notes": "/member_id",
}


def cosmos_configured() -> bool:
    settings = get_settings()
    return bool(settings.cosmos_endpoint and settings.cosmos_key)


@lru_cache
def get_client() -> CosmosClient:
    settings = get_settings()
    return CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)


@lru_cache
def get_database() -> DatabaseProxy:
    settings = get_settings()
    client = get_client()
    return client.create_database_if_not_exists(id=settings.cosmos_database)


@lru_cache
def get_container(name: str) -> ContainerProxy:
    if name not in CONTAINER_DEFS:
        raise KeyError(f"unknown Cosmos container: {name}")
    pk = CONTAINER_DEFS[name]
    return get_database().create_container_if_not_exists(
        id=name,
        partition_key=PartitionKey(path=pk),
    )


def ensure_all_containers() -> None:
    """Create database + all expected containers if missing. Safe to call repeatedly."""
    for name in CONTAINER_DEFS:
        get_container(name)


def count_items(container_name: str) -> int:
    container = get_container(container_name)
    result = list(
        container.query_items(
            "SELECT VALUE COUNT(1) FROM c", enable_cross_partition_query=True
        )
    )
    return int(result[0]) if result else 0


def query(container_name: str, sql: str, *, parameters: list[dict] | None = None) -> Iterable[dict]:
    container = get_container(container_name)
    return container.query_items(
        query=sql,
        parameters=parameters or [],
        enable_cross_partition_query=True,
    )

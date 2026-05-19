"""Re-seed the production Cosmos DB from the local data/atlascorp/ files.

Use this after `seed_atlascorp.py` has been re-run to refresh the YAML/MD
source files. Existing rows in Cosmos with the same `id` are overwritten via
UPSERT; rows whose id is no longer in the local files are left alone (we
don't issue deletes).

Run from the repo root with COSMOS_ENDPOINT + COSMOS_KEY env vars set:

    cd backend
    source .venv/bin/activate
    COSMOS_ENDPOINT='https://atlaslens-cosmos.documents.azure.com:443/' \
    COSMOS_KEY='...' \
    DATA_DIR=../data/atlascorp \
    python scripts/reseed_cosmos.py
"""

from __future__ import annotations

import logging
import sys

from app.models.schemas import DailyReport, Goal, OneOnOne
from app.services import cosmos_repo, org_repo
from app.services.data_loader import DataLoader
from app.services.seed_migration import (
    _file_daily,
    _file_goals,
    _file_meetings,
    _file_one_on_ones,
    _file_profiles,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    profiles = _file_profiles()
    if not profiles:
        log.error("No file profiles found. Check DATA_DIR.")
        return 1
    log.info("Loaded %d member profiles from files", len(profiles))

    # --- org hierarchy (upsert always) ---
    org_repo.upsert_company(org_repo.SEED_COMPANY)
    for d in org_repo.SEED_DIVISIONS:
        org_repo.upsert_division(d)
    for d in org_repo.SEED_DEPARTMENTS:
        org_repo.upsert_department(d)
    for t in org_repo.SEED_TEAMS:
        org_repo.upsert_team(t)
    log.info("Upserted org hierarchy: %d divs, %d depts, %d teams",
             len(org_repo.SEED_DIVISIONS), len(org_repo.SEED_DEPARTMENTS), len(org_repo.SEED_TEAMS))

    # --- members ---
    enriched = org_repo.apply_assignments_to(profiles)
    n_members = cosmos_repo.bulk_upsert_members(enriched)
    log.info("Upserted %d members", n_members)

    # --- goals ---
    all_goals: list[Goal] = []
    for m in profiles:
        all_goals.extend(_file_goals(m.id))
    if all_goals:
        n = cosmos_repo.bulk_upsert_goals(all_goals)
        log.info("Upserted %d goals", n)

    # --- daily reports ---
    all_daily: list[DailyReport] = []
    for m in profiles:
        all_daily.extend(_file_daily(m.id))
    if all_daily:
        n = cosmos_repo.bulk_upsert_daily(all_daily)
        log.info("Upserted %d daily reports", n)

    # --- one_on_ones ---
    all_one_on_ones: list[OneOnOne] = []
    for m in profiles:
        all_one_on_ones.extend(_file_one_on_ones(m.id))
    if all_one_on_ones:
        n = cosmos_repo.bulk_upsert_one_on_ones(all_one_on_ones)
        log.info("Upserted %d 1on1s", n)

    # --- meetings ---
    meetings = _file_meetings()
    if meetings:
        n = cosmos_repo.bulk_upsert_meetings(meetings)
        log.info("Upserted %d meetings", n)

    # Sanity: re-read members from Cosmos
    loader = DataLoader()
    after = loader.load_profiles()
    log.info("Cosmos now has %d members: %s", len(after), [m.id for m in after])
    return 0


if __name__ == "__main__":
    sys.exit(main())

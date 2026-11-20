"""Seed the database with synthetic demo data (personas + optional population).

uv run python backend/scripts/seed_demo.py [--population 400]
"""

import argparse
import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parents[1]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db.session import get_session_factory, init_db
from app.demo_seed import (  # noqa: F401 - re-exported for tests and scripts
    PERSONAS,
    generate_population,
    hash_phone,
    seed_demo_personas,
    seed_population,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed TrustLedger demo data")
    parser.add_argument("--population", type=int, default=0, help="Synthetic applicants to add")
    args = parser.parse_args()
    users = seed_demo_personas()
    print(f"Seeded {len(users)} demo personas.")
    for u in users:
        print(f"  - {u.id}: group={u.gender}_{u.region} division={u.division}")
    if args.population:
        init_db()
        with get_session_factory()() as session:
            count = seed_population(session, args.population)
        print(f"Seeded {count} synthetic applicants.")


if __name__ == "__main__":
    main()

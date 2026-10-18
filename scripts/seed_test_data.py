"""Seed fabricated demo hazard records (every workflow state) so the Dashboard,
Register, Follow-up and Reports screens have content without a real first visit.

    python scripts/seed_test_data.py                          # Firestore (auto)
    SITEGUARD_BACKEND=local python scripts/seed_test_data.py  # local demo storage
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from lib import demo_seed, store  # noqa: E402


def main() -> None:
    print(f"Backend: {store.backend_name()}")
    created = demo_seed.seed()
    for hid in created:
        print(f"Created hazard: {hid}")
    print(f"\nSeeded {len(created)} fabricated hazard record(s).")


if __name__ == "__main__":
    main()

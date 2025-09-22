#!/usr/bin/env python3
"""
Migration script to migrate jobs from JSON to SQLite database.

This script can be run manually to migrate existing job data.
The migration is also performed automatically when the API starts.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import init_db, migrate_from_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main migration function."""
    print("🔄 Starting job data migration...")

    # Initialize database
    init_db()
    print("✅ Database initialized")

    # Migrate from JSON
    json_file = Path("outputs/jobs.json")
    if json_file.exists():
        print(f"📁 Found existing JSON file: {json_file}")
        migrate_from_json(json_file)
        print("✅ Migration completed")

        # Optionally backup the JSON file
        backup_file = json_file.with_suffix(".json.backup")
        json_file.rename(backup_file)
        print(f"📦 JSON file backed up to: {backup_file}")

    else:
        print("📭 No existing JSON file found - nothing to migrate")

    print("🎉 Migration process finished!")


if __name__ == "__main__":
    main()

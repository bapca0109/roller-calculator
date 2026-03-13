"""
Migration script to backfill packing_type for existing quotes.
Sets packing_type to 'standard' for all quotes that don't have it set.

Run with: python migrations/backfill_packing_type.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient


async def backfill_packing_type():
    """Backfill packing_type='standard' for quotes without it."""
    
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME', 'roller_calculator')
    
    if not mongo_url:
        print("ERROR: MONGO_URL environment variable not set")
        return
    
    print(f"Connecting to MongoDB...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Count quotes without packing_type
        count_without = await db.quotes.count_documents({
            "$or": [
                {"packing_type": {"$exists": False}},
                {"packing_type": None},
                {"packing_type": ""}
            ]
        })
        
        total_count = await db.quotes.count_documents({})
        
        print(f"\n=== Migration: Backfill packing_type ===")
        print(f"Total quotes in database: {total_count}")
        print(f"Quotes without packing_type: {count_without}")
        
        if count_without == 0:
            print("\n✅ All quotes already have packing_type set. No migration needed.")
            return
        
        # Confirm before proceeding
        print(f"\nThis will update {count_without} quotes to have packing_type='standard'")
        
        # Perform the update
        result = await db.quotes.update_many(
            {
                "$or": [
                    {"packing_type": {"$exists": False}},
                    {"packing_type": None},
                    {"packing_type": ""}
                ]
            },
            {
                "$set": {
                    "packing_type": "standard",
                    "migration_updated_at": datetime.utcnow(),
                    "migration_note": "backfill_packing_type_2026_03_13"
                }
            }
        )
        
        print(f"\n✅ Migration complete!")
        print(f"   Matched: {result.matched_count}")
        print(f"   Modified: {result.modified_count}")
        
        # Verify
        remaining = await db.quotes.count_documents({
            "$or": [
                {"packing_type": {"$exists": False}},
                {"packing_type": None},
                {"packing_type": ""}
            ]
        })
        
        print(f"\n   Remaining quotes without packing_type: {remaining}")
        
        # Show sample of updated quotes
        print(f"\n📋 Sample of updated quotes:")
        cursor = db.quotes.find(
            {"migration_note": "backfill_packing_type_2026_03_13"},
            {"quote_number": 1, "packing_type": 1, "packing_charges": 1}
        ).limit(5)
        
        async for quote in cursor:
            print(f"   - {quote.get('quote_number', 'N/A')}: packing_type={quote.get('packing_type')}, charges={quote.get('packing_charges', 0)}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        client.close()
        print(f"\nDatabase connection closed.")


if __name__ == "__main__":
    print("=" * 50)
    print("  Packing Type Backfill Migration")
    print("=" * 50)
    asyncio.run(backfill_packing_type())

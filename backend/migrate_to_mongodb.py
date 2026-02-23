"""
Migration script to move hardcoded roller standards data to MongoDB.
Run this script once to populate the database with initial data.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "roller_calculator")

# Data to migrate
MIGRATION_DATA = {
    # Pipe Diameters with display codes
    "pipe_diameters": [
        {"actual_od": 60.8, "display_code": 60, "standard": "IS-9295"},
        {"actual_od": 76.1, "display_code": 76, "standard": "IS-9295"},
        {"actual_od": 88.9, "display_code": 89, "standard": "IS-9295"},
        {"actual_od": 114.3, "display_code": 114, "standard": "IS-9295"},
        {"actual_od": 127.0, "display_code": 127, "standard": "IS-9295"},
        {"actual_od": 139.7, "display_code": 139, "standard": "IS-9295"},
        {"actual_od": 152.4, "display_code": 152, "standard": "IS-9295"},
        {"actual_od": 159.0, "display_code": 159, "standard": "IS-9295"},
        {"actual_od": 165.0, "display_code": 165, "standard": "IS-9295"},
    ],
    
    # Shaft Diameters
    "shaft_diameters": [
        {"diameter": 20, "weight_per_meter": 2.47},
        {"diameter": 25, "weight_per_meter": 3.85},
        {"diameter": 30, "weight_per_meter": 5.55},
        {"diameter": 35, "weight_per_meter": 7.55},
        {"diameter": 40, "weight_per_meter": 9.87},
        {"diameter": 45, "weight_per_meter": 12.48},
        {"diameter": 50, "weight_per_meter": 15.41},
    ],
    
    # Shaft End Types
    "shaft_end_types": [
        {"type": "A", "extension_mm": 26, "description": "Type A (+26mm)"},
        {"type": "B", "extension_mm": 36, "description": "Type B (+36mm) - Default"},
        {"type": "C", "extension_mm": 56, "description": "Type C (+56mm)"},
    ],
    
    # Bearings with costs
    "bearings": [
        # 20mm shaft
        {"number": "6204", "shaft_dia": 20, "od": 47, "series": "62", "costs": {"china": 20, "skf": 70, "fag": 70, "timken": 61}, "seal_cost": 13},
        {"number": "6304", "shaft_dia": 20, "od": 52, "series": "63", "costs": {"china": 30, "skf": 97, "fag": 89, "timken": 85}, "seal_cost": 18},
        {"number": "420204", "shaft_dia": 20, "od": 47, "series": "42", "costs": {"fag": 54}, "seal_cost": 13},
        # 25mm shaft
        {"number": "6205", "shaft_dia": 25, "od": 52, "series": "62", "costs": {"china": 26, "skf": 84, "fag": 70, "timken": 70}, "seal_cost": 18},
        {"number": "6305", "shaft_dia": 25, "od": 62, "series": "63", "costs": {"skf": 178, "fag": 124, "timken": 124}, "seal_cost": 25},
        {"number": "420205", "shaft_dia": 25, "od": 52, "series": "42", "costs": {"fag": 60}, "seal_cost": 18},
        # 30mm shaft
        {"number": "6206", "shaft_dia": 30, "od": 62, "series": "62", "costs": {"china": 40, "skf": 135, "fag": 105, "timken": 105}, "seal_cost": 25},
        {"number": "6306", "shaft_dia": 30, "od": 72, "series": "63", "costs": {"skf": 216, "fag": 177, "timken": 177}, "seal_cost": 40},
        {"number": "420206", "shaft_dia": 30, "od": 62, "series": "42", "costs": {"fag": 83}, "seal_cost": 25},
        # 35mm shaft
        {"number": "6207", "shaft_dia": 35, "od": 72, "series": "62", "costs": {"skf": 205, "fag": 190, "timken": 190}, "seal_cost": 40},
        {"number": "6307", "shaft_dia": 35, "od": 80, "series": "63", "costs": {"skf": 342, "fag": 225, "timken": 216}, "seal_cost": 50},
        # 40mm shaft
        {"number": "6208", "shaft_dia": 40, "od": 80, "series": "62", "costs": {"skf": 264, "fag": 210, "timken": 210}, "seal_cost": 50},
        {"number": "6308", "shaft_dia": 40, "od": 90, "series": "63", "costs": {"skf": 320, "fag": 275, "timken": 275}, "seal_cost": 90},
        # 45mm shaft
        {"number": "6209", "shaft_dia": 45, "od": 85, "series": "62", "costs": {"skf": 320, "fag": 270, "timken": 270}, "seal_cost": 90},
        {"number": "6309", "shaft_dia": 45, "od": 100, "series": "63", "costs": {"skf": 520, "fag": 400, "timken": 400}, "seal_cost": 120},
        # 50mm shaft
        {"number": "6210", "shaft_dia": 50, "od": 90, "series": "62", "costs": {"skf": 515, "fag": 400, "timken": 400}, "seal_cost": 120},
        {"number": "6310", "shaft_dia": 50, "od": 110, "series": "63", "costs": {"skf": 1046, "fag": 800, "timken": 800}, "seal_cost": 140},
    ],
    
    # Housing configurations and costs
    "housings": [
        {"housing_dia": 56, "bearing_bore": 47, "pipe_dia": 60.8, "cost": 21},
        {"housing_dia": 72, "bearing_bore": 47, "pipe_dia": 76.1, "cost": 22},
        {"housing_dia": 72, "bearing_bore": 52, "pipe_dia": 76.1, "cost": 24},
        {"housing_dia": 84, "bearing_bore": 47, "pipe_dia": 88.9, "cost": 23},
        {"housing_dia": 84, "bearing_bore": 52, "pipe_dia": 88.9, "cost": 25},
        {"housing_dia": 84, "bearing_bore": 62, "pipe_dia": 88.9, "cost": 28},
        {"housing_dia": 108, "bearing_bore": 47, "pipe_dia": 114.3, "cost": 33},
        {"housing_dia": 108, "bearing_bore": 52, "pipe_dia": 114.3, "cost": 35},
        {"housing_dia": 108, "bearing_bore": 62, "pipe_dia": 114.3, "cost": 45},
        {"housing_dia": 108, "bearing_bore": 72, "pipe_dia": 114.3, "cost": 50},
        {"housing_dia": 121, "bearing_bore": 47, "pipe_dia": 127.0, "cost": 42},
        {"housing_dia": 121, "bearing_bore": 52, "pipe_dia": 127.0, "cost": 45},
        {"housing_dia": 121, "bearing_bore": 62, "pipe_dia": 127.0, "cost": 50},
        {"housing_dia": 121, "bearing_bore": 72, "pipe_dia": 127.0, "cost": 57},
        {"housing_dia": 121, "bearing_bore": 80, "pipe_dia": 127.0, "cost": 68},
        {"housing_dia": 133, "bearing_bore": 52, "pipe_dia": 139.7, "cost": 50},
        {"housing_dia": 133, "bearing_bore": 62, "pipe_dia": 139.7, "cost": 55},
        {"housing_dia": 133, "bearing_bore": 72, "pipe_dia": 139.7, "cost": 60},
        {"housing_dia": 133, "bearing_bore": 80, "pipe_dia": 139.7, "cost": 65},
        {"housing_dia": 133, "bearing_bore": 90, "pipe_dia": 139.7, "cost": 70},
        {"housing_dia": 146, "bearing_bore": 52, "pipe_dia": 152.4, "cost": 57},
        {"housing_dia": 146, "bearing_bore": 62, "pipe_dia": 152.4, "cost": 60},
        {"housing_dia": 146, "bearing_bore": 72, "pipe_dia": 152.4, "cost": 65},
        {"housing_dia": 146, "bearing_bore": 80, "pipe_dia": 152.4, "cost": 70},
        {"housing_dia": 146, "bearing_bore": 90, "pipe_dia": 152.4, "cost": 80},
        {"housing_dia": 153, "bearing_bore": 62, "pipe_dia": 159.0, "cost": 60},
        {"housing_dia": 153, "bearing_bore": 72, "pipe_dia": 159.0, "cost": 65},
        {"housing_dia": 153, "bearing_bore": 80, "pipe_dia": 159.0, "cost": 70},
        {"housing_dia": 153, "bearing_bore": 90, "pipe_dia": 159.0, "cost": 80},
        {"housing_dia": 153, "bearing_bore": 100, "pipe_dia": 159.0, "cost": 90},
        {"housing_dia": 159, "bearing_bore": 52, "pipe_dia": 165.0, "cost": 65},
        {"housing_dia": 159, "bearing_bore": 62, "pipe_dia": 165.0, "cost": 70},
        {"housing_dia": 159, "bearing_bore": 72, "pipe_dia": 165.0, "cost": 75},
        {"housing_dia": 159, "bearing_bore": 80, "pipe_dia": 165.0, "cost": 80},
        {"housing_dia": 159, "bearing_bore": 90, "pipe_dia": 165.0, "cost": 100},
        {"housing_dia": 159, "bearing_bore": 100, "pipe_dia": 165.0, "cost": 120},
    ],
    
    # Pipe weights per meter (by type A/B/C)
    "pipe_weights": [
        {"pipe_dia": 60.8, "type_a": 4.14, "type_b": 5.14, "type_c": 6.21},
        {"pipe_dia": 76.1, "type_a": 5.84, "type_b": 6.52, "type_c": 7.90},
        {"pipe_dia": 88.9, "type_a": 6.86, "type_b": 8.47, "type_c": 10.05},
        {"pipe_dia": 114.3, "type_a": 9.96, "type_b": 12.11, "type_c": 14.32},
        {"pipe_dia": 127.0, "type_a": 12.13, "type_b": 14.61, "type_c": 15.99},
        {"pipe_dia": 139.7, "type_a": 13.39, "type_b": 16.13, "type_c": 17.66},
        {"pipe_dia": 152.4, "type_a": 14.64, "type_b": 17.65, "type_c": 19.33},
        {"pipe_dia": 159.0, "type_a": 15.29, "type_b": 18.44, "type_c": 20.20},
        {"pipe_dia": 165.0, "type_a": 15.88, "type_b": 19.16, "type_c": 20.99},
    ],
    
    # Roller lengths by belt width (carrying)
    "roller_lengths": [
        {"belt_width": 500, "roller_type": "carrying", "lengths": [200]},
        {"belt_width": 650, "roller_type": "carrying", "lengths": [250]},
        {"belt_width": 800, "roller_type": "carrying", "lengths": [315]},
        {"belt_width": 1000, "roller_type": "carrying", "lengths": [380]},
        {"belt_width": 1200, "roller_type": "carrying", "lengths": [465]},
        {"belt_width": 1400, "roller_type": "carrying", "lengths": [530]},
        {"belt_width": 1600, "roller_type": "carrying", "lengths": [600]},
        {"belt_width": 1800, "roller_type": "carrying", "lengths": [670]},
        {"belt_width": 2000, "roller_type": "carrying", "lengths": [750]},
        # Return roller lengths
        {"belt_width": 500, "roller_type": "return", "single_length": 600, "two_piece_length": 250},
        {"belt_width": 650, "roller_type": "return", "single_length": 750, "two_piece_length": 380},
        {"belt_width": 800, "roller_type": "return", "single_length": 950, "two_piece_length": 465},
        {"belt_width": 1000, "roller_type": "return", "single_length": 1150, "two_piece_length": 600},
        {"belt_width": 1200, "roller_type": "return", "single_length": 1400, "two_piece_length": 700},
        {"belt_width": 1400, "roller_type": "return", "single_length": 1600, "two_piece_length": 800},
        {"belt_width": 1600, "roller_type": "return", "single_length": 1800, "two_piece_length": 900},
        {"belt_width": 1800, "roller_type": "return", "single_length": 2000, "two_piece_length": 1000},
        {"belt_width": 2000, "roller_type": "return", "single_length": 2200, "two_piece_length": 1100},
    ],
    
    # Circlip costs by shaft diameter
    "circlips": [
        {"shaft_dia": 20, "cost_per_piece": 1.0},
        {"shaft_dia": 25, "cost_per_piece": 1.5},
        {"shaft_dia": 30, "cost_per_piece": 2.0},
        {"shaft_dia": 35, "cost_per_piece": 2.5},
        {"shaft_dia": 40, "cost_per_piece": 3.0},
        {"shaft_dia": 45, "cost_per_piece": 10.0},
        {"shaft_dia": 50, "cost_per_piece": 12.0},
    ],
    
    # Rubber lagging options for impact rollers
    "rubber_lagging": [
        {"pipe_code": 60, "rubber_options": [90, 114]},
        {"pipe_code": 76, "rubber_options": [114, 127, 140]},
        {"pipe_code": 89, "rubber_options": [127, 140, 152]},
        {"pipe_code": 114, "rubber_options": [139, 152, 165, 190]},
        {"pipe_code": 127, "rubber_options": [165, 190]},
        {"pipe_code": 139, "rubber_options": [165, 190]},
        {"pipe_code": 152, "rubber_options": [190]},
    ],
    
    # Rubber ring costs
    "rubber_rings": [
        {"pipe_code": 60, "rubber_dia": 90, "cost_per_ring": 16},
        {"pipe_code": 60, "rubber_dia": 114, "cost_per_ring": 20},
        {"pipe_code": 76, "rubber_dia": 114, "cost_per_ring": 20},
        {"pipe_code": 76, "rubber_dia": 127, "cost_per_ring": 22},
        {"pipe_code": 76, "rubber_dia": 140, "cost_per_ring": 30},
        {"pipe_code": 89, "rubber_dia": 127, "cost_per_ring": 32},
        {"pipe_code": 89, "rubber_dia": 140, "cost_per_ring": 36},
        {"pipe_code": 89, "rubber_dia": 152, "cost_per_ring": 42},
        {"pipe_code": 114, "rubber_dia": 139, "cost_per_ring": 35},
        {"pipe_code": 114, "rubber_dia": 152, "cost_per_ring": 40},
        {"pipe_code": 114, "rubber_dia": 165, "cost_per_ring": 47},
        {"pipe_code": 114, "rubber_dia": 190, "cost_per_ring": 72},
        {"pipe_code": 127, "rubber_dia": 165, "cost_per_ring": 55},
        {"pipe_code": 127, "rubber_dia": 190, "cost_per_ring": 68},
        {"pipe_code": 139, "rubber_dia": 165, "cost_per_ring": 54},
        {"pipe_code": 139, "rubber_dia": 190, "cost_per_ring": 63},
        {"pipe_code": 152, "rubber_dia": 190, "cost_per_ring": 65},
    ],
    
    # Locking ring costs for impact rollers
    "locking_rings": [
        {"pipe_code": 60, "cost": 18},
        {"pipe_code": 76, "cost": 20},
        {"pipe_code": 89, "cost": 22},
        {"pipe_code": 114, "cost": 26},
        {"pipe_code": 127, "cost": 28},
        {"pipe_code": 139, "cost": 30},
        {"pipe_code": 152, "cost": 32},
        {"pipe_code": 159, "cost": 34},
        {"pipe_code": 165, "cost": 38},
    ],
    
    # Discount slabs
    "discount_slabs": [
        {"min_value": 0, "max_value": 200000, "discount_percent": 5.0},
        {"min_value": 200000, "max_value": 500000, "discount_percent": 7.5},
        {"min_value": 500000, "max_value": 750000, "discount_percent": 10.0},
        {"min_value": 750000, "max_value": 1000000, "discount_percent": 15.0},
        {"min_value": 1000000, "max_value": 1500000, "discount_percent": 20.0},
        {"min_value": 1500000, "max_value": 3000000, "discount_percent": 25.0},
        {"min_value": 3000000, "max_value": 5000000, "discount_percent": 28.0},
        {"min_value": 5000000, "max_value": 10000000, "discount_percent": 30.0},
        {"min_value": 10000000, "max_value": 999999999, "discount_percent": 35.0},
    ],
    
    # Freight rates
    "freight_rates": [
        {"min_km": 0, "max_km": 300, "rate_per_kg": 2.0},
        {"min_km": 300, "max_km": 600, "rate_per_kg": 4.0},
        {"min_km": 600, "max_km": 1000, "rate_per_kg": 5.0},
        {"min_km": 1000, "max_km": 1500, "rate_per_kg": 7.0},
        {"min_km": 1500, "max_km": 9999, "rate_per_kg": 9.0},
    ],
    
    # Packing charges
    "packing_options": [
        {"type": "none", "percent": 0.0, "description": "No packing"},
        {"type": "standard", "percent": 1.0, "description": "Standard packing"},
        {"type": "pallet", "percent": 4.0, "description": "Pallet packing"},
        {"type": "wooden_box", "percent": 8.0, "description": "Wooden box packing"},
    ],
    
    # GST configuration
    "gst_config": [
        {"key": "gst_rate", "value": 18.0, "description": "Standard GST rate"},
        {"key": "cgst_rate", "value": 9.0, "description": "Central GST rate"},
        {"key": "sgst_rate", "value": 9.0, "description": "State GST rate"},
        {"key": "igst_rate", "value": 18.0, "description": "Integrated GST rate"},
        {"key": "company_state_code", "value": "24", "description": "Gujarat state code"},
        {"key": "dispatch_pincode", "value": "382433", "description": "Dispatch location pincode"},
    ],
    
    # Raw material costs
    "raw_material_costs": [
        {"material": "pipe", "cost_per_kg": 67, "unit": "INR/kg"},
        {"material": "shaft", "cost_per_kg": 62, "unit": "INR/kg"},
        {"material": "rubber_ring_thickness", "value": 35, "unit": "mm"},
        {"material": "layout_markup", "value": 0.32, "unit": "percent"},
        {"material": "profit_markup", "value": 0.60, "unit": "percent"},
    ],
}


async def run_migration():
    """Run the migration to populate MongoDB with roller standards data"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print(f"Connected to MongoDB: {DB_NAME}")
    print("Starting migration...")
    
    migration_summary = []
    
    for collection_name, data in MIGRATION_DATA.items():
        try:
            # Check if collection already has data
            existing_count = await db[collection_name].count_documents({})
            
            if existing_count > 0:
                print(f"  ⚠️  {collection_name}: Already has {existing_count} documents, skipping...")
                migration_summary.append(f"{collection_name}: SKIPPED (existing: {existing_count})")
                continue
            
            # Add metadata to each document
            for item in data:
                item["created_at"] = datetime.utcnow()
                item["migrated_from"] = "roller_standards.py"
            
            # Insert all documents
            result = await db[collection_name].insert_many(data)
            inserted_count = len(result.inserted_ids)
            print(f"  ✅ {collection_name}: Inserted {inserted_count} documents")
            migration_summary.append(f"{collection_name}: INSERTED {inserted_count}")
            
        except Exception as e:
            print(f"  ❌ {collection_name}: Error - {str(e)}")
            migration_summary.append(f"{collection_name}: ERROR - {str(e)}")
    
    # Create indexes for faster lookups
    print("\nCreating indexes...")
    try:
        await db.pipe_diameters.create_index("actual_od", unique=True)
        await db.shaft_diameters.create_index("diameter", unique=True)
        await db.bearings.create_index("number", unique=True)
        await db.housings.create_index([("housing_dia", 1), ("bearing_bore", 1)])
        await db.pipe_weights.create_index("pipe_dia", unique=True)
        await db.circlips.create_index("shaft_dia", unique=True)
        await db.rubber_rings.create_index([("pipe_code", 1), ("rubber_dia", 1)])
        await db.locking_rings.create_index("pipe_code", unique=True)
        print("  ✅ Indexes created successfully")
    except Exception as e:
        print(f"  ⚠️  Index creation: {str(e)}")
    
    print("\n" + "="*50)
    print("MIGRATION SUMMARY")
    print("="*50)
    for item in migration_summary:
        print(f"  {item}")
    print("="*50)
    
    client.close()
    return migration_summary


if __name__ == "__main__":
    asyncio.run(run_migration())

"""
Database-backed prices module
Fetches prices from MongoDB with fallback to hardcoded values
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, Optional
import asyncio

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "roller_calculator")

# Global client and cache
_client = None
_db = None
_price_cache = {}
_cache_timestamp = 0
_cache_ttl = 60  # Cache for 60 seconds


def get_db():
    """Get database connection"""
    global _client, _db
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URL)
        _db = _client[DB_NAME]
    return _db


async def refresh_price_cache():
    """Refresh the price cache from MongoDB"""
    global _price_cache, _cache_timestamp
    import time
    
    db = get_db()
    
    try:
        # Fetch all prices from custom_prices collection
        cursor = db.custom_prices.find({})
        prices = await cursor.to_list(length=100)
        
        cache = {}
        for price in prices:
            key = price.get("key")
            value = price.get("value")
            if key and value is not None:
                cache[key] = value
        
        _price_cache = cache
        _cache_timestamp = time.time()
        return True
    except Exception as e:
        print(f"Error refreshing price cache: {e}")
        return False


async def get_custom_price(key: str, default: float = 0) -> float:
    """Get a custom price from cache/DB with fallback to default"""
    global _price_cache, _cache_timestamp
    import time
    
    # Check if cache needs refresh
    if time.time() - _cache_timestamp > _cache_ttl:
        await refresh_price_cache()
    
    return _price_cache.get(key, default)


async def get_bearing_cost_from_db(bearing_number: str, make: str = "china") -> Optional[float]:
    """Get bearing cost from MongoDB"""
    db = get_db()
    
    try:
        bearing = await db.bearings.find_one({"number": bearing_number})
        if bearing and "costs" in bearing:
            costs = bearing["costs"]
            make_lower = make.lower()
            if make_lower in costs:
                return costs[make_lower]
            # Return cheapest if requested make not available
            if costs:
                return min(costs.values())
    except Exception as e:
        print(f"Error fetching bearing cost: {e}")
    
    return None


async def get_seal_cost_from_db(bearing_number: str) -> Optional[float]:
    """Get seal cost from MongoDB"""
    db = get_db()
    
    try:
        bearing = await db.bearings.find_one({"number": bearing_number})
        if bearing and "seal_cost" in bearing:
            return bearing["seal_cost"]
    except Exception as e:
        print(f"Error fetching seal cost: {e}")
    
    return None


async def get_housing_cost_from_db(housing_dia: int, bearing_bore: int) -> Optional[float]:
    """Get housing cost from MongoDB"""
    db = get_db()
    
    try:
        housing = await db.housings.find_one({
            "housing_dia": housing_dia,
            "bearing_bore": bearing_bore
        })
        if housing and "cost" in housing:
            return housing["cost"]
    except Exception as e:
        print(f"Error fetching housing cost: {e}")
    
    return None


async def get_circlip_cost_from_db(shaft_dia: int) -> Optional[float]:
    """Get circlip cost from MongoDB"""
    db = get_db()
    
    try:
        circlip = await db.circlips.find_one({"shaft_dia": shaft_dia})
        if circlip and "cost_per_piece" in circlip:
            return circlip["cost_per_piece"]
    except Exception as e:
        print(f"Error fetching circlip cost: {e}")
    
    return None


async def get_rubber_ring_cost_from_db(pipe_code: int, rubber_dia: int) -> Optional[float]:
    """Get rubber ring cost from MongoDB"""
    db = get_db()
    
    try:
        ring = await db.rubber_rings.find_one({
            "pipe_code": pipe_code,
            "rubber_dia": rubber_dia
        })
        if ring and "cost_per_ring" in ring:
            return ring["cost_per_ring"]
    except Exception as e:
        print(f"Error fetching rubber ring cost: {e}")
    
    return None


async def get_locking_ring_cost_from_db(pipe_code: int) -> Optional[float]:
    """Get locking ring cost from MongoDB"""
    db = get_db()
    
    try:
        ring = await db.locking_rings.find_one({"pipe_code": pipe_code})
        if ring and "cost" in ring:
            return ring["cost"]
    except Exception as e:
        print(f"Error fetching locking ring cost: {e}")
    
    return None


async def get_pipe_weight_from_db(pipe_dia: float, pipe_type: str) -> Optional[float]:
    """Get pipe weight per meter from MongoDB"""
    db = get_db()
    
    try:
        pipe = await db.pipe_weights.find_one({"pipe_dia": pipe_dia})
        if pipe:
            type_key = f"type_{pipe_type.lower()}"
            if type_key in pipe:
                return pipe[type_key]
    except Exception as e:
        print(f"Error fetching pipe weight: {e}")
    
    return None


async def get_shaft_weight_from_db(shaft_dia: int) -> Optional[float]:
    """Get shaft weight per meter from MongoDB"""
    db = get_db()
    
    try:
        shaft = await db.shaft_diameters.find_one({"diameter": shaft_dia})
        if shaft and "weight_per_meter" in shaft:
            return shaft["weight_per_meter"]
    except Exception as e:
        print(f"Error fetching shaft weight: {e}")
    
    return None


async def get_raw_material_rates_from_db() -> Dict[str, float]:
    """Get raw material rates from MongoDB"""
    db = get_db()
    rates = {}
    
    try:
        cursor = db.raw_material_costs.find({})
        materials = await cursor.to_list(length=20)
        
        for mat in materials:
            if mat.get("material") == "pipe":
                rates["pipe_cost_per_kg"] = mat.get("cost_per_kg", 67)
            elif mat.get("material") == "shaft":
                rates["shaft_cost_per_kg"] = mat.get("cost_per_kg", 62)
    except Exception as e:
        print(f"Error fetching raw material rates: {e}")
    
    return rates


async def get_all_prices_for_calculation() -> Dict[str, Any]:
    """
    Get all prices needed for roller cost calculation from MongoDB.
    Returns a dict with all price data, using DB values where available
    and falling back to hardcoded values where not.
    """
    db = get_db()
    prices = {}
    
    try:
        # Get raw material rates
        raw_rates = await get_raw_material_rates_from_db()
        prices["pipe_cost_per_kg"] = raw_rates.get("pipe_cost_per_kg", 67)
        prices["shaft_cost_per_kg"] = raw_rates.get("shaft_cost_per_kg", 62)
        
        # Get bearings
        cursor = db.bearings.find({})
        bearings = await cursor.to_list(length=50)
        prices["bearings"] = {b["number"]: b for b in bearings}
        
        # Get housings
        cursor = db.housings.find({})
        housings = await cursor.to_list(length=100)
        prices["housings"] = {f"{h['housing_dia']}/{h['bearing_bore']}": h["cost"] for h in housings}
        
        # Get circlips
        cursor = db.circlips.find({})
        circlips = await cursor.to_list(length=20)
        prices["circlips"] = {c["shaft_dia"]: c["cost_per_piece"] for c in circlips}
        
        # Get rubber rings
        cursor = db.rubber_rings.find({})
        rings = await cursor.to_list(length=50)
        prices["rubber_rings"] = {f"{r['pipe_code']}/{r['rubber_dia']}": r["cost_per_ring"] for r in rings}
        
        # Get locking rings
        cursor = db.locking_rings.find({})
        locking = await cursor.to_list(length=20)
        prices["locking_rings"] = {l["pipe_code"]: l["cost"] for l in locking}
        
        # Get pipe weights
        cursor = db.pipe_weights.find({})
        pipe_weights = await cursor.to_list(length=20)
        prices["pipe_weights"] = {}
        for pw in pipe_weights:
            prices["pipe_weights"][pw["pipe_dia"]] = {
                "A": pw.get("type_a", 0),
                "B": pw.get("type_b", 0),
                "C": pw.get("type_c", 0),
            }
        
        # Get shaft weights
        cursor = db.shaft_diameters.find({})
        shafts = await cursor.to_list(length=20)
        prices["shaft_weights"] = {s["diameter"]: s["weight_per_meter"] for s in shafts}
        
    except Exception as e:
        print(f"Error fetching all prices: {e}")
    
    return prices


# Synchronous wrapper functions for use in non-async code
def get_bearing_cost_sync(bearing_number: str, make: str = "china", fallback: float = 0) -> float:
    """Synchronous wrapper to get bearing cost"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, can't use run_until_complete
            return fallback
        result = loop.run_until_complete(get_bearing_cost_from_db(bearing_number, make))
        return result if result is not None else fallback
    except:
        return fallback


def get_all_prices_sync() -> Dict[str, Any]:
    """Synchronous wrapper to get all prices"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return {}
        return loop.run_until_complete(get_all_prices_for_calculation())
    except:
        return {}

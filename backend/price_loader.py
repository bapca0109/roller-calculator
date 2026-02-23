"""
Price Loader Module - Synchronous MongoDB access for calculation functions

This module provides synchronous access to custom prices stored in MongoDB,
with fallback to hardcoded defaults from roller_standards.py
"""

import os
from pymongo import MongoClient
from typing import Dict, Any, Optional
import time

# MongoDB connection (synchronous)
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# Cache settings
_cache: Dict[str, Any] = {}
_cache_timestamp: float = 0
_cache_ttl: int = 30  # Cache for 30 seconds

# Lazy-loaded client
_client: Optional[MongoClient] = None
_db = None


def _get_db():
    """Get synchronous database connection (lazy initialization)"""
    global _client, _db
    if _client is None:
        _client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
        _db = _client[DB_NAME]
    return _db


def _refresh_cache():
    """Refresh price cache from MongoDB"""
    global _cache, _cache_timestamp
    
    try:
        db = _get_db()
        custom_prices = db.custom_prices.find_one({"_id": "prices"})
        if custom_prices:
            _cache = custom_prices
        else:
            _cache = {}
        _cache_timestamp = time.time()
    except Exception as e:
        print(f"[price_loader] Error refreshing cache: {e}")
        # Keep existing cache on error
        _cache_timestamp = time.time()  # Reset timestamp to avoid rapid retries


def _ensure_cache_fresh():
    """Ensure cache is fresh, refresh if stale"""
    global _cache_timestamp
    if time.time() - _cache_timestamp > _cache_ttl:
        _refresh_cache()


def get_pipe_cost_per_kg(default: float = 67) -> float:
    """Get pipe cost per kg from DB or default"""
    _ensure_cache_fresh()
    return _cache.get("pipe_cost_per_kg", default)


def get_shaft_cost_per_kg(default: float = 62) -> float:
    """Get shaft cost per kg from DB or default"""
    _ensure_cache_fresh()
    return _cache.get("shaft_cost_per_kg", default)


def get_bearing_costs(default_costs: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Get bearing costs from DB or defaults"""
    _ensure_cache_fresh()
    return _cache.get("bearing_costs", default_costs)


def get_bearing_cost(bearing_number: str, make: str, default_costs: Dict[str, Dict[str, float]]) -> float:
    """Get specific bearing cost"""
    _ensure_cache_fresh()
    
    # Try custom prices first
    custom_bearing_costs = _cache.get("bearing_costs", {})
    if bearing_number in custom_bearing_costs:
        bearing_prices = custom_bearing_costs[bearing_number]
        if make.lower() in bearing_prices:
            return bearing_prices[make.lower()]
        # Return cheapest available if make not found
        if bearing_prices:
            return min(v for v in bearing_prices.values() if isinstance(v, (int, float)))
    
    # Fall back to defaults
    if bearing_number in default_costs:
        bearing_prices = default_costs[bearing_number]
        if make.lower() in bearing_prices:
            return bearing_prices[make.lower()]
        if bearing_prices:
            return min(v for v in bearing_prices.values() if isinstance(v, (int, float)))
    
    return 0


def get_seal_costs(default_costs: Dict[str, float]) -> Dict[str, float]:
    """Get seal costs from DB or defaults"""
    _ensure_cache_fresh()
    return _cache.get("seal_costs", default_costs)


def get_seal_cost(bearing_number: str, default_costs: Dict[str, float]) -> float:
    """Get specific seal cost"""
    _ensure_cache_fresh()
    custom_seal_costs = _cache.get("seal_costs", {})
    if bearing_number in custom_seal_costs:
        return custom_seal_costs[bearing_number]
    return default_costs.get(bearing_number, 0)


def get_housing_costs(default_costs: Dict[str, float]) -> Dict[str, float]:
    """Get housing costs from DB or defaults"""
    _ensure_cache_fresh()
    return _cache.get("housing_costs", default_costs)


def get_housing_cost(housing_key: str, default_costs: Dict[str, float]) -> float:
    """Get specific housing cost"""
    _ensure_cache_fresh()
    custom_housing_costs = _cache.get("housing_costs", {})
    if housing_key in custom_housing_costs:
        return custom_housing_costs[housing_key]
    return default_costs.get(housing_key, 0)


def get_circlip_costs(default_costs: Dict[int, float]) -> Dict[str, float]:
    """Get circlip costs from DB or defaults"""
    _ensure_cache_fresh()
    custom = _cache.get("circlip_costs", {})
    if custom:
        # Normalize keys to strings for comparison
        return {str(k): v for k, v in custom.items()}
    return {str(k): v for k, v in default_costs.items()}


def get_circlip_cost(shaft_dia: int, default_costs: Dict[int, float]) -> float:
    """Get specific circlip cost"""
    _ensure_cache_fresh()
    custom_circlip_costs = _cache.get("circlip_costs", {})
    # Try string key first (MongoDB stores keys as strings)
    if str(shaft_dia) in custom_circlip_costs:
        return custom_circlip_costs[str(shaft_dia)]
    return default_costs.get(shaft_dia, 0)


def get_rubber_ring_costs(default_costs: Dict[str, float]) -> Dict[str, float]:
    """Get rubber ring costs from DB or defaults"""
    _ensure_cache_fresh()
    return _cache.get("rubber_ring_costs", default_costs)


def get_rubber_ring_cost(rubber_key: str, default_costs: Dict[str, float]) -> float:
    """Get specific rubber ring cost"""
    _ensure_cache_fresh()
    custom_rubber_costs = _cache.get("rubber_ring_costs", {})
    if rubber_key in custom_rubber_costs:
        return custom_rubber_costs[rubber_key]
    return default_costs.get(rubber_key, 0)


def get_locking_ring_costs(default_costs: Dict[int, float]) -> Dict[str, float]:
    """Get locking ring costs from DB or defaults"""
    _ensure_cache_fresh()
    custom = _cache.get("locking_ring_costs", {})
    if custom:
        return {str(k): v for k, v in custom.items()}
    return {str(k): v for k, v in default_costs.items()}


def get_locking_ring_cost(pipe_code: int, default_costs: Dict[int, float]) -> float:
    """Get specific locking ring cost"""
    _ensure_cache_fresh()
    custom_locking_costs = _cache.get("locking_ring_costs", {})
    if str(pipe_code) in custom_locking_costs:
        return custom_locking_costs[str(pipe_code)]
    return default_costs.get(pipe_code, 0)


def get_pipe_weight_per_meter(default_weights: Dict[float, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Get pipe weights from DB or defaults"""
    _ensure_cache_fresh()
    custom = _cache.get("pipe_weight", {})
    if custom:
        return custom
    return {str(k): v for k, v in default_weights.items()}


def get_pipe_weight(pipe_dia: float, pipe_type: str, default_weights: Dict[float, Dict[str, float]]) -> float:
    """Get specific pipe weight per meter"""
    _ensure_cache_fresh()
    custom_weights = _cache.get("pipe_weight", {})
    
    # Try custom weights first (keys are strings in MongoDB)
    if str(pipe_dia) in custom_weights:
        type_weights = custom_weights[str(pipe_dia)]
        if pipe_type in type_weights:
            return type_weights[pipe_type]
    
    # Fall back to defaults
    if pipe_dia in default_weights:
        return default_weights[pipe_dia].get(pipe_type, default_weights[pipe_dia].get("B", 0))
    
    return 0


def get_shaft_weight_per_meter(default_weights: Dict[int, float]) -> Dict[str, float]:
    """Get shaft weights from DB or defaults"""
    _ensure_cache_fresh()
    custom = _cache.get("shaft_weight", {})
    if custom:
        return custom
    return {str(k): v for k, v in default_weights.items()}


def get_shaft_weight(shaft_dia: int, default_weights: Dict[int, float]) -> float:
    """Get specific shaft weight per meter"""
    _ensure_cache_fresh()
    custom_weights = _cache.get("shaft_weight", {})
    
    if str(shaft_dia) in custom_weights:
        return custom_weights[str(shaft_dia)]
    
    return default_weights.get(shaft_dia, 0)


def invalidate_cache():
    """Force cache refresh on next access"""
    global _cache_timestamp
    _cache_timestamp = 0


def get_all_custom_prices() -> Dict[str, Any]:
    """Get all custom prices (for debugging)"""
    _ensure_cache_fresh()
    return _cache.copy()

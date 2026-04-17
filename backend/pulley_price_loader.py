"""Load pulley prices from MongoDB (sync version for calculator)"""
from pymongo import MongoClient
import os

_client = None
_db = None

def _get_db():
    global _client, _db
    if _db is None:
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        _client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
        _db = _client[os.environ.get('DB_NAME', 'test_database')]
    return _db

def get_pulley_prices():
    """Get pulley prices from MongoDB, fallback to default if custom not found"""
    try:
        db = _get_db()
        prices = db.pulley_custom_prices.find_one({"id": "pulley_prices"}, {"_id": 0})
        if not prices:
            prices = db.pulley_default_prices.find_one({"id": "pulley_prices"}, {"_id": 0})
        return prices or {}
    except Exception:
        return {}

def get_pipe_rate(pipe_dia, pipe_thickness):
    prices = get_pulley_prices()
    pipe_rates = prices.get("pipe_rates", {})
    dia_rates = pipe_rates.get(str(int(pipe_dia)), pipe_rates.get(str(pipe_dia), {}))
    return dia_rates.get(str(pipe_thickness), dia_rates.get(str(int(pipe_thickness)), 72.0))

def get_shaft_rate(shaft_dia, material):
    prices = get_pulley_prices()
    shaft_rates = prices.get("shaft_rates", {})
    dia_rates = shaft_rates.get(str(shaft_dia), {})
    return dia_rates.get(material, 65.0)

def get_end_plate_rate(thickness):
    prices = get_pulley_prices()
    return prices.get("end_plate_rates", {}).get(str(thickness), 72.0)

def get_hub_rate(hub_dia):
    prices = get_pulley_prices()
    return prices.get("hub_rates", {}).get(str(hub_dia), 65.0)

def get_rubber_plain_rate(thickness):
    prices = get_pulley_prices()
    return prices.get("rubber_plain_rates", {}).get(str(thickness), 0)

def get_rubber_ceramic_rate(thickness):
    prices = get_pulley_prices()
    return prices.get("rubber_ceramic_rates", {}).get(str(thickness), 0)

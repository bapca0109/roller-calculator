"""Price Change History - Audit log for Roller & Pulley rate changes"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from routes import db, get_current_user

router = APIRouter()


async def log_price_change(
    user_email: str,
    product_type: str,  # 'roller' | 'pulley'
    category: str,      # e.g. 'bearing', 'pipe_rates', 'shaft_rates'
    key: str,           # e.g. '6204' or '139'
    sub_key: Optional[str],  # e.g. 'china' or '4.8' (thickness/material)
    old_value: Optional[float],
    new_value: float,
) -> None:
    """Insert one row into price_history. Fire-and-forget; never raises to caller."""
    try:
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_email": user_email or "unknown",
            "product_type": product_type,
            "category": category,
            "key": str(key),
            "sub_key": str(sub_key) if sub_key is not None else None,
            "old_value": float(old_value) if old_value is not None else None,
            "new_value": float(new_value),
        }
        await db.price_history.insert_one(entry)
    except Exception:
        # Never let audit logging block the main flow
        pass


def _diff_nested_prices(old: Dict[str, Any], new: Dict[str, Any], path: Optional[List[str]] = None):
    """Yield (path_list, old_val, new_val) for every changed scalar leaf between
    two nested dicts. Skips mongo internals (_id, id, updated_at, updated_by)."""
    if path is None:
        path = []
    skip = {"_id", "id", "updated_at", "updated_by"}
    keys = set((old or {}).keys()) | set((new or {}).keys())
    for k in keys:
        if k in skip:
            continue
        ov = (old or {}).get(k)
        nv = (new or {}).get(k)
        if isinstance(nv, dict) or isinstance(ov, dict):
            yield from _diff_nested_prices(ov or {}, nv or {}, path + [str(k)])
        else:
            try:
                if ov is None and nv is None:
                    continue
                if ov is None or float(ov) != float(nv):
                    yield (path + [str(k)], ov, nv)
            except (TypeError, ValueError):
                if ov != nv:
                    yield (path + [str(k)], ov, nv)


async def log_pulley_diff(user_email: str, old_prices: Dict[str, Any], new_prices: Dict[str, Any]):
    """Diff old vs new pulley price document; log each changed leaf."""
    for path, old_val, new_val in _diff_nested_prices(old_prices or {}, new_prices or {}):
        if not path:
            continue
        category = path[0]           # e.g. 'pipe_rates'
        key = path[1] if len(path) > 1 else ""
        sub_key = path[2] if len(path) > 2 else None
        try:
            new_f = float(new_val) if new_val is not None else 0.0
        except (TypeError, ValueError):
            continue
        await log_price_change(
            user_email=user_email,
            product_type="pulley",
            category=category,
            key=key,
            sub_key=sub_key,
            old_value=old_val if isinstance(old_val, (int, float)) else None,
            new_value=new_f,
        )


@router.get("/price-history")
async def get_price_history(
    product_type: Optional[str] = Query(None, description="Filter: 'roller' or 'pulley'"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Return recent price changes (newest first)."""
    q: Dict[str, Any] = {}
    if product_type in ("roller", "pulley"):
        q["product_type"] = product_type
    total = await db.price_history.count_documents(q)
    cursor = db.price_history.find(q, {"_id": 0}).sort("timestamp", -1).skip(offset).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"total": total, "items": items}

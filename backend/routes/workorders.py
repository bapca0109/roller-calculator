"""Work Order Routes — Create from SO, production tracking"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from routes import db, get_current_user, require_role, get_ist_now, get_financial_year, UserRole
import logging
import base64

router = APIRouter()

WORK_ORDER_STAGES = ["created", "material_issued", "in_progress", "qc", "completed"]
WO_STAGE_LABELS = {
    "created": "Created", "material_issued": "Material Issued",
    "in_progress": "In Progress", "qc": "QC", "completed": "Completed"
}


class ShaftSlot(BaseModel):
    width: float  # mm
    dimension: float  # depth (A/B) or hole dia (C)
    slot_type: str  # A, B5, C35 etc.


class ProductionDetails(BaseModel):
    drawing_number: Optional[str] = None
    drawing_base64: Optional[str] = None  # base64 encoded drawing file
    drawing_filename: Optional[str] = None
    paint_details: Optional[str] = None
    shaft_length: Optional[float] = None  # mm
    shaft_slot: Optional[ShaftSlot] = None
    production_notes: Optional[str] = None


class UpdateProductionDetails(BaseModel):
    item_index: int
    production_details: ProductionDetails


async def generate_wo_number():
    fy = get_financial_year()
    prefix = f"WO/{fy}/"
    last = await db.work_orders.find(
        {"wo_number": {"$regex": f"^{prefix}"}}, {"wo_number": 1}
    ).sort("wo_number", -1).limit(1).to_list(1)
    if last:
        num = int(last[0]["wo_number"].split("/")[-1])
        return f"{prefix}{num + 1:04d}"
    return f"{prefix}0001"


# ============= UPDATE PRODUCTION DETAILS ON SO ITEM =============

@router.put("/orders/{order_id}/production-details")
async def update_item_production_details(
    order_id: str,
    update: UpdateProductionDetails,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    products = order.get("products", [])
    if update.item_index < 0 or update.item_index >= len(products):
        raise HTTPException(status_code=400, detail="Invalid item index")

    # Update the production details for this item
    pd = update.production_details.dict()
    products[update.item_index]["production_details"] = pd

    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"products": products, "updated_at": get_ist_now().isoformat()}}
    )

    return {"message": f"Production details updated for item {update.item_index + 1}"}


# ============= CREATE WORK ORDER FROM SO =============

@router.post("/orders/{order_id}/work-order")
async def create_work_order(
    order_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check if WO already exists
    existing = await db.work_orders.find_one({"order_id": order.get("id")})
    if existing:
        raise HTTPException(status_code=400, detail=f"Work Order already exists: {existing['wo_number']}")

    # Validate: all items must have production details filled
    products = order.get("products", [])
    missing = []
    for i, p in enumerate(products):
        pd = p.get("production_details")
        if not pd:
            missing.append(f"Item {i+1}: No production details")
            continue
        if not pd.get("drawing_number"):
            missing.append(f"Item {i+1}: Drawing number missing")
        if not pd.get("shaft_length"):
            missing.append(f"Item {i+1}: Shaft length missing")
        if not pd.get("shaft_slot") or not pd["shaft_slot"].get("slot_type"):
            missing.append(f"Item {i+1}: Shaft slot details missing")

    if missing:
        raise HTTPException(status_code=400, detail=f"Production details incomplete: {'; '.join(missing)}")

    now = get_ist_now()
    wo_number = await generate_wo_number()

    # Build WO items from SO products with production details
    wo_items = []
    for i, p in enumerate(products):
        pd = p.get("production_details", {})
        slot = pd.get("shaft_slot", {})
        slot_str = ""
        if slot:
            st = slot.get("slot_type", "")
            slot_str = f"{slot.get('width', '')} × {slot.get('dimension', '')} {st}"

        wo_items.append({
            "index": i,
            "product_name": p.get("product_name"),
            "product_code": p.get("product_id"),
            "quantity": p.get("quantity"),
            "specifications": p.get("specifications"),
            "drawing_number": pd.get("drawing_number"),
            "drawing_filename": pd.get("drawing_filename"),
            "drawing_base64": pd.get("drawing_base64"),
            "paint_details": pd.get("paint_details"),
            "shaft_length_mm": pd.get("shaft_length"),
            "shaft_slot": slot_str,
            "shaft_slot_details": slot,
            "production_notes": pd.get("production_notes"),
            "item_status": "pending",
        })

    work_order = {
        "id": str(ObjectId()),
        "wo_number": wo_number,
        "order_id": order.get("id"),
        "so_number": order.get("so_number"),
        "quote_number": order.get("quote_number"),
        "customer_name": order.get("customer_name"),
        "customer_company": order.get("customer_company"),
        "items": wo_items,
        "stage": "created",
        "stage_history": [{
            "stage": "created",
            "timestamp": now.isoformat(),
            "by": current_user.get("email"),
            "notes": f"Work Order created from {order.get('so_number')}"
        }],
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.work_orders.insert_one(work_order)

    # Update SO with WO reference
    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"work_order": wo_number, "updated_at": now.isoformat()}}
    )

    del work_order["_id"]
    return {"message": f"Work Order {wo_number} created", "work_order": work_order}


# ============= WORK ORDER CRUD =============

@router.get("/work-orders")
async def get_work_orders(
    stage: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    query = {}
    if stage:
        query["stage"] = stage
    wos = await db.work_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"work_orders": wos, "total": len(wos)}


@router.get("/work-orders/{wo_id}")
async def get_work_order(wo_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    wo = await db.work_orders.find_one(
        {"$or": [{"id": wo_id}, {"wo_number": wo_id}]}, {"_id": 0}
    )
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    return wo


@router.put("/work-orders/{wo_id}/stage")
async def update_wo_stage(
    wo_id: str,
    stage: str,
    notes: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    if stage not in WORK_ORDER_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of {WORK_ORDER_STAGES}")

    now = get_ist_now()
    stage_entry = {"stage": stage, "timestamp": now.isoformat(), "by": current_user.get("email"), "notes": notes}

    update_fields = {"stage": stage, "updated_at": now.isoformat()}

    # If completed, auto-update SO stage to "ready"
    if stage == "completed" and wo.get("order_id"):
        await db.sales_orders.update_one(
            {"id": wo["order_id"]},
            {"$set": {"stage": "ready", "updated_at": now.isoformat()},
             "$push": {"stage_history": {"stage": "ready", "timestamp": now.isoformat(),
                                          "by": current_user.get("email"),
                                          "notes": f"Auto-updated: WO {wo['wo_number']} completed"}}}
        )

    await db.work_orders.update_one(
        {"_id": wo["_id"]},
        {"$set": update_fields, "$push": {"stage_history": stage_entry}}
    )

    return {"message": f"Work Order stage updated to {stage}"}


@router.put("/work-orders/{wo_id}/item-status")
async def update_wo_item_status(
    wo_id: str,
    item_index: int,
    status: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    items = wo.get("items", [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=400, detail="Invalid item index")

    items[item_index]["item_status"] = status
    await db.work_orders.update_one(
        {"_id": wo["_id"]},
        {"$set": {"items": items, "updated_at": get_ist_now().isoformat()}}
    )

    return {"message": f"Item {item_index + 1} status updated to {status}"}


# ============= WORK ORDER SUMMARY =============

@router.get("/work-orders/summary/stats")
async def get_wo_stats(current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    pipeline = [{"$group": {"_id": "$stage", "count": {"$sum": 1}}}]
    stage_stats = await db.work_orders.aggregate(pipeline).to_list(10)

    total = await db.work_orders.count_documents({})

    return {
        "total": total,
        "by_stage": {s["_id"]: s["count"] for s in stage_stats},
    }

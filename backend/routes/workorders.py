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

    # Build WO items from SO products with production details + auto-generate BOM
    wo_items = []
    for i, p in enumerate(products):
        pd = p.get("production_details", {})
        slot = pd.get("shaft_slot", {})
        slot_str = ""
        if slot:
            st = slot.get("slot_type", "")
            slot_str = f"{slot.get('width', '')} × {slot.get('dimension', '')} {st}"

        specs = p.get("specifications", {})
        qty = p.get("quantity", 1)

        # Auto-generate BOM from specs
        bom = _generate_bom(p, pd, specs, qty)

        wo_items.append({
            "index": i,
            "product_name": p.get("product_name"),
            "product_code": p.get("product_id"),
            "quantity": qty,
            "specifications": specs,
            "drawing_number": pd.get("drawing_number"),
            "drawing_filename": pd.get("drawing_filename"),
            "drawing_base64": pd.get("drawing_base64"),
            "paint_details": pd.get("paint_details"),
            "shaft_length_mm": pd.get("shaft_length"),
            "shaft_slot": slot_str,
            "shaft_slot_details": slot,
            "production_notes": pd.get("production_notes"),
            "bom": bom,
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


# ============= BOM AUTO-GENERATION =============

import math

STEEL_DENSITY = 7850  # kg/m³

def _calc_weight(volume_mm3):
    """Convert volume in mm³ to weight in kg"""
    return round(volume_mm3 / 1e9 * STEEL_DENSITY, 3)


def _generate_bom(product: dict, production_details: dict, specs: dict, qty: int) -> list:
    """Auto-generate Bill of Materials from product specs"""
    bom = []
    product_name = (product.get("product_name") or "").lower()
    is_pulley = "pulley" in product_name
    is_roller = not is_pulley

    pipe_dia = specs.get("pipe_diameter", 0)
    pipe_length = specs.get("pipe_length", 0)  # roller face length or pulley face length
    shaft_dia = specs.get("shaft_diameter", 0)
    shaft_length = production_details.get("shaft_length", 0) or specs.get("shaft_length", 0) or 0
    pipe_type = specs.get("pipe_type", "")  # wall thickness info

    # Try to get wall thickness from pipe_type string like "8mm wall"
    wall_thk = 0
    if pipe_type:
        import re
        thk_match = re.search(r'(\d+\.?\d*)\s*mm', str(pipe_type))
        if thk_match:
            wall_thk = float(thk_match.group(1))

    if is_roller:
        # === ROLLER BOM ===
        # 1. Pipe
        if pipe_dia > 0 and pipe_length > 0:
            effective_thk = wall_thk if wall_thk > 0 else 3.2  # default
            od = pipe_dia
            id_val = od - 2 * effective_thk
            pipe_vol = (math.pi / 4) * (od**2 - id_val**2) * pipe_length
            pipe_wt = _calc_weight(pipe_vol)
            bom.append({
                "component": "Pipe",
                "description": f"{pipe_dia}mm OD × {effective_thk}mm thk × {pipe_length}mm L",
                "material": "MS ERW",
                "qty_per_unit": 1,
                "total_qty": qty,
                "weight_per_unit_kg": pipe_wt,
                "total_weight_kg": round(pipe_wt * qty, 3),
            })

        # 2. Shaft
        if shaft_dia > 0 and shaft_length > 0:
            shaft_vol = (math.pi / 4) * (shaft_dia**2) * shaft_length
            shaft_wt = _calc_weight(shaft_vol)
            bom.append({
                "component": "Shaft",
                "description": f"{shaft_dia}mm dia × {shaft_length}mm L",
                "material": "MS Bright Bar",
                "qty_per_unit": 1,
                "total_qty": qty,
                "weight_per_unit_kg": shaft_wt,
                "total_weight_kg": round(shaft_wt * qty, 3),
            })

        # 3. Bearings
        bearing = specs.get("bearing_number", specs.get("bearing", ""))
        if bearing:
            bom.append({
                "component": "Bearing",
                "description": bearing,
                "material": bearing,
                "qty_per_unit": 2,
                "total_qty": qty * 2,
                "weight_per_unit_kg": 0,
                "total_weight_kg": 0,
            })

        # 4. Seals
        bom.append({
            "component": "Seal",
            "description": f"For {pipe_dia}mm pipe",
            "material": "Labyrinth Seal",
            "qty_per_unit": 2,
            "total_qty": qty * 2,
            "weight_per_unit_kg": 0,
            "total_weight_kg": 0,
        })

        # 5. Grease
        bom.append({
            "component": "Grease",
            "description": "Bearing grease",
            "material": "EP2 Grease",
            "qty_per_unit": 1,
            "total_qty": qty,
            "weight_per_unit_kg": 0,
            "total_weight_kg": 0,
        })

    elif is_pulley:
        # === PULLEY BOM ===
        face_length = pipe_length or specs.get("face_length", 0) or specs.get("pipe_length", 0) or 0

        # 1. Pipe
        if pipe_dia > 0 and face_length > 0:
            effective_thk = wall_thk if wall_thk > 0 else 8  # default for pulley
            # Pulley pipe weight uses thickness + 2mm
            calc_thk = effective_thk + 2
            od = pipe_dia
            id_val = od - 2 * calc_thk
            pipe_vol = (math.pi / 4) * (od**2 - id_val**2) * face_length
            pipe_wt = _calc_weight(pipe_vol)
            bom.append({
                "component": "Pipe",
                "description": f"{pipe_dia}mm OD × {effective_thk}mm thk × {face_length}mm FL",
                "material": "MS Seamless",
                "qty_per_unit": 1,
                "total_qty": qty,
                "weight_per_unit_kg": pipe_wt,
                "total_weight_kg": round(pipe_wt * qty, 3),
            })

        # 2. Shaft
        if shaft_dia > 0 and shaft_length > 0:
            shaft_vol = (math.pi / 4) * (shaft_dia**2) * shaft_length
            shaft_wt = _calc_weight(shaft_vol)
            shaft_mat = specs.get("shaft_material", "MS")
            bom.append({
                "component": "Shaft",
                "description": f"{shaft_dia}mm dia × {shaft_length}mm L",
                "material": shaft_mat,
                "qty_per_unit": 1,
                "total_qty": qty,
                "weight_per_unit_kg": shaft_wt,
                "total_weight_kg": round(shaft_wt * qty, 3),
            })

        # 3. End Plates
        ep_thk = specs.get("end_plate_thickness", 12)
        ep_qty = specs.get("end_plate_qty", 2)
        if pipe_dia > 0 and shaft_dia > 0:
            ep_vol = (math.pi / 4) * (pipe_dia**2 - shaft_dia**2) * ep_thk
            ep_wt = _calc_weight(ep_vol)
            bom.append({
                "component": "End Plate",
                "description": f"{pipe_dia}mm OD × {shaft_dia}mm bore × {ep_thk}mm thk",
                "material": "MS Plate",
                "qty_per_unit": ep_qty,
                "total_qty": qty * ep_qty,
                "weight_per_unit_kg": ep_wt,
                "total_weight_kg": round(ep_wt * ep_qty * qty, 3),
            })

        # 4. Hub (if applicable)
        hub_type = specs.get("hub_type", "no_hub")
        hub_dia = specs.get("hub_diameter", 0)
        hub_length = specs.get("hub_length", 0)
        if hub_type == "with_hub" and hub_dia > 0 and hub_length > 0:
            hub_vol = (math.pi / 4) * (hub_dia**2 - shaft_dia**2) * hub_length
            hub_wt = _calc_weight(hub_vol)
            bom.append({
                "component": "Hub",
                "description": f"{hub_dia}mm OD × {shaft_dia}mm bore × {hub_length}mm L",
                "material": "MS",
                "qty_per_unit": 2,
                "total_qty": qty * 2,
                "weight_per_unit_kg": hub_wt,
                "total_weight_kg": round(hub_wt * 2 * qty, 3),
            })
        elif hub_type == "kla":
            kla_model = specs.get("kla_model", "KLA")
            bom.append({
                "component": "KLA",
                "description": kla_model,
                "material": "Keyless Locking Assembly",
                "qty_per_unit": 2,
                "total_qty": qty * 2,
                "weight_per_unit_kg": 0,
                "total_weight_kg": 0,
            })

        # 5. Rubber Lagging (if applicable)
        rubber_type = specs.get("rubber_type", "none")
        rubber_thk = specs.get("rubber_thickness", 0)
        if rubber_type != "none" and rubber_thk > 0 and pipe_dia > 0 and face_length > 0:
            area_sqm = math.pi * pipe_dia * face_length / 1e6
            bom.append({
                "component": "Rubber Lagging",
                "description": f"{rubber_type.title()} {rubber_thk}mm — {round(area_sqm, 3)} sqm",
                "material": rubber_type.title(),
                "qty_per_unit": 1,
                "total_qty": qty,
                "weight_per_unit_kg": 0,
                "total_weight_kg": 0,
            })

    # Calculate BOM totals
    total_weight = sum(item.get("total_weight_kg", 0) for item in bom)
    for item in bom:
        item["_total_bom_weight_kg"] = round(total_weight, 3)

    return bom

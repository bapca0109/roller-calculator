"""Work Order Routes — Create from SO, production tracking"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from routes import (db, get_current_user, require_role, get_ist_now, get_financial_year, 
                    UserRole, SECRET_KEY, ALGORITHM, get_convero_logo_base64, format_date_dmy)
from jose import jwt
import logging
import base64
import io
import os

router = APIRouter()

WORK_ORDER_STAGES = ["created", "completed"]
WO_STAGE_LABELS = {
    "created": "Created", "completed": "Completed"
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
    from routes import _next_seq, _max_suffix, format_number
    seed = await _max_suffix(db.work_orders, "wo_number", f"WO/{fy}/")
    n = await _next_seq(f"wo:{fy}", seed_value=seed)
    return await format_number("wo", n)


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


# ============= BULK: SET PRODUCTION DETAILS + CREATE WO IN ONE CLICK =============

PAINT_TYPES = ["Synthetic Enamel", "Auto Paint", "Epoxy", "PU"]


class BulkProductionItem(BaseModel):
    item_index: int
    drawing_number: Optional[str] = None
    drawing_base64: Optional[str] = None
    drawing_filename: Optional[str] = None
    shaft_length: Optional[float] = None
    shaft_slot: Optional[ShaftSlot] = None
    production_notes: Optional[str] = None


class BulkCreateWorkOrder(BaseModel):
    items: List[BulkProductionItem]
    ral_code: Optional[str] = None  # e.g., "RAL 9005"
    paint_type: Optional[str] = None  # Synthetic Enamel / Auto Paint / Epoxy / PU
    paint_spec: Optional[str] = None  # Auto-carried from quote commercial_terms.color_finish
    selected_item_indexes: Optional[List[int]] = None  # if provided, WO only for these items


@router.post("/orders/{order_id}/create-work-order")
async def bulk_create_work_order(
    order_id: str,
    data: BulkCreateWorkOrder,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Single click: set production details for selected items + auto-generate BOM + create Work Order.
    Supports partial WOs — multiple WOs per SO, one per batch of selected items.
    """
    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    products = order.get("products", [])
    n_products = len(products)

    # Determine which item indexes this WO is for. If none given, all items.
    payload_indexes = {it.item_index for it in data.items}
    if data.selected_item_indexes:
        target_indexes = [i for i in data.selected_item_indexes if 0 <= i < n_products]
    else:
        target_indexes = sorted(payload_indexes)
    if not target_indexes:
        raise HTTPException(status_code=400, detail="No items selected for Work Order")

    # Check items already assigned to a WO
    already = [i for i in target_indexes if products[i].get("wo_number")]
    if already:
        raise HTTPException(status_code=400, detail=f"Items {', '.join(str(i+1) for i in already)} already have a Work Order")

    # Step 1: Apply production details to targeted items
    items_by_idx = {it.item_index: it for it in data.items}
    for idx in target_indexes:
        item_data = items_by_idx.get(idx)
        existing_pd = products[idx].get("production_details") or {}
        if item_data:
            # Keep existing drawing_number if new one not provided (e.g. inherited from SO conversion)
            new_dwg = item_data.drawing_number or existing_pd.get("drawing_number")
            products[idx]["production_details"] = {
                "drawing_number": new_dwg,
                "drawing_base64": item_data.drawing_base64 or existing_pd.get("drawing_base64"),
                "drawing_filename": item_data.drawing_filename or existing_pd.get("drawing_filename"),
                "shaft_length": item_data.shaft_length if item_data.shaft_length is not None else existing_pd.get("shaft_length"),
                "shaft_slot": item_data.shaft_slot.dict() if item_data.shaft_slot else existing_pd.get("shaft_slot"),
                "production_notes": item_data.production_notes if item_data.production_notes is not None else existing_pd.get("production_notes"),
            }

    # Step 2: Validate targeted items have required fields (skip for pulley)
    missing = []
    for i in target_indexes:
        p = products[i]
        pd = p.get("production_details") or {}
        product_name = (p.get("product_name") or "").lower()
        is_pulley = "pulley" in product_name

        if is_pulley:
            if not pd:
                products[i]["production_details"] = {}
            continue

        if not pd:
            missing.append(f"Item {i+1}: No production details")
            continue
        # Drawing number is optional — can be added later from Admin/Dispatch
        if not pd.get("shaft_length"):
            missing.append(f"Item {i+1}: Shaft length missing")
        if not pd.get("shaft_slot") or not pd["shaft_slot"].get("slot_type"):
            missing.append(f"Item {i+1}: Shaft slot details missing")

    if missing:
        raise HTTPException(status_code=400, detail=f"Production details incomplete: {'; '.join(missing)}")

    # Step 3: Generate WO number first so we can tag products
    now = get_ist_now()
    wo_number = await generate_wo_number()

    # Step 4: Save production details + WO tag on targeted products
    for idx in target_indexes:
        products[idx]["wo_number"] = wo_number
    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"products": products, "updated_at": now.isoformat()}}
    )

    # Step 5: Build WO items for targeted products only
    wo_items = []
    for i in target_indexes:
        p = products[i]
        pd = p.get("production_details", {}) or {}
        slot = pd.get("shaft_slot", {}) or {}
        slot_str = ""
        if slot:
            st = slot.get("slot_type", "")
            slot_str = f"{slot.get('width', '')} × {slot.get('dimension', '')} {st}"

        specs = p.get("specifications", {}) or {}
        qty = p.get("quantity", 1)
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

    commercial_terms = order.get("commercial_terms") or {}
    paint_spec = data.paint_spec or commercial_terms.get("color_finish", "")

    work_order = {
        "id": str(ObjectId()),
        "wo_number": wo_number,
        "order_id": order.get("id"),
        "so_number": order.get("so_number"),
        "quote_number": order.get("quote_number"),
        "customer_name": order.get("customer_name"),
        "customer_company": order.get("customer_company"),
        "customer_po_number": order.get("customer_po_number"),
        "customer_po_date": order.get("customer_po_date"),
        "delivery_date": order.get("delivery_date"),
        "test_requirements": order.get("test_requirements") or {},
        "so_item_indexes": target_indexes,
        "items": wo_items,
        "ral_code": data.ral_code or "",
        "paint_type": data.paint_type or "",
        "paint_spec": paint_spec,
        "stage": "created",
        "stage_history": [{"stage": "created", "timestamp": now.isoformat(), "by": current_user.get("email"), "notes": f"Created from {order.get('so_number')} — items {', '.join(str(i+1) for i in target_indexes)} ({len(wo_items)} line(s))"}],
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.work_orders.insert_one(work_order)
    # Append to SO's work_orders list (instead of singleton)
    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {"$addToSet": {"work_orders": wo_number},
         "$set": {"work_order": wo_number, "updated_at": now.isoformat()}}
    )

    # Auto-create Pipe + Shaft sub-work-orders (job cards for shop floor)
    sub_wos = await _create_sub_wos(work_order, current_user.get("email"))

    # Auto-check BOM against stock and find shortages
    shortages = await _check_bom_shortages(work_order)

    del work_order["_id"]
    return {"message": f"Work Order {wo_number} created with {len(wo_items)} item(s)", "work_order": work_order, "shortages": shortages, "sub_work_orders": [{"sub_wo_number": s["sub_wo_number"], "type": s["type"], "lines": len(s["items"])} for s in sub_wos]}

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
        # Drawing number is optional — can be added later from Admin/Dispatch
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
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES, UserRole.SALES_MANAGER, UserRole.PRODUCTION_HEAD, UserRole.ACCOUNTS, UserRole.DISPATCH, UserRole.QUALITY_INSPECTOR]))
):
    query = {}
    if stage:
        query["stage"] = stage
    wos = await db.work_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"work_orders": wos, "total": len(wos)}


@router.get("/work-orders/{wo_id}")
async def get_work_order(wo_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES, UserRole.SALES_MANAGER, UserRole.PRODUCTION_HEAD, UserRole.ACCOUNTS, UserRole.DISPATCH, UserRole.QUALITY_INSPECTOR]))):
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


@router.delete("/work-orders/{wo_id}")
async def delete_work_order(
    wo_id: str,
    force: bool = False,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Admin-only hard delete. Guards: refuses if stage has moved beyond 'created',
    QC has been stamped, stock has been issued, or a Final Inspection exists —
    unless force=true is explicitly passed. Cascades by deleting related
    sub-work-orders, final-inspection, stock-issue records for this WO."""
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    blockers = []
    if (wo.get("stage") or "created") != "created":
        blockers.append(f"stage is '{wo.get('stage')}' (not 'created')")
    if wo.get("qc_status") and wo.get("qc_status") != "pending":
        blockers.append(f"QC already stamped ({wo.get('qc_status')})")
    # Stock issued against this WO? Tracked as 'out' rows in stock_transactions.
    issued_count = await db.stock_transactions.count_documents({"wo_id": wo.get("id"), "type": "out"})
    if issued_count:
        blockers.append(f"{issued_count} stock-issue transaction(s) exist")
    # Final inspection exists?
    fi = await db.final_inspections.count_documents({"wo_id": wo.get("id")})
    if fi:
        blockers.append(f"final inspection exists ({fi} record)")

    if blockers and not force:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete {wo.get('wo_number')}: {'; '.join(blockers)}. Pass ?force=true to override.",
        )

    # Revert any issued stock back to inventory BEFORE deleting the WO so we
    # never leave the register drifted. Each 'out' transaction gets a matching
    # 'in' reversal and the stock item's current_stock is bumped by the qty.
    now = get_ist_now()
    reverted = []
    out_txns = await db.stock_transactions.find(
        {"wo_id": wo.get("id"), "type": "out", "reversed_at": {"$exists": False}},
        {"_id": 0},
    ).to_list(2000)
    for tx in out_txns:
        qty = float(tx.get("qty") or 0)
        if qty <= 0:
            continue
        await db.stock_items.update_one(
            {"id": tx.get("stock_item_id")},
            {"$inc": {"current_stock": qty}},
        )
        await db.stock_transactions.insert_one({
            "id": str(ObjectId()),
            "stock_item_id": tx.get("stock_item_id"),
            "stock_item_name": tx.get("stock_item_name"),
            "type": "in",
            "qty": qty,
            "reference": f"Reversal — WO {wo.get('wo_number')} deleted",
            "wo_id": wo.get("id"),
            "notes": f"Auto-reversal of txn {tx.get('id')} on WO force-delete",
            "reversal_of": tx.get("id"),
            "by": current_user.get("email"),
            "at": now.isoformat(),
        })
        # Flag the original so double-reversal is impossible if re-run
        await db.stock_transactions.update_one(
            {"id": tx.get("id")},
            {"$set": {"reversed_at": now.isoformat()}},
        )
        reverted.append({"item": tx.get("stock_item_name"), "qty": qty})

    # Cascade delete dependent records
    await db.sub_work_orders.delete_many({"wo_id": wo.get("id")})
    await db.final_inspections.delete_many({"wo_id": wo.get("id")})
    await db.work_orders.delete_one({"_id": wo["_id"]})

    return {
        "message": f"Work Order {wo.get('wo_number')} deleted",
        "cascaded": True,
        "forced": bool(force and blockers),
        "blockers_overridden": blockers if force else [],
        "stock_reverted": reverted,
    }


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

# ============= EDIT BOM =============

class BomItemUpdate(BaseModel):
    component: str
    description: Optional[str] = None
    material: Optional[str] = None
    qty_per_unit: Optional[int] = None
    total_qty: Optional[int] = None
    weight_per_unit_kg: Optional[float] = None
    total_weight_kg: Optional[float] = None


class BomUpdate(BaseModel):
    item_index: int
    bom: List[BomItemUpdate]


@router.put("/work-orders/{wo_id}/bom")
async def update_wo_bom(
    wo_id: str,
    update: BomUpdate,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Update BOM for a work order item — add, remove, or edit quantities"""
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    items = wo.get("items", [])
    if update.item_index < 0 or update.item_index >= len(items):
        raise HTTPException(status_code=400, detail="Invalid item index")

    # Replace BOM with updated list
    new_bom = [b.dict() for b in update.bom]
    items[update.item_index]["bom"] = new_bom

    await db.work_orders.update_one(
        {"_id": wo["_id"]},
        {"$set": {"items": items, "updated_at": get_ist_now().isoformat()}}
    )

    return {"message": f"BOM updated for item {update.item_index + 1}", "bom": new_bom}


@router.post("/work-orders/{wo_id}/bom/add-item")
async def add_bom_item(
    wo_id: str,
    item_index: int,
    bom_item: BomItemUpdate,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Add a single component to BOM"""
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    items = wo.get("items", [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=400, detail="Invalid item index")

    bom = items[item_index].get("bom", [])
    bom.append(bom_item.dict())
    items[item_index]["bom"] = bom

    await db.work_orders.update_one(
        {"_id": wo["_id"]},
        {"$set": {"items": items, "updated_at": get_ist_now().isoformat()}}
    )

    return {"message": f"{bom_item.component} added to BOM", "bom": bom}


@router.delete("/work-orders/{wo_id}/bom/remove-item")
async def remove_bom_item(
    wo_id: str,
    item_index: int,
    bom_index: int,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Remove a component from BOM by index"""
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    items = wo.get("items", [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=400, detail="Invalid item index")

    bom = items[item_index].get("bom", [])
    if bom_index < 0 or bom_index >= len(bom):
        raise HTTPException(status_code=400, detail="Invalid BOM index")

    removed = bom.pop(bom_index)
    items[item_index]["bom"] = bom

    await db.work_orders.update_one(
        {"_id": wo["_id"]},
        {"$set": {"items": items, "updated_at": get_ist_now().isoformat()}}
    )

    return {"message": f"{removed.get('component', 'Item')} removed from BOM", "bom": bom}


@router.get("/work-orders/summary/stats")
async def get_wo_stats(current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    pipeline = [{"$group": {"_id": "$stage", "count": {"$sum": 1}}}]
    stage_stats = await db.work_orders.aggregate(pipeline).to_list(10)

    total = await db.work_orders.count_documents({})

    return {
        "total": total,
        "by_stage": {s["_id"]: s["count"] for s in stage_stats},
    }


# ============= WORK ORDER PDF =============

COMPANY = {
    "name": os.environ.get("COMPANY_NAME", "CONVERO SOLUTIONS"),
    "address": os.environ.get("COMPANY_ADDRESS", ""),
    "phone": os.environ.get("COMPANY_PHONE", ""),
    "email": os.environ.get("COMPANY_EMAIL", ""),
    "gstin": os.environ.get("COMPANY_GSTIN", "24BAUPP4310D2ZT"),
}

@router.get("/work-orders/{wo_id}/pdf")
async def get_work_order_pdf(
    wo_id: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization[7:]
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]}, {"_id": 0})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    logo_b64 = get_convero_logo_base64()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:40px" />' if logo_b64 else f'<b>{COMPANY["name"]}</b>'

    # Build items summary table (roller-style) and consolidated BOM
    all_items = wo.get("items", [])
    
    # TABLE 1: Items Summary
    items_summary_rows = ""
    import roller_standards as rs
    for idx, item in enumerate(all_items, 1):
        specs = item.get("specifications", {})
        slot_str = item.get("shaft_slot", "N/A")
        # Format slot: remove decimals, ensure uppercase (e.g., "14.0 × 10.0 A" → "14 x 10 A")
        import re
        if slot_str and slot_str != "N/A":
            slot_str = re.sub(r'(\d+)\.0\b', r'\1', slot_str)  # Remove .0 decimals
            slot_str = slot_str.replace('×', 'x').upper()
        pipe_type_str = specs.get("pipe_type", "")
        
        # Get housing size from roller standards
        bearing_number = specs.get("bearing_number", specs.get("bearing", ""))
        bearing_make = specs.get("bearing_make", "china")
        pipe_dia = specs.get("pipe_diameter", 0)

        # Get pipe thickness from roller standards based on pipe_type (A/B/C)
        import re
        pipe_thk = "-"
        pipe_type_code = specs.get("pipe_type", "B").upper()
        if len(pipe_type_code) == 1 and pipe_type_code in ("A", "B", "C"):
            # Wall thickness lookup by pipe dia and type
            PIPE_WALL_THK = {
                60.8: {"A": 2.9, "B": 3.6, "C": 4.5},
                76.1: {"A": 3.2, "B": 3.6, "C": 4.5},
                88.9: {"A": 3.2, "B": 4.0, "C": 4.8},
                114.3: {"A": 3.6, "B": 4.5, "C": 5.4},
                127.0: {"A": 4.0, "B": 4.8, "C": 5.4},
                139.7: {"A": 4.0, "B": 4.8, "C": 5.4},
                152.4: {"A": 4.0, "B": 4.8, "C": 5.4},
                159.0: {"A": 4.0, "B": 4.8, "C": 5.4},
                165.0: {"A": 4.0, "B": 4.8, "C": 5.4},
            }
            thk_data = PIPE_WALL_THK.get(pipe_dia, {})
            thk_val = thk_data.get(pipe_type_code)
            if thk_val:
                pipe_thk = str(thk_val)
        if pipe_thk == "-":
            # Fallback: try from BOM description
            for b in item.get("bom", []):
                if b.get("component") == "Pipe":
                    thk_match = re.search(r'x\s*(\d+\.?\d*)\s*mm\s*thk', b.get("description", ""))
                    if thk_match:
                        pipe_thk = thk_match.group(1)
                        break

        # Get housing size from roller standards
        housing_size = rs.get_housing_for_pipe_and_bearing(pipe_dia, bearing_number) if pipe_dia and bearing_number else "-"
        if not housing_size:
            housing_size = "-"

        # Bearing with make
        bearing_display = f"{bearing_number} {(bearing_make or 'china').upper()}" if bearing_number else "-"
        
        items_summary_rows += f"""<tr>
            <td style="text-align:center">{idx}</td>
            <td>{item.get('product_code','')}</td>
            <td style="text-align:center">{pipe_dia}</td>
            <td style="text-align:center">{specs.get('rubber_diameter','') or '-'}</td>
            <td style="text-align:center">{specs.get('pipe_length','') or specs.get('face_length','')}</td>
            <td style="text-align:center">{pipe_thk}</td>
            <td style="text-align:center">{housing_size}</td>
            <td style="text-align:center">{specs.get('shaft_diameter','')}</td>
            <td style="text-align:center">{int(item.get('shaft_length_mm',0)) if item.get('shaft_length_mm') else ''}</td>
            <td style="text-align:center">{slot_str}</td>
            <td style="text-align:center">{bearing_display}</td>
            <td style="text-align:center;font-weight:700">{item.get('quantity','')}</td>
        </tr>"""

    items_summary_html = f"""
    <div style="font-size:12px;font-weight:700;color:#C5964A;text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px">Items Summary</div>
    <table style="width:100%;border-collapse:collapse;font-size:10px;margin-bottom:16px">
        <tr style="background:#0F172A;color:#fff">
            <th style="padding:6px;text-align:center">Sr.</th>
            <th style="padding:6px">Code</th>
            <th style="padding:6px;text-align:center">Pipe Dia</th>
            <th style="padding:6px;text-align:center">Rubber Dia</th>
            <th style="padding:6px;text-align:center">Pipe L.</th>
            <th style="padding:6px;text-align:center">Pipe Thk (mm)</th>
            <th style="padding:6px;text-align:center">Housing</th>
            <th style="padding:6px;text-align:center">Shaft Dia</th>
            <th style="padding:6px;text-align:center">Shaft L.</th>
            <th style="padding:6px;text-align:center">End Type</th>
            <th style="padding:6px;text-align:center">Bearing</th>
            <th style="padding:6px;text-align:center">Qty</th>
        </tr>
        {items_summary_rows}
    </table>"""

    # TABLE 2: Consolidated BOM — group by component + size (merge same dia, ignore length)
    consolidated_bom = {}
    import re as _re
    for item in all_items:
        for b in item.get("bom", []):
            comp = b.get("component", "")
            desc = b.get("description", "")
            mat = b.get("material", "")
            # Strip length from description for grouping key (e.g., remove "x 1000mm L")
            short_desc = _re.sub(r'\s*x?\s*\d+\.?\d*\s*mm\s*[LF]L?\b', '', desc).strip().rstrip('x').strip()
            # Also strip "— X nos/roller" from rubber ring
            short_desc = _re.sub(r'\s*—.*$', '', short_desc).strip()
            key = f"{comp}|{short_desc}"
            if key in consolidated_bom:
                consolidated_bom[key]["total_qty"] += b.get("total_qty", 0)
                consolidated_bom[key]["total_weight_kg"] += b.get("total_weight_kg", 0)
            else:
                consolidated_bom[key] = {
                    "component": comp,
                    "description": short_desc,
                    "material": mat,
                    "total_qty": b.get("total_qty", 0),
                    "total_weight_kg": b.get("total_weight_kg", 0),
                }

    consolidated_rows = ""
    grand_bom_weight = 0
    # Group by component for section headers
    from collections import OrderedDict
    component_groups = OrderedDict()
    for comp_key, cb in consolidated_bom.items():
        comp = cb["component"]
        if comp not in component_groups:
            component_groups[comp] = []
        component_groups[comp].append(cb)

    sr = 1
    for comp_name, items in component_groups.items():
        # Component header row
        consolidated_rows += f"""<tr style="background:#E2E8F0">
            <td colspan="6" style="padding:6px 10px;font-weight:700;color:#0F172A;font-size:11px">{comp_name}</td>
        </tr>"""
        for cb in items:
            grand_bom_weight += cb["total_weight_kg"]
            consolidated_rows += f"""<tr>
            <td style="text-align:center">{sr}</td>
            <td>{cb['description']}</td>
            <td>{cb['material']}</td>
            <td style="text-align:center;font-weight:700">{cb['total_qty']}</td>
            <td style="text-align:right">{round(cb['total_weight_kg'],3) if cb['total_weight_kg'] else '-'}</td>
        </tr>"""
            sr += 1

    consolidated_bom_html = f"""
    <div style="font-size:12px;font-weight:700;color:#C5964A;text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px">Total Bill of Materials (All Items)</div>
    <table style="width:100%;border-collapse:collapse;font-size:10px;margin-bottom:16px">
        <tr style="background:#1E293B;color:#fff">
            <th style="padding:7px;text-align:center;width:30px">Sr.</th>
            <th style="padding:7px">Description</th>
            <th style="padding:7px">Material</th>
            <th style="padding:7px;text-align:center">Total Qty</th>
            <th style="padding:7px;text-align:right">Total Wt (kg)</th>
        </tr>
        {consolidated_rows}
        <tr style="font-weight:700;background:#F0F4F8">
            <td colspan="4" style="text-align:right;padding:8px">Grand Total Weight</td>
            <td style="text-align:right;padding:8px">{round(grand_bom_weight,3)} kg</td>
        </tr>
    </table>""" if consolidated_bom else ""

    # Build per-item detail HTML
    items_html = ""
    for item in all_items:
        slot = item.get("shaft_slot", "N/A")
        specs = item.get("specifications", {})

        # Drawing image
        drawing_html = ""
        if item.get("drawing_base64") and item.get("drawing_filename"):
            ext = item["drawing_filename"].rsplit(".", 1)[-1].lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            drawing_html = f'<div style="margin:10px 0"><img src="data:{mime};base64,{item["drawing_base64"]}" style="max-width:100%;max-height:300px;border:1px solid #ddd;border-radius:4px" /></div>'

        # BOM table
        bom = item.get("bom", [])
        bom_rows = ""
        total_bom_weight = 0
        for bi, b in enumerate(bom, 1):
            tw = b.get("total_weight_kg", 0)
            total_bom_weight += tw
            bom_rows += f"""<tr>
                <td style="text-align:center">{bi}</td>
                <td><b>{b.get('component','')}</b></td>
                <td>{b.get('description','')}</td>
                <td>{b.get('material','')}</td>
                <td style="text-align:center">{b.get('qty_per_unit','')}</td>
                <td style="text-align:center">{b.get('total_qty','')}</td>
                <td style="text-align:right">{b.get('weight_per_unit_kg','') if b.get('weight_per_unit_kg') else '-'}</td>
                <td style="text-align:right">{tw if tw else '-'}</td>
            </tr>"""

        bom_total_row = f"""<tr style="font-weight:700;background:#F0F4F8">
            <td colspan="7" style="text-align:right;padding:8px">Total BOM Weight</td>
            <td style="text-align:right;padding:8px">{round(total_bom_weight,3)} kg</td>
        </tr>""" if total_bom_weight > 0 else ""

        items_html += f"""
        <div style="page-break-inside:avoid;margin-bottom:24px;border:1px solid #E2E8F0;border-radius:8px;overflow:hidden">
            <div style="background:#0F172A;color:#fff;padding:12px 16px;font-size:14px">
                <b>{item.get('product_name','')}</b> &nbsp; | &nbsp; Code: {item.get('product_code','')} &nbsp; | &nbsp; Qty: <b>{item.get('quantity','')}</b>
            </div>
            <div style="padding:16px">
                <table style="width:100%;margin-bottom:12px">
                    <tr>
                        <td style="width:50%;vertical-align:top">
                            <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:1px">Drawing Number</div>
                            <div style="font-size:14px;font-weight:600;color:#0F172A">{item.get('drawing_number','N/A')}</div>
                        </td>
                        <td style="width:50%;vertical-align:top">
                            <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:1px">Paint Details</div>
                            <div style="font-size:14px;color:#0F172A">{item.get('paint_details','N/A')}</div>
                        </td>
                    </tr>
                    <tr>
                        <td style="vertical-align:top;padding-top:10px">
                            <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:1px">Shaft Length</div>
                            <div style="font-size:14px;font-weight:600;color:#0F172A">{item.get('shaft_length_mm','N/A')} mm</div>
                        </td>
                        <td style="vertical-align:top;padding-top:10px">
                            <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:1px">Shaft End Slot (Both Ends)</div>
                            <div style="font-size:14px;font-weight:700;color:#960018">{slot}</div>
                        </td>
                    </tr>
                </table>
                {f'<div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:1px">Production Notes</div><div style="font-size:12px;color:#475569;margin-bottom:10px;padding:8px;background:#F8FAFC;border-radius:4px">{item.get("production_notes")}</div>' if item.get("production_notes") else ''}
                {drawing_html}
                {'<div style="font-size:11px;font-weight:700;color:#C5964A;text-transform:uppercase;letter-spacing:1px;margin:12px 0 8px">Bill of Materials</div><table style="width:100%;border-collapse:collapse;font-size:11px"><tr style="background:#1E293B;color:#fff"><th style="padding:6px;text-align:center">Sr</th><th style="padding:6px">Component</th><th style="padding:6px">Description</th><th style="padding:6px">Material</th><th style="padding:6px;text-align:center">Qty/Unit</th><th style="padding:6px;text-align:center">Total Qty</th><th style="padding:6px;text-align:right">Wt/Unit (kg)</th><th style="padding:6px;text-align:right">Total Wt (kg)</th></tr>' + bom_rows + bom_total_row + '</table>' if bom else ''}
            </div>
        </div>"""

    # Stage history
    stage_html = ""
    for sh in wo.get("stage_history", []):
        sh_date = format_date_dmy(sh.get("timestamp"))
        sh_stage_label = WO_STAGE_LABELS.get(sh.get("stage"), sh.get("stage", ""))
        sh_by = sh.get("by", "")
        sh_notes = (" — " + sh.get("notes")) if sh.get("notes") else ""
        stage_html += f'<div style="margin-bottom:4px"><span style="display:inline-block;width:8px;height:8px;border-radius:4px;background:#C5964A;margin-right:6px"></span><b>{sh_stage_label}</b> — {sh_date} by {sh_by}{sh_notes}</div>'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 12mm; }}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color:#1E293B; font-size:11px; line-height:1.5; }}
    .wo {{ max-width:800px; margin:0 auto; }}
    .header {{ display:flex; justify-content:space-between; align-items:center; border-bottom:3px solid #C5964A; padding-bottom:12px; margin-bottom:16px; }}
    .wo-title {{ font-size:20px; font-weight:800; color:#960018; }}
    .wo-num {{ font-size:14px; font-weight:600; color:#0F172A; }}
    .info-grid {{ display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }}
    .info-box {{ flex:1; min-width:140px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px; }}
    .info-label {{ font-size:9px; font-weight:700; color:#C5964A; letter-spacing:1px; text-transform:uppercase; }}
    .info-value {{ font-size:12px; font-weight:600; color:#0F172A; margin-top:2px; }}
    table {{ border-collapse:collapse; }}
    table td, table th {{ border-bottom:1px solid #E2E8F0; }}
    .footer {{ text-align:center; margin-top:20px; padding-top:10px; border-top:1px solid #E2E8F0; font-size:9px; color:#94A3B8; }}
    .stamp-area {{ display:flex; justify-content:space-between; margin-top:40px; }}
    .stamp-line {{ width:180px; border-top:1px solid #CBD5E1; margin-top:50px; padding-top:4px; font-size:10px; color:#64748B; text-align:center; }}
</style>
</head><body>
<div class="wo">
    <div class="header">
        <div>{logo_html}<br><span style="font-size:9px;color:#64748B">{COMPANY['address'][:60]}</span></div>
        <div style="text-align:right">
            <div class="wo-title">WORK ORDER</div>
            <div class="wo-num">{wo.get('wo_number','')}</div>
            <div style="font-size:11px;color:#64748B">Date: {format_date_dmy(wo.get('created_at'))}</div>
        </div>
    </div>

    <div class="info-grid">
        <div class="info-box"><div class="info-label">Sales Order</div><div class="info-value">{wo.get('so_number','N/A')}</div></div>
        <div class="info-box"><div class="info-label">Quote Ref</div><div class="info-value">{wo.get('quote_number','N/A')}</div></div>
        <div class="info-box"><div class="info-label">Customer</div><div class="info-value">{wo.get('customer_name','')}</div></div>
        <div class="info-box"><div class="info-label">Company</div><div class="info-value">{wo.get('customer_company','') or 'N/A'}</div></div>
        <div class="info-box"><div class="info-label">Stage</div><div class="info-value">{WO_STAGE_LABELS.get(wo.get('stage',''), wo.get('stage',''))}</div></div>
    </div>
    <div class="info-grid">
        <div class="info-box"><div class="info-label">Customer PO</div><div class="info-value">{wo.get('customer_po_number','') or 'N/A'}</div></div>
        <div class="info-box"><div class="info-label">PO Date</div><div class="info-value">{wo.get('customer_po_date','') or 'N/A'}</div></div>
        <div class="info-box"><div class="info-label">Delivery Date</div><div class="info-value" style="font-weight:700;color:#960018">{wo.get('delivery_date','') or 'N/A'}</div></div>
    </div>
    <div class="info-grid">
        <div class="info-box"><div class="info-label">RAL Code</div><div class="info-value" style="font-weight:700;color:#960018">{wo.get('ral_code','') or 'N/A'}</div></div>
        <div class="info-box"><div class="info-label">Paint Type</div><div class="info-value">{wo.get('paint_type','') or 'N/A'}</div></div>
        <div class="info-box" style="flex:3"><div class="info-label">Paint Specification</div><div class="info-value">{wo.get('paint_spec','') or 'N/A'}</div></div>
    </div>

    {items_summary_html}

    {consolidated_bom_html}

    <div style="font-size:12px;font-weight:700;color:#C5964A;text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px">Item Details</div>
    {items_html}

    <div style="font-size:11px;font-weight:700;color:#C5964A;text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px">Stage History</div>
    {stage_html}

    <div class="stamp-area">
        <div><div class="stamp-line">Production Head</div></div>
        <div><div class="stamp-line">QC Approved</div></div>
        <div><div class="stamp-line">Authorized Signatory</div></div>
    </div>

    <div class="footer">{COMPANY['name']} | {COMPANY['email']} | {COMPANY['phone']}</div>
</div>
</body></html>"""

    output = io.BytesIO(html.encode('utf-8'))
    output.seek(0)
    filename = f"{wo.get('wo_number', 'WO').replace('/', '-')}.html"

    return StreamingResponse(output, media_type="text/html",
                           headers={"Content-Disposition": f"attachment; filename={filename}"})

import math

STEEL_DENSITY = 7850  # kg/m³

def _calc_weight(volume_mm3):
    """Convert volume in mm³ to weight in kg"""
    return round(volume_mm3 / 1e9 * STEEL_DENSITY, 3)


def _build_sub_wo_items(wo_items: list) -> tuple:
    """From WO items, extract pipe & shaft job card lines.
    Returns (pipe_items, shaft_items).
    """
    import roller_standards as rs
    import re
    pipe_items = []
    shaft_items = []
    for it in wo_items:
        specs = it.get("specifications") or {}
        qty = int(it.get("quantity") or 1)
        name = (it.get("product_name") or "").lower()
        is_pulley = "pulley" in name
        # Sub-WOs (Pipe/Shaft job cards) are rollers-only; pulleys have different processing parameters
        if is_pulley:
            continue

        pipe_dia = specs.get("pipe_diameter") or 0
        pipe_length = specs.get("pipe_length") or 0
        shaft_dia = specs.get("shaft_diameter") or 0
        shaft_length = it.get("shaft_length_mm") or specs.get("shaft_length") or 0
        pipe_type = specs.get("pipe_type") or ""
        bearing_number = specs.get("bearing_number") or specs.get("bearing") or ""
        bearing_make = specs.get("bearing_make") or "china"

        # Derive wall thickness from pipe_type (A/B/C or explicit mm)
        wall_thk = 0
        if pipe_type:
            m = re.search(r'(\d+\.?\d*)\s*mm', str(pipe_type))
            if m:
                wall_thk = float(m.group(1))
        if wall_thk == 0 and pipe_type and len(str(pipe_type).strip()) == 1:
            PIPE_WALL_THK = {
                60.8: {"A": 2.9, "B": 3.6, "C": 4.5},
                76.1: {"A": 3.2, "B": 3.6, "C": 4.5},
                88.9: {"A": 3.2, "B": 4.0, "C": 4.8},
                114.3: {"A": 3.6, "B": 4.5, "C": 5.4},
                127.0: {"A": 4.0, "B": 4.8, "C": 5.4},
                139.7: {"A": 4.0, "B": 4.8, "C": 5.4},
                152.4: {"A": 4.0, "B": 4.8, "C": 5.4},
                159.0: {"A": 4.0, "B": 4.8, "C": 5.4},
                165.0: {"A": 4.0, "B": 4.8, "C": 5.4},
            }
            wall_thk = PIPE_WALL_THK.get(pipe_dia, {}).get(str(pipe_type).strip().upper(), 0)

        # Housing size (CRC) — only if we have pipe + bearing
        housing_size = None
        if pipe_dia and bearing_number:
            try:
                housing_size = rs.get_housing_for_pipe_and_bearing(pipe_dia, bearing_number)
            except Exception:
                housing_size = None

        base = {
            "product_name": it.get("product_name"),
            "product_code": it.get("product_code"),
            "drawing_number": it.get("drawing_number"),
            "quantity": qty,
        }

        # Pipe sub-WO line (skip if no pipe dia/length)
        if pipe_dia and pipe_length:
            pipe_items.append({
                **base,
                "pipe_diameter": pipe_dia,
                "pipe_thickness": wall_thk,
                "pipe_length": pipe_length,
                "pipe_type": pipe_type,
                "housing_number": housing_size or "-",
                "housing_qty": qty * 2,  # 2 housings per roller
            })

        # Shaft sub-WO line (skip if pulley without shaft_dia)
        if shaft_dia or shaft_length:
            slot = it.get("shaft_slot_details") or {}
            slot_str = it.get("shaft_slot") or ""
            if not slot_str and slot:
                slot_str = f"{slot.get('width','')}×{slot.get('dimension','')} {slot.get('slot_type','')}"
            shaft_items.append({
                **base,
                "shaft_diameter": shaft_dia,
                "shaft_length": shaft_length,
                "end_slot": slot_str or "-",
                "shaft_slot_details": slot or {},
                "bearing_number": bearing_number or "-",
                "bearing_make": (bearing_make or "china").upper(),
                "bearing_qty": qty * 2,  # 2 bearings per roller (1 pair per pulley if applicable)
            })

    return pipe_items, shaft_items


async def _create_sub_wos(work_order: dict, current_user_email: str):
    """Create Pipe + Shaft sub-WOs linked to the main Work Order."""
    pipe_items, shaft_items = _build_sub_wo_items(work_order.get("items") or [])
    now_iso = datetime.now(timezone.utc).isoformat()
    parent = {
        "parent_wo_id": work_order.get("id"),
        "parent_wo_number": work_order.get("wo_number"),
        "order_id": work_order.get("order_id"),
        "so_number": work_order.get("so_number"),
        "customer_name": work_order.get("customer_name"),
        "customer_company": work_order.get("customer_company"),
        "customer_po_number": work_order.get("customer_po_number"),
        "customer_po_date": work_order.get("customer_po_date"),
        "delivery_date": work_order.get("delivery_date"),
        "created_at": now_iso,
        "created_by": current_user_email,
    }
    created = []
    if pipe_items:
        doc = {
            "id": str(ObjectId()),
            "sub_wo_number": f"{work_order.get('wo_number')}/P",
            "type": "pipe",
            "items": pipe_items,
            **parent,
        }
        await db.sub_work_orders.insert_one(doc)
        doc.pop("_id", None)
        created.append(doc)
    if shaft_items:
        doc = {
            "id": str(ObjectId()),
            "sub_wo_number": f"{work_order.get('wo_number')}/S",
            "type": "shaft",
            "items": shaft_items,
            **parent,
        }
        await db.sub_work_orders.insert_one(doc)
        doc.pop("_id", None)
        created.append(doc)
    return created


def _generate_bom(product: dict, production_details: dict, specs: dict, qty: int) -> list:
    """Auto-generate Bill of Materials from product specs with detailed sizes"""
    import roller_standards as rs
    
    bom = []
    product_name = (product.get("product_name") or "").lower()
    is_pulley = "pulley" in product_name
    is_roller = not is_pulley

    pipe_dia = specs.get("pipe_diameter", 0)
    pipe_length = specs.get("pipe_length", 0)
    shaft_dia = specs.get("shaft_diameter", 0)
    shaft_length = production_details.get("shaft_length", 0) or specs.get("shaft_length", 0) or 0
    pipe_type = specs.get("pipe_type", "")
    bearing_number = specs.get("bearing_number", specs.get("bearing", ""))
    bearing_make = specs.get("bearing_make", "china")

    wall_thk = 0
    if pipe_type:
        import re
        thk_match = re.search(r'(\d+\.?\d*)\s*mm', str(pipe_type))
        if thk_match:
            wall_thk = float(thk_match.group(1))
    # If pipe_type is just a letter (A/B/C), lookup from standard thickness table
    if wall_thk == 0 and pipe_type and len(pipe_type.strip()) == 1 and pipe_type.strip().upper() in ("A", "B", "C"):
        PIPE_WALL_THK = {
            60.8: {"A": 2.9, "B": 3.6, "C": 4.5},
            76.1: {"A": 3.2, "B": 3.6, "C": 4.5},
            88.9: {"A": 3.2, "B": 4.0, "C": 4.8},
            114.3: {"A": 3.6, "B": 4.5, "C": 5.4},
            127.0: {"A": 4.0, "B": 4.8, "C": 5.4},
            139.7: {"A": 4.0, "B": 4.8, "C": 5.4},
            152.4: {"A": 4.0, "B": 4.8, "C": 5.4},
            159.0: {"A": 4.0, "B": 4.8, "C": 5.4},
            165.0: {"A": 4.0, "B": 4.8, "C": 5.4},
        }
        wall_thk = PIPE_WALL_THK.get(pipe_dia, {}).get(pipe_type.strip().upper(), 0)

    if is_roller:
        product_code = (product.get("product_id") or "").upper()
        is_impact = "IR" in product_code or "IMPACT" in product_name.upper()
        
        # Get bearing OD for housing
        bearing_od = rs.BEARING_OD.get(bearing_number, 0)
        # Get housing size
        housing_size = rs.get_housing_for_pipe_and_bearing(pipe_dia, bearing_number) if pipe_dia and bearing_number else None

        # 1. Pipe
        if pipe_dia > 0 and pipe_length > 0:
            effective_thk = wall_thk if wall_thk > 0 else 3.2
            od = pipe_dia
            id_val = od - 2 * effective_thk
            pipe_vol = (math.pi / 4) * (od**2 - id_val**2) * pipe_length
            pipe_wt = _calc_weight(pipe_vol)
            bom.append({
                "component": "Pipe",
                "description": f"{pipe_dia}mm OD x {effective_thk}mm thk x {pipe_length}mm L",
                "material": "MS ERW",
                "bom_match_key": f"pipe:{pipe_dia}:{effective_thk}",
                "qty_per_unit": 1, "total_qty": qty,
                "weight_per_unit_kg": pipe_wt, "total_weight_kg": round(pipe_wt * qty, 3),
            })

        # 2. Shaft
        if shaft_dia > 0 and shaft_length > 0:
            shaft_vol = (math.pi / 4) * (shaft_dia**2) * shaft_length
            shaft_wt = _calc_weight(shaft_vol)
            bom.append({
                "component": "Shaft",
                "description": f"{shaft_dia}mm dia x {shaft_length}mm L",
                "material": "EN-8 Bright Bar",
                "bom_match_key": f"shaft:{shaft_dia}:EN-8",
                "qty_per_unit": 1, "total_qty": qty,
                "weight_per_unit_kg": shaft_wt, "total_weight_kg": round(shaft_wt * qty, 3),
            })

        # 3. Bearing — number + make, with standard weight from datasheet
        if bearing_number:
            make_label = (bearing_make or "china").upper()
            brg_unit_wt = rs.BEARING_WEIGHT_KG.get(bearing_number, 0) or 0
            brg_qty_per_unit = 2
            bom.append({
                "component": "Bearing",
                "description": f"{bearing_number} ZZ - {make_label} (OD: {bearing_od}mm)",
                "material": f"{bearing_number} - {make_label}",
                "bom_match_key": f"bearing:{bearing_number}:{(bearing_make or 'china').lower()}",
                "qty_per_unit": brg_qty_per_unit, "total_qty": qty * brg_qty_per_unit,
                "weight_per_unit_kg": brg_unit_wt,
                "total_weight_kg": round(brg_unit_wt * brg_qty_per_unit * qty, 3),
            })

        # 4. Housing — with size (housing_dia/bearing_OD)
        if housing_size:
            bom.append({
                "component": "Housing",
                "description": f"Housing {housing_size} for {pipe_dia}mm pipe",
                "material": f"CRC Housing {housing_size}",
                "bom_match_key": f"housing:{housing_size}",
                "qty_per_unit": 2, "total_qty": qty * 2,
                "weight_per_unit_kg": 0, "total_weight_kg": 0,
            })
        else:
            bom.append({
                "component": "Housing",
                "description": f"For {pipe_dia}mm pipe / {bearing_number}",
                "material": "MS Pressed",
                "qty_per_unit": 2, "total_qty": qty * 2,
                "weight_per_unit_kg": 0, "total_weight_kg": 0,
            })

        # 5. Seal — by bearing number
        seal_desc = f"Seal for {bearing_number}" if bearing_number else f"Seal for {pipe_dia}mm"
        bom.append({
            "component": "Seal",
            "description": seal_desc,
            "material": f"Labyrinth Seal - {bearing_number}",
            "bom_match_key": f"seal:{bearing_number}",
            "qty_per_unit": 2, "total_qty": qty * 2,
            "weight_per_unit_kg": 0, "total_weight_kg": 0,
        })

        # 6. Circlip — A{shaft_dia}
        circlip_num = f"A{shaft_dia}" if shaft_dia else "Circlip"
        bom.append({
            "component": "Circlip",
            "description": f"{circlip_num} for {shaft_dia}mm shaft",
            "material": f"Spring Steel {circlip_num}",
            "bom_match_key": f"circlip:{shaft_dia}",
            "qty_per_unit": 4, "total_qty": qty * 4,
            "weight_per_unit_kg": 0, "total_weight_kg": 0,
        })

        # 7. Grease
        bom.append({
            "component": "Grease",
            "description": "Bearing grease",
            "material": "EP2 Grease",
            "bom_match_key": "grease:EP2",
            "qty_per_unit": 1, "total_qty": qty,
            "weight_per_unit_kg": 0, "total_weight_kg": 0,
        })

        # 8. Rubber Rings — Impact roller only
        if is_impact and pipe_dia > 0 and pipe_length > 0:
            ring_width = 35
            ring_qty = max(1, int(pipe_length / ring_width))
            # Ring ID = rounded pipe dia (60, 76, 89, 114 etc.)
            ring_id = round(pipe_dia)
            # Get rubber OD from specs or from RUBBER_LAGGING_OPTIONS
            rubber_dia = specs.get("rubber_diameter", 0)
            if not rubber_dia:
                options = rs.RUBBER_LAGGING_OPTIONS.get(ring_id, [])
                rubber_dia = options[0] if options else 0
            # Weight from the master RUBBER_RING_WEIGHTS lookup (user-provided sheet)
            ring_unit_wt = 0
            if rubber_dia:
                lookup_wt = rs.get_rubber_ring_weight(pipe_dia, rubber_dia)
                if lookup_wt is not None:
                    ring_unit_wt = lookup_wt
            ring_desc = f"{ring_id}mm ID x {rubber_dia}mm OD x {ring_width}mm thk" if rubber_dia else f"{ring_id}mm ID x {ring_width}mm thk"
            bom.append({
                "component": "Rubber Ring",
                "description": f"{ring_desc} — {ring_qty} nos/roller",
                "material": "Natural Rubber",
                "bom_match_key": f"rubber_ring:{ring_id}:{rubber_dia}",
                "qty_per_unit": ring_qty, "total_qty": qty * ring_qty,
                "weight_per_unit_kg": ring_unit_wt,
                "total_weight_kg": round(ring_unit_wt * ring_qty * qty, 3),
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
                "bom_match_key": f"pipe:{pipe_dia}:{effective_thk}",
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
                "bom_match_key": f"shaft:{shaft_dia}:{shaft_mat}",
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
                "bom_match_key": f"end_plate:{pipe_dia}:{ep_thk}",
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
                "bom_match_key": f"kla:{kla_model}",
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


# ============= BOM-STOCK MATCHING & SHORTAGE CHECK =============

def _derive_bom_match_key(component: str, description: str) -> Optional[str]:
    """Legacy-BOM fallback: reconstruct a stock-register match key from the
    component + description when `bom_match_key` was never saved.
    Handles: Pipe, Shaft, Bearing, Housing, Seal, Circlip, Grease, End Plate, KLA.
    """
    import re as _re
    comp = (component or "").lower().strip()
    desc = description or ""
    if comp == "pipe":
        # "88.9mm OD × 3.2mm thk × 1000mm L" → pipe:88.9:3.2 (float to match stock convention)
        m = _re.search(r"([\d.]+)\s*mm\s*OD\s*[x×*]\s*([\d.]+)\s*mm\s*thk", desc, _re.I)
        if m: return f"pipe:{float(m.group(1))}:{float(m.group(2))}"
    if comp == "shaft":
        # "25mm dia x 400mm L EN-8" or "25mm dia × 750.0mm L" (material default EN-8)
        m = _re.search(r"([\d.]+)\s*mm\s*dia", desc, _re.I)
        if m:
            try: dia = int(float(m.group(1)))
            except Exception: dia = m.group(1)
            mat_m = _re.search(r"(EN-?\d+|SS-?\d+|AISI-?\d+|MS)", desc, _re.I)
            mat = mat_m.group(1).upper().replace(" ", "") if mat_m else "EN-8"
            if mat and mat[:2] == "EN" and "-" not in mat:
                mat = mat[:2] + "-" + mat[2:]
            return f"shaft:{dia}:{mat}"
    if comp == "bearing":
        # Description like "6204 ZZ china" or "6204 NBC"
        m = _re.search(r"(\d{3,5})\s*(?:ZZ|2RS|RS)?\s*([A-Za-z]+)?", desc)
        if m:
            make = (m.group(2) or "china").lower()
            return f"bearing:{m.group(1)}:{make}"
    if comp == "housing":
        # "Housing 84/52 for 88.9mm pipe" → housing:84/52
        m = _re.search(r"(\d+\s*/\s*\d+)", desc)
        if m: return f"housing:{m.group(1).replace(' ','')}"
    if comp == "seal":
        m = _re.search(r"(\d{3,5})", desc)
        if m: return f"seal:{m.group(1)}"
    if comp == "circlip":
        m = _re.search(r"([\d.]+)\s*mm", desc)
        if m:
            v = float(m.group(1))
            # Use int form ("circlip:25") when whole number to match stock register convention
            return f"circlip:{int(v)}" if v == int(v) else f"circlip:{v}"
    if comp == "rubber ring" or comp == "rubber_ring":
        # "114mm ID x 139mm OD x 35mm thk" → rubber_ring:114:139
        m = _re.search(r"([\d.]+)\s*mm\s*ID\s*[x×*]\s*([\d.]+)\s*mm\s*OD", desc, _re.I)
        if m:
            try:
                id_v = int(float(m.group(1)))
                od_v = int(float(m.group(2)))
                return f"rubber_ring:{id_v}:{od_v}"
            except Exception:
                pass
        # Fallback "88.9mm dia × 35mm wide" → rubber_ring:89 (prefix-match picks any OD in stock)
        m2 = _re.search(r"([\d.]+)\s*mm\s*dia", desc, _re.I)
        if m2:
            try:
                id_v = int(round(float(m2.group(1))))
                return f"rubber_ring:{id_v}"
            except Exception:
                pass
    if comp == "housing":
        # Primary: "Housing 84/52 for 88.9mm pipe" → housing:84/52
        m = _re.search(r"(\d+\s*/\s*\d+)", desc)
        if m: return f"housing:{m.group(1).replace(' ','')}"
        # Fallback: "Bearing housing for 88.9mm pipe" → housing_for:88.9 (prefix for later resolve)
        m2 = _re.search(r"([\d.]+)\s*mm\s*pipe", desc, _re.I)
        if m2:
            pd = float(m2.group(1))
            pd_s = str(int(pd)) if pd == int(pd) else str(pd)
            return f"housing_for_pipe:{pd_s}"
    if comp == "grease":
        return "grease:EP2"
    if comp == "end plate":
        m = _re.search(r"(\d+)\s*mm\s*pipe.*?([\d.]+)\s*mm", desc)
        if m: return f"end_plate:{m.group(1)}:{m.group(2)}"
    if "kla" in comp:
        m = _re.search(r"(KLA-?[A-Z0-9/-]+)", desc, _re.I)
        if m: return f"kla:{m.group(1)}"
    return None


async def _match_bom_to_stock(bom_component: str, bom_description: str, bom_material: str, bom_match_key: str = None) -> dict:
    """Find matching stock item for a BOM component using bom_match_key.
    Tries exact match first. If none, falls back to a prefix match so brand-
    qualified stock items (e.g. `bearing:6205:china`) still resolve a brand-
    agnostic BOM key (`bearing:6205`). Picks the variant with highest
    current_stock for stability.
    Fallback: derive the key from description for legacy WOs missing the field."""
    if not bom_match_key:
        bom_match_key = _derive_bom_match_key(bom_component, bom_description)
    if bom_match_key:
        # 1) Exact match
        stock_item = await db.stock_items.find_one({"bom_match_key": bom_match_key}, {"_id": 0})
        if stock_item:
            return stock_item
        # 2) Prefix-tolerant match (e.g. bearing:6205 → bearing:6205:china/skf/fag)
        import re as _re
        pattern = "^" + _re.escape(bom_match_key) + ":"
        candidates = await db.stock_items.find(
            {"bom_match_key": {"$regex": pattern}}, {"_id": 0}
        ).to_list(20)
        if candidates:
            candidates.sort(key=lambda x: (-(x.get("current_stock") or 0), (x.get("name") or "")))
            return candidates[0]
    return None


async def _check_bom_shortages(work_order: dict) -> list:
    """Check all BOM items against stock and return shortage list"""
    import re as _re
    shortages = []

    def _kg_from_meters(component: str, description: str, meters: float) -> Optional[float]:
        """Steel-weight conversion — Pipe: W=0.0246615·t·(D-t) kg/m, Shaft: W=0.006165·d² kg/m."""
        if meters <= 0:
            return None
        c = (component or "").lower()
        if c == "pipe":
            m = _re.search(r"([\d.]+)\s*mm\s*OD\s*[x×*]\s*([\d.]+)\s*mm\s*thk", description or "", _re.I)
            if m:
                try:
                    D = float(m.group(1)); t = float(m.group(2))
                    return round(meters * 0.0246615 * t * (D - t), 2)
                except Exception: return None
        if c == "shaft":
            m = _re.search(r"([\d.]+)\s*mm\s*dia", description or "", _re.I)
            if m:
                try:
                    d = float(m.group(1))
                    return round(meters * 0.006165 * d * d, 2)
                except Exception: return None
        return None

    for item in work_order.get("items", []):
        for bom in item.get("bom", []):
            component = bom.get("component", "")
            description = bom.get("description", "")
            material = bom.get("material", "")
            required_qty = bom.get("total_qty", 0)

            if required_qty <= 0:
                continue

            stock_item = await _match_bom_to_stock(component, description, material, bom.get("bom_match_key"))

            if stock_item:
                available = stock_item.get("current_stock", 0)
                if available < required_qty:
                    short_qty = round(required_qty - available, 3)
                    row = {
                        "component": component,
                        "description": description,
                        "stock_item_id": stock_item.get("id"),
                        "stock_item_name": stock_item.get("name"),
                        "required": required_qty,
                        "available": available,
                        "shortage": short_qty,
                        "unit": stock_item.get("unit_purchase", "nos"),
                        "wo_number": work_order.get("wo_number"),
                    }
                    # Add kg weight for Pipe / Shaft so procurement sees both meters & kg
                    kg = _kg_from_meters(component, description, short_qty)
                    if kg is not None:
                        row["shortage_kg"] = kg
                        row["required_kg"] = _kg_from_meters(component, description, required_qty)
                        row["available_kg"] = _kg_from_meters(component, description, available)
                    shortages.append(row)
            else:
                # No matching stock item found — report as unknown
                row = {
                    "component": component,
                    "description": description,
                    "stock_item_id": None,
                    "stock_item_name": "NOT IN STOCK REGISTER",
                    "required": required_qty,
                    "available": 0,
                    "shortage": required_qty,
                    "unit": "nos",
                    "wo_number": work_order.get("wo_number"),
                }
                kg = _kg_from_meters(component, description, required_qty)
                if kg is not None:
                    row["shortage_kg"] = kg
                    row["required_kg"] = kg
                    row["available_kg"] = 0
                    row["unit"] = "meters"
                shortages.append(row)

    return shortages


@router.get("/wo-shortages")
async def get_wo_shortages(current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Get material shortages for all pending (non-completed) work orders"""
    wos = await db.work_orders.find({"stage": {"$ne": "completed"}}, {"_id": 0}).to_list(100)
    
    all_shortages = []
    for wo in wos:
        shortages = await _check_bom_shortages(wo)
        if shortages:
            all_shortages.extend(shortages)
    
    # Group by stock item for consolidated view
    consolidated = {}
    for s in all_shortages:
        key = s.get("stock_item_name", s.get("description", ""))
        if key in consolidated:
            consolidated[key]["required"] += s["required"]
            consolidated[key]["shortage"] += s["shortage"]
            if s.get("shortage_kg") is not None:
                consolidated[key]["shortage_kg"] = round((consolidated[key].get("shortage_kg") or 0) + s["shortage_kg"], 2)
                consolidated[key]["required_kg"] = round((consolidated[key].get("required_kg") or 0) + (s.get("required_kg") or 0), 2)
                consolidated[key]["available_kg"] = round((consolidated[key].get("available_kg") or 0) + (s.get("available_kg") or 0), 2)
            consolidated[key]["wo_numbers"].append(s["wo_number"])
        else:
            consolidated[key] = {
                "component": s["component"],
                "description": s["description"],
                "stock_item_id": s["stock_item_id"],
                "stock_item_name": s["stock_item_name"],
                "required": s["required"],
                "available": s["available"],
                "shortage": s["shortage"],
                "shortage_kg": s.get("shortage_kg"),
                "required_kg": s.get("required_kg"),
                "available_kg": s.get("available_kg"),
                "unit": s["unit"],
                "wo_numbers": [s["wo_number"]],
            }
    
    return {
        "shortages": list(consolidated.values()),
        "total": len(consolidated),
        "detail": all_shortages,
    }


@router.get("/wo-shortages/by-wo")
async def get_wo_shortages_by_wo(current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Per-WO view of material shortages — one row per WO with the full shortage list."""
    wos = await db.work_orders.find({"stage": {"$ne": "completed"}}, {"_id": 0}).sort("created_at", -1).to_list(200)
    rows = []
    for wo in wos:
        shortages = await _check_bom_shortages(wo)
        if not shortages:
            continue
        rows.append({
            "wo_id": wo.get("id"),
            "wo_number": wo.get("wo_number"),
            "so_number": wo.get("so_number"),
            "customer_name": wo.get("customer_name"),
            "delivery_date": wo.get("delivery_date"),
            "stage": wo.get("stage"),
            "shortage_count": len(shortages),
            "shortages": shortages,
        })
    return {"rows": rows, "total": len(rows)}


async def _wo_material_status(wo: dict) -> dict:
    """Compute material-status snapshot for a single WO.
    Status:
      - 'all_in_stock' if no shortages exist
      - 'po_received'  if shortages exist but sum of po_wo_receipts for this WO covers it
      - 'po_pending'   if at least one open PO (status != received) is linked to this WO
      - 'not_procured' otherwise
    """
    shortages = await _check_bom_shortages(wo)
    if not shortages:
        return {"status": "all_in_stock", "shortage_count": 0, "linked_pos": 0}

    wo_id = wo.get("id")
    pos = await db.purchase_orders.find({"linked_wo_ids": wo_id}, {"_id": 0, "po_number": 1, "status": 1}).to_list(100)
    open_pos = [p for p in pos if p.get("status") not in ("received", "cancelled")]
    if open_pos:
        return {
            "status": "po_pending",
            "shortage_count": len(shortages),
            "linked_pos": len(pos),
            "open_pos": [p.get("po_number") for p in open_pos][:5],
        }
    # Check if everything has been received already via po_wo_receipts
    received_ids = set()
    async for r in db.po_wo_receipts.find({"wo_id": wo_id}, {"_id": 0, "stock_item_id": 1}):
        received_ids.add(r.get("stock_item_id"))
    if shortages and all(s.get("stock_item_id") in received_ids for s in shortages if s.get("stock_item_id")):
        return {"status": "po_received", "shortage_count": len(shortages), "linked_pos": len(pos)}

    return {"status": "not_procured", "shortage_count": len(shortages), "linked_pos": len(pos)}


@router.get("/work-orders/material-status/overview")
async def wo_material_status_overview(
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PRODUCTION_HEAD]))
):
    """Batch material-status for every non-completed WO. Used by WorkOrders list to show a chip per row."""
    wos = await db.work_orders.find({"stage": {"$ne": "completed"}}, {"_id": 0}).sort("created_at", -1).to_list(500)
    result: dict = {}
    for wo in wos:
        result[wo.get("id")] = await _wo_material_status(wo)
    return {"statuses": result}


@router.post("/admin/backfill-pipe-thickness")
async def backfill_pipe_thickness(
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """One-shot fix: re-derive the Pipe BOM row's thickness on every WO from
    the parent item's `pipe_type` (A/B/C) + `pipe_diameter` specs, replacing
    the legacy 3.2mm fallback with the correct IS-9295 value.

    Updates pipe row's `description` and `bom_match_key`. Leaves other BOM
    rows untouched. Returns a per-WO summary.
    """
    import re as _re
    PIPE_WALL_THK = {
        60.8:  {"A": 2.9, "B": 3.6, "C": 4.5},
        76.1:  {"A": 3.2, "B": 3.6, "C": 4.5},
        88.9:  {"A": 3.2, "B": 4.0, "C": 4.8},
        114.3: {"A": 3.6, "B": 4.5, "C": 5.4},
        127.0: {"A": 4.0, "B": 4.8, "C": 5.4},
        139.7: {"A": 4.0, "B": 4.8, "C": 5.4},
        152.4: {"A": 4.0, "B": 4.8, "C": 5.4},
        159.0: {"A": 4.0, "B": 4.8, "C": 5.4},
        165.0: {"A": 4.0, "B": 4.8, "C": 5.4},
    }
    fixed = []
    wos = await db.work_orders.find({}, {"_id": 0}).to_list(5000)
    for wo in wos:
        wo_changes = []
        for it in (wo.get("items") or []):
            specs = it.get("specifications") or it.get("specs") or {}
            pt = specs.get("pipe_type")
            pd_raw = specs.get("pipe_diameter")
            if not pt or pd_raw is None or len(str(pt).strip()) != 1:
                continue
            try:
                pd = float(pd_raw)
            except (TypeError, ValueError):
                continue
            correct_thk = PIPE_WALL_THK.get(pd, {}).get(str(pt).strip().upper())
            if not correct_thk:
                continue
            for b in (it.get("bom") or []):
                if (b.get("component") or "").lower() != "pipe":
                    continue
                old_desc = b.get("description") or ""
                m = _re.search(r"([\d.]+)\s*mm\s*OD\s*[x×*]\s*([\d.]+)\s*mm\s*thk", old_desc, _re.I)
                if not m:
                    continue
                old_thk = float(m.group(2))
                if abs(old_thk - correct_thk) < 0.01:
                    continue  # already correct
                # Patch description + match key (preserve original length suffix)
                length_m = _re.search(r"([\d.]+)\s*mm\s*L", old_desc, _re.I)
                length_str = f" x {length_m.group(1)}mm L" if length_m else ""
                b["description"] = f"{pd}mm OD x {correct_thk}mm thk{length_str}"
                b["bom_match_key"] = f"pipe:{pd}:{correct_thk}"
                wo_changes.append({
                    "item": it.get("product_name"),
                    "was": f"{pd}x{old_thk}",
                    "now": f"{pd}x{correct_thk}",
                })
        if wo_changes:
            await db.work_orders.update_one({"id": wo.get("id")}, {"$set": {"items": wo.get("items")}})
            fixed.append({"wo_number": wo.get("wo_number"), "changes": wo_changes})
    return {"fixed_wos": fixed, "total_fixed": len(fixed)}


@router.post("/admin/backfill-bom-keys")
async def backfill_bom_keys(
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """One-shot: re-run `_derive_bom_match_key` on every BOM row of every WO
    and overwrite the stored key whenever the newly-derived key differs.
    Useful after derivation-rule fixes (circlip float, rubber ring, etc.).
    """
    updated = 0
    wos = await db.work_orders.find({}, {"_id": 0}).to_list(5000)
    for wo in wos:
        changed = False
        for it in (wo.get("items") or []):
            for b in (it.get("bom") or []):
                new_key = _derive_bom_match_key(b.get("component") or "", b.get("description") or "")
                if new_key and new_key != b.get("bom_match_key"):
                    b["bom_match_key"] = new_key
                    changed = True
                    updated += 1
        if changed:
            await db.work_orders.update_one({"id": wo.get("id")}, {"$set": {"items": wo.get("items")}})
    return {"updated_rows": updated, "message": f"Rewrote {updated} BOM match keys using latest derivation rules"}


@router.get("/admin/unresolved-bom-rows")
async def list_unresolved_bom_rows(
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Diagnostic: every BOM row (across all WOs) whose `bom_match_key` is still
    null or whose derived key does not map to any stock item in the register.
    Admin can use this to either edit the WO, or add a matching stock item.
    """
    rows = []
    wos = await db.work_orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    for wo in wos:
        for it_idx, it in enumerate(wo.get("items") or []):
            for b_idx, b in enumerate(it.get("bom") or []):
                key = b.get("bom_match_key") or _derive_bom_match_key(b.get("component") or "", b.get("description") or "")
                resolved = False
                if key:
                    stock = await db.stock_items.find_one({"bom_match_key": key}, {"_id": 0, "name": 1})
                    if not stock:
                        # Prefix-tolerant: "bearing:6205" matches "bearing:6205:china"
                        import re as _re2
                        stock = await db.stock_items.find_one(
                            {"bom_match_key": {"$regex": "^" + _re2.escape(key) + ":"}},
                            {"_id": 0, "name": 1},
                        )
                    resolved = bool(stock)
                if not resolved:
                    rows.append({
                        "wo_number": wo.get("wo_number"),
                        "wo_id": wo.get("id"),
                        "so_number": wo.get("so_number"),
                        "customer_name": wo.get("customer_name"),
                        "stage": wo.get("stage"),
                        "item_name": it.get("product_name"),
                        "component": b.get("component"),
                        "description": b.get("description"),
                        "material": b.get("material"),
                        "total_qty": b.get("total_qty"),
                        "stored_key": b.get("bom_match_key"),
                        "derived_key": key,
                        "reason": "no stock item matches key" if key else "no key could be derived",
                    })
    return {"rows": rows, "total": len(rows)}


class AddBomRowToStock(BaseModel):
    bom_match_key: str
    name: str
    category: str
    unit_purchase: Optional[str] = None
    unit_bom: Optional[str] = None
    reorder_level: Optional[float] = 0
    hsn_code: Optional[str] = None


@router.post("/admin/unresolved-bom/add-to-stock")
async def add_unresolved_bom_row_to_stock(
    req: AddBomRowToStock,
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
):
    """Create a stock item with the given bom_match_key so this unresolved BOM
    row (and any other WOs using the same derived key) resolve in one shot.

    Idempotent — if a stock item with the same bom_match_key already exists,
    returns that item instead of creating a duplicate.
    """
    key = (req.bom_match_key or "").strip()
    if not key or ":" not in key:
        raise HTTPException(status_code=400, detail="A valid bom_match_key (e.g. 'pipe:88.9:3.2') is required")
    existing = await db.stock_items.find_one({"bom_match_key": key}, {"_id": 0})
    if existing:
        return {"message": "Already in stock register", "item": existing, "created": False}

    # Default units by category (mirrors the app's other create flows)
    cat = (req.category or key.split(":", 1)[0] or "other").strip().lower()
    default_units = {
        "pipe":        ("kg", "meters"),
        "shaft":       ("kg", "meters"),
        "bearing":     ("nos", "nos"),
        "housing":     ("nos", "nos"),
        "seal":        ("nos", "nos"),
        "circlip":     ("nos", "nos"),
        "end_plate":   ("nos", "nos"),
        "hub":         ("nos", "nos"),
        "rubber_ring": ("nos", "nos"),
        "rubber_lagging": ("sqm", "sqm"),
        "grease":      ("kg", "kg"),
        "paint":       ("litres", "litres"),
        "kla":         ("nos", "nos"),
    }
    up, ub = default_units.get(cat, ("nos", "nos"))
    unit_purchase = (req.unit_purchase or up).strip()
    unit_bom = (req.unit_bom or ub).strip()

    now = get_ist_now().isoformat()
    doc = {
        "id": str(ObjectId()),
        "name": req.name.strip(),
        "category": cat,
        "unit_purchase": unit_purchase,
        "unit_bom": unit_bom,
        "conversion_factor": 1.0,
        "current_stock": 0,
        "reorder_level": float(req.reorder_level or 0),
        "bom_match_key": key,
        "hsn_code": (req.hsn_code or "").strip(),
        "specifications": {},
        "created_by": current_user.get("email"),
        "created_at": now,
        "source": "unresolved_bom_autocreate",
    }
    await db.stock_items.insert_one(doc)
    doc.pop("_id", None)
    return {"message": "Added to stock register", "item": doc, "created": True}

async def backfill_bom_match_keys(
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """One-time data tool — walk every Work Order and persist a `bom_match_key` on
    each BOM row that's currently null/missing by deriving it from the description.
    Safe to re-run (skips already-populated keys)."""
    wos = await db.work_orders.find({}).to_list(5000)
    wos_updated = 0
    rows_updated = 0
    rows_unresolved = 0
    for wo in wos:
        changed = False
        items = wo.get("items") or []
        for it in items:
            for b in it.get("bom") or []:
                if b.get("bom_match_key"):
                    continue
                derived = _derive_bom_match_key(b.get("component") or "", b.get("description") or "")
                if derived:
                    b["bom_match_key"] = derived
                    rows_updated += 1
                    changed = True
                else:
                    rows_unresolved += 1
        if changed:
            await db.work_orders.update_one({"_id": wo["_id"]}, {"$set": {"items": items}})
            wos_updated += 1
    return {
        "message": f"Backfill complete — {rows_updated} BOM rows updated across {wos_updated} WOs ({rows_unresolved} rows could not be derived).",
        "wos_updated": wos_updated,
        "rows_updated": rows_updated,
        "rows_unresolved": rows_unresolved,
        "total_wos_scanned": len(wos),
    }


@router.get("/work-orders/{wo_id}/issue-plan")
async def get_wo_issue_plan(wo_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    """For manual stock issue against a WO:
    returns every BOM line consolidated by bom_match_key, showing
    required_qty, already_issued_qty, remaining_qty, stock_item match and current stock.
    """
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]}, {"_id": 0})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    # 1. Aggregate required qty across all WO items by bom_match_key
    required_map: Dict[str, Dict[str, Any]] = {}
    for item in wo.get("items", []):
        for bom in item.get("bom", []):
            key = bom.get("bom_match_key")
            if not key:
                continue
            q = float(bom.get("total_qty") or 0)
            if q <= 0:
                continue
            if key not in required_map:
                required_map[key] = {
                    "bom_match_key": key,
                    "component": bom.get("component"),
                    "description": bom.get("description"),
                    "required_qty": 0,
                }
            required_map[key]["required_qty"] = round(required_map[key]["required_qty"] + q, 3)

    # 2. Sum already-issued qty from stock_transactions for this WO
    issued_map: Dict[str, float] = {}
    cursor = db.stock_transactions.find(
        {"wo_id": wo.get("id"), "type": "out"},
        {"_id": 0, "stock_item_id": 1, "qty": 1},
    )
    async for t in cursor:
        sid = t.get("stock_item_id")
        if sid:
            issued_map[sid] = round(issued_map.get(sid, 0) + float(t.get("qty") or 0), 3)

    # 3. Match each bom_match_key to a stock_item and build the plan
    plan = []
    for key, row in required_map.items():
        stock_item = await db.stock_items.find_one({"bom_match_key": key}, {"_id": 0})
        stock_item_id = stock_item.get("id") if stock_item else None
        already = issued_map.get(stock_item_id, 0) if stock_item_id else 0
        remaining = max(round(row["required_qty"] - already, 3), 0)
        available = float(stock_item.get("current_stock", 0)) if stock_item else 0
        plan.append({
            "bom_match_key": key,
            "component": row["component"],
            "description": row["description"],
            "required_qty": row["required_qty"],
            "already_issued_qty": already,
            "remaining_qty": remaining,
            "stock_item_id": stock_item_id,
            "stock_item_name": stock_item.get("name") if stock_item else None,
            "current_stock": available,
            "unit": stock_item.get("unit_purchase", "nos") if stock_item else "nos",
            "in_register": stock_item is not None,
        })

    # Also list all extra stock_items the user may want to add manually (not in BOM) — skip for minimalism
    # 4. Recent issues against this WO (last 5)
    recent_cursor = db.stock_transactions.find(
        {"wo_id": wo.get("id"), "type": "out"},
        {"_id": 0},
    ).sort("timestamp", -1).limit(5)
    recent_issues = []
    async for t in recent_cursor:
        si = None
        if t.get("stock_item_id"):
            si = await db.stock_items.find_one({"id": t["stock_item_id"]}, {"_id": 0, "name": 1, "unit_purchase": 1})
        recent_issues.append({
            "timestamp": t.get("timestamp"),
            "stock_item_name": si.get("name") if si else t.get("stock_item_name") or "Unknown",
            "qty": t.get("qty"),
            "unit": si.get("unit_purchase", "nos") if si else "nos",
            "by": t.get("by") or t.get("user_email"),
        })

    return {
        "wo_number": wo.get("wo_number"),
        "stage": wo.get("stage"),
        "plan": plan,
        "total_lines": len(plan),
        "recent_issues": recent_issues,
    }


# ============= FINISHED GOODS QC =============

class FinishedGoodsQC(BaseModel):
    status: str  # "passed" | "failed"
    remarks: Optional[str] = None


@router.post("/work-orders/{wo_id}/qc")
async def stamp_wo_qc(
    wo_id: str,
    body: FinishedGoodsQC,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.QUALITY_INSPECTOR])),
):
    """Stamp outgoing QC on a Work Order. Only passed WOs can be dispatched."""
    if body.status not in ("passed", "failed"):
        raise HTTPException(status_code=400, detail="status must be 'passed' or 'failed'")
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]}, {"_id": 0})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    if wo.get("stage") != "completed":
        raise HTTPException(status_code=400, detail="Only completed work orders can be QC-stamped")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.work_orders.update_one(
        {"id": wo.get("id")},
        {
            "$set": {
                "qc_status": body.status,
                "qc_remarks": (body.remarks or "").strip(),
                "qc_by": current_user.get("email"),
                "qc_at": now_iso,
                "updated_at": now_iso,
            },
            "$push": {
                "stage_history": {
                    "stage": f"qc_{body.status}",
                    "timestamp": now_iso,
                    "by": current_user.get("email"),
                    "notes": (body.remarks or "").strip(),
                }
            },
        },
    )
    return {"message": f"QC {body.status}", "wo_number": wo.get("wo_number")}



# ============= QC REPORT PDF =============

def _format_dmy(iso_val) -> str:
    if not iso_val:
        return ""
    try:
        from datetime import datetime as _dt
        if isinstance(iso_val, str):
            dt = _dt.fromisoformat(iso_val.replace("Z", "+00:00"))
        else:
            dt = iso_val
        return dt.strftime("%d-%m-%Y %H:%M")
    except Exception:
        return str(iso_val)[:16]


@router.get("/work-orders/{wo_id}/qc-report")
async def get_wo_qc_report_pdf(
    wo_id: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """Branded A4 QC Report PDF (HTML) for a Work Order."""
    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization[7:]
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]}, {"_id": 0})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    qc_status = (wo.get("qc_status") or "pending").lower()
    stamp_color = "#059669" if qc_status == "passed" else "#DC2626" if qc_status == "failed" else "#D97706"
    stamp_label = {"passed": "PASSED", "failed": "FAILED", "pending": "PENDING"}[qc_status]

    # Build item inspection rows
    item_rows = ""
    for idx, item in enumerate(wo.get("items") or [], 1):
        specs = item.get("specifications") or {}
        inspected = []
        if specs.get("pipe_diameter"): inspected.append(f"Pipe Ø{specs['pipe_diameter']}mm")
        if specs.get("pipe_length"): inspected.append(f"L={specs['pipe_length']}mm")
        if specs.get("shaft_diameter"): inspected.append(f"Shaft Ø{specs['shaft_diameter']}mm")
        if specs.get("bearing_number"): inspected.append(f"Brg {specs['bearing_number']}")
        if specs.get("pipe_thickness"): inspected.append(f"Wall {specs['pipe_thickness']}mm")
        item_rows += f"""<tr>
          <td style="text-align:center">{idx}</td>
          <td><b>{item.get('product_name','')}</b><br><span style="color:#960018;font-size:9px">{item.get('product_id','')}</span></td>
          <td style="font-size:10px;color:#475569">{' | '.join(inspected)}</td>
          <td style="text-align:center;font-weight:700">{item.get('quantity',1)}</td>
          <td style="text-align:center">
            <span style="display:inline-block;padding:2px 6px;border-radius:4px;background:{stamp_color}18;color:{stamp_color};font-weight:800;font-size:10px">{stamp_label}</span>
          </td>
        </tr>"""

    qc_by = wo.get("qc_by") or "—"
    qc_at = _format_dmy(wo.get("qc_at")) or "—"
    remarks = (wo.get("qc_remarks") or "").strip() or "No additional observations."

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>QC Report — {wo.get('wo_number','')}</title>
<style>
  @page {{ size: A4; margin: 14mm; }}
  body {{ font-family: -apple-system, Arial, sans-serif; color: #1F2937; font-size: 11px; }}
  .wrap {{ max-width: 800px; margin: 0 auto; position: relative; }}
  .head {{ display: flex; justify-content: space-between; border-bottom: 3px solid #960018; padding-bottom: 10px; margin-bottom: 14px; }}
  .head h1 {{ margin: 0; color: #960018; font-size: 22px; letter-spacing: 1px; }}
  .head .sub {{ color: #64748B; font-size: 10px; margin-top: 2px; }}
  .doc-title {{ text-align: right; }}
  .doc-title .label {{ color: #64748B; font-size: 10px; letter-spacing: 1.5px; }}
  .doc-title h2 {{ margin: 2px 0; font-size: 20px; color: #111; letter-spacing: 1.2px; }}
  .meta-grid {{ display: flex; gap: 12px; margin-bottom: 14px; }}
  .meta-box {{ flex: 1; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; background: #fff; }}
  .meta-box .title {{ color: #960018; font-weight: 700; font-size: 10px; letter-spacing: 1.2px; margin-bottom: 4px; }}
  .meta-row {{ display: flex; justify-content: space-between; margin-bottom: 2px; font-size: 10px; }}
  .meta-row span:first-child {{ color: #64748B; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
  th {{ background: #960018; color: #fff; padding: 8px 6px; font-size: 10px; text-align: left; }}
  td {{ border-bottom: 1px solid #E2E8F0; padding: 7px; font-size: 10px; vertical-align: top; }}
  .verdict {{
    position: absolute; top: 60px; right: 20px;
    border: 4px solid {stamp_color}; color: {stamp_color};
    font-weight: 900; font-size: 28px; letter-spacing: 3px;
    padding: 6px 18px; transform: rotate(-12deg); opacity: 0.85;
    font-family: 'Courier New', monospace;
  }}
  .remarks {{ background: #FFFBEB; border: 1px dashed #F59E0B; padding: 10px; border-radius: 6px; margin-top: 14px; }}
  .remarks b {{ color: #92400E; }}
  .sign {{ display: flex; gap: 18px; margin-top: 40px; }}
  .sign div {{ flex: 1; border-top: 1px solid #64748B; padding-top: 4px; font-size: 10px; color: #64748B; text-align: center; }}
  .footer {{ text-align: center; color: #94A3B8; font-size: 9px; margin-top: 20px; border-top: 1px solid #E2E8F0; padding-top: 6px; }}
</style></head><body><div class="wrap">
  <div class="verdict">{stamp_label}</div>
  <div class="head">
    <div>
      <h1>{COMPANY['name']}</h1>
      <div class="sub">{COMPANY['address']}<br>GSTIN: {COMPANY['gstin']}  |  {COMPANY['email']}</div>
    </div>
    <div class="doc-title">
      <div class="label">QC INSPECTION REPORT</div>
      <h2>{wo.get('wo_number','')}</h2>
      <div style="font-size:10px;color:#64748B">Inspected: <b>{qc_at}</b></div>
    </div>
  </div>

  <div class="meta-grid">
    <div class="meta-box">
      <div class="title">WORK ORDER</div>
      <div class="meta-row"><span>SO Ref.</span><b>{wo.get('so_number','')}</b></div>
      <div class="meta-row"><span>Customer</span><b>{wo.get('customer_name','')}</b></div>
      <div class="meta-row"><span>Stage</span><b>{wo.get('stage','')}</b></div>
    </div>
    <div class="meta-box">
      <div class="title">INSPECTOR</div>
      <div class="meta-row"><span>Inspected By</span><b>{qc_by}</b></div>
      <div class="meta-row"><span>Date & Time</span><b>{qc_at}</b></div>
      <div class="meta-row"><span>Verdict</span><b style="color:{stamp_color}">{stamp_label}</b></div>
    </div>
  </div>

  <table>
    <thead><tr>
      <th style="width:30px;text-align:center">#</th>
      <th>Item / Product Code</th>
      <th>Measured Specifications</th>
      <th style="width:50px;text-align:center">Qty</th>
      <th style="width:80px;text-align:center">Verdict</th>
    </tr></thead>
    <tbody>{item_rows or '<tr><td colspan="5" style="text-align:center;color:#9CA3AF;padding:20px">No items on this WO.</td></tr>'}</tbody>
  </table>

  <div class="remarks"><b>Inspector's Remarks:</b><br>{remarks}</div>

  <div class="sign">
    <div>Quality Inspector<br><span style="font-size:9px">{qc_by if qc_status != 'pending' else ''}</span></div>
    <div>Production Head</div>
    <div>Authorised Signatory<br>(for {COMPANY['name']})</div>
  </div>

  <div class="footer">
    This is a system-generated QC Report. | {COMPANY['name']} | GSTIN: {COMPANY['gstin']}
  </div>
</div></body></html>"""

    output = io.BytesIO(html.encode("utf-8"))
    output.seek(0)
    filename = f"QC-{(wo.get('wo_number','report')).replace('/', '-')}.html"
    return StreamingResponse(
        output, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============= SUB WORK ORDERS (Pipe & Shaft job cards) =============

@router.get("/work-orders/{wo_id}/sub-wos")
async def get_sub_wos(
    wo_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PRODUCTION_HEAD])),
):
    """List Pipe + Shaft sub-work-orders for a parent WO."""
    wo = await db.work_orders.find_one({"$or": [{"id": wo_id}, {"wo_number": wo_id}]}, {"_id": 0, "id": 1, "wo_number": 1})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    subs = await db.sub_work_orders.find({"parent_wo_id": wo.get("id")}, {"_id": 0}).to_list(10)
    # Lazy backfill: if no sub-WOs exist yet for this WO, create them now from the stored WO
    if not subs:
        full_wo = await db.work_orders.find_one({"id": wo.get("id")}, {"_id": 0})
        if full_wo and full_wo.get("items"):
            await _create_sub_wos(full_wo, current_user.get("email"))
            subs = await db.sub_work_orders.find({"parent_wo_id": wo.get("id")}, {"_id": 0}).to_list(10)
    return {"parent_wo_number": wo.get("wo_number"), "sub_work_orders": subs}


@router.get("/wip-qc/overview")
async def get_wip_qc_overview(
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PRODUCTION_HEAD, UserRole.QUALITY_INSPECTOR])),
):
    """Aggregated view of Pipe + Shaft WIP QC status for every Work Order.
    Response: { rows: [ { wo_id, wo_number, customer_name, so_number,
                          delivery_date, stage, pipe: {...}|None, shaft: {...}|None } ] }
    Each pipe/shaft block: { sub_wo_id, sub_wo_number, status: 'pending'|'passed'|'failed',
                             pass_count, fail_count, inspected_by, inspected_at }
    """
    # Pull non-pulley WOs (rollers only); sub-WOs exist only for rollers
    wos = await db.work_orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    subs = await db.sub_work_orders.find({}, {"_id": 0}).to_list(5000)
    sub_by_parent: dict = {}
    for s in subs:
        sub_by_parent.setdefault(s.get("parent_wo_id"), []).append(s)

    def _block(sub: dict | None):
        if not sub:
            return None
        wip = sub.get("wip_qc") or None
        pass_count = 0
        fail_count = 0
        if wip and isinstance(wip.get("items"), list):
            for it in wip["items"]:
                pass_count += int(it.get("pass_count") or 0)
                fail_count += int(it.get("fail_count") or 0)
        status = (wip or {}).get("status") or "pending"
        return {
            "sub_wo_id": sub.get("id"),
            "sub_wo_number": sub.get("sub_wo_number"),
            "status": status,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "inspected_by": (wip or {}).get("inspected_by"),
            "inspected_at": (wip or {}).get("inspected_at"),
        }

    rows = []
    for wo in wos:
        items = wo.get("items") or []
        # Only include WOs that have any non-pulley items (rollers have sub-WOs)
        has_roller = any(not ("pulley" in (it.get("product_name") or "").lower()) for it in items)
        if not has_roller:
            continue
        wo_subs = sub_by_parent.get(wo.get("id")) or []
        pipe = next((s for s in wo_subs if s.get("type") == "pipe"), None)
        shaft = next((s for s in wo_subs if s.get("type") == "shaft"), None)
        rows.append({
            "wo_id": wo.get("id"),
            "wo_number": wo.get("wo_number"),
            "so_number": wo.get("so_number"),
            "customer_name": wo.get("customer_name"),
            "customer_company": wo.get("customer_company"),
            "delivery_date": wo.get("delivery_date"),
            "stage": wo.get("stage"),
            "item_count": len(items),
            "pipe": _block(pipe),
            "shaft": _block(shaft),
        })
    return {"rows": rows}


# ============= WIP QC for Pipe & Shaft sub-WOs =============

class PipeQCSample(BaseModel):
    sample_no: int
    pipe_dia_ok: Optional[bool] = None            # yes/no answer
    pipe_dia_remarks: Optional[str] = None
    pipe_length_measured: Optional[float] = None  # actual length measured
    pipe_length_remarks: Optional[str] = None
    pipe_thickness_measured: Optional[float] = None  # actual thickness measured
    pipe_thickness_remarks: Optional[str] = None


class PipeQCItemRecord(BaseModel):
    item_index: int
    sample_qty: int
    samples: List[PipeQCSample]


class PipeWIPQCRequest(BaseModel):
    items: List[PipeQCItemRecord]


class ShaftQCSample(BaseModel):
    sample_no: int
    shaft_dia_ok: Optional[bool] = None
    shaft_dia_remarks: Optional[str] = None
    shaft_length_measured: Optional[float] = None
    shaft_length_remarks: Optional[str] = None
    slot_width_measured: Optional[float] = None
    slot_width_remarks: Optional[str] = None
    slot_dimension_measured: Optional[float] = None
    slot_dimension_remarks: Optional[str] = None
    slot_third_measured: Optional[float] = None   # Notch (B) or Centre (C)
    slot_third_remarks: Optional[str] = None


class ShaftQCItemRecord(BaseModel):
    item_index: int
    sample_qty: int
    samples: List[ShaftQCSample]


class ShaftWIPQCRequest(BaseModel):
    items: List[ShaftQCItemRecord]


def _evaluate_pipe_sample(sample: dict, required_length: float, required_thickness: float):
    """Return (overall_pass: bool, per_field: dict) for a pipe sample.
    Length tolerance: ±1mm
    Thickness tolerance: ±10%"""
    # Dia check
    dia_ok = bool(sample.get("pipe_dia_ok"))
    # Length
    length_val = sample.get("pipe_length_measured")
    length_ok = False
    if length_val is not None and required_length:
        length_ok = abs(float(length_val) - float(required_length)) <= 1.0
    # Thickness (±10%)
    thk_val = sample.get("pipe_thickness_measured")
    thk_ok = False
    if thk_val is not None and required_thickness:
        tol = float(required_thickness) * 0.10
        thk_ok = abs(float(thk_val) - float(required_thickness)) <= tol
    return (dia_ok and length_ok and thk_ok), {"dia_ok": dia_ok, "length_ok": length_ok, "thk_ok": thk_ok}


def _parse_slot_meta(slot_type: str):
    """Parse shaft end-type string (A, B5, B7, B10, C30, C35 …) into QC metadata.
    Returns: {
      kind: 'A' | 'B' | 'C',
      third_label: None | 'Notch' | 'Centre',
      third_required: None | float,  # mm (derived from numeric suffix)
      third_tol: None | float,       # ± tolerance (0.5 for B, 1.0 for C)
    }
    Slot Width tolerance is always -0.2 / +0 (asymmetric).
    Slot Dimension tolerance is always ±0.5.
    """
    import re as _re
    st = (slot_type or "").strip().upper()
    if not st:
        return {"kind": None, "third_label": None, "third_required": None, "third_tol": None}
    kind = st[0]
    third_required = None
    m = _re.search(r"(\d+(?:\.\d+)?)", st)
    if m:
        try:
            third_required = float(m.group(1))
        except Exception:
            third_required = None
    if kind == "A":
        return {"kind": "A", "third_label": None, "third_required": None, "third_tol": None}
    if kind == "B":
        return {"kind": "B", "third_label": "Notch", "third_required": third_required, "third_tol": 0.5}
    if kind == "C":
        return {"kind": "C", "third_label": "Centre", "third_required": third_required, "third_tol": 1.0}
    return {"kind": kind, "third_label": None, "third_required": None, "third_tol": None}


def _ensure_shaft_slot_details(item: dict) -> dict:
    """Back-compat: older shaft sub-WO items only stored `end_slot` as a display string
    (e.g. "14.0 × 9.0 A" or "12×8 B7"). Parse it into a structured dict if
    `shaft_slot_details` is missing, so QC tolerances can be evaluated."""
    import re as _re
    existing = item.get("shaft_slot_details") or {}
    if existing and existing.get("slot_type"):
        return existing
    s = str(item.get("end_slot") or "").strip()
    if not s or s == "-":
        return existing or {}
    # Normalise separators
    s = s.replace("×", "x").replace("X", "x").replace("*", "x")
    m = _re.match(r"\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*([A-Za-z]\d*)?", s)
    if not m:
        return existing or {}
    width = float(m.group(1))
    dimension = float(m.group(2))
    slot_type = (m.group(3) or "").upper()
    return {"width": width, "dimension": dimension, "slot_type": slot_type}


def _evaluate_shaft_sample(sample: dict, req_dia, req_length: float, slot: dict, slot_meta: dict):
    """Return (overall_pass, flags).
    Length tolerance: ±1mm
    Slot Width tolerance: -0.2 / +0 (i.e. actual must be in [W-0.2, W])
    Slot Dimension tolerance: ±0.5mm
    Third (Notch B = ±0.5, Centre C = ±1.0) when applicable.
    """
    flags = {}
    # Dia Y/N
    dia_ok = bool(sample.get("shaft_dia_ok"))
    flags["dia_ok"] = dia_ok
    # Length ±1
    length_val = sample.get("shaft_length_measured")
    length_ok = False
    if length_val is not None and req_length:
        length_ok = abs(float(length_val) - float(req_length)) <= 1.0
    flags["length_ok"] = length_ok
    overall = dia_ok and length_ok

    req_w = float((slot or {}).get("width") or 0)
    req_d = float((slot or {}).get("dimension") or 0)

    # Width: actual in [req_w - 0.2, req_w] (asymmetric -0.2 / +0)
    w_val = sample.get("slot_width_measured")
    width_ok = False
    if w_val is not None and req_w:
        v = float(w_val)
        width_ok = (v <= req_w) and (v >= req_w - 0.2)
    flags["width_ok"] = width_ok
    overall = overall and width_ok

    # Dimension: ±0.5
    d_val = sample.get("slot_dimension_measured")
    dim_ok = False
    if d_val is not None and req_d:
        dim_ok = abs(float(d_val) - req_d) <= 0.5
    flags["dim_ok"] = dim_ok
    overall = overall and dim_ok

    # Third (Notch/Centre) only when applicable
    if slot_meta and slot_meta.get("third_label") and slot_meta.get("third_required") is not None:
        t_val = sample.get("slot_third_measured")
        t_req = float(slot_meta["third_required"])
        t_tol = float(slot_meta.get("third_tol") or 0.5)
        third_ok = False
        if t_val is not None:
            third_ok = abs(float(t_val) - t_req) <= t_tol
        flags["third_ok"] = third_ok
        overall = overall and third_ok

    return overall, flags


@router.get("/sub-work-orders/{sub_id}/wip-qc")
async def get_sub_wo_wip_qc(
    sub_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PRODUCTION_HEAD, UserRole.QUALITY_INSPECTOR])),
):
    sub = await db.sub_work_orders.find_one({"id": sub_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Sub Work Order not found")
    stype = sub.get("type")
    if stype not in ("pipe", "shaft"):
        raise HTTPException(status_code=400, detail="WIP QC is only supported on Pipe or Shaft sub-WOs")
    payload = {
        "sub_wo_number": sub.get("sub_wo_number"),
        "type": stype,
        "items": sub.get("items", []),
        "wip_qc": sub.get("wip_qc"),
    }
    # For shaft, enrich each item with slot_meta so frontend can render dynamic fields
    if stype == "shaft":
        for it in payload["items"]:
            slot = _ensure_shaft_slot_details(it)
            it["shaft_slot_details"] = slot
            it["slot_meta"] = _parse_slot_meta((slot or {}).get("slot_type") or "")
    return payload


@router.post("/sub-work-orders/{sub_id}/wip-qc")
async def save_sub_wo_wip_qc(
    sub_id: str,
    data: dict,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PRODUCTION_HEAD, UserRole.QUALITY_INSPECTOR])),
):
    sub = await db.sub_work_orders.find_one({"id": sub_id})
    if not sub:
        raise HTTPException(status_code=404, detail="Sub Work Order not found")
    stype = sub.get("type")
    if stype not in ("pipe", "shaft"):
        raise HTTPException(status_code=400, detail="WIP QC is only supported on Pipe or Shaft sub-WOs")

    items_src = sub.get("items") or []
    records_in = (data or {}).get("items") or []
    enriched = []
    any_fail = False

    if stype == "pipe":
        for rec in records_in:
            idx = rec.get("item_index")
            if idx is None or idx < 0 or idx >= len(items_src):
                continue
            src = items_src[idx]
            req_length = float(src.get("pipe_length") or 0)
            req_thk = float(src.get("pipe_thickness") or 0)
            samples_out = []
            pass_count = 0
            for s in rec.get("samples") or []:
                sd = dict(s)
                overall, flags = _evaluate_pipe_sample(sd, req_length, req_thk)
                sd.update(flags)
                sd["overall_pass"] = overall
                samples_out.append(sd)
                if overall: pass_count += 1
                else: any_fail = True
            enriched.append({
                "item_index": idx,
                "sample_qty": int(rec.get("sample_qty") or 0),
                "samples": samples_out,
                "pass_count": pass_count,
                "fail_count": len(samples_out) - pass_count,
                "required_dia": src.get("pipe_diameter"),
                "required_length": req_length,
                "required_thickness": req_thk,
            })
    else:  # shaft
        for rec in records_in:
            idx = rec.get("item_index")
            if idx is None or idx < 0 or idx >= len(items_src):
                continue
            src = items_src[idx]
            req_dia = src.get("shaft_diameter")
            req_length = float(src.get("shaft_length") or 0)
            slot = _ensure_shaft_slot_details(src)
            slot_meta = _parse_slot_meta((slot or {}).get("slot_type") or "")
            samples_out = []
            pass_count = 0
            for s in rec.get("samples") or []:
                sd = dict(s)
                overall, flags = _evaluate_shaft_sample(sd, req_dia, req_length, slot, slot_meta)
                sd.update(flags)
                sd["overall_pass"] = overall
                samples_out.append(sd)
                if overall: pass_count += 1
                else: any_fail = True
            enriched.append({
                "item_index": idx,
                "sample_qty": int(rec.get("sample_qty") or 0),
                "samples": samples_out,
                "pass_count": pass_count,
                "fail_count": len(samples_out) - pass_count,
                "required_dia": req_dia,
                "required_length": req_length,
                "required_slot_width": slot.get("width"),
                "required_slot_dimension": slot.get("dimension"),
                "slot_type": slot.get("slot_type"),
                "slot_meta": slot_meta,
            })

    now = datetime.now(timezone.utc).isoformat()
    wip_qc = {
        "items": enriched,
        "status": "failed" if any_fail else "passed",
        "inspected_by": current_user.get("email"),
        "inspected_at": now,
        "type": stype,
    }
    await db.sub_work_orders.update_one(
        {"_id": sub["_id"]},
        {"$set": {"wip_qc": wip_qc}},
    )
    label = "Pipe" if stype == "pipe" else "Shaft"
    return {"message": f"{label} WIP QC saved — status: {wip_qc['status'].upper()}", "wip_qc": wip_qc}


def _render_sub_wo_pdf(sub: dict) -> str:
    """Render an A4 HTML job card for a pipe or shaft sub-WO."""
    sub_type = sub.get("type", "pipe")
    title = "PIPE PROCESS JOB CARD" if sub_type == "pipe" else "SHAFT PROCESS JOB CARD"
    accent = "#960018" if sub_type == "pipe" else "#0F766E"
    subtitle = "Pipe Cutting & Housing Assembly" if sub_type == "pipe" else "Shaft Turning, Slotting & Bearing Fitment"
    items = sub.get("items") or []

    # Build header row and body rows by type
    if sub_type == "pipe":
        headers = ["#", "Product", "Drawing", "Pipe OD (mm)", "Wall Thk (mm)", "Pipe Length (mm)", "Qty", "Housing (CRC)", "Housing Qty"]
        rows = ""
        for i, it in enumerate(items, 1):
            rows += f"""<tr>
                <td style="text-align:center">{i}</td>
                <td><b>{it.get('product_name','')}</b><br><span style="color:#64748B;font-size:10px">{it.get('product_code','')}</span></td>
                <td style="text-align:center;font-weight:700;color:{accent}">{it.get('drawing_number') or '-'}</td>
                <td style="text-align:center;font-weight:700">{it.get('pipe_diameter','-')}</td>
                <td style="text-align:center">{it.get('pipe_thickness') or '-'}</td>
                <td style="text-align:center;font-weight:700">{it.get('pipe_length','-')}</td>
                <td style="text-align:center;font-weight:700">{it.get('quantity',1)}</td>
                <td style="text-align:center;font-weight:700;color:{accent}">{it.get('housing_number','-')}</td>
                <td style="text-align:center;font-weight:700">{it.get('housing_qty','-')}</td>
            </tr>"""
    else:
        headers = ["#", "Product", "Drawing", "Shaft Dia (mm)", "Shaft Length (mm)", "End Slot (W×D T)", "Qty", "Bearing", "Bearing Qty"]
        rows = ""
        for i, it in enumerate(items, 1):
            brg = it.get('bearing_number','-')
            mk = it.get('bearing_make','')
            rows += f"""<tr>
                <td style="text-align:center">{i}</td>
                <td><b>{it.get('product_name','')}</b><br><span style="color:#64748B;font-size:10px">{it.get('product_code','')}</span></td>
                <td style="text-align:center;font-weight:700;color:{accent}">{it.get('drawing_number') or '-'}</td>
                <td style="text-align:center;font-weight:700">{it.get('shaft_diameter','-')}</td>
                <td style="text-align:center;font-weight:700">{it.get('shaft_length','-')}</td>
                <td style="text-align:center">{it.get('end_slot','-')}</td>
                <td style="text-align:center;font-weight:700">{it.get('quantity',1)}</td>
                <td style="text-align:center;font-weight:700;color:{accent}">{brg}<br><span style="font-size:9px;color:#64748B;font-weight:400">{mk}</span></td>
                <td style="text-align:center;font-weight:700">{it.get('bearing_qty','-')}</td>
            </tr>"""

    header_html = "".join(f'<th style="padding:8px;background:{accent};color:#fff;font-size:11px;font-weight:700;border:1px solid #fff">{h}</th>' for h in headers)

    po_html = f'<span>PO: <b>{sub.get("customer_po_number","-")}</b> &nbsp;·&nbsp; Date: {sub.get("customer_po_date","-")}</span>' if sub.get('customer_po_number') else ''
    delivery_html = f'<span style="color:{accent};font-weight:700">Delivery: {sub.get("delivery_date","-")}</span>' if sub.get('delivery_date') else ''

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{sub.get('sub_wo_number','')}</title>
<style>
@page {{ size: A4; margin: 12mm; }}
body {{ font-family: 'Helvetica', sans-serif; margin:0; padding:0; color:#0F172A; }}
.page {{ padding: 8mm; }}
.banner {{ background: {accent}; color: #fff; padding: 14px 18px; border-radius: 6px; }}
.banner h1 {{ margin: 0; font-size: 22px; letter-spacing: 1.5px; }}
.banner .sub {{ font-size: 11px; opacity: 0.9; letter-spacing: 0.5px; }}
.banner .num {{ position: absolute; right: 24px; top: 18px; font-size: 14px; background: rgba(255,255,255,0.18); padding: 6px 14px; border-radius: 20px; font-weight: 700; letter-spacing: 1px; }}
.meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 14px 0; }}
.meta {{ background: #F8FAFC; border-left: 3px solid {accent}; padding: 8px 12px; border-radius: 4px; }}
.meta .k {{ font-size: 9px; color: #64748B; letter-spacing: 0.5px; text-transform: uppercase; }}
.meta .v {{ font-size: 13px; font-weight: 700; color: #0F172A; margin-top: 2px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }}
td {{ padding: 8px; border: 1px solid #CBD5E1; vertical-align: top; }}
.instructions {{ background: #FFFBEB; border: 1px dashed #F59E0B; padding: 10px 14px; border-radius: 6px; margin-top: 16px; font-size: 11px; color: #92400E; }}
.instructions b {{ color: #78350F; }}
.sig-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 45px; padding-top: 14px; }}
.sig {{ border-top: 2px dashed #94A3B8; padding-top: 8px; font-size: 11px; text-align: center; color: #475569; font-weight: 600; }}
.footer {{ font-size: 9px; color: #94A3B8; text-align: center; margin-top: 20px; padding-top: 8px; border-top: 1px solid #E2E8F0; }}
</style></head><body><div class="page">
  <div class="banner" style="position:relative">
    <h1>{title}</h1>
    <div class="sub">{subtitle}</div>
    <div class="num">{sub.get('sub_wo_number','')}</div>
  </div>
  <div class="meta-grid">
    <div class="meta"><div class="k">Parent WO</div><div class="v">{sub.get('parent_wo_number','-')}</div></div>
    <div class="meta"><div class="k">Sales Order</div><div class="v">{sub.get('so_number','-')}</div></div>
    <div class="meta"><div class="k">Customer</div><div class="v">{sub.get('customer_name','-')}{('<br><span style="font-size:10px;font-weight:400;color:#64748B">'+sub.get('customer_company','')+'</span>') if sub.get('customer_company') else ''}</div></div>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:11px;color:#475569;margin-bottom:8px">{po_html}{delivery_html}</div>
  <table>
    <thead><tr>{header_html}</tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="instructions">
    <b>Shop-floor instructions:</b>
    {'Cut pipes to the exact length shown. Check OD and wall thickness against drawing. Pair with the specified CRC Housing (press-fit). Deburr and inspect weld seams before next station.' if sub_type=='pipe' else 'Turn shaft to the exact diameter ±0.05mm. Cut to length. Mill end slot as per drawing (Width × Depth × Type). Install bearing at both ends with the specified make. Check rotation before hand-over.'}
  </div>
  <div class="sig-row">
    <div class="sig">Issued By (Production Head)</div>
    <div class="sig">{'Pipe' if sub_type=='pipe' else 'Shaft'} Operator</div>
    <div class="sig">QC Verified</div>
  </div>
  <div class="footer">{COMPANY['name']} | {COMPANY['email']} | {COMPANY['phone']}</div>
</div></body></html>"""
    return html


@router.get("/sub-work-orders/{sub_id}/pdf")
async def sub_wo_pdf(sub_id: str, token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """A4 printable job card for Pipe or Shaft sub-WO."""
    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization[7:]
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    sub = await db.sub_work_orders.find_one({"id": sub_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Sub Work Order not found")

    html = _render_sub_wo_pdf(sub)
    output = io.BytesIO(html.encode('utf-8'))
    output.seek(0)
    filename = f"{sub.get('sub_wo_number','sub').replace('/', '-')}-JobCard.html"
    return StreamingResponse(output, media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"})


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


@router.post("/orders/{order_id}/create-work-order")
async def bulk_create_work_order(
    order_id: str,
    data: BulkCreateWorkOrder,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Single click: set production details for all items + auto-generate BOM + create Work Order"""
    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    existing = await db.work_orders.find_one({"order_id": order.get("id")})
    if existing:
        raise HTTPException(status_code=400, detail=f"Work Order already exists: {existing['wo_number']}")

    products = order.get("products", [])

    # Step 1: Apply production details to all items
    for item_data in data.items:
        idx = item_data.item_index
        if idx < 0 or idx >= len(products):
            raise HTTPException(status_code=400, detail=f"Invalid item index: {idx}")
        products[idx]["production_details"] = {
            "drawing_number": item_data.drawing_number,
            "drawing_base64": item_data.drawing_base64,
            "drawing_filename": item_data.drawing_filename,
            "paint_details": item_data.paint_details,
            "shaft_length": item_data.shaft_length,
            "shaft_slot": item_data.shaft_slot.dict() if item_data.shaft_slot else None,
            "production_notes": item_data.production_notes,
        }

    # Step 2: Validate all items have required fields
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

    # Step 3: Save production details to SO
    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"products": products, "updated_at": get_ist_now().isoformat()}}
    )

    # Step 4: Build WO items with BOM
    now = get_ist_now()
    wo_number = await generate_wo_number()

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

    # Get paint spec from quote commercial terms if not provided
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
        "items": wo_items,
        "ral_code": data.ral_code or "",
        "paint_type": data.paint_type or "",
        "paint_spec": paint_spec,
        "stage": "created",
        "stage_history": [{"stage": "created", "timestamp": now.isoformat(), "by": current_user.get("email"), "notes": f"Created from {order.get('so_number')} with {len(wo_items)} items"}],
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.work_orders.insert_one(work_order)
    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"work_order": wo_number, "updated_at": now.isoformat()}}
    )

    del work_order["_id"]
    return {"message": f"Work Order {wo_number} created with {len(wo_items)} items", "work_order": work_order}

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
                "qty_per_unit": 1, "total_qty": qty,
                "weight_per_unit_kg": shaft_wt, "total_weight_kg": round(shaft_wt * qty, 3),
            })

        # 3. Bearing — number + make
        if bearing_number:
            make_label = (bearing_make or "china").upper()
            bom.append({
                "component": "Bearing",
                "description": f"{bearing_number} ZZ - {make_label} (OD: {bearing_od}mm)",
                "material": f"{bearing_number} - {make_label}",
                "qty_per_unit": 2, "total_qty": qty * 2,
                "weight_per_unit_kg": 0, "total_weight_kg": 0,
            })

        # 4. Housing — with size (housing_dia/bearing_OD)
        if housing_size:
            bom.append({
                "component": "Housing",
                "description": f"Housing {housing_size} for {pipe_dia}mm pipe",
                "material": f"CRC Housing {housing_size}",
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
            "qty_per_unit": 2, "total_qty": qty * 2,
            "weight_per_unit_kg": 0, "total_weight_kg": 0,
        })

        # 6. Circlip — A{shaft_dia}
        circlip_num = f"A{shaft_dia}" if shaft_dia else "Circlip"
        bom.append({
            "component": "Circlip",
            "description": f"{circlip_num} for {shaft_dia}mm shaft",
            "material": f"Spring Steel {circlip_num}",
            "qty_per_unit": 4, "total_qty": qty * 4,
            "weight_per_unit_kg": 0, "total_weight_kg": 0,
        })

        # 7. Grease
        bom.append({
            "component": "Grease",
            "description": "Bearing grease",
            "material": "EP2 Grease",
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
            ring_desc = f"{ring_id}mm ID x {rubber_dia}mm OD x {ring_width}mm thk" if rubber_dia else f"{ring_id}mm ID x {ring_width}mm thk"
            bom.append({
                "component": "Rubber Ring",
                "description": f"{ring_desc} — {ring_qty} nos/roller",
                "material": "Natural Rubber",
                "qty_per_unit": ring_qty, "total_qty": qty * ring_qty,
                "weight_per_unit_kg": 0, "total_weight_kg": 0,
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

"""Inventory/Store Routes — Stock management, Purchase Orders, QC, Issue, Alerts"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from bson import ObjectId
from routes import db, get_current_user, require_role, get_ist_now, get_financial_year, UserRole, format_date_dmy
import logging

router = APIRouter(prefix="/store")

STOCK_CATEGORIES = ["pipe", "shaft", "bearing", "housing", "seal", "circlip", "end_plate", "hub", "rubber_ring", "rubber_lagging", "grease", "paint", "other"]
PO_STATUSES = ["draft", "ordered", "partial_received", "received", "cancelled"]
QC_STATUSES = ["pending", "passed", "failed", "partial"]


# ============= MODELS =============

class StockItemCreate(BaseModel):
    name: str  # e.g., "Pipe 114.3mm x 4.5mm"
    category: str  # pipe, shaft, bearing, etc.
    unit_purchase: str = "meters"  # meters, kg, nos, sqm, litres
    unit_bom: str = "kg"  # kg, nos, sqm
    conversion_factor: float = 1.0  # purchase_unit × factor = bom_unit (e.g., meters × density = kg)
    current_stock: float = 0
    reorder_level: float = 0
    specifications: Optional[Dict[str, Any]] = None  # dia, thickness, material, bearing_no etc.


class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    items: List[Dict[str, Any]]  # [{stock_item_id, qty, rate, unit}]
    notes: Optional[str] = None
    expected_delivery: Optional[str] = None


class QCEntry(BaseModel):
    po_id: str
    item_index: int
    status: str  # passed, failed, partial
    accepted_qty: float = 0
    rejected_qty: float = 0
    reason: Optional[str] = None


class StockIssue(BaseModel):
    wo_id: str
    items: List[Dict[str, Any]]  # [{stock_item_id, qty, notes}]


# ============= HELPERS =============

async def generate_po_number():
    fy = get_financial_year()
    prefix = f"PO/{fy}/"
    last = await db.purchase_orders.find({"po_number": {"$regex": f"^{prefix}"}}, {"po_number": 1}).sort("po_number", -1).limit(1).to_list(1)
    if last:
        num = int(last[0]["po_number"].split("/")[-1])
        return f"{prefix}{num + 1:04d}"
    return f"{prefix}0001"


# ============= STOCK ITEMS =============

@router.get("/items")
async def get_stock_items(category: Optional[str] = None, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    query = {}
    if category:
        query["category"] = category
    items = await db.stock_items.find(query, {"_id": 0}).sort("category", 1).to_list(1000)
    return {"items": items, "total": len(items)}


@router.post("/items")
async def create_stock_item(item: StockItemCreate, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    now = get_ist_now()
    doc = item.dict()
    doc.update({"id": str(ObjectId()), "created_by": current_user.get("email"), "created_at": now.isoformat()})
    await db.stock_items.insert_one(doc)
    del doc["_id"]
    return {"message": "Stock item created", "item": doc}


@router.put("/items/{item_id}")
async def update_stock_item(item_id: str, item: StockItemCreate, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    result = await db.stock_items.update_one({"id": item_id}, {"$set": {**item.dict(), "updated_at": get_ist_now().isoformat()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return {"message": "Stock item updated"}


@router.delete("/items/{item_id}")
async def delete_stock_item(item_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    result = await db.stock_items.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return {"message": "Stock item deleted"}


# ============= PURCHASE ORDERS =============

@router.get("/purchase-orders")
async def get_purchase_orders(status: Optional[str] = None, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    query = {}
    if status:
        query["status"] = status
    pos = await db.purchase_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Enrich with supplier name
    for po in pos:
        supplier = await db.suppliers_master.find_one({"id": po.get("supplier_id")}, {"_id": 0, "name": 1})
        po["supplier_name"] = supplier.get("name") if supplier else "Unknown"
    return {"purchase_orders": pos, "total": len(pos)}


@router.post("/purchase-orders")
async def create_purchase_order(po: PurchaseOrderCreate, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    now = get_ist_now()
    po_number = await generate_po_number()

    # Enrich items with stock item names
    items = []
    total_amount = 0
    for item in po.items:
        stock_item = await db.stock_items.find_one({"id": item.get("stock_item_id")}, {"_id": 0})
        qty = item.get("qty", 0)
        rate = item.get("rate", 0)
        amount = qty * rate
        total_amount += amount
        items.append({
            "stock_item_id": item.get("stock_item_id"),
            "stock_item_name": stock_item.get("name") if stock_item else "Unknown",
            "category": stock_item.get("category") if stock_item else "",
            "qty_ordered": qty,
            "rate": rate,
            "unit": item.get("unit", stock_item.get("unit_purchase", "nos") if stock_item else "nos"),
            "amount": round(amount, 2),
            "qty_received": 0,
            "qty_accepted": 0,
            "qty_rejected": 0,
            "qc_status": "pending",
        })

    doc = {
        "id": str(ObjectId()),
        "po_number": po_number,
        "supplier_id": po.supplier_id,
        "items": items,
        "total_amount": round(total_amount, 2),
        "status": "ordered",
        "notes": po.notes,
        "expected_delivery": po.expected_delivery,
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
    }
    await db.purchase_orders.insert_one(doc)
    del doc["_id"]
    return {"message": f"Purchase Order {po_number} created", "purchase_order": doc}


# ============= QC (Quality Check) =============

@router.post("/qc")
async def process_qc(qc: QCEntry, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    po = await db.purchase_orders.find_one({"id": qc.po_id})
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    items = po.get("items", [])
    if qc.item_index < 0 or qc.item_index >= len(items):
        raise HTTPException(status_code=400, detail="Invalid item index")

    now = get_ist_now()
    item = items[qc.item_index]
    item["qc_status"] = qc.status
    item["qty_received"] = qc.accepted_qty + qc.rejected_qty
    item["qty_accepted"] = qc.accepted_qty
    item["qty_rejected"] = qc.rejected_qty
    item["qc_reason"] = qc.reason
    item["qc_by"] = current_user.get("email")
    item["qc_at"] = now.isoformat()

    # If QC passed/partial, add accepted qty to stock
    if qc.accepted_qty > 0:
        stock_item = await db.stock_items.find_one({"id": item.get("stock_item_id")})
        if stock_item:
            new_stock = stock_item.get("current_stock", 0) + qc.accepted_qty
            await db.stock_items.update_one({"id": item["stock_item_id"]}, {"$set": {"current_stock": round(new_stock, 3)}})

            # Log transaction
            await db.stock_transactions.insert_one({
                "id": str(ObjectId()),
                "stock_item_id": item["stock_item_id"],
                "stock_item_name": item.get("stock_item_name"),
                "type": "in",
                "qty": qc.accepted_qty,
                "reference": f"PO: {po.get('po_number')} (QC {qc.status})",
                "po_id": qc.po_id,
                "by": current_user.get("email"),
                "at": now.isoformat(),
            })

    # Update PO status
    all_qc = all(i.get("qc_status") in ["passed", "failed"] for i in items)
    any_received = any(i.get("qty_accepted", 0) > 0 for i in items)
    if all_qc:
        po_status = "received"
    elif any_received:
        po_status = "partial_received"
    else:
        po_status = "ordered"

    await db.purchase_orders.update_one({"_id": po["_id"]}, {"$set": {"items": items, "status": po_status, "updated_at": now.isoformat()}})

    return {"message": f"QC processed: {qc.status} ({qc.accepted_qty} accepted, {qc.rejected_qty} rejected)"}


# ============= STOCK ISSUE (against Work Order) =============

@router.post("/issue")
async def issue_stock(issue: StockIssue, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    wo = await db.work_orders.find_one({"id": issue.wo_id}, {"_id": 0, "wo_number": 1})
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    now = get_ist_now()
    issued_items = []
    insufficient = []

    for item in issue.items:
        stock_item = await db.stock_items.find_one({"id": item.get("stock_item_id")})
        if not stock_item:
            continue

        qty = item.get("qty", 0)
        current = stock_item.get("current_stock", 0)

        if current < qty:
            insufficient.append(f"{stock_item.get('name')}: need {qty}, have {current}")
            continue

        # Deduct stock
        new_stock = current - qty
        await db.stock_items.update_one({"id": item["stock_item_id"]}, {"$set": {"current_stock": round(new_stock, 3)}})

        # Log transaction
        await db.stock_transactions.insert_one({
            "id": str(ObjectId()),
            "stock_item_id": item["stock_item_id"],
            "stock_item_name": stock_item.get("name"),
            "type": "out",
            "qty": qty,
            "reference": f"WO: {wo.get('wo_number')}",
            "wo_id": issue.wo_id,
            "notes": item.get("notes", ""),
            "by": current_user.get("email"),
            "at": now.isoformat(),
        })

        issued_items.append({"name": stock_item.get("name"), "qty": qty})

    if insufficient:
        raise HTTPException(status_code=400, detail=f"Insufficient stock: {'; '.join(insufficient)}")

    return {"message": f"{len(issued_items)} items issued against {wo.get('wo_number')}", "issued": issued_items}


# ============= STOCK TRANSACTIONS LOG =============

@router.get("/transactions")
async def get_transactions(stock_item_id: Optional[str] = None, type: Optional[str] = None, limit: int = 100, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    query = {}
    if stock_item_id:
        query["stock_item_id"] = stock_item_id
    if type:
        query["type"] = type
    txns = await db.stock_transactions.find(query, {"_id": 0}).sort("at", -1).to_list(limit)
    return {"transactions": txns, "total": len(txns)}


# ============= LOW STOCK ALERTS =============

@router.get("/alerts")
async def get_low_stock_alerts(current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    # Find items where current_stock <= reorder_level
    items = await db.stock_items.find({"reorder_level": {"$gt": 0}}, {"_id": 0}).to_list(1000)
    alerts = []
    for item in items:
        if item.get("current_stock", 0) <= item.get("reorder_level", 0):
            alerts.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "category": item.get("category"),
                "current_stock": item.get("current_stock", 0),
                "reorder_level": item.get("reorder_level", 0),
                "deficit": round(item.get("reorder_level", 0) - item.get("current_stock", 0), 3),
                "unit": item.get("unit_purchase"),
            })
    return {"alerts": alerts, "total": len(alerts)}


# ============= STORE DASHBOARD =============

@router.get("/dashboard")
async def get_store_dashboard(current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    total_items = await db.stock_items.count_documents({})
    total_pos = await db.purchase_orders.count_documents({})
    pending_pos = await db.purchase_orders.count_documents({"status": {"$in": ["ordered", "partial_received"]}})

    # Low stock count
    items = await db.stock_items.find({"reorder_level": {"$gt": 0}}, {"_id": 0, "current_stock": 1, "reorder_level": 1}).to_list(1000)
    low_stock_count = sum(1 for i in items if i.get("current_stock", 0) <= i.get("reorder_level", 0))

    # Category counts
    pipeline = [{"$group": {"_id": "$category", "count": {"$sum": 1}, "total_value": {"$sum": "$current_stock"}}}]
    categories = await db.stock_items.aggregate(pipeline).to_list(20)

    # Recent transactions
    recent = await db.stock_transactions.find({}, {"_id": 0}).sort("at", -1).to_list(10)

    return {
        "total_items": total_items,
        "total_pos": total_pos,
        "pending_pos": pending_pos,
        "low_stock_alerts": low_stock_count,
        "categories": {c["_id"]: c["count"] for c in categories if c["_id"]},
        "recent_transactions": recent,
    }


# ============= OPTIONS =============

@router.get("/options")
async def get_store_options(current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    return {
        "categories": STOCK_CATEGORIES,
        "po_statuses": PO_STATUSES,
        "qc_statuses": QC_STATUSES,
        "units": ["meters", "kg", "nos", "sqm", "litres", "sets"],
    }

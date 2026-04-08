"""Sales Order Routes — Convert quotes to orders, order tracking, payment, invoicing"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from routes import (db, get_current_user, require_role, get_ist_now, get_financial_year,
                    UserRole, GMAIL_USER, GMAIL_APP_PASSWORD)
import logging

router = APIRouter()

# ============= MODELS =============

ORDER_STAGES = ["confirmed", "in_production", "ready", "dispatched", "delivered"]
PAYMENT_STATUSES = ["unpaid", "partial", "paid"]
PAYMENT_MODES = ["bank_transfer", "cheque", "cash", "upi", "other"]

class PaymentCreate(BaseModel):
    amount: float
    mode: str = "bank_transfer"
    reference: Optional[str] = None  # UTR/cheque no
    notes: Optional[str] = None


class OrderStageUpdate(BaseModel):
    stage: str
    notes: Optional[str] = None


# ============= HELPERS =============

async def generate_so_number():
    fy = get_financial_year()
    prefix = f"SO/{fy}/"
    last = await db.sales_orders.find(
        {"so_number": {"$regex": f"^{prefix}"}}, {"so_number": 1}
    ).sort("so_number", -1).limit(1).to_list(1)
    if last:
        num = int(last[0]["so_number"].split("/")[-1])
        return f"{prefix}{num + 1:04d}"
    return f"{prefix}0001"


async def generate_invoice_number(doc_type="INV"):
    fy = get_financial_year()
    prefix = f"{doc_type}/{fy}/"
    last = await db.invoices.find(
        {"invoice_number": {"$regex": f"^{prefix}"}}, {"invoice_number": 1}
    ).sort("invoice_number", -1).limit(1).to_list(1)
    if last:
        num = int(last[0]["invoice_number"].split("/")[-1])
        return f"{prefix}{num + 1:04d}"
    return f"{prefix}0001"


# ============= SALES ORDER ROUTES =============

@router.post("/orders/from-quote/{quote_id}")
async def convert_quote_to_order(quote_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Convert an approved quote to a Sales Order"""
    # Try to find quote by various ID formats
    query_filters = [{"quote_number": quote_id}]
    try:
        query_filters.append({"_id": ObjectId(quote_id)})
    except:
        pass
    quote = await db.quotes.find_one({"$or": query_filters})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved quotes can be converted to Sales Orders")

    # Check if already converted
    existing = await db.sales_orders.find_one({"quote_id": str(quote.get("_id", quote.get("id")))})
    if existing:
        raise HTTPException(status_code=400, detail=f"Already converted to SO: {existing['so_number']}")

    now = get_ist_now()
    so_number = await generate_so_number()
    quote_id_str = str(quote.get("_id", quote.get("id")))

    order = {
        "id": str(ObjectId()),
        "so_number": so_number,
        "quote_id": quote_id_str,
        "quote_number": quote.get("quote_number"),
        "original_rfq_number": quote.get("original_rfq_number"),
        "customer_name": quote.get("customer_name"),
        "customer_email": quote.get("customer_email"),
        "customer_company": quote.get("customer_company"),
        "customer_code": quote.get("customer_code"),
        "customer_details": quote.get("customer_details"),
        "products": quote.get("products", []),
        "subtotal": quote.get("subtotal", 0),
        "discount_percent": quote.get("discount_percent", 0),
        "total_discount": quote.get("total_discount", 0),
        "packing_charges": quote.get("packing_charges", 0),
        "packing_type": quote.get("packing_type"),
        "shipping_cost": quote.get("shipping_cost", 0),
        "freight_details": quote.get("freight_details"),
        "total_price": quote.get("total_price", 0),
        "commercial_terms": quote.get("commercial_terms"),
        "stage": "confirmed",
        "payment_status": "unpaid",
        "payments": [],
        "total_paid": 0,
        "balance_due": quote.get("total_price", 0),
        "proforma_invoice": None,
        "tax_invoice": None,
        "notes": None,
        "stage_history": [{
            "stage": "confirmed",
            "timestamp": now.isoformat(),
            "by": current_user.get("email"),
            "notes": f"Converted from {quote.get('quote_number')}"
        }],
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    await db.sales_orders.insert_one(order)
    # Update quote to mark as converted
    await db.quotes.update_one(
        {"_id": quote["_id"]},
        {"$set": {"converted_to_so": so_number, "updated_at": datetime.utcnow()}}
    )

    del order["_id"]
    return {"message": f"Sales Order {so_number} created", "order": order}


@router.get("/orders")
async def get_orders(
    stage: Optional[str] = None,
    payment_status: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    query = {}
    if stage:
        query["stage"] = stage
    if payment_status:
        query["payment_status"] = payment_status

    orders = await db.sales_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"orders": orders, "total": len(orders)}


@router.get("/orders/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    order = await db.sales_orders.find_one(
        {"$or": [{"id": order_id}, {"so_number": order_id}]}, {"_id": 0}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/orders/{order_id}/stage")
async def update_order_stage(order_id: str, update: OrderStageUpdate, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if update.stage not in ORDER_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of {ORDER_STAGES}")

    now = get_ist_now()
    stage_entry = {
        "stage": update.stage,
        "timestamp": now.isoformat(),
        "by": current_user.get("email"),
        "notes": update.notes,
    }

    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {
            "$set": {"stage": update.stage, "updated_at": now.isoformat()},
            "$push": {"stage_history": stage_entry}
        }
    )
    return {"message": f"Order stage updated to {update.stage}"}


# ============= PAYMENT ROUTES =============

@router.post("/orders/{order_id}/payments")
async def add_payment(order_id: str, payment: PaymentCreate, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    now = get_ist_now()
    payment_entry = {
        "id": str(ObjectId()),
        "amount": payment.amount,
        "mode": payment.mode,
        "reference": payment.reference,
        "notes": payment.notes,
        "recorded_by": current_user.get("email"),
        "recorded_at": now.isoformat(),
    }

    new_total_paid = order.get("total_paid", 0) + payment.amount
    total_price = order.get("total_price", 0)
    new_balance = total_price - new_total_paid
    new_status = "paid" if new_balance <= 0 else ("partial" if new_total_paid > 0 else "unpaid")

    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {
            "$push": {"payments": payment_entry},
            "$set": {
                "total_paid": round(new_total_paid, 2),
                "balance_due": round(max(new_balance, 0), 2),
                "payment_status": new_status,
                "updated_at": now.isoformat(),
            }
        }
    )
    return {"message": f"Payment of Rs.{payment.amount} recorded", "payment_status": new_status, "balance_due": round(max(new_balance, 0), 2)}


# ============= INVOICE ROUTES =============

@router.post("/orders/{order_id}/proforma")
async def generate_proforma(order_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    now = get_ist_now()
    pi_number = await generate_invoice_number("PI")

    invoice = {
        "id": str(ObjectId()),
        "invoice_number": pi_number,
        "invoice_type": "proforma",
        "order_id": order.get("id"),
        "so_number": order.get("so_number"),
        "customer_name": order.get("customer_name"),
        "customer_details": order.get("customer_details"),
        "products": order.get("products"),
        "subtotal": order.get("subtotal"),
        "total_discount": order.get("total_discount"),
        "packing_charges": order.get("packing_charges"),
        "shipping_cost": order.get("shipping_cost"),
        "total_price": order.get("total_price"),
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
    }

    await db.invoices.insert_one(invoice)
    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"proforma_invoice": pi_number, "updated_at": now.isoformat()}}
    )

    del invoice["_id"]
    return {"message": f"Proforma Invoice {pi_number} generated", "invoice": invoice}


@router.post("/orders/{order_id}/tax-invoice")
async def generate_tax_invoice(order_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    now = get_ist_now()
    inv_number = await generate_invoice_number("INV")

    # GST calc (18%)
    taxable = order.get("total_price", 0)
    cgst = round(taxable * 0.09, 2)
    sgst = round(taxable * 0.09, 2)
    total_with_gst = round(taxable + cgst + sgst, 2)

    invoice = {
        "id": str(ObjectId()),
        "invoice_number": inv_number,
        "invoice_type": "tax",
        "order_id": order.get("id"),
        "so_number": order.get("so_number"),
        "customer_name": order.get("customer_name"),
        "customer_company": order.get("customer_company"),
        "customer_code": order.get("customer_code"),
        "customer_details": order.get("customer_details"),
        "products": order.get("products"),
        "subtotal": order.get("subtotal"),
        "total_discount": order.get("total_discount"),
        "packing_charges": order.get("packing_charges"),
        "shipping_cost": order.get("shipping_cost"),
        "taxable_amount": taxable,
        "cgst_rate": 9, "cgst_amount": cgst,
        "sgst_rate": 9, "sgst_amount": sgst,
        "total_gst": round(cgst + sgst, 2),
        "total_with_gst": total_with_gst,
        "hsn_code": "8431",
        "total_price": order.get("total_price"),
        "payment_status": order.get("payment_status"),
        "total_paid": order.get("total_paid"),
        "balance_due": order.get("balance_due"),
        "created_by": current_user.get("email"),
        "created_at": now.isoformat(),
    }

    await db.invoices.insert_one(invoice)
    await db.sales_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"tax_invoice": inv_number, "updated_at": now.isoformat()}}
    )

    del invoice["_id"]
    return {"message": f"Tax Invoice {inv_number} generated", "invoice": invoice}


@router.get("/invoices")
async def get_invoices(
    invoice_type: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    query = {}
    if invoice_type:
        query["invoice_type"] = invoice_type
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"invoices": invoices, "total": len(invoices)}


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    invoice = await db.invoices.find_one(
        {"$or": [{"id": invoice_id}, {"invoice_number": invoice_id}]}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


# ============= ORDER SUMMARY =============

@router.get("/orders/summary/stats")
async def get_order_stats(current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    pipeline_stage = [{"$group": {"_id": "$stage", "count": {"$sum": 1}, "value": {"$sum": "$total_price"}}}]
    stage_stats = await db.sales_orders.aggregate(pipeline_stage).to_list(10)

    pipeline_payment = [{"$group": {"_id": "$payment_status", "count": {"$sum": 1}, "value": {"$sum": "$balance_due"}}}]
    payment_stats = await db.sales_orders.aggregate(pipeline_payment).to_list(10)

    total_orders = await db.sales_orders.count_documents({})
    total_invoices = await db.invoices.count_documents({"invoice_type": "tax"})

    return {
        "total_orders": total_orders,
        "total_invoices": total_invoices,
        "by_stage": {s["_id"]: {"count": s["count"], "value": s["value"]} for s in stage_stats},
        "by_payment": {s["_id"]: {"count": s["count"], "outstanding": s["value"]} for s in payment_stats},
    }

"""Sales Order Routes — Convert quotes to orders, order tracking, payment, invoicing"""
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from routes import (db, get_current_user, require_role, get_ist_now, get_financial_year,
                    UserRole, GMAIL_USER, GMAIL_APP_PASSWORD, SECRET_KEY, ALGORITHM,
                    format_date_dmy)
from jose import jwt
import logging
import io
import os

router = APIRouter()

# Company details from env
COMPANY = {
    "name": os.environ.get("COMPANY_NAME", "CONVERO SOLUTIONS"),
    "address": os.environ.get("COMPANY_ADDRESS", ""),
    "email": os.environ.get("COMPANY_EMAIL", "Info@convero.in"),
    "website": os.environ.get("COMPANY_WEBSITE", "www.convero.in"),
    "phone": os.environ.get("COMPANY_PHONE", ""),
    "gstin": os.environ.get("COMPANY_GSTIN", ""),
    "bank_name": os.environ.get("COMPANY_BANK_NAME", ""),
    "bank_account": os.environ.get("COMPANY_BANK_ACCOUNT", ""),
    "bank_ifsc": os.environ.get("COMPANY_BANK_IFSC", ""),
    "bank_branch": os.environ.get("COMPANY_BANK_BRANCH", ""),
    "hsn_code": os.environ.get("COMPANY_HSN_CODE", "84313910"),
}

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
    from routes import _next_seq, _max_suffix, format_number
    seed = await _max_suffix(db.sales_orders, "so_number", f"SO/{fy}/")
    n = await _next_seq(f"so:{fy}", seed_value=seed)
    return await format_number("so", n)


async def generate_invoice_number(doc_type="INV"):
    fy = get_financial_year()
    from routes import _next_seq, _max_suffix, format_number
    key = doc_type.lower()
    seed = await _max_suffix(db.invoices, "invoice_number", f"{doc_type}/{fy}/")
    n = await _next_seq(f"{key}:{fy}", seed_value=seed)
    return await format_number(key, n)


# ============= SALES ORDER ROUTES =============

class ConvertToSORequest(BaseModel):
    delivery_date: Optional[str] = None  # YYYY-MM-DD


@router.post("/orders/from-quote/{quote_id}")
async def convert_quote_to_order(
    quote_id: str,
    body: Optional[ConvertToSORequest] = None,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
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
        "delivery_date": body.delivery_date if body else None,
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
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES, UserRole.SALES_MANAGER, UserRole.PRODUCTION_HEAD, UserRole.ACCOUNTS, UserRole.DISPATCH]))
):
    query = {}
    if stage:
        query["stage"] = stage
    if payment_status:
        query["payment_status"] = payment_status

    orders = await db.sales_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"orders": orders, "total": len(orders)}


@router.get("/orders/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES, UserRole.SALES_MANAGER, UserRole.PRODUCTION_HEAD, UserRole.ACCOUNTS, UserRole.DISPATCH]))):
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


# ============= INVOICE PDF GENERATION =============

def _generate_invoice_html(invoice: dict, order: dict = None) -> str:
    """Generate professional HTML invoice for PDF rendering"""
    is_proforma = invoice.get("invoice_type") == "proforma"
    doc_title = "PROFORMA INVOICE" if is_proforma else "TAX INVOICE"
    inv_num = invoice.get("invoice_number", "")
    inv_date = format_date_dmy(invoice.get('created_at'))

    # Customer details
    cust = invoice.get("customer_details") or {}
    cust_name = cust.get("name") or invoice.get("customer_name", "")
    cust_company = cust.get("company") or invoice.get("customer_company", "")
    cust_address = ", ".join(filter(None, [cust.get("address"), cust.get("city"), cust.get("state"), cust.get("pincode")]))
    cust_gst = cust.get("gst_number", "")
    cust_phone = cust.get("phone", "")
    cust_email = cust.get("email") or invoice.get("customer_email", "")

    # Products
    products = invoice.get("products") or []
    subtotal = invoice.get("subtotal", 0)
    total_discount = invoice.get("total_discount", 0)
    packing = invoice.get("packing_charges", 0)
    shipping = invoice.get("shipping_cost", 0)
    taxable = invoice.get("taxable_amount", invoice.get("total_price", 0))
    cgst_rate = invoice.get("cgst_rate", 9)
    cgst_amt = invoice.get("cgst_amount", round(taxable * 0.09, 2))
    sgst_amt = invoice.get("sgst_amount", round(taxable * 0.09, 2))
    total_gst = invoice.get("total_gst", round(cgst_amt + sgst_amt, 2))
    grand_total = invoice.get("total_with_gst", round(taxable + total_gst, 2))

    # SO ref
    so_num = invoice.get("so_number", "")
    quote_num = order.get("quote_number", "") if order else ""

    # Payment info
    payments = order.get("payments", []) if order else []
    total_paid = order.get("total_paid", 0) if order else 0
    balance = order.get("balance_due", grand_total) if order else grand_total

    # Build product rows
    product_rows = ""
    for i, p in enumerate(products, 1):
        qty = p.get("quantity", 1)
        unit = p.get("unit_price", 0)
        total = qty * unit
        specs = p.get("specifications", {})
        spec_text = f"{specs.get('pipe_diameter', '')}mm" if specs.get('pipe_diameter') else ""
        product_rows += f"""<tr>
            <td style="text-align:center">{i}</td>
            <td><b>{p.get('product_name', '')}</b><br><span style="color:#64748B;font-size:10px">Code: {p.get('product_id', '')} {spec_text}</span></td>
            <td style="text-align:center">{COMPANY['hsn_code']}</td>
            <td style="text-align:center">{qty}</td>
            <td style="text-align:right">{unit:,.2f}</td>
            <td style="text-align:right"><b>{total:,.2f}</b></td>
        </tr>"""

    # Payment rows
    payment_rows = ""
    for pay in payments:
        payment_rows += f"""<tr>
            <td>{format_date_dmy(pay.get('recorded_at'))}</td>
            <td>{pay.get('mode','').replace('_',' ').title()}</td>
            <td>{pay.get('reference','—')}</td>
            <td style="text-align:right">Rs.{pay.get('amount',0):,.2f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 15mm; }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1E293B; font-size: 11px; line-height: 1.5; }}
    .invoice {{ max-width: 800px; margin: 0 auto; }}
    .header {{ display: flex; justify-content: space-between; border-bottom: 3px solid #C5964A; padding-bottom: 16px; margin-bottom: 16px; }}
    .company-name {{ font-size: 22px; font-weight: 800; color: #0F172A; letter-spacing: 1px; }}
    .company-details {{ font-size: 10px; color: #475569; line-height: 1.6; }}
    .doc-title {{ font-size: 20px; font-weight: 800; color: #960018; text-align: right; }}
    .doc-number {{ font-size: 13px; color: #0F172A; font-weight: 600; text-align: right; }}
    .doc-date {{ font-size: 11px; color: #64748B; text-align: right; }}
    .info-grid {{ display: flex; gap: 20px; margin-bottom: 16px; }}
    .info-box {{ flex: 1; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; }}
    .info-label {{ font-size: 9px; font-weight: 700; color: #C5964A; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }}
    .info-value {{ font-size: 11px; color: #0F172A; }}
    .info-value b {{ font-weight: 600; }}
    table.items {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
    table.items th {{ background: #0F172A; color: #fff; padding: 8px 10px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
    table.items td {{ padding: 8px 10px; border-bottom: 1px solid #E2E8F0; font-size: 11px; }}
    table.items tr:nth-child(even) {{ background: #F8FAFC; }}
    .totals {{ display: flex; justify-content: flex-end; }}
    .totals-table {{ width: 320px; }}
    .totals-table td {{ padding: 5px 10px; font-size: 11px; }}
    .totals-table .label {{ color: #64748B; text-align: right; }}
    .totals-table .value {{ text-align: right; font-weight: 600; color: #0F172A; }}
    .totals-table .grand {{ font-size: 14px; font-weight: 800; color: #960018; border-top: 2px solid #C5964A; padding-top: 8px; }}
    .grand-label {{ font-size: 14px; font-weight: 800; color: #0F172A; }}
    .section-title {{ font-size: 11px; font-weight: 700; color: #C5964A; text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 8px; }}
    .bank-grid {{ display: flex; gap: 20px; margin-bottom: 16px; }}
    .bank-box {{ flex: 1; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 12px; }}
    .bank-label {{ font-size: 9px; font-weight: 700; color: #92400E; text-transform: uppercase; }}
    .bank-value {{ font-size: 12px; font-weight: 600; color: #0F172A; }}
    table.payments {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
    table.payments th {{ background: #F1F5F9; color: #475569; padding: 6px 10px; font-size: 10px; text-align: left; }}
    table.payments td {{ padding: 6px 10px; border-bottom: 1px solid #E2E8F0; font-size: 11px; }}
    .terms {{ font-size: 10px; color: #64748B; line-height: 1.6; }}
    .terms b {{ color: #475569; }}
    .footer {{ text-align: center; margin-top: 24px; padding-top: 12px; border-top: 1px solid #E2E8F0; font-size: 9px; color: #94A3B8; }}
    .stamp-area {{ display: flex; justify-content: space-between; margin-top: 40px; }}
    .stamp-box {{ text-align: center; }}
    .stamp-line {{ width: 180px; border-top: 1px solid #CBD5E1; margin-top: 50px; padding-top: 4px; font-size: 10px; color: #64748B; }}
</style>
</head><body>
<div class="invoice">

    <!-- Header -->
    <div class="header">
        <div>
            <div class="company-name">{COMPANY['name']}</div>
            <div class="company-details">
                {COMPANY['address']}<br>
                Ph: {COMPANY['phone']} | {COMPANY['email']}<br>
                {COMPANY['website']}<br>
                <b>GSTIN: {COMPANY['gstin']}</b>
            </div>
        </div>
        <div>
            <div class="doc-title">{doc_title}</div>
            <div class="doc-number">{inv_num}</div>
            <div class="doc-date">Date: {inv_date}</div>
            {'<div class="doc-date">SO: ' + so_num + '</div>' if so_num else ''}
            {'<div class="doc-date">Quote: ' + quote_num + '</div>' if quote_num else ''}
        </div>
    </div>

    <!-- Bill To / Ship To -->
    <div class="info-grid">
        <div class="info-box">
            <div class="info-label">Bill To</div>
            <div class="info-value">
                <b>{cust_company or cust_name}</b><br>
                {cust_name if cust_company else ''}<br>
                {cust_address}<br>
                {'Ph: ' + cust_phone + '<br>' if cust_phone else ''}
                {cust_email}<br>
                {'<b>GSTIN: ' + cust_gst + '</b>' if cust_gst else ''}
            </div>
        </div>
        <div class="info-box">
            <div class="info-label">Ship To</div>
            <div class="info-value">
                <b>{cust_company or cust_name}</b><br>
                {cust_address or 'Same as billing address'}
            </div>
        </div>
    </div>

    <!-- Items Table -->
    <table class="items">
        <tr>
            <th style="width:40px">Sr.</th>
            <th>Description</th>
            <th style="width:80px">HSN</th>
            <th style="width:50px">Qty</th>
            <th style="width:90px;text-align:right">Unit Price (Rs.)</th>
            <th style="width:100px;text-align:right">Amount (Rs.)</th>
        </tr>
        {product_rows}
    </table>

    <!-- Totals -->
    <div class="totals">
        <table class="totals-table">
            <tr><td class="label">Subtotal</td><td class="value">Rs.{subtotal:,.2f}</td></tr>
            {'<tr><td class="label">Discount</td><td class="value">- Rs.' + f'{total_discount:,.2f}' + '</td></tr>' if total_discount > 0 else ''}
            {'<tr><td class="label">Packing Charges</td><td class="value">Rs.' + f'{packing:,.2f}' + '</td></tr>' if packing > 0 else ''}
            {'<tr><td class="label">Freight / Shipping</td><td class="value">Rs.' + f'{shipping:,.2f}' + '</td></tr>' if shipping > 0 else ''}
            <tr><td class="label">Taxable Amount</td><td class="value">Rs.{taxable:,.2f}</td></tr>
            <tr><td class="label">CGST @ {cgst_rate}%</td><td class="value">Rs.{cgst_amt:,.2f}</td></tr>
            <tr><td class="label">SGST @ {cgst_rate}%</td><td class="value">Rs.{sgst_amt:,.2f}</td></tr>
            <tr><td class="grand-label">Grand Total</td><td class="grand">Rs.{grand_total:,.2f}</td></tr>
            {'<tr><td class="label">Less: Payment Received</td><td class="value" style="color:#10B981">- Rs.' + f'{total_paid:,.2f}' + '</td></tr><tr><td class="grand-label">Amount Due</td><td class="grand">Rs.' + f'{balance:,.2f}' + '</td></tr>' if total_paid > 0 else ''}
        </table>
    </div>

    <!-- Payment History -->
    {f'''<div class="section-title">Payment History</div>
    <table class="payments">
        <tr><th>Date</th><th>Mode</th><th>Reference</th><th style="text-align:right">Amount</th></tr>
        {payment_rows}
        <tr style="font-weight:700"><td colspan="3">Total Paid</td><td style="text-align:right">Rs.{total_paid:,.2f}</td></tr>
        <tr style="font-weight:700;color:#960018"><td colspan="3">Balance Due</td><td style="text-align:right">Rs.{balance:,.2f}</td></tr>
    </table>''' if payments else ''}

    <!-- Bank Details -->
    <div class="section-title">Bank Details for Payment</div>
    <div class="bank-grid">
        <div class="bank-box">
            <div class="bank-label">Bank</div>
            <div class="bank-value">{COMPANY['bank_name']}</div>
        </div>
        <div class="bank-box">
            <div class="bank-label">Account No.</div>
            <div class="bank-value">{COMPANY['bank_account']}</div>
        </div>
        <div class="bank-box">
            <div class="bank-label">IFSC Code</div>
            <div class="bank-value">{COMPANY['bank_ifsc']}</div>
        </div>
        <div class="bank-box">
            <div class="bank-label">Branch</div>
            <div class="bank-value">{COMPANY['bank_branch']}</div>
        </div>
    </div>

    <!-- Terms -->
    <div class="section-title">Terms & Conditions</div>
    <div class="terms">
        <b>1.</b> Goods once sold will not be taken back.<br>
        <b>2.</b> Interest @ 18% p.a. will be charged on delayed payments.<br>
        <b>3.</b> Subject to Ahmedabad Jurisdiction only.<br>
        <b>4.</b> E. & O.E.
    </div>

    <!-- Signature -->
    <div class="stamp-area">
        <div class="stamp-box">
            <div class="stamp-line">Customer's Seal & Signature</div>
        </div>
        <div class="stamp-box">
            <div class="stamp-line">For {COMPANY['name']}<br>Authorized Signatory</div>
        </div>
    </div>

    <div class="footer">
        This is a computer-generated document. | {COMPANY['name']} | GSTIN: {COMPANY['gstin']} | {COMPANY['email']}
    </div>
</div>
</body></html>"""

    return html


@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Generate and download invoice PDF (HTML format for printing)"""
    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization[7:]
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    invoice = await db.invoices.find_one(
        {"$or": [{"id": invoice_id}, {"invoice_number": invoice_id}]}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Get order for payment history
    order = None
    if invoice.get("order_id"):
        order = await db.sales_orders.find_one({"id": invoice["order_id"]}, {"_id": 0})

    html = _generate_invoice_html(invoice, order)

    output = io.BytesIO(html.encode('utf-8'))
    output.seek(0)
    filename = f"{invoice.get('invoice_number', 'Invoice').replace('/', '-')}.html"

    return StreamingResponse(
        output,
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============= SALES ORDER PDF =============

@router.get("/orders/{order_id}/pdf")
async def get_sales_order_pdf(
    order_id: str,
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

    order = await db.sales_orders.find_one({"$or": [{"id": order_id}, {"so_number": order_id}]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    so_num = order.get("so_number", "")
    so_date = format_date_dmy(order.get('created_at'))
    quote_num = order.get("quote_number", "")

    # Customer
    cust = order.get("customer_details") or {}
    cust_name = cust.get("name") or order.get("customer_name", "")
    cust_company = cust.get("company") or order.get("customer_company", "")
    cust_address = ", ".join(filter(None, [cust.get("address"), cust.get("city"), cust.get("state"), cust.get("pincode")]))
    cust_gst = cust.get("gst_number", "")
    cust_phone = cust.get("phone", "")
    cust_email = cust.get("email") or order.get("customer_email", "")
    cust_code = order.get("customer_code", "")

    # Products
    products = order.get("products") or []
    product_rows = ""
    grand_weight = 0
    for i, p in enumerate(products, 1):
        qty = p.get("quantity", 1)
        unit = p.get("unit_price", 0)
        total = qty * unit
        specs = p.get("specifications", {})
        spec_parts = []
        if specs.get("pipe_diameter"): spec_parts.append(f"Pipe: {specs['pipe_diameter']}mm")
        if specs.get("shaft_diameter"): spec_parts.append(f"Shaft: {specs['shaft_diameter']}mm")
        if specs.get("pipe_length"): spec_parts.append(f"L: {specs['pipe_length']}mm")
        spec_text = " | ".join(spec_parts)
        weight = p.get("weight_kg", p.get("weight", 0)) or 0
        item_total_weight = weight * qty
        grand_weight += item_total_weight
        product_rows += f"""<tr>
            <td style="text-align:center">{i}</td>
            <td><b>{p.get('product_name','')}</b><br><span style="color:#960018;font-size:9px;font-weight:600">Code: {p.get('product_id','')}</span><br><span style="color:#64748B;font-size:9px">{spec_text}</span></td>
            <td style="text-align:center">{COMPANY['hsn_code']}</td>
            <td style="text-align:center">{qty}</td>
            <td style="text-align:right">{weight:.2f}</td>
            <td style="text-align:right">{unit:,.2f}</td>
            <td style="text-align:right"><b>{total:,.2f}</b></td>
        </tr>"""
    # Total weight row
    product_rows += f"""<tr style="font-weight:700;background:#F0F4F8">
        <td colspan="4" style="text-align:right;padding:8px">Total Weight</td>
        <td style="text-align:right;padding:8px">{grand_weight:.2f} kg</td>
        <td></td>
        <td></td>
    </tr>"""

    # Pricing
    subtotal = order.get("subtotal", 0)
    total_discount = order.get("total_discount", 0)
    discount_percent = order.get("discount_percent", 0)
    packing = order.get("packing_charges", 0)
    packing_type = order.get("packing_type", "")
    shipping = order.get("shipping_cost", 0)
    total_price = order.get("total_price", 0)

    # Freight details
    freight = order.get("freight_details") or {}
    freight_amount = freight.get("freight_amount", freight.get("freight_cost", shipping)) or 0

    # GST calculation (18%)
    taxable = round(subtotal - total_discount + packing + freight_amount, 2)
    cgst = round(taxable * 0.09, 2)
    sgst = round(taxable * 0.09, 2)
    total_gst = round(cgst + sgst, 2)
    grand_total = round(taxable + total_gst, 2)

    # Commercial terms
    terms = order.get("commercial_terms") or {}
    terms_html = ""
    if terms:
        terms_rows = ""
        term_labels = {
            "payment_terms": "Payment Terms",
            "freight_terms": "Delivery Terms",
            "color_finish": "Color & Finish",
            "delivery_timeline": "Delivery Timeline",
            "warranty": "Warranty",
        }
        for key, label in term_labels.items():
            val = terms.get(key)
            if val:
                terms_rows += f"<tr><td style='padding:5px 10px;color:#64748B;font-size:10px;width:140px;vertical-align:top'>{label}</td><td style='padding:5px 10px;font-size:11px;color:#0F172A'>{val}</td></tr>"
        if terms_rows:
            terms_html = f"""<div style="font-size:11px;font-weight:700;color:#C5964A;text-transform:uppercase;letter-spacing:1px;margin:16px 0 8px">Commercial Terms</div>
            <table style="width:100%;border-collapse:collapse;margin-bottom:12px;background:#F8FAFC;border-radius:6px">{terms_rows}</table>"""

    # Freight details
    freight = order.get("freight_details") or {}
    freight_html = ""
    if freight:
        freight_parts = []
        if freight.get("delivery_location"): freight_parts.append(f"Delivery: {freight['delivery_location']}")
        if freight.get("freight_cost"): freight_parts.append(f"Freight: Rs.{freight['freight_cost']:,.2f}")
        if freight.get("distance_km"): freight_parts.append(f"Distance: {freight['distance_km']} km")
        if freight_parts:
            freight_html = f"""<div style="font-size:10px;color:#64748B;margin-bottom:8px">{'  |  '.join(freight_parts)}</div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 15mm; }}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color:#1E293B; font-size:11px; line-height:1.5; }}
    .so {{ max-width:800px; margin:0 auto; }}
    .header {{ display:flex; justify-content:space-between; border-bottom:3px solid #C5964A; padding-bottom:14px; margin-bottom:16px; }}
    .company-name {{ font-size:22px; font-weight:800; color:#0F172A; letter-spacing:1px; }}
    .company-details {{ font-size:10px; color:#475569; line-height:1.6; }}
    .doc-title {{ font-size:22px; font-weight:800; color:#960018; text-align:right; }}
    .doc-number {{ font-size:14px; font-weight:600; color:#0F172A; text-align:right; }}
    .doc-date {{ font-size:11px; color:#64748B; text-align:right; }}
    .info-grid {{ display:flex; gap:16px; margin-bottom:16px; }}
    .info-box {{ flex:1; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px; }}
    .info-label {{ font-size:9px; font-weight:700; color:#C5964A; letter-spacing:1px; text-transform:uppercase; margin-bottom:6px; }}
    .info-value {{ font-size:11px; color:#0F172A; }}
    table.items {{ width:100%; border-collapse:collapse; margin-bottom:16px; }}
    table.items th {{ background:#0F172A; color:#fff; padding:7px 8px; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }}
    table.items td {{ padding:7px 8px; border-bottom:1px solid #E2E8F0; font-size:11px; }}
    table.items tr:nth-child(even) {{ background:#F8FAFC; }}
    .totals {{ display:flex; justify-content:flex-end; }}
    .totals-table {{ width:320px; }}
    .totals-table td {{ padding:5px 10px; font-size:11px; }}
    .totals-table .label {{ color:#64748B; text-align:right; }}
    .totals-table .value {{ text-align:right; font-weight:600; color:#0F172A; }}
    .totals-table .grand {{ font-size:14px; font-weight:800; color:#960018; border-top:2px solid #C5964A; padding-top:8px; }}
    .grand-label {{ font-size:14px; font-weight:800; color:#0F172A; }}
    .stamp-area {{ display:flex; justify-content:space-between; margin-top:40px; }}
    .stamp-line {{ width:180px; border-top:1px solid #CBD5E1; margin-top:50px; padding-top:4px; font-size:10px; color:#64748B; text-align:center; }}
    .footer {{ text-align:center; margin-top:20px; padding-top:10px; border-top:1px solid #E2E8F0; font-size:9px; color:#94A3B8; }}
</style>
</head><body>
<div class="so">
    <div class="header">
        <div>
            <div class="company-name">{COMPANY['name']}</div>
            <div class="company-details">
                {COMPANY['address']}<br>
                Ph: {COMPANY['phone']} | {COMPANY['email']}<br>
                {COMPANY['website']}<br>
                <b>GSTIN: {COMPANY['gstin']}</b>
            </div>
        </div>
        <div>
            <div class="doc-title">SALES ORDER</div>
            <div class="doc-number">{so_num}</div>
            <div class="doc-date">Date: {so_date}</div>
            {'<div class="doc-date">Delivery: ' + order.get('delivery_date', '') + '</div>' if order.get('delivery_date') else ''}
            {'<div class="doc-date">Quote: ' + quote_num + '</div>' if quote_num else ''}
        </div>
    </div>

    <div class="info-grid">
        <div class="info-box">
            <div class="info-label">Bill To</div>
            <div class="info-value">
                <b>{cust_company or cust_name}</b><br>
                {cust_name if cust_company else ''}<br>
                {cust_address}<br>
                {'Ph: ' + cust_phone + '<br>' if cust_phone else ''}
                {cust_email}<br>
                {'<b>GSTIN: ' + cust_gst + '</b><br>' if cust_gst else ''}
                {'Code: ' + cust_code if cust_code else ''}
            </div>
        </div>
        <div class="info-box">
            <div class="info-label">Ship To</div>
            <div class="info-value">
                <b>{cust_company or cust_name}</b><br>
                {cust_address or 'Same as billing address'}
            </div>
        </div>
    </div>

    {freight_html}

    <table class="items">
        <tr>
            <th style="width:30px">Sr.</th>
            <th>Description</th>
            <th style="width:70px">HSN</th>
            <th style="width:40px">Qty</th>
            <th style="width:70px;text-align:right">Wt (kg)</th>
            <th style="width:80px;text-align:right">Unit Price</th>
            <th style="width:90px;text-align:right">Amount (Rs.)</th>
        </tr>
        {product_rows}
    </table>

    <div class="totals">
        <table class="totals-table">
            <tr><td class="label">Subtotal</td><td class="value">Rs.{subtotal:,.2f}</td></tr>
            {'<tr><td class="label">Discount (' + str(discount_percent) + '%)</td><td class="value">- Rs.' + f'{total_discount:,.2f}' + '</td></tr>' if total_discount > 0 else ''}
            {'<tr><td class="label">Packing (' + packing_type + ')</td><td class="value">Rs.' + f'{packing:,.2f}' + '</td></tr>' if packing > 0 else ''}
            {'<tr><td class="label">Freight</td><td class="value">Rs.' + f'{freight_amount:,.2f}' + '</td></tr>' if freight_amount > 0 else ''}
            <tr><td class="label" style="border-top:1px solid #E2E8F0;padding-top:6px">Taxable Amount</td><td class="value" style="border-top:1px solid #E2E8F0;padding-top:6px">Rs.{taxable:,.2f}</td></tr>
            <tr><td class="label">CGST @ 9%</td><td class="value">Rs.{cgst:,.2f}</td></tr>
            <tr><td class="label">SGST @ 9%</td><td class="value">Rs.{sgst:,.2f}</td></tr>
            <tr><td class="grand-label">Grand Total</td><td class="grand">Rs.{grand_total:,.2f}</td></tr>
        </table>
    </div>

    {terms_html}

    <div class="stamp-area">
        <div><div class="stamp-line">Customer's Seal & Signature</div></div>
        <div><div class="stamp-line">For {COMPANY['name']}<br>Authorized Signatory</div></div>
    </div>

    <div class="footer">This is a computer-generated document. | {COMPANY['name']} | GSTIN: {COMPANY['gstin']} | {COMPANY['email']}</div>
</div>
</body></html>"""

    output = io.BytesIO(html.encode('utf-8'))
    output.seek(0)
    filename = f"{so_num.replace('/', '-')}.html"

    return StreamingResponse(output, media_type="text/html",
                           headers={"Content-Disposition": f"attachment; filename={filename}"})

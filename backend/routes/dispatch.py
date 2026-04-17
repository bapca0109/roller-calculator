"""Delivery Challan Routes — Create DC from SO, list, PDF download"""
import os
import io
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from jose import jwt

from routes import (
    db, get_current_user, require_role, UserRole,
    get_financial_year, SECRET_KEY, ALGORITHM,
)

router = APIRouter()

# Company constants (mirrors orders.py to keep PDF consistent)
COMPANY = {
    "name": os.environ.get("COMPANY_NAME", "CONVERO SOLUTIONS"),
    "address": os.environ.get("COMPANY_ADDRESS", ""),
    "email": os.environ.get("COMPANY_EMAIL", "Info@convero.in"),
    "website": os.environ.get("COMPANY_WEBSITE", "www.convero.in"),
    "phone": os.environ.get("COMPANY_PHONE", ""),
    "gstin": os.environ.get("COMPANY_GSTIN", ""),
    "hsn_code": os.environ.get("COMPANY_HSN_CODE", "84313910"),
}

EWAY_THRESHOLD = 50000  # ₹50,000 — e-way bill mandatory above this

# ============= MODELS =============

class ChallanItem(BaseModel):
    product_id: str
    product_name: str
    quantity: float
    unit: str = "Nos"
    weight_kg: Optional[float] = 0
    specifications: Optional[Dict[str, Any]] = None

class DeliveryChallanCreate(BaseModel):
    order_id: str
    vehicle_no: str = Field(..., min_length=1)
    driver_name: str = Field(..., min_length=1)
    driver_phone: Optional[str] = None
    transporter_name: str = Field(..., min_length=1)
    eway_bill_no: Optional[str] = None
    dispatch_date: str  # DD-MM-YYYY or ISO
    remarks: Optional[str] = None
    items: Optional[List[ChallanItem]] = None  # override SO items if provided


# ============= HELPERS =============

async def generate_dc_number() -> str:
    fy = get_financial_year()
    from routes import _next_seq, _max_suffix, format_number
    seed = await _max_suffix(db.delivery_challans, "dc_number", f"DC/{fy}/")
    n = await _next_seq(f"dc:{fy}", seed_value=seed)
    return await format_number("dc", n)


def format_date_dmy(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        # Accept already-formatted DD-MM-YYYY
        if len(value) >= 10 and value[2] == '-' and value[5] == '-':
            return value[:10]
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return value[:10]
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    return str(value)[:10]


def _total_value(items: List[Dict[str, Any]], order: Dict[str, Any]) -> float:
    """Sum up item totals using SO unit prices."""
    so_products_by_id = {p.get("product_id"): p for p in (order.get("products") or [])}
    total = 0.0
    for it in items:
        pid = it.get("product_id")
        qty = float(it.get("quantity") or 0)
        unit_price = 0.0
        if pid and pid in so_products_by_id:
            unit_price = float(so_products_by_id[pid].get("unit_price") or 0)
        total += qty * unit_price
    return total


# ============= ENDPOINTS =============

DISPATCH_ROLES = [
    UserRole.ADMIN, UserRole.SALES_MANAGER,
    UserRole.DISPATCH, UserRole.ACCOUNTS,
]


@router.post("/delivery-challans")
async def create_delivery_challan(
    req: DeliveryChallanCreate,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.DISPATCH, UserRole.SALES_MANAGER])),
):
    # Fetch SO
    order = await db.sales_orders.find_one(
        {"$or": [{"id": req.order_id}, {"so_number": req.order_id}]},
        {"_id": 0}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Sales Order not found")

    # Items: default to SO products, else use provided override
    if req.items:
        items = [it.model_dump() for it in req.items]
    else:
        items = []
        for p in (order.get("products") or []):
            items.append({
                "product_id": p.get("product_id", ""),
                "product_name": p.get("product_name", ""),
                "quantity": p.get("quantity", 1),
                "unit": "Nos",
                "weight_kg": p.get("weight_kg", p.get("weight", 0)) or 0,
                "specifications": p.get("specifications") or {},
            })

    # E-way bill compulsory above threshold
    total_value = order.get("total_price") or _total_value(items, order)
    if total_value > EWAY_THRESHOLD and not (req.eway_bill_no and req.eway_bill_no.strip()):
        raise HTTPException(
            status_code=400,
            detail=f"E-way bill number is compulsory for consignments above Rs.{EWAY_THRESHOLD:,}"
        )

    dc_number = await generate_dc_number()
    dc_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    dc = {
        "id": dc_id,
        "dc_number": dc_number,
        "order_id": order.get("id", ""),
        "so_number": order.get("so_number", ""),
        "customer_email": order.get("customer_email", ""),
        "customer_name": order.get("customer_name", ""),
        "customer_company": order.get("customer_company", ""),
        "customer_code": order.get("customer_code", ""),
        "customer_details": order.get("customer_details") or {},
        "items": items,
        "vehicle_no": req.vehicle_no.strip().upper(),
        "driver_name": req.driver_name.strip(),
        "driver_phone": (req.driver_phone or "").strip(),
        "transporter_name": req.transporter_name.strip(),
        "eway_bill_no": (req.eway_bill_no or "").strip(),
        "dispatch_date": req.dispatch_date,
        "remarks": (req.remarks or "").strip(),
        "total_value": total_value,
        "status": "dispatched",
        "created_by": current_user.get("email"),
        "created_at": now_iso,
    }
    await db.delivery_challans.insert_one(dc)

    # Update SO stage to dispatched
    await db.sales_orders.update_one(
        {"id": order.get("id")},
        {
            "$set": {
                "stage": "dispatched",
                "dispatch_date": req.dispatch_date,
                "dc_number": dc_number,
                "updated_at": now_iso,
            },
            "$push": {
                "stage_history": {
                    "stage": "dispatched",
                    "timestamp": now_iso,
                    "notes": f"Challan {dc_number} created by {current_user.get('email')}",
                    "by": current_user.get("email"),
                }
            },
        }
    )
    dc.pop("_id", None)
    return {"message": "Delivery Challan created", "challan": dc}


@router.get("/delivery-challans")
async def list_delivery_challans(
    order_id: Optional[str] = Query(None),
    current_user: dict = Depends(require_role(DISPATCH_ROLES)),
):
    q: Dict[str, Any] = {}
    if order_id:
        q["$or"] = [{"order_id": order_id}, {"so_number": order_id}]
    items = await db.delivery_challans.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"challans": items, "total": len(items)}


@router.get("/delivery-challans/{dc_id}")
async def get_delivery_challan(
    dc_id: str,
    current_user: dict = Depends(require_role(DISPATCH_ROLES)),
):
    dc = await db.delivery_challans.find_one(
        {"$or": [{"id": dc_id}, {"dc_number": dc_id}]},
        {"_id": 0}
    )
    if not dc:
        raise HTTPException(status_code=404, detail="Delivery Challan not found")
    return dc


@router.get("/delivery-challans/{dc_id}/pdf")
async def get_delivery_challan_pdf(
    dc_id: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None),
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

    dc = await db.delivery_challans.find_one(
        {"$or": [{"id": dc_id}, {"dc_number": dc_id}]}, {"_id": 0}
    )
    if not dc:
        raise HTTPException(status_code=404, detail="Delivery Challan not found")

    cust = dc.get("customer_details") or {}
    cust_name = cust.get("name") or dc.get("customer_name", "")
    cust_company = cust.get("company") or dc.get("customer_company", "")
    cust_address = ", ".join(filter(None, [cust.get("address"), cust.get("city"), cust.get("state"), cust.get("pincode")]))
    cust_gst = cust.get("gst_number", "")
    cust_phone = cust.get("phone", "")

    rows_html = ""
    total_qty = 0
    total_weight = 0.0
    for i, it in enumerate(dc.get("items") or [], 1):
        qty = it.get("quantity") or 0
        wt = it.get("weight_kg") or 0
        total_qty += qty
        total_weight += wt * qty
        specs = it.get("specifications") or {}
        sp = []
        if specs.get("pipe_diameter"): sp.append(f"Pipe: {specs['pipe_diameter']}mm")
        if specs.get("shaft_diameter"): sp.append(f"Shaft: {specs['shaft_diameter']}mm")
        if specs.get("pipe_length"): sp.append(f"L: {specs['pipe_length']}mm")
        spec_text = " | ".join(sp)
        rows_html += f"""<tr>
            <td style="text-align:center">{i}</td>
            <td><b>{it.get('product_name','')}</b><br><span style="color:#960018;font-size:9px;font-weight:600">Code: {it.get('product_id','')}</span><br><span style="color:#64748B;font-size:9px">{spec_text}</span></td>
            <td style="text-align:center">{COMPANY['hsn_code']}</td>
            <td style="text-align:center">{qty}</td>
            <td style="text-align:center">{it.get('unit','Nos')}</td>
            <td style="text-align:right">{(wt * qty):.2f}</td>
        </tr>"""

    rows_html += f"""<tr style="font-weight:700;background:#F0F4F8">
        <td colspan="3" style="text-align:right;padding:8px">Totals</td>
        <td style="text-align:center;padding:8px">{total_qty}</td>
        <td></td>
        <td style="text-align:right;padding:8px">{total_weight:.2f} kg</td>
    </tr>"""

    total_value = dc.get("total_value") or 0
    eway = dc.get("eway_bill_no") or "—"
    dispatch_date = format_date_dmy(dc.get("dispatch_date"))

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{dc.get('dc_number','')}</title>
<style>
  @page {{ size: A4; margin: 14mm; }}
  body {{ font-family: -apple-system, Arial, sans-serif; color: #1F2937; font-size: 11px; }}
  .wrap {{ max-width: 800px; margin: 0 auto; }}
  .head {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #960018; padding-bottom: 8px; margin-bottom: 10px; }}
  .head h1 {{ margin: 0; color: #960018; font-size: 22px; letter-spacing: 1px; }}
  .head .sub {{ color: #64748B; font-size: 10px; margin-top: 2px; }}
  .doc-title {{ text-align: right; }}
  .doc-title .label {{ color: #64748B; font-size: 10px; letter-spacing: 1.5px; }}
  .doc-title h2 {{ margin: 2px 0; font-size: 18px; color: #111; letter-spacing: 1px; }}
  .grid {{ display: flex; gap: 12px; margin-bottom: 10px; }}
  .block {{ flex: 1; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; background: #fff; }}
  .block .title {{ color: #960018; font-weight: 700; font-size: 10px; letter-spacing: 1.2px; margin-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
  th {{ background: #960018; color: #fff; padding: 8px 6px; font-size: 10px; text-align: left; }}
  td {{ border-bottom: 1px solid #E2E8F0; padding: 6px; font-size: 10px; vertical-align: top; }}
  .meta-row {{ display: flex; justify-content: space-between; margin-bottom: 2px; font-size: 10px; }}
  .meta-row span:first-child {{ color: #64748B; }}
  .sign {{ display: flex; gap: 18px; margin-top: 36px; }}
  .sign div {{ flex: 1; border-top: 1px solid #64748B; padding-top: 4px; font-size: 10px; color: #64748B; text-align: center; }}
  .footer {{ text-align: center; color: #94A3B8; font-size: 9px; margin-top: 16px; border-top: 1px solid #E2E8F0; padding-top: 6px; }}
  .remark {{ background: #FFFBEB; border: 1px dashed #F59E0B; padding: 8px; border-radius: 6px; margin-top: 8px; font-size: 10px; }}
  .eway {{ display: inline-block; background: #FEF2F2; border: 1px solid #FCA5A5; color: #B91C1C; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 10px; }}
</style></head><body><div class="wrap">
  <div class="head">
    <div>
      <h1>{COMPANY['name']}</h1>
      <div class="sub">{COMPANY['address']}<br>GSTIN: {COMPANY['gstin']} | {COMPANY['email']} | {COMPANY['phone']}</div>
    </div>
    <div class="doc-title">
      <div class="label">DELIVERY CHALLAN</div>
      <h2>{dc.get('dc_number','')}</h2>
      <div style="font-size:10px;color:#64748B">Dispatch Date: <b>{dispatch_date}</b></div>
    </div>
  </div>

  <div class="grid">
    <div class="block">
      <div class="title">CONSIGNEE / BILL TO</div>
      <div><b>{cust_company or cust_name}</b></div>
      {f'<div>Attn: {cust_name}</div>' if cust_company and cust_name else ''}
      <div>{cust_address}</div>
      {f'<div>Phone: {cust_phone}</div>' if cust_phone else ''}
      {f'<div>GSTIN: {cust_gst}</div>' if cust_gst else ''}
      {f'<div style="color:#64748B;font-size:9px">Customer Code: {dc.get("customer_code","")}</div>' if dc.get('customer_code') else ''}
    </div>
    <div class="block">
      <div class="title">DISPATCH DETAILS</div>
      <div class="meta-row"><span>SO Ref.</span><b>{dc.get('so_number','')}</b></div>
      <div class="meta-row"><span>Transporter</span><b>{dc.get('transporter_name','')}</b></div>
      <div class="meta-row"><span>Vehicle No.</span><b>{dc.get('vehicle_no','')}</b></div>
      <div class="meta-row"><span>Driver</span><b>{dc.get('driver_name','')}</b></div>
      {f'<div class="meta-row"><span>Driver Phone</span><b>{dc.get("driver_phone","")}</b></div>' if dc.get('driver_phone') else ''}
      <div class="meta-row" style="margin-top:4px"><span>E-way Bill</span><span class="eway">{eway}</span></div>
    </div>
  </div>

  <table>
    <thead><tr>
      <th style="width:30px;text-align:center">#</th>
      <th>Description of Goods</th>
      <th style="width:60px;text-align:center">HSN</th>
      <th style="width:50px;text-align:center">Qty</th>
      <th style="width:50px;text-align:center">Unit</th>
      <th style="width:70px;text-align:right">Wt (kg)</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>

  <div style="margin-top:8px;text-align:right;font-size:11px">
    <b>Consignment Value:</b> Rs. {total_value:,.2f}
  </div>

  {f'<div class="remark"><b>Remarks:</b> {dc.get("remarks","")}</div>' if dc.get('remarks') else ''}

  <div class="sign">
    <div>Prepared By</div>
    <div>Transporter's Signature</div>
    <div>Received in Good Condition<br>(Consignee Seal & Signature)</div>
  </div>

  <div class="footer">
    This is a computer-generated Delivery Challan. NOT a Tax Invoice.
    | {COMPANY['name']} | GSTIN: {COMPANY['gstin']} | {COMPANY['website']}
  </div>
</div></body></html>"""

    output = io.BytesIO(html.encode("utf-8"))
    output.seek(0)
    filename = f"{dc.get('dc_number','challan').replace('/', '-')}.html"
    return StreamingResponse(
        output,
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

"""Quote Routes — CRUD, RFQ Approval, Revision, Attachments, Stats"""
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Body, Header
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from routes import (db, get_current_user, require_role, get_ist_now, utc_to_ist, IST,
                    generate_quote_number, generate_rfq_number, GMAIL_USER, GMAIL_APP_PASSWORD,
                    ADMIN_RFQ_EMAILS, ROOT_DIR, QuoteInDB, QuoteCreate, QuoteUpdate, QuoteReject,
                    QuoteProduct, RollerQuoteCreate, Quote, QuoteStatus, CommercialTerms,
                    RevisionHistoryEntry, UserRole)
from routes.auth import send_push_notification_to_user
import base64
import io
import logging

router = APIRouter()

# ============= QUOTE ROUTES =============

@router.post("/quotes", response_model=QuoteInDB)
async def create_quote(
    quote: QuoteCreate,
    current_user: dict = Depends(get_current_user)
):
    # Check if user is a customer
    is_customer = current_user["role"] == UserRole.CUSTOMER
    
    # Admin must provide a customer_id when creating RFQ
    if not is_customer and not quote.customer_id:
        raise HTTPException(
            status_code=400, 
            detail="Customer selection is required for admin users"
        )
    
    # Calculate pricing - no system discount, admin will set during approval
    subtotal = 0.0
    
    processed_products = []
    for item in quote.products:
        # Calculate base line total
        line_total = item.quantity * item.unit_price
        
        # No system discount - admin will set during approval
        item.calculated_discount = 0
        subtotal += line_total
        
        processed_products.append(item.dict())
    
    # Calculate total price (no system discount, admin will set later)
    total_price = subtotal  # Original value without discount
    
    # Generate sequential RFQ number - both customers AND admins create RFQs first
    # Admin will approve RFQ to convert it to a Quote
    quote_number = await generate_rfq_number()
    quote_type = "rfq"
    
    ist_now = get_ist_now()
    
    # Get customer code from current user
    customer_code = current_user.get("customer_code")
    
    quote_dict = {
        "quote_number": quote_number,
        "quote_type": quote_type,
        "customer_id": current_user.get("email"),
        "customer_code": customer_code,
        "customer_name": current_user["name"],
        "customer_company": current_user.get("company", ""),
        "customer_email": current_user["email"],
        "customer_rfq_no": quote.customer_rfq_no,  # Customer's own reference number (optional)
        "products": processed_products,
        "subtotal": subtotal,
        "total_discount": 0,  # No system discount - admin will set during approval
        "shipping_cost": quote.shipping_cost or 0.0,  # Use freight from customer if provided
        "freight_details": quote.freight_details,  # Custom freight details from admin
        "delivery_location": quote.delivery_location,
        "packing_type": quote.packing_type,  # Packing type from cart submission
        "total_price": total_price,
        "status": QuoteStatus.PENDING,
        "notes": quote.notes,
        "created_at": ist_now,
        "updated_at": ist_now
    }
    
    result = await db.quotes.insert_one(quote_dict)
    quote_dict["id"] = str(result.inserted_id)
    
    # Log attachment info for debugging
    total_attachments = sum(len(p.attachments or []) for p in quote.products)
    logging.info(f"Quote created with {total_attachments} attachments across {len(quote.products)} products")
    for i, p in enumerate(quote.products):
        if p.attachments:
            for att in p.attachments:
                logging.info(f"  Product {i}: attachment '{att.name}' has base64: {bool(att.base64)}")
    
    # If customer created RFQ, send email to admins
    if is_customer:
        await send_rfq_notification_email(quote_dict, current_user)
        # Send push notification to admins
        await send_push_notification_to_admins(
            title="New RFQ Received! 📋",
            body=f"New RFQ {quote_number} from {current_user['name']} ({len(quote.products)} items)",
            data={
                "type": "new_rfq",
                "quote_id": str(result.inserted_id),
                "quote_number": quote_number,
                "customer_name": current_user["name"]
            }
        )
    
    return QuoteInDB(**quote_dict)

@router.post("/quotes/roller")
async def create_roller_quote(
    quote_data: RollerQuoteCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a quote from roller calculation results"""
    
    config = quote_data.configuration
    pricing = quote_data.pricing
    is_customer = current_user.get("role") == UserRole.CUSTOMER
    
    # Create product entry from roller calculation
    product = {
        "product_id": config.get("product_code", "ROLLER"),
        "product_name": f"{config.get('roller_type', 'Carrying').title()} Roller - {config.get('product_code', '')}",
        "quantity": config.get("quantity", 1),
        "unit_price": pricing.get("unit_price", 0),
        "specifications": {
            "pipe_diameter": config.get("pipe_diameter_mm"),
            "pipe_length": config.get("pipe_length_mm"),
            "pipe_type": config.get("pipe_type"),
            "shaft_diameter": config.get("shaft_diameter_mm"),
            "bearing": config.get("bearing"),
            "bearing_make": config.get("bearing_make"),
            "housing": config.get("housing"),
            "rubber_diameter": config.get("rubber_diameter_mm")
        },
        "calculated_discount": pricing.get("discount_amount", 0),
        "custom_premium": 0.0
    }
    
    # Generate sequential quote/RFQ number based on user role
    if is_customer:
        quote_number = await generate_rfq_number()
        quote_type = "rfq"
    else:
        quote_number = await generate_quote_number()
        quote_type = "quote"
    
    ist_now = get_ist_now()
    
    # Get customer code - try from customer_details first, then from current user
    customer_code = None
    if quote_data.customer_details:
        customer_code = quote_data.customer_details.get("customer_code")
    if not customer_code:
        customer_code = current_user.get("customer_code")
    
    quote_dict = {
        "quote_number": quote_number,
        "quote_type": quote_type,
        "customer_id": quote_data.customer_id or current_user.get("email"),
        "customer_code": customer_code,
        "customer_name": quote_data.customer_name or current_user["name"],
        "customer_company": quote_data.customer_details.get("company", "") if quote_data.customer_details else current_user.get("company", ""),
        "customer_email": current_user["email"],
        "customer_details": quote_data.customer_details,  # Full customer info for PDF
        "products": [product],
        "subtotal": pricing.get("order_value", 0),
        "total_discount": 0,  # No system discount - admin will set during approval
        "packing_charges": pricing.get("packing_charges", 0),  # Customer can set packing
        "shipping_cost": quote_data.freight.get("freight_charges", 0) if quote_data.freight else 0,  # Customer can set freight
        "delivery_location": quote_data.freight.get("destination_pincode") if quote_data.freight else None,
        "total_price": pricing.get("order_value", 0),  # Original value, no discount yet
        "status": QuoteStatus.PENDING,
        "notes": quote_data.notes,
        "cost_breakdown": quote_data.cost_breakdown,
        "pricing_details": quote_data.pricing,
        "freight_details": quote_data.freight,  # Customer's freight details
        "created_at": ist_now,
        "updated_at": ist_now
    }
    
    result = await db.quotes.insert_one(quote_dict)
    quote_dict["id"] = str(result.inserted_id)
    
    # If customer created RFQ, send email to admins
    if is_customer:
        await send_rfq_notification_email(quote_dict, current_user)
    
    return {
        "id": quote_dict["id"],
        "message": f"{'RFQ' if is_customer else 'Quote'} created successfully",
        "quote_number": quote_number,
        "total_price": quote_dict["total_price"]
    }

@router.get("/quotes")
async def get_quotes(current_user: dict = Depends(get_current_user)):
    query = {}
    # Customers can only see their own quotes
    if current_user["role"] == UserRole.CUSTOMER:
        query["customer_id"] = current_user.get("email")
    
    quotes = await db.quotes.find(query).sort("created_at", -1).limit(100).to_list(100)
    result = []
    for quote in quotes:
        quote["id"] = str(quote["_id"])
        del quote["_id"]
        # Handle legacy quotes that might be missing required fields
        # Set defaults for missing fields to prevent validation errors
        quote.setdefault("subtotal", quote.get("total_price", 0))
        quote.setdefault("products", [])
        quote.setdefault("total_price", 0)
        quote.setdefault("customer_id", "")
        quote.setdefault("customer_name", "Unknown")
        quote.setdefault("customer_email", "")
        quote.setdefault("read_by_admin", False)  # Default for legacy quotes
        
        # Calculate missing weights for products
        for product in quote.get("products", []):
            if not product.get("weight_kg") and not product.get("weight"):
                # Try to calculate weight from specifications
                specs = product.get("specifications") or {}
                if specs.get("pipe_diameter") and specs.get("pipe_length") and specs.get("shaft_diameter"):
                    try:
                        weight = rs.calculate_roller_weight(
                            pipe_dia=float(specs.get("pipe_diameter", 0)),
                            pipe_length_mm=float(specs.get("pipe_length", 0)),
                            shaft_dia=float(specs.get("shaft_diameter", 0)),
                            pipe_type=specs.get("pipe_type", "B")
                        )
                        product["weight_kg"] = weight
                        product["weight"] = weight
                    except Exception as e:
                        logging.warning(f"Could not calculate weight for product: {e}")
        
        # Generate quote_number for legacy quotes that don't have one
        if not quote.get("quote_number"):
            quote["quote_number"] = f"QT-{quote['id'][-6:].upper()}"
        
        # Convert created_at to IST string for display
        if quote.get("created_at"):
            ist_time = utc_to_ist(quote["created_at"])
            if ist_time:
                quote["created_at_ist"] = ist_time.strftime("%d %b %Y, %I:%M %p IST")
        
        # Convert approved_at to IST string for display
        if quote.get("approved_at"):
            approved_ist_time = utc_to_ist(quote["approved_at"])
            if approved_ist_time:
                quote["approved_at_ist"] = approved_ist_time.strftime("%d %b %Y, %I:%M %p IST")
        
        result.append(quote)
    return result

# Get unread RFQ count for admin notifications
@router.get("/quotes/unread/count")
async def get_unread_rfq_count(current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    """Get count of unread pending RFQs for admin notification badge"""
    count = await db.quotes.count_documents({
        "status": "pending",
        "read_by_admin": {"$ne": True}
    })
    return {"unread_count": count}

# Export quotes to Excel - MUST be before /quotes/{quote_id} routes
@router.get("/quotes/export/excel")
async def export_quotes_excel_v2(
    status: str = None,
    search: str = None,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Export quotes to Excel file. Accepts token as query param or Authorization header."""
    # Validate token from query param OR Authorization header
    current_user = None
    auth_token = token
    
    # Try to get token from Authorization header if not in query
    if not auth_token and authorization:
        if authorization.startswith("Bearer "):
            auth_token = authorization[7:]
    
    if auth_token:
        try:
            payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email:
                user = await db.users.find_one({"email": email})
                if user:
                    user["id"] = str(user["_id"])
                    current_user = user
        except Exception as e:
            logging.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Build query
        query = {}
        if current_user.get("role") != "admin":
            query["customer_email"] = current_user.get("email")
        if status and status != "all":
            query["status"] = status
        if search:
            query["$or"] = [
                {"quote_number": {"$regex": search, "$options": "i"}},
                {"customer_name": {"$regex": search, "$options": "i"}},
                {"customer_company": {"$regex": search, "$options": "i"}}
            ]
        
        quotes = await db.quotes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
        
        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Quotes"
        
        # Headers
        headers = ["Quote Number", "Customer", "Company", "Status", "Products", "Subtotal", "Discount", "Packing", "Freight", "Total", "Created Date"]
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="960018", end_color="960018", fill_type="solid")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        # Data rows
        for row, quote in enumerate(quotes, 2):
            ws.cell(row=row, column=1, value=quote.get("quote_number", "N/A"))
            ws.cell(row=row, column=2, value=quote.get("customer_name", "N/A"))
            ws.cell(row=row, column=3, value=quote.get("customer_company", "N/A"))
            ws.cell(row=row, column=4, value=quote.get("status", "N/A"))
            ws.cell(row=row, column=5, value=len(quote.get("products", [])))
            ws.cell(row=row, column=6, value=quote.get("subtotal", 0))
            ws.cell(row=row, column=7, value=quote.get("total_discount", 0))
            ws.cell(row=row, column=8, value=quote.get("packing_charges", 0))
            ws.cell(row=row, column=9, value=quote.get("shipping_cost", 0))
            ws.cell(row=row, column=10, value=quote.get("total_price", 0))
            created = quote.get("created_at")
            if created:
                ws.cell(row=row, column=11, value=created.strftime("%Y-%m-%d %H:%M") if hasattr(created, 'strftime') else str(created)[:16])
        
        # Adjust column widths
        for col in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 30)
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Quotes_Export_{get_ist_now().strftime('%Y%m%d_%H%M')}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Quote Excel export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Export quotes to PDF - MUST be before /quotes/{quote_id} routes
@router.get("/quotes/export/pdf")
async def export_quotes_pdf_v2(
    status: str = None,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Export quotes to PDF file. Accepts token as query param or Authorization header."""
    # Validate token from query param OR Authorization header
    current_user = None
    auth_token = token
    
    # Try to get token from Authorization header if not in query
    if not auth_token and authorization:
        if authorization.startswith("Bearer "):
            auth_token = authorization[7:]
    
    if auth_token:
        try:
            payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email:
                user = await db.users.find_one({"email": email})
                if user:
                    user["id"] = str(user["_id"])
                    current_user = user
        except Exception as e:
            logging.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        query = {}
        if current_user.get("role") != "admin":
            query["customer_email"] = current_user.get("email")
        if status:
            query["status"] = status
        
        quotes = await db.quotes.find(query, {
            "quote_number": 1, "customer_name": 1, "customer_company": 1,
            "total_price": 1, "status": 1, "created_at": 1, "items": 1
        }).sort("created_at", -1).limit(500).to_list(500)
        
        # Generate PDF HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Quotes Export</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #960018; border-bottom: 2px solid #960018; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background-color: #960018; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .status {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
                .approved {{ background-color: #4CAF50; color: white; }}
                .pending {{ background-color: #FF9800; color: white; }}
                .rejected {{ background-color: #f44336; color: white; }}
                .footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>Quotes Export</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <table>
                <thead>
                    <tr>
                        <th>Quote #</th>
                        <th>Customer</th>
                        <th>Items</th>
                        <th>Total</th>
                        <th>Status</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for quote in quotes:
            status_class = quote.get('status', 'pending').lower().replace('rfq_', '')
            created = quote.get('created_at', datetime.now())
            if isinstance(created, str):
                created = datetime.fromisoformat(created.replace('Z', '+00:00'))
            
            html_content += f"""
                    <tr>
                        <td>{quote.get('quote_number', 'N/A')}</td>
                        <td>{quote.get('customer_name', 'N/A')}</td>
                        <td>{len(quote.get('products', []))}</td>
                        <td>Rs. {quote.get('total_price', 0):,.2f}</td>
                        <td><span class="status {status_class}">{quote.get('status', 'N/A').upper()}</span></td>
                        <td>{created.strftime('%Y-%m-%d')}</td>
                    </tr>
            """
        
        html_content += """
                </tbody>
            </table>
            <div class="footer">
                <p>Convero - Belt Conveyor Roller Solutions</p>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF using weasyprint
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        filename = f"quotes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Quote PDF export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Mark RFQ as read by admin
@router.post("/quotes/{quote_id}/mark-read")
async def mark_quote_as_read(
    quote_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """Mark an RFQ as read by admin"""
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    result = await db.quotes.update_one(
        {"_id": obj_id},
        {"$set": {"read_by_admin": True, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"success": True, "message": "Quote marked as read"}

@router.get("/quotes/{quote_id}", response_model=QuoteInDB)
async def get_quote(quote_id: str, current_user: dict = Depends(get_current_user)):
    try:
        quote = await db.quotes.find_one({"_id": ObjectId(quote_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check permissions
    if current_user["role"] == UserRole.CUSTOMER and quote["customer_id"] != current_user.get("email"):
        raise HTTPException(status_code=403, detail="Not authorized to view this quote")
    
    # Calculate missing weights for products
    for product in quote.get("products", []):
        if not product.get("weight_kg") and not product.get("weight"):
            specs = product.get("specifications", {})
            if specs.get("pipe_diameter") and specs.get("pipe_length") and specs.get("shaft_diameter"):
                try:
                    weight = rs.calculate_roller_weight(
                        pipe_dia=float(specs.get("pipe_diameter", 0)),
                        pipe_length_mm=float(specs.get("pipe_length", 0)),
                        shaft_dia=float(specs.get("shaft_diameter", 0)),
                        pipe_type=specs.get("pipe_type", "B")
                    )
                    product["weight_kg"] = weight
                    product["weight"] = weight
                except Exception as e:
                    logging.warning(f"Could not calculate weight for product: {e}")
    
    quote["id"] = str(quote["_id"])
    del quote["_id"]
    return QuoteInDB(**quote)

@router.get("/quotes/{quote_id}/history")
async def get_quote_revision_history(
    quote_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get revision history for a specific quote - accessible by admin, sales, and the quote owner"""
    try:
        quote = await db.quotes.find_one(
            {"_id": ObjectId(quote_id)},
            {"revision_history": 1, "quote_number": 1, "customer_id": 1}
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check access: Admin/Sales can view any, Customers can only view their own
    is_admin_or_sales = current_user["role"] in [UserRole.ADMIN, UserRole.SALES]
    is_quote_owner = quote.get("customer_id") == current_user.get("email")
    
    if not is_admin_or_sales and not is_quote_owner:
        raise HTTPException(status_code=403, detail="Access denied")
    
    revision_history = quote.get("revision_history", [])
    
    # Sort by timestamp descending (most recent first)
    revision_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "quote_id": quote_id,
        "quote_number": quote.get("quote_number"),
        "revision_count": len(revision_history),
        "history": revision_history
    }

@router.get("/quotes/{quote_id}/pdf")
async def get_quote_pdf(
    quote_id: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Generate and download PDF for a specific quote/RFQ. Accepts token as query param or Authorization header."""
    # Validate token from query param OR Authorization header
    current_user = None
    auth_token = token
    
    # Try to get token from Authorization header if not in query
    if not auth_token and authorization:
        if authorization.startswith("Bearer "):
            auth_token = authorization[7:]
    
    if auth_token:
        try:
            payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email:
                user = await db.users.find_one({"email": email})
                if user:
                    user["id"] = str(user["_id"])
                    current_user = user
        except Exception as e:
            logging.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        quote = await db.quotes.find_one({"_id": ObjectId(quote_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check access permissions
    is_admin_or_sales = current_user["role"] in [UserRole.ADMIN, UserRole.SALES]
    is_quote_owner = quote.get("customer_email") == current_user.get("email")
    is_approved = quote.get("status", "").lower() == "approved"
    is_rfq = quote.get("quote_number", "").startswith("RFQ")
    
    if not is_admin_or_sales:
        if not is_quote_owner:
            raise HTTPException(status_code=403, detail="Access denied")
        # Customers can download:
        # 1. Their own RFQs (any status) - uses RFQ PDF format (no prices)
        # 2. Their own approved quotes - uses Quote PDF format (with prices)
        # Customers CANNOT download pending/rejected quotes (non-RFQ)
        if not is_rfq and not is_approved:
            raise HTTPException(status_code=403, detail="Quote not yet approved")
    
    try:
        # Prepare quote data for PDF generation
        quote_data = {
            "quote_number": quote.get("quote_number", "N/A"),
            "customer_name": quote.get("customer_name", "N/A"),
            "customer_email": quote.get("customer_email", ""),
            "customer_code": quote.get("customer_code", ""),
            "customer_company": quote.get("customer_company", ""),
            "customer_details": quote.get("customer_details", {}),
            "customer_rfq_no": quote.get("customer_rfq_no"),
            "products": quote.get("products", []),
            "subtotal": quote.get("subtotal", 0),
            "total_discount": quote.get("total_discount", 0),
            "use_item_discounts": quote.get("use_item_discounts", False),
            "packing_charges": quote.get("packing_charges", 0),
            "packing_type": quote.get("packing_type"),
            "shipping_cost": quote.get("shipping_cost", 0),
            "delivery_location": quote.get("delivery_location"),
            "total_price": quote.get("total_price", 0),
            "notes": quote.get("notes"),
            "status": quote.get("status"),
            "created_at": quote.get("created_at"),
            "approved_at": quote.get("approved_at"),
            "original_rfq_number": quote.get("original_rfq_number"),
            "commercial_terms": quote.get("commercial_terms", {}),
        }
        
        # Use the correct PDF generator based on document type
        # RFQs use the RFQ PDF format (same as email) - no prices shown
        # Quotes use the Quote PDF format - with prices
        if is_rfq:
            # Use the same RFQ PDF generator that's used for emails
            pdf_bytes = generate_rfq_pdf(quote_data)
        else:
            # Use the Quote PDF generator for approved quotes
            pdf_bytes = generate_quote_pdf(quote_data)
        
        # Create filename
        safe_quote_number = quote.get("quote_number", "Quote").replace("/", "-")
        filename = f"{safe_quote_number}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"PDF generation error for quote {quote_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

@router.put("/quotes/{quote_id}", response_model=QuoteInDB)
async def update_quote(
    quote_id: str,
    quote_update: QuoteUpdate,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    # Fetch the current quote to track changes
    existing_quote = await db.quotes.find_one({"_id": obj_id})
    if not existing_quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    update_dict = quote_update.dict(exclude_unset=True)
    update_dict["updated_at"] = datetime.utcnow()
    
    # Convert products to dict format if present
    if "products" in update_dict and update_dict["products"]:
        update_dict["products"] = [p.dict() if hasattr(p, 'dict') else p for p in update_dict["products"]]
    
    # Track changes for revision history
    changes = {}
    tracked_fields = [
        ('discount_percent', 'Discount %'),
        ('total_discount', 'Total Discount'),
        ('packing_type', 'Packing Type'),
        ('packing_charges', 'Packing Charges'),
        ('shipping_cost', 'Freight'),
        ('delivery_location', 'Delivery Pincode'),
        ('total_price', 'Grand Total'),
        ('use_item_discounts', 'Discount Mode'),
        ('status', 'Status'),
    ]
    
    for field, label in tracked_fields:
        if field in update_dict:
            old_value = existing_quote.get(field)
            new_value = update_dict[field]
            # Only track if value actually changed
            if old_value != new_value:
                # Format values for display
                if field == 'packing_type':
                    old_display = _format_packing_type(old_value) if old_value else 'None'
                    new_display = _format_packing_type(new_value) if new_value else 'None'
                elif field in ['total_discount', 'packing_charges', 'shipping_cost', 'total_price']:
                    old_display = f"Rs. {old_value:,.2f}" if old_value else "Rs. 0.00"
                    new_display = f"Rs. {new_value:,.2f}" if new_value else "Rs. 0.00"
                elif field == 'discount_percent':
                    old_display = f"{old_value}%" if old_value else "0%"
                    new_display = f"{new_value}%" if new_value else "0%"
                elif field == 'use_item_discounts':
                    old_display = "Per-Item" if old_value else "Total"
                    new_display = "Per-Item" if new_value else "Total"
                else:
                    old_display = str(old_value) if old_value else 'None'
                    new_display = str(new_value) if new_value else 'None'
                
                changes[label] = {'old': old_display, 'new': new_display}
    
    # Check for product quantity changes
    if 'products' in update_dict:
        old_products = existing_quote.get('products', [])
        new_products = update_dict['products']
        qty_changes = []
        for i, new_p in enumerate(new_products):
            if i < len(old_products):
                old_qty = old_products[i].get('quantity', 0)
                new_qty = new_p.get('quantity', 0)
                if old_qty != new_qty:
                    product_name = new_p.get('product_name') or new_p.get('product_id', f'Item {i+1}')
                    qty_changes.append(f"{product_name}: {old_qty} → {new_qty}")
        if qty_changes:
            changes['Product Quantities'] = {'old': '', 'new': ', '.join(qty_changes)}
    
    # Create revision history entry if there are changes
    if changes:
        # Build summary
        change_summary_parts = []
        for label, vals in changes.items():
            if label == 'Product Quantities':
                change_summary_parts.append(f"Updated quantities")
            else:
                change_summary_parts.append(f"{label}: {vals['old']} → {vals['new']}")
        
        revision_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "changed_by": current_user.get('email', 'Unknown'),
            "changed_by_name": current_user.get('name', current_user.get('email', 'Unknown')),
            "action": "updated",
            "changes": changes,
            "summary": "; ".join(change_summary_parts)
        }
        
        # Append to revision history
        await db.quotes.update_one(
            {"_id": obj_id},
            {"$push": {"revision_history": revision_entry}}
        )
    
    # Apply the update
    result = await db.quotes.update_one(
        {"_id": obj_id},
        {"$set": update_dict}
    )
    
    updated_quote = await db.quotes.find_one({"_id": obj_id})
    updated_quote["id"] = str(updated_quote["_id"])
    del updated_quote["_id"]
    
    return QuoteInDB(**updated_quote)

def _format_packing_type(packing_type: str) -> str:
    """Format packing type for display"""
    if packing_type == 'standard':
        return 'Standard (1%)'
    elif packing_type == 'pallet':
        return 'Pallet (4%)'
    elif packing_type == 'wooden_box':
        return 'Wooden Box (8%)'
    elif packing_type and packing_type.startswith('custom_'):
        percent = packing_type.split('_')[1] if '_' in packing_type else '0'
        return f'Custom ({percent}%)'
    return packing_type or 'None'

# ============= RFQ APPROVAL WORKFLOW =============

async def send_quote_approval_email(quote_data: dict, customer_email: str):
    """Send approved quote email to customer and admins WITH PDF ATTACHMENT"""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logging.warning("Email service not configured, skipping quote approval notification")
        return False
    
    # Send to customer + admin emails
    recipient_emails = [customer_email] + ADMIN_RFQ_EMAILS
    
    try:
        msg = MIMEMultipart('mixed')
        msg['From'] = f"Convero Solutions <{GMAIL_USER}>"
        msg['To'] = ', '.join(recipient_emails)
        msg['Subject'] = f"Quotation Approved - {quote_data.get('quote_number')} | Convero Solutions"
        
        # Get product details
        products = quote_data.get('products', [])
        products_html = ""
        grand_total_weight = 0
        for p in products:
            qty = p.get('quantity', 1)
            unit_weight = p.get('weight', 0) or p.get('specifications', {}).get('weight', 0) or 0
            total_weight = unit_weight * qty
            grand_total_weight += total_weight
            unit_weight_str = f"{unit_weight:.2f}" if unit_weight > 0 else "-"
            total_weight_str = f"{total_weight:.2f}" if total_weight > 0 else "-"
            products_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px;">{p.get('product_name', 'Product')}</td>
                <td style="padding: 12px; text-align: center;">{qty}</td>
                <td style="padding: 12px; text-align: right;">{unit_weight_str}</td>
                <td style="padding: 12px; text-align: right;">{total_weight_str}</td>
            </tr>
            """
        # Add grand total weight row
        weight_total_row = f"""
        <tr style="background: #f0f9ff; font-weight: bold;">
            <td colspan="3" style="padding: 12px; text-align: right;">Grand Total Weight:</td>
            <td style="padding: 12px; text-align: right;">{grand_total_weight:.2f} kg</td>
        </tr>
        """ if grand_total_weight > 0 else ""
        
        # Calculate grand total properly (same as PDF)
        # Get subtotal after discount - recalculate from products
        use_item_discounts = quote_data.get('use_item_discounts', False)
        subtotal_raw = quote_data.get('subtotal', 0)
        total_discount_raw = quote_data.get('total_discount', 0)
        overall_discount_percent = (total_discount_raw / subtotal_raw * 100) if subtotal_raw > 0 else 0
        
        calculated_subtotal = 0
        for p in products:
            qty = p.get('quantity', 0)
            unit_price = p.get('unit_price', 0)
            
            # Use individual item discount if available, otherwise use overall discount percentage
            if use_item_discounts and p.get('item_discount_percent') is not None:
                item_discount_percent = p.get('item_discount_percent', 0)
            else:
                item_discount_percent = overall_discount_percent
            
            value_after_discount = unit_price * (1 - item_discount_percent / 100)
            line_total = qty * value_after_discount
            calculated_subtotal += line_total
        
        subtotal_after_discount = calculated_subtotal
        packing = quote_data.get('packing_charges', 0) or 0
        shipping = quote_data.get('shipping_cost', 0) or 0
        taxable_amount = subtotal_after_discount + packing + shipping
        grand_total = taxable_amount * 1.18  # Including 18% GST
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Calibri, Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 20px auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: #960018; color: white; padding: 20px; text-align: center; }}
                .quote-number {{ font-size: 24px; font-weight: bold; color: #960018; }}
                .content {{ padding: 30px; }}
                .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .info-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .info-value {{ font-size: 16px; font-weight: bold; color: #333; }}
                .total-box {{ background: #960018; color: white; padding: 20px; text-align: center; margin-top: 20px; border-radius: 8px; }}
                .approved-badge {{ display: inline-block; background: #4CAF50; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-bottom: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">CONVERO SOLUTIONS</h1>
                    <p style="margin: 10px 0 0 0; font-size: 14px;">Your Quotation Has Been Approved!</p>
                </div>
                <div class="content">
                    <div style="text-align: center;">
                        <span class="approved-badge">✓ APPROVED</span>
                        <p class="quote-number">{quote_data.get('quote_number')}</p>
                    </div>
                    
                    <div class="info-box">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <div class="info-label">Customer Name</div>
                                <div class="info-value">{quote_data.get('customer_name')}</div>
                            </div>
                            <div>
                                <div class="info-label">Company</div>
                                <div class="info-value">{quote_data.get('customer_company', 'N/A')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <h3 style="color: #333; border-bottom: 2px solid #960018; padding-bottom: 10px;">Products</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 12px; text-align: left;">Product</th>
                            <th style="padding: 12px; text-align: center;">Qty</th>
                            <th style="padding: 12px; text-align: right;">Wt/Pc (kg)</th>
                            <th style="padding: 12px; text-align: right;">Total Wt (kg)</th>
                        </tr>
                        {products_html}
                        {weight_total_row}
                    </table>
                    
                    <div class="total-box">
                        <span style="font-size: 14px;">TOTAL VALUE</span>
                        <span style="font-size: 24px; font-weight: bold; margin-left: 10px;">Rs. {grand_total:,.2f}</span>
                    </div>
                    
                    {f'''<div class="info-box" style="display: flex; gap: 30px; flex-wrap: wrap;">
                        {f'<div><div class="info-label">Packing Type</div><div class="info-value">{quote_data.get("packing_type", "").replace("_", " ").title() if quote_data.get("packing_type") else "N/A"}</div></div>' if quote_data.get('packing_type') else ''}
                        {f'<div><div class="info-label">Delivery Pincode</div><div class="info-value">{quote_data.get("delivery_location")}</div></div>' if quote_data.get('delivery_location') else ''}
                    </div>''' if quote_data.get('packing_type') or quote_data.get('delivery_location') else ''}
                    
                    <div style="margin-top: 30px; padding: 20px; background: #E8F5E9; border-radius: 8px; text-align: center;">
                        <p style="margin: 0; color: #2E7D32; font-weight: bold;">
                            This quotation has been approved and is ready for processing.
                        </p>
                        <p style="margin: 10px 0 0 0; color: #666;">
                            Please find the detailed quotation PDF attached.
                        </p>
                        <p style="margin: 10px 0 0 0; color: #666;">
                            For any queries, please contact us at info@convero.in
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create message body
        msg_alternative = MIMEMultipart('alternative')
        msg_alternative.attach(MIMEText(html_content, 'html'))
        msg.attach(msg_alternative)
        
        # Generate and attach Quote PDF (with prices)
        try:
            quote_pdf_bytes = generate_quote_pdf(quote_data)
            pdf_filename = f"{quote_data.get('quote_number', 'Quote').replace('/', '-')}.pdf"
            
            pdf_attachment = MIMEApplication(quote_pdf_bytes, _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            msg.attach(pdf_attachment)
            
            logging.info(f"Quote PDF attached to approval email: {pdf_filename}")
        except Exception as pdf_error:
            logging.error(f"Failed to generate/attach Quote PDF: {str(pdf_error)}")
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipient_emails, msg.as_string())
        
        logging.info(f"Quote approval email sent with PDF for: {quote_data.get('quote_number')}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send quote approval email: {str(e)}")
        return False

@router.post("/quotes/{quote_id}/approve")
async def approve_rfq(
    quote_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """
    Approve an RFQ and convert it to a Quote.
    - Changes quote_number from RFQ/XX-XX/XXXX to Q/XX-XX/XXXX
    - Sets status to APPROVED
    - Sends email to customer and admins
    """
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    # Get the quote
    quote = await db.quotes.find_one({"_id": obj_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check if it's an RFQ (has RFQ prefix)
    old_number = quote.get("quote_number", "")
    if not old_number.startswith("RFQ"):
        raise HTTPException(status_code=400, detail="This is already a Quote, not an RFQ")
    
    if quote.get("status") == QuoteStatus.APPROVED:
        raise HTTPException(status_code=400, detail="This RFQ has already been approved")
    
    # Generate new Quote number
    new_quote_number = await generate_quote_number()
    ist_now = get_ist_now()
    
    # Auto-calculate freight if delivery_location (pincode) is provided
    freight_details = quote.get("freight_details") or {}
    shipping_cost = quote.get("shipping_cost", 0)
    delivery_location = quote.get("delivery_location")
    total_price = quote.get("total_price", 0)
    
    # Check if admin manually set freight (freight_amount key exists in freight_details)
    admin_set_freight = "freight_amount" in freight_details
    
    # Calculate total weight from products
    products = quote.get("products", [])
    total_weight = 0.0
    for product in products:
        specs = product.get("specifications") or {}  # Handle null specifications
        item_weight = specs.get("weight_kg", 0) or product.get("weight_kg", 0) or product.get("weight", 0) or 0
        quantity = product.get("quantity", 1)
        total_weight += item_weight * quantity
    
    # Only auto-calculate freight if:
    # 1. Pincode is provided AND
    # 2. Admin did NOT manually set freight (no freight_amount in freight_details)
    if delivery_location and not admin_set_freight:
        try:
            freight_calc = rs.calculate_freight_charges(total_weight, delivery_location)
            freight_details = {
                "destination_pincode": delivery_location,
                "total_weight_kg": round(total_weight, 2),
                "distance_km": freight_calc["distance_km"],
                "freight_rate_per_kg": freight_calc["freight_rate_per_kg"],
                "freight_charges": freight_calc["freight_charges"],
                "auto_calculated": True
            }
            shipping_cost = freight_calc["freight_charges"]
            # Update total price to include freight
            subtotal_before_freight = quote.get("subtotal", 0) - quote.get("total_discount", 0) + quote.get("packing_charges", 0)
            gst_amount = subtotal_before_freight * 0.18  # 18% GST
            total_price = subtotal_before_freight + gst_amount + shipping_cost
            logging.info(f"Auto-calculated freight for quote {old_number}: Rs. {shipping_cost} for {total_weight} kg to {delivery_location}")
        except Exception as e:
            logging.warning(f"Could not auto-calculate freight: {str(e)}")
    
    # Update the quote
    update_result = await db.quotes.update_one(
        {"_id": obj_id},
        {"$set": {
            "quote_number": new_quote_number,
            "original_rfq_number": old_number,
            "quote_type": "quote",
            "status": QuoteStatus.APPROVED,
            "approved_by": current_user["email"],
            "approved_at": ist_now,
            "updated_at": ist_now,
            "freight_details": freight_details,
            "shipping_cost": shipping_cost,
            "total_price": total_price,
            "revision_number": 0,  # First approval is R0, revisions will be R1, R2, etc.
            "revision_history": []  # Initialize empty revision history
        }}
    )
    
    if update_result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update quote")
    
    # Update customer type to "quoted" if they were "registered"
    customer_id = quote.get("customer_id")
    if customer_id:
        try:
            # Find user by customer_id
            user = await db.users.find_one({"_id": ObjectId(customer_id)})
            if user and user.get("email"):
                # Find and update customer record by email
                await db.customers.update_one(
                    {"email": user.get("email"), "customer_type": "registered"},
                    {"$set": {"customer_type": "quoted"}}
                )
                logging.info(f"Updated customer {user.get('email')} type to 'quoted'")
        except Exception as e:
            logging.warning(f"Could not update customer type: {str(e)}")
    
    # Get updated quote
    updated_quote = await db.quotes.find_one({"_id": obj_id})
    updated_quote["id"] = str(updated_quote["_id"])
    
    # Send approval email to customer and admins with COMPLETE quote data
    customer_email = quote.get("customer_email")
    if customer_email:
        # Pass the complete updated quote for PDF generation - include ALL fields
        # Use the newly calculated freight values
        await send_quote_approval_email({
            "quote_number": new_quote_number,
            "original_rfq_number": old_number,
            "customer_name": quote.get("customer_name"),
            "customer_company": quote.get("customer_company"),
            "customer_code": quote.get("customer_code"),
            "customer_details": quote.get("customer_details") or {},
            "products": quote.get("products", []),
            "subtotal": quote.get("subtotal", 0),
            "total_discount": quote.get("total_discount", 0),
            "use_item_discounts": quote.get("use_item_discounts", False),
            "discount_percent": quote.get("discount_percent", 0),
            "packing_charges": quote.get("packing_charges", 0),
            "packing_type": quote.get("packing_type"),
            "shipping_cost": shipping_cost,  # Use auto-calculated value
            "delivery_location": delivery_location,
            "total_price": total_price,  # Use updated total
            "notes": quote.get("notes"),
            "approved_at": updated_quote.get("approved_at"),
            "cost_breakdown": quote.get("cost_breakdown"),
            "pricing_details": quote.get("pricing_details"),
            "freight_details": freight_details,  # Use auto-calculated freight details
            "commercial_terms": quote.get("commercial_terms", {})
        }, customer_email)
    
    # Send push notification to customer about approval
    await send_push_notification_to_user(
        user_email=customer_email,
        title="Quote Approved! ✅",
        body=f"Your quote {new_quote_number} has been approved. Total: ₹{total_price:,.2f}",
        data={
            "type": "quote_approved",
            "quote_id": str(quote["_id"]),
            "quote_number": new_quote_number,
            "total_price": total_price
        }
    )
    
    return {
        "message": "RFQ approved successfully",
        "old_number": old_number,
        "new_quote_number": new_quote_number,
        "status": QuoteStatus.APPROVED,
        "freight_auto_calculated": freight_details.get("auto_calculated", False) if freight_details else False,
        "shipping_cost": shipping_cost,
        "freight_details": freight_details
    }

@router.post("/quotes/{quote_id}/reject")
async def reject_rfq(
    quote_id: str,
    rejection: QuoteReject,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """
    Reject an RFQ with a reason.
    - Sets status to REJECTED
    - Stores rejection reason
    - Sends email notification to customer
    """
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    # Get the quote
    quote = await db.quotes.find_one({"_id": obj_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check if it's an RFQ
    quote_number = quote.get("quote_number", "")
    if not quote_number.startswith("RFQ"):
        raise HTTPException(status_code=400, detail="Only RFQs can be rejected")
    
    if quote.get("status") == QuoteStatus.REJECTED:
        raise HTTPException(status_code=400, detail="This RFQ has already been rejected")
    
    if quote.get("status") == QuoteStatus.APPROVED:
        raise HTTPException(status_code=400, detail="This RFQ has already been approved")
    
    # Map rejection reasons to human-readable messages
    rejection_reasons = {
        "low_quantity": "Rejected due to low quantity",
        "low_amount": "Rejected due to low amount",
        "not_in_range": "Rejected due to product is not within the manufacturing range"
    }
    
    reason_text = rejection_reasons.get(rejection.reason, rejection.reason)
    ist_now = get_ist_now()
    
    # Update the quote
    update_result = await db.quotes.update_one(
        {"_id": obj_id},
        {"$set": {
            "status": QuoteStatus.REJECTED,
            "rejection_reason": rejection.reason,
            "rejection_reason_text": reason_text,
            "rejection_message": rejection.custom_message,
            "rejected_by": current_user["email"],
            "rejected_at": ist_now,
            "updated_at": ist_now
        }}
    )
    
    if update_result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to reject RFQ")
    
    # Send rejection email to customer
    customer_email = quote.get("customer_email")
    customer_name = quote.get("customer_name", "Customer")
    
    if customer_email and GMAIL_USER and GMAIL_APP_PASSWORD:
        try:
            # Create rejection email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"RFQ {quote_number} - Status Update"
            msg['From'] = f"Convero Solutions <{GMAIL_USER}>"
            msg['To'] = customer_email
            msg['Cc'] = "design@convero.in, info@convero.in"
            
            # HTML email content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #960018; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px; }}
                    .reason-box {{ background: #fff5f5; border-left: 4px solid #960018; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0; font-size: 24px;">RFQ Status Update</h1>
                    </div>
                    <div class="content">
                        <p>Dear {customer_name},</p>
                        <p>Thank you for your Request for Quotation <strong>{quote_number}</strong>.</p>
                        <p>After careful review, we regret to inform you that we are unable to proceed with your request at this time.</p>
                        
                        <div class="reason-box">
                            <strong>Reason:</strong><br>
                            {reason_text}
                            {f'<br><br><strong>Additional Note:</strong><br>{rejection.custom_message}' if rejection.custom_message else ''}
                        </div>
                        
                        <p>We encourage you to submit a new request with revised specifications. Our team is always happy to assist you in finding the right solution for your needs.</p>
                        <p>If you have any questions, please don't hesitate to contact us at info@convero.in</p>
                        <p>Best regards,<br>Convero Solutions Team</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message from Convero Solutions.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            RFQ Status Update - Convero Solutions
            
            Dear {customer_name},
            
            Thank you for your Request for Quotation {quote_number}.
            
            After careful review, we regret to inform you that we are unable to proceed with your request at this time.
            
            Reason: {reason_text}
            {f'Additional Note: {rejection.custom_message}' if rejection.custom_message else ''}
            
            We encourage you to submit a new request with revised specifications.
            
            If you have any questions, please contact us at info@convero.in
            
            Best regards,
            Convero Solutions Team
            """
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_USER, [customer_email, "design@convero.in", "info@convero.in"], msg.as_string())
            
            logging.info(f"Rejection email sent for RFQ: {quote_number}")
        except Exception as e:
            logging.error(f"Failed to send rejection email: {str(e)}")
    
    # Send push notification to customer about rejection
    await send_push_notification_to_user(
        user_email=customer_email,
        title="RFQ Update ❌",
        body=f"Your RFQ {quote_number} was not approved. Reason: {reason_text}",
        data={
            "type": "rfq_rejected",
            "quote_id": quote_id,
            "quote_number": quote_number,
            "reason": reason_text
        }
    )
    
    return {
        "message": "RFQ rejected successfully",
        "quote_number": quote_number,
        "reason": reason_text,
        "status": QuoteStatus.REJECTED
    }

@router.put("/quotes/{quote_id}/discount")
async def update_quote_discount(
    quote_id: str,
    discount_percent: float,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """Update discount on a quote before approval"""
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    quote = await db.quotes.find_one({"_id": obj_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Calculate new prices
    subtotal = quote.get("subtotal", 0)
    discount_amount = (subtotal * discount_percent) / 100
    new_total = subtotal - discount_amount + quote.get("packing_charges", 0) + quote.get("shipping_cost", 0)
    
    ist_now = get_ist_now()
    
    # Update quote
    await db.quotes.update_one(
        {"_id": obj_id},
        {"$set": {
            "total_discount": discount_amount,
            "discount_percent": discount_percent,
            "total_price": new_total,
            "updated_at": ist_now,
            "updated_by": current_user["email"]
        }}
    )
    
    return {
        "message": "Discount updated successfully",
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "new_total_price": new_total
    }

# ============= QUOTE REVISION SYSTEM =============

async def send_quote_revision_email(quote_data: dict, customer_email: str, revision_number: str):
    """Send revised quote email to customer and admins WITH PDF ATTACHMENT"""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logging.warning("Email service not configured, skipping revision notification")
        return False
    
    # Send to customer + admin emails
    recipient_emails = [customer_email] + ADMIN_RFQ_EMAILS
    
    try:
        msg = MIMEMultipart('mixed')
        msg['From'] = f"Convero Solutions <{GMAIL_USER}>"
        msg['To'] = ', '.join(recipient_emails)
        msg['Subject'] = f"Revised Quotation - {quote_data.get('quote_number')} | Convero Solutions"
        
        # Get product details
        products = quote_data.get('products', [])
        products_html = ""
        grand_total_weight = 0
        for p in products:
            qty = p.get('quantity', 1)
            unit_weight = (
                p.get('weight') or 
                p.get('weight_kg') or 
                p.get('specifications', {}).get('weight') or 
                p.get('specifications', {}).get('weight_kg') or 
                p.get('specifications', {}).get('single_roller_weight_kg') or 
                0
            )
            total_weight = unit_weight * qty
            grand_total_weight += total_weight
            unit_weight_str = f"{unit_weight:.2f}" if unit_weight > 0 else "-"
            total_weight_str = f"{total_weight:.2f}" if total_weight > 0 else "-"
            products_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px;">{p.get('product_name', 'Product')}</td>
                <td style="padding: 12px; text-align: center;">{qty}</td>
                <td style="padding: 12px; text-align: right;">{unit_weight_str}</td>
                <td style="padding: 12px; text-align: right;">{total_weight_str}</td>
            </tr>
            """
        # Add grand total weight row
        weight_total_row = f"""
        <tr style="background: #f0f9ff; font-weight: bold;">
            <td colspan="3" style="padding: 12px; text-align: right;">Grand Total Weight:</td>
            <td style="padding: 12px; text-align: right;">{grand_total_weight:.2f} kg</td>
        </tr>
        """ if grand_total_weight > 0 else ""
        
        discount_percent = quote_data.get('discount_percent', 0)
        discount_amount = quote_data.get('total_discount', 0)
        
        # Calculate the revised total price
        new_total_price = quote_data.get('total_price', 0)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Calibri, Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 20px auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: #960018; color: white; padding: 20px; text-align: center; }}
                .revision-badge {{ display: inline-block; background: #FF9500; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-bottom: 10px; }}
                .quote-number {{ font-size: 24px; font-weight: bold; color: #960018; }}
                .content {{ padding: 30px; }}
                .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .discount-box {{ background: #E8F5E9; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
                .total-box {{ background: #960018; color: white; padding: 20px; text-align: center; margin-top: 20px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">CONVERO SOLUTIONS</h1>
                    <p style="margin: 10px 0 0 0; font-size: 14px;">Revised Quotation</p>
                </div>
                <div class="content">
                    <div style="text-align: center;">
                        <span class="revision-badge">{revision_number}</span>
                        <p class="quote-number">{quote_data.get('quote_number')}</p>
                    </div>
                    
                    <div class="info-box">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <div style="font-size: 12px; color: #666;">Customer Name</div>
                                <div style="font-weight: bold;">{quote_data.get('customer_name')}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #666;">Company</div>
                                <div style="font-weight: bold;">{quote_data.get('customer_company', 'N/A')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <h3 style="color: #333; border-bottom: 2px solid #960018; padding-bottom: 10px;">Products</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 12px; text-align: left;">Product</th>
                            <th style="padding: 12px; text-align: center;">Qty</th>
                            <th style="padding: 12px; text-align: right;">Wt/Pc (kg)</th>
                            <th style="padding: 12px; text-align: right;">Total Wt (kg)</th>
                        </tr>
                        {products_html}
                        {weight_total_row}
                    </table>
                    
                    <div class="total-box">
                        <span style="font-size: 14px;">REVISED TOTAL</span>
                        <span style="font-size: 28px; font-weight: bold; margin-left: 10px;">Rs. {new_total_price:,.2f}</span>
                    </div>
                    
                    <div style="margin-top: 30px; padding: 20px; background: #FFF3E0; border-radius: 8px; text-align: center;">
                        <p style="margin: 0; color: #E65100; font-weight: bold;">
                            This is a revised quotation. Please review the updated pricing.
                        </p>
                        <p style="margin: 10px 0 0 0; color: #666;">
                            Please find the detailed revised quotation PDF attached.
                        </p>
                        <p style="margin: 10px 0 0 0; color: #666;">
                            For any queries, please contact us at info@convero.in
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create message body
        msg_alternative = MIMEMultipart('alternative')
        msg_alternative.attach(MIMEText(html_content, 'html'))
        msg.attach(msg_alternative)
        
        # Generate and attach Quote PDF (with prices)
        try:
            quote_pdf_bytes = generate_quote_pdf(quote_data)
            pdf_filename = f"{quote_data.get('quote_number', 'Quote').replace('/', '-')}-{revision_number.replace(' ', '-')}.pdf"
            
            pdf_attachment = MIMEApplication(quote_pdf_bytes, _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            msg.attach(pdf_attachment)
            
            logging.info(f"Revised Quote PDF attached: {pdf_filename}")
        except Exception as pdf_error:
            logging.error(f"Failed to generate/attach revised Quote PDF: {str(pdf_error)}")
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipient_emails, msg.as_string())
        
        logging.info(f"Quote revision email sent with PDF for: {quote_data.get('quote_number')} - {revision_number}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send quote revision email: {str(e)}")
        return False

class QuoteRevisionRequest(BaseModel):
    discount_percent: float
    notes: Optional[str] = None

@router.post("/quotes/{quote_id}/revise")
async def create_quote_revision(
    quote_id: str,
    revision_data: QuoteRevisionRequest,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """
    Create a revision of an approved quote with new discount.
    - Adds revision number (R1, R2, etc.) to quote
    - Sends email to customer and admins
    """
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    # Get the quote
    quote = await db.quotes.find_one({"_id": obj_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check if it's an approved quote
    if quote.get("status") != QuoteStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only approved quotes can be revised")
    
    # Get current revision number
    current_revision = quote.get("revision_number", 0)
    new_revision = current_revision + 1
    revision_label = f"R{new_revision}"
    
    # Calculate new prices with new discount
    subtotal = quote.get("subtotal", 0)
    discount_amount = (subtotal * revision_data.discount_percent) / 100
    new_total = subtotal - discount_amount + quote.get("packing_charges", 0) + quote.get("shipping_cost", 0)
    
    ist_now = get_ist_now()
    
    # Store revision history
    revision_history = quote.get("revision_history", [])
    revision_history.append({
        "revision": revision_label,
        "discount_percent": revision_data.discount_percent,
        "discount_amount": discount_amount,
        "total_price": new_total,
        "revised_by": current_user["email"],
        "revised_at": ist_now,
        "notes": revision_data.notes
    })
    
    # Update quote
    update_result = await db.quotes.update_one(
        {"_id": obj_id},
        {"$set": {
            "total_discount": discount_amount,
            "discount_percent": revision_data.discount_percent,
            "total_price": new_total,
            "revision_number": new_revision,
            "current_revision": revision_label,
            "revision_history": revision_history,
            "updated_at": ist_now,
            "updated_by": current_user["email"]
        }}
    )
    
    if update_result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to create revision")
    
    # Get updated quote
    updated_quote = await db.quotes.find_one({"_id": obj_id})
    
    # Send revision email to customer and admins with COMPLETE quote data
    customer_email = quote.get("customer_email")
    if customer_email:
        await send_quote_revision_email({
            "quote_number": quote.get("quote_number"),
            "original_rfq_number": quote.get("original_rfq_number"),
            "customer_name": quote.get("customer_name"),
            "customer_company": quote.get("customer_company"),
            "customer_code": quote.get("customer_code"),
            "customer_details": quote.get("customer_details") or {},
            "products": quote.get("products", []),
            "subtotal": quote.get("subtotal", 0),
            "discount_percent": revision_data.discount_percent,
            "total_discount": discount_amount,
            "use_item_discounts": quote.get("use_item_discounts", False),
            "packing_charges": quote.get("packing_charges", 0),
            "shipping_cost": quote.get("shipping_cost", 0),
            "delivery_location": quote.get("delivery_location"),
            "total_price": new_total,
            "notes": quote.get("notes"),
            "approved_at": quote.get("approved_at")
        }, customer_email, revision_label)
    
    return {
        "message": f"Quote revised successfully - {revision_label}",
        "quote_number": quote.get("quote_number"),
        "revision": revision_label,
        "discount_percent": revision_data.discount_percent,
        "discount_amount": discount_amount,
        "new_total_price": new_total,
        "email_sent": customer_email is not None
    }


@router.post("/quotes/{quote_id}/save-and-mail")
async def save_quote_and_mail(
    quote_id: str,
    quote_update: QuoteUpdate,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """
    Save all changes to a quote AND send email notification.
    This is for approved quotes when admin edits and wants to notify customer.
    """
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    # Get the quote
    quote = await db.quotes.find_one({"_id": obj_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check if it's an approved quote
    if quote.get("status") != QuoteStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only approved quotes can be revised")
    
    # Get current revision number
    current_revision_num = quote.get("revision_number", 0)
    new_revision_num = current_revision_num + 1
    revision_label = f"R{new_revision_num}"
    
    ist_now = get_ist_now()
    
    # Prepare update data
    update_dict = quote_update.dict(exclude_unset=True)
    update_dict["updated_at"] = ist_now
    update_dict["updated_by"] = current_user["email"]
    update_dict["revision_number"] = new_revision_num
    update_dict["current_revision"] = revision_label
    
    # Convert products to dict format if present
    if "products" in update_dict and update_dict["products"]:
        update_dict["products"] = [p.dict() if hasattr(p, 'dict') else p for p in update_dict["products"]]
    
    # Track changes for revision history
    changes = {}
    tracked_fields = [
        ('discount_percent', 'Discount %'),
        ('total_discount', 'Total Discount'),
        ('packing_type', 'Packing Type'),
        ('packing_charges', 'Packing Charges'),
        ('shipping_cost', 'Freight'),
        ('delivery_location', 'Delivery Pincode'),
        ('total_price', 'Grand Total'),
    ]
    
    for field, label in tracked_fields:
        if field in update_dict:
            old_value = quote.get(field)
            new_value = update_dict[field]
            if old_value != new_value:
                if field == 'packing_type':
                    old_display = _format_packing_type(old_value) if old_value else 'None'
                    new_display = _format_packing_type(new_value) if new_value else 'None'
                elif field in ['total_discount', 'packing_charges', 'shipping_cost', 'total_price']:
                    old_display = f"Rs. {old_value:,.2f}" if old_value else "Rs. 0.00"
                    new_display = f"Rs. {new_value:,.2f}" if new_value else "Rs. 0.00"
                elif field == 'discount_percent':
                    old_display = f"{old_value}%" if old_value else "0%"
                    new_display = f"{new_value}%" if new_value else "0%"
                else:
                    old_display = str(old_value) if old_value else 'None'
                    new_display = str(new_value) if new_value else 'None'
                changes[label] = {'old': old_display, 'new': new_display}
    
    # Check for product quantity changes
    if 'products' in update_dict:
        old_products = quote.get('products', [])
        new_products = update_dict['products']
        qty_changes = []
        for i, new_p in enumerate(new_products):
            if i < len(old_products):
                old_qty = old_products[i].get('quantity', 0)
                new_qty = new_p.get('quantity', 0)
                if old_qty != new_qty:
                    product_name = new_p.get('product_name') or new_p.get('product_id', f'Item {i+1}')
                    qty_changes.append(f"{product_name}: {old_qty} → {new_qty}")
        if qty_changes:
            changes['Product Quantities'] = {'old': '', 'new': ', '.join(qty_changes)}
    
    # Create revision history entry
    change_summary_parts = []
    for label, vals in changes.items():
        if label == 'Product Quantities':
            change_summary_parts.append("Updated quantities")
        else:
            change_summary_parts.append(f"{label}: {vals['old']} → {vals['new']}")
    
    revision_entry = {
        "timestamp": ist_now.isoformat() if hasattr(ist_now, 'isoformat') else str(ist_now),
        "changed_by": current_user.get('email', 'Unknown'),
        "changed_by_name": current_user.get('name', current_user.get('email', 'Unknown')),
        "action": "revised",
        "changes": changes,
        "summary": f"{revision_label}: " + ("; ".join(change_summary_parts) if change_summary_parts else "Quote revised")
    }
    
    # Update the quote
    await db.quotes.update_one(
        {"_id": obj_id},
        {
            "$set": update_dict,
            "$push": {"revision_history": revision_entry}
        }
    )
    
    # Get updated quote for email
    updated_quote = await db.quotes.find_one({"_id": obj_id})
    
    # Send revision email to customer and admins
    customer_email = quote.get("customer_email")
    email_sent = False
    if customer_email:
        try:
            await send_quote_revision_email({
                "quote_number": updated_quote.get("quote_number"),
                "original_rfq_number": updated_quote.get("original_rfq_number"),
                "customer_name": updated_quote.get("customer_name"),
                "customer_company": updated_quote.get("customer_company"),
                "customer_code": updated_quote.get("customer_code"),
                "customer_details": updated_quote.get("customer_details") or {},
                "products": updated_quote.get("products", []),
                "subtotal": updated_quote.get("subtotal", 0),
                "discount_percent": updated_quote.get("discount_percent", 0),
                "total_discount": updated_quote.get("total_discount", 0),
                "use_item_discounts": updated_quote.get("use_item_discounts", False),
                "packing_charges": updated_quote.get("packing_charges", 0),
                "packing_type": updated_quote.get("packing_type"),
                "shipping_cost": updated_quote.get("shipping_cost", 0),
                "delivery_location": updated_quote.get("delivery_location"),
                "total_price": updated_quote.get("total_price", 0),
                "notes": updated_quote.get("notes"),
                "approved_at": updated_quote.get("approved_at"),
                "commercial_terms": updated_quote.get("commercial_terms", {})
            }, customer_email, revision_label)
            email_sent = True
        except Exception as e:
            print(f"Failed to send email: {e}")
    
    # Return response
    updated_quote["id"] = str(updated_quote["_id"])
    del updated_quote["_id"]
    
    return {
        "message": f"Quote updated and email sent - {revision_label}",
        "quote_number": updated_quote.get("quote_number"),
        "revision": revision_label,
        "total_price": updated_quote.get("total_price"),
        "email_sent": email_sent,
        "quote": QuoteInDB(**updated_quote)
    }

# ============= ATTACHMENT DOWNLOAD ROUTES =============

@router.get("/quotes/{quote_id}/attachments")
async def get_quote_attachments(
    quote_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """Get list of all attachments for a quote"""
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    quote = await db.quotes.find_one({"_id": obj_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    attachments = []
    products = quote.get("products", [])
    for product_idx, product in enumerate(products):
        product_attachments = product.get("attachments", [])
        for att_idx, att in enumerate(product_attachments):
            attachments.append({
                "product_index": product_idx,
                "product_name": product.get("product_name", f"Product {product_idx + 1}"),
                "attachment_index": att_idx,
                "name": att.get("name", f"attachment_{att_idx}"),
                "type": att.get("type", "file"),
                "has_data": bool(att.get("base64"))
            })
    
    return {
        "quote_id": quote_id,
        "quote_number": quote.get("quote_number"),
        "total_attachments": len(attachments),
        "attachments": attachments
    }

@router.get("/quotes/{quote_id}/attachments/{product_idx}/{attachment_idx}/download")
async def download_single_attachment(
    quote_id: str,
    product_idx: int,
    attachment_idx: int,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """Download a single attachment"""
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    quote = await db.quotes.find_one({"_id": obj_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    products = quote.get("products", [])
    if product_idx >= len(products):
        raise HTTPException(status_code=404, detail="Product not found")
    
    attachments = products[product_idx].get("attachments", [])
    if attachment_idx >= len(attachments):
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    attachment = attachments[attachment_idx]
    base64_data = attachment.get("base64")
    if not base64_data:
        raise HTTPException(status_code=404, detail="Attachment data not available")
    
    # Decode base64
    file_data = base64.b64decode(base64_data)
    filename = attachment.get("name", f"attachment_{attachment_idx}")
    
    # Determine content type
    if filename.lower().endswith(('.jpg', '.jpeg')):
        media_type = "image/jpeg"
    elif filename.lower().endswith('.png'):
        media_type = "image/png"
    elif filename.lower().endswith('.pdf'):
        media_type = "application/pdf"
    elif filename.lower().endswith(('.doc', '.docx')):
        media_type = "application/msword"
    else:
        media_type = "application/octet-stream"
    
    return StreamingResponse(
        io.BytesIO(file_data),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/quotes/{quote_id}/attachments/download-all")
async def download_all_attachments_zip(
    quote_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    """Download all attachments as a ZIP file"""
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    quote = await db.quotes.find_one({"_id": obj_id})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        attachment_count = 0
        products = quote.get("products", [])
        
        for product_idx, product in enumerate(products):
            product_name = product.get("product_name", f"Product_{product_idx + 1}")
            # Clean product name for folder
            safe_product_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in product_name)[:50]
            
            attachments = product.get("attachments", [])
            for att_idx, att in enumerate(attachments):
                base64_data = att.get("base64")
                if base64_data:
                    try:
                        file_data = base64.b64decode(base64_data)
                        filename = att.get("name", f"attachment_{att_idx}")
                        # Create path inside ZIP: Product_Name/filename
                        zip_path = f"{safe_product_name}/{filename}"
                        zip_file.writestr(zip_path, file_data)
                        attachment_count += 1
                    except Exception as e:
                        logging.error(f"Failed to add attachment to ZIP: {e}")
    
    if attachment_count == 0:
        raise HTTPException(status_code=404, detail="No attachments found")
    
    zip_buffer.seek(0)
    quote_number = quote.get("quote_number", quote_id).replace("/", "-")
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={quote_number}_attachments.zip"}
    )

# ============= STATS ROUTES (Admin only) =============

@router.get("/stats")
async def get_stats(current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    total_products = await db.products.count_documents({})
    total_quotes = await db.quotes.count_documents({})
    pending_quotes = await db.quotes.count_documents({"status": QuoteStatus.PENDING})
    approved_quotes = await db.quotes.count_documents({"status": QuoteStatus.APPROVED})
    
    return {
        "total_products": total_products,
        "total_quotes": total_quotes,
        "pending_quotes": pending_quotes,
        "approved_quotes": approved_quotes
    }


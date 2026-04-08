"""Customer Management Routes"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime
from bson import ObjectId
from routes import db, get_current_user, generate_customer_code, ROOT_DIR, Customer
import re

router = APIRouter()

@router.post("/customers")
async def create_customer(customer: Customer, current_user: dict = Depends(get_current_user)):
    """Create a new customer"""
    customer_dict = customer.dict()
    customer_dict["created_by"] = current_user.get("email")
    customer_dict["created_at"] = datetime.utcnow()
    
    result = await db.customers.insert_one(customer_dict)
    customer_dict["id"] = str(result.inserted_id)
    if "_id" in customer_dict:
        del customer_dict["_id"]
    
    return {"message": "Customer created successfully", "customer": customer_dict}

@router.get("/customers")
async def get_customers(
    customer_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all customers - admin sees all, others see their own. 
    Filter by customer_type: 'registered' or 'quoted'"""
    customers = []
    
    # Build query
    query = {}
    
    # Admin users see all customers
    if current_user.get("role") != "admin":
        query["created_by"] = current_user.get("email")
    
    # Filter by customer type if specified
    if customer_type == "registered":
        query["customer_type"] = "registered"
    elif customer_type == "quoted":
        query["$or"] = [
            {"customer_type": "quoted"},
            {"customer_type": {"$exists": False}},
            {"customer_type": None}
        ]
    
    cursor = db.customers.find(query).sort("created_at", -1).limit(100)
    
    async for customer in cursor:
        customer["id"] = str(customer["_id"])
        del customer["_id"]
        # Add customer_type for display (default to 'quoted' for legacy customers)
        if not customer.get("customer_type"):
            customer["customer_type"] = "quoted"
        customers.append(customer)
    
    return {"customers": customers}

@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific customer"""
    from bson import ObjectId
    customer = await db.customers.find_one({
        "_id": ObjectId(customer_id),
        "created_by": current_user.get("email")
    })
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer["id"] = str(customer["_id"])
    del customer["_id"]
    return customer

@router.put("/customers/{customer_id}")
async def update_customer(customer_id: str, customer: Customer, current_user: dict = Depends(get_current_user)):
    """Update a customer"""
    from bson import ObjectId
    customer_dict = customer.dict()
    customer_dict["updated_at"] = datetime.utcnow()
    
    result = await db.customers.update_one(
        {"_id": ObjectId(customer_id), "created_by": current_user.get("email")},
        {"$set": customer_dict}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {"message": "Customer updated successfully"}

@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a customer"""
    from bson import ObjectId
    result = await db.customers.delete_one({
        "_id": ObjectId(customer_id),
        "created_by": current_user.get("email")
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {"message": "Customer deleted successfully"}

@router.delete("/admin/clear-all-data")
async def clear_all_data(current_user: dict = Depends(get_current_user)):
    """Clear all quotes, customers, and admin requests - Admin only"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Clear quotes
        quotes_result = await db.quotes.delete_many({})
        
        # Clear customers
        customers_result = await db.customers.delete_many({})
        
        # Clear admin requests
        admin_requests_result = await db.admin_requests.delete_many({})
        
        # Reset customer code counter
        await db.counters.update_one(
            {"_id": "customer_code"},
            {"$set": {"seq": 0}},
            upsert=True
        )
        
        logging.info(f"Data cleared by {current_user.get('email')}: {quotes_result.deleted_count} quotes, {customers_result.deleted_count} customers, {admin_requests_result.deleted_count} admin requests")
        
        return {
            "message": "All data cleared successfully",
            "deleted": {
                "quotes": quotes_result.deleted_count,
                "customers": customers_result.deleted_count,
                "admin_requests": admin_requests_result.deleted_count
            }
        }
    except Exception as e:
        logging.error(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")

@router.get("/customers/search/gstin/{gstin}")
async def search_customer_by_gstin(gstin: str, current_user: dict = Depends(get_current_user)):
    """Search for existing customer by GSTIN - Quick lookup before GST portal fetch"""
    customer = await db.customers.find_one({
        "gst_number": gstin.upper(),
        "created_by": current_user.get("email")
    })
    
    if customer:
        customer["id"] = str(customer["_id"])
        del customer["_id"]
        return {"found": True, "customer": customer}
    
    return {"found": False, "customer": None}


@router.get("/customers/{customer_id}/quotes")
async def get_customer_quotes(customer_id: str, current_user: dict = Depends(get_current_user)):
    """Get all quotes for a specific customer"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Verify customer exists
        customer = await db.customers.find_one({"_id": ObjectId(customer_id)})
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get customer's email (quotes are linked by customer_id which is user_id)
        customer_email = customer.get("email")
        
        # Find user by email to get their user_id
        user = await db.users.find_one({"email": customer_email})
        user_id = str(user["_id"]) if user else None
        
        # Find quotes either by customer_id (user_id) or by customer email/company match
        query = {
            "$or": [
                {"customer_id": user_id} if user_id else {"customer_id": None},
                {"customer_email": customer_email} if customer_email else {"customer_email": None},
                {"customer_name": customer.get("name"), "company": customer.get("company")}
            ]
        }
        
        quotes = await db.quotes.find(query).sort("created_at", -1).to_list(100)
        
        result = []
        for quote in quotes:
            quote["id"] = str(quote["_id"])
            del quote["_id"]
            if quote.get("created_at"):
                quote["created_at"] = quote["created_at"].isoformat()
            if quote.get("approved_at"):
                quote["approved_at"] = quote["approved_at"].isoformat()
            result.append(quote)
        
        return {
            "customer": {
                "id": str(customer["_id"]),
                "name": customer.get("name"),
                "company": customer.get("company"),
                "email": customer.get("email")
            },
            "quotes": result,
            "total_count": len(result)
        }
    except Exception as e:
        logging.error(f"Error fetching customer quotes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch customer quotes: {str(e)}")


def validate_gstin_format(gstin: str) -> bool:
    """
    Validate GSTIN format (basic validation)
    Format: 2 digit state code + 10 char PAN + 1 entity code + 1 check digit
    Example: 27AAACE8661R1Z5
    """
    import re
    if not gstin or len(gstin) != 15:
        return False
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}[Z]{1}[A-Z0-9]{1}$'
    return bool(re.match(pattern, gstin.upper()))

def get_state_from_gstin(gstin: str):
    """Extract state from GSTIN (first 2 digits are state code)"""
    state_codes = {
        '01': 'Jammu and Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab',
        '04': 'Chandigarh', '05': 'Uttarakhand', '06': 'Haryana',
        '07': 'Delhi', '08': 'Rajasthan', '09': 'Uttar Pradesh',
        '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh',
        '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram',
        '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam',
        '19': 'West Bengal', '20': 'Jharkhand', '21': 'Odisha',
        '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
        '27': 'Maharashtra', '29': 'Karnataka', '32': 'Kerala',
        '33': 'Tamil Nadu', '36': 'Telangana', '37': 'Andhra Pradesh'
    }
    if gstin and len(gstin) >= 2:
        return state_codes.get(gstin[:2])
    return None

@router.get("/gst/validate/{gstin}")
async def validate_gstin(gstin: str, current_user: dict = Depends(get_current_user)):
    """Validate GSTIN format (local validation only, no external API)"""
    is_valid = validate_gstin_format(gstin)
    state = get_state_from_gstin(gstin) if is_valid else None
    
    return {
        "gstin": gstin.upper(),
        "is_valid_format": is_valid,
        "state": state
    }

@router.get("/download/raw-materials")
async def download_raw_materials():
    """Download raw materials Excel file"""
    file_path = ROOT_DIR / "static" / "raw_material_costs.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        filename="raw_material_costs.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============= PULLEY ROUTES (moved to routes/pulley.py) =============



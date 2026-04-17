"""Supplier Management Routes"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId
from routes import db, get_current_user, require_role, get_ist_now, UserRole

router = APIRouter(prefix="/suppliers")


class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    categories: Optional[List[str]] = []  # pipe, shaft, bearing, housing, seal, etc.


@router.get("")
async def get_suppliers(current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    suppliers = await db.suppliers_master.find({}, {"_id": 0}).sort("name", 1).to_list(500)
    return {"suppliers": suppliers, "total": len(suppliers)}


@router.post("")
async def create_supplier(supplier: SupplierCreate, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    now = get_ist_now()
    doc = supplier.dict()
    doc.update({"id": str(ObjectId()), "created_by": current_user.get("email"), "created_at": now.isoformat()})
    await db.suppliers_master.insert_one(doc)
    del doc["_id"]
    return {"message": "Supplier created", "supplier": doc}


@router.put("/{supplier_id}")
async def update_supplier(supplier_id: str, supplier: SupplierCreate, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    result = await db.suppliers_master.update_one({"id": supplier_id}, {"$set": {**supplier.dict(), "updated_at": get_ist_now().isoformat()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier updated"}


@router.delete("/{supplier_id}")
async def delete_supplier(supplier_id: str, current_user: dict = Depends(require_role([UserRole.ADMIN]))):
    result = await db.suppliers_master.delete_one({"id": supplier_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted"}

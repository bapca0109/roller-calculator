"""Product Routes — CRUD, Pricing Calculator, Freight, Roller Config, Search"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from routes import db, get_current_user, require_role, ROOT_DIR, ProductCreate, ProductInDB, UserRole
import roller_standards as rs
import logging

router = APIRouter()

# ============= PRODUCT ROUTES =============

@router.get("/products", response_model=List[ProductInDB])
async def get_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"sku": {"$regex": search, "$options": "i"}}
        ]
    
    products = await db.products.find(query).limit(100).to_list(100)
    result = []
    for product in products:
        product["id"] = str(product["_id"])
        del product["_id"]
        result.append(ProductInDB(**product))
    return result

@router.get("/products/{product_id}", response_model=ProductInDB)
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    try:
        product = await db.products.find_one({"_id": ObjectId(product_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product["id"] = str(product["_id"])
    del product["_id"]
    return ProductInDB(**product)

@router.post("/products", response_model=ProductInDB)
async def create_product(
    product: ProductCreate,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    # Check if SKU already exists
    existing = await db.products.find_one({"sku": product.sku})
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")
    
    product_dict = product.dict()
    product_dict["created_at"] = datetime.utcnow()
    
    result = await db.products.insert_one(product_dict)
    product_dict["id"] = str(result.inserted_id)
    if "_id" in product_dict:
        del product_dict["_id"]
    
    return ProductInDB(**product_dict)

@router.put("/products/{product_id}", response_model=ProductInDB)
async def update_product(
    product_id: str,
    product: ProductCreate,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    try:
        obj_id = ObjectId(product_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    product_dict = product.dict()
    result = await db.products.update_one(
        {"_id": obj_id},
        {"$set": product_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_product = await db.products.find_one({"_id": obj_id})
    updated_product["id"] = str(updated_product["_id"])
    del updated_product["_id"]
    
    return ProductInDB(**updated_product)

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    current_user: dict = Depends(require_role([UserRole.ADMIN]))
):
    try:
        obj_id = ObjectId(product_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    result = await db.products.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted successfully"}

@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_current_user)):
    categories = await db.products.distinct("category")
    return {"categories": categories}

# ============= PRICING CALCULATOR =============

class PriceCalculationRequest(BaseModel):
    product_id: str
    quantity: int
    delivery_location: Optional[str] = None

class PriceCalculationResponse(BaseModel):
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float
    quantity_discount: float
    discount_percent: float
    shipping_estimate: float
    total_price: float

@router.post("/calculate-price", response_model=PriceCalculationResponse)
async def calculate_price(
    request: PriceCalculationRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        product = await db.products.find_one({"_id": ObjectId(request.product_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate base price
    unit_price = product["base_price"]
    
    # Apply manual adjustment if exists
    if product.get("pricing_factors") and product["pricing_factors"].get("manual_adjustment"):
        unit_price += product["pricing_factors"]["manual_adjustment"]
    
    subtotal = unit_price * request.quantity
    
    # Calculate quantity discount
    discount_percent = 0.0
    if request.quantity >= 100:
        discount_percent = 15.0
    elif request.quantity >= 50:
        discount_percent = 10.0
    elif request.quantity >= 10:
        discount_percent = 5.0
    
    quantity_discount = subtotal * (discount_percent / 100)
    
    # Estimate shipping (placeholder - would be calculated based on location)
    shipping_estimate = 0.0
    if request.delivery_location:
        # Simple shipping estimation
        shipping_estimate = 50.0  # Base shipping
    
    total_price = subtotal - quantity_discount + shipping_estimate
    
    return PriceCalculationResponse(
        product_name=product["name"],
        quantity=request.quantity,
        unit_price=unit_price,
        subtotal=subtotal,
        quantity_discount=quantity_discount,
        discount_percent=discount_percent,
        shipping_estimate=shipping_estimate,
        total_price=total_price
    )

# ============= FREIGHT CALCULATION ENDPOINT =============

class FreightCalculationRequest(BaseModel):
    pincode: str
    total_weight_kg: float

class FreightCalculationResponse(BaseModel):
    destination_pincode: str
    dispatch_pincode: str
    distance_km: float
    total_weight_kg: float
    freight_rate_per_kg: float
    freight_charges: float

@router.post("/calculate-freight", response_model=FreightCalculationResponse)
async def calculate_freight(
    request: FreightCalculationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate freight charges based on destination pincode and total weight.
    Used by admin when reviewing RFQs to auto-populate freight costs.
    """
    # Validate pincode format
    if not request.pincode or len(request.pincode) != 6 or not request.pincode.isdigit():
        raise HTTPException(status_code=400, detail="Invalid pincode format. Must be 6 digits.")
    
    if request.total_weight_kg <= 0:
        raise HTTPException(status_code=400, detail="Weight must be greater than 0")
    
    # Use the existing freight calculation from roller_standards
    freight_calc = rs.calculate_freight_charges(request.total_weight_kg, request.pincode)
    
    return FreightCalculationResponse(
        destination_pincode=request.pincode,
        dispatch_pincode=rs.DISPATCH_PINCODE,
        distance_km=freight_calc["distance_km"],
        total_weight_kg=freight_calc["roller_weight_kg"],
        freight_rate_per_kg=freight_calc["freight_rate_per_kg"],
        freight_charges=freight_calc["freight_charges"]
    )

# ============= ROLLER CONFIGURATION ENDPOINTS =============

@router.get("/roller-standards")
async def get_roller_standards(current_user: dict = Depends(get_current_user)):
    """Get all IS standard options for roller configuration"""
    return {
        "pipe_diameters": rs.PIPE_DIAMETERS,
        "shaft_diameters": rs.SHAFT_DIAMETERS,
        "bearing_options": rs.BEARING_OPTIONS,
        "roller_lengths_by_belt_width": rs.ROLLER_LENGTHS,
        "pipe_shaft_compatibility": rs.PIPE_SHAFT_COMPATIBILITY,
    }

@router.get("/compatible-shafts/{pipe_dia}")
async def get_compatible_shafts(pipe_dia: float, current_user: dict = Depends(get_current_user)):
    """Get compatible shaft diameters for a given pipe diameter"""
    compatible_shafts = rs.get_compatible_shafts(pipe_dia)
    
    # Check if any shafts work without housing
    no_housing_warning = None
    shafts_without_housing = rs.PIPES_WITHOUT_HOUSING.get(pipe_dia, [])
    if shafts_without_housing:
        no_housing_warning = f"Note: For {pipe_dia}mm pipe, shafts {shafts_without_housing} fit WITHOUT housing"
    
    return {
        "pipe_diameter": pipe_dia,
        "compatible_shafts": compatible_shafts,
        "shafts_without_housing": shafts_without_housing,
        "warning": no_housing_warning
    }

@router.get("/compatible-bearings/{shaft_dia}")
async def get_compatible_bearings(shaft_dia: int, current_user: dict = Depends(get_current_user)):
    """Get compatible bearings for a shaft diameter"""
    bearings = rs.BEARING_OPTIONS.get(shaft_dia, [])
    if not bearings:
        raise HTTPException(status_code=404, detail=f"No bearings found for shaft diameter {shaft_dia}mm")
    return {"shaft_diameter": shaft_dia, "bearings": bearings}

@router.get("/compatible-bearings-for-pipe/{pipe_dia}/{shaft_dia}")
async def get_compatible_bearings_for_pipe(
    pipe_dia: float, 
    shaft_dia: int, 
    current_user: dict = Depends(get_current_user)
):
    """Get bearings compatible with both pipe diameter (via housing) and shaft diameter"""
    # Get all bearings for the shaft diameter
    all_bearings = rs.BEARING_OPTIONS.get(shaft_dia, [])
    if not all_bearings:
        raise HTTPException(status_code=404, detail=f"No bearings found for shaft diameter {shaft_dia}mm")
    
    # Get housing bores available for this pipe
    housings = await db.housings.find({"pipe_dia": pipe_dia}).to_list(length=100)
    available_bores = set(h.get("bearing_bore") for h in housings)
    
    if not available_bores:
        raise HTTPException(status_code=404, detail=f"No housings found for pipe diameter {pipe_dia}mm")
    
    # Filter bearings to only those with OD matching available housing bores
    compatible_bearings = []
    for bearing_num in all_bearings:
        bearing_info = await db.bearings.find_one({"number": bearing_num, "shaft_dia": shaft_dia})
        if bearing_info and bearing_info.get("od") in available_bores:
            compatible_bearings.append({
                "number": bearing_num,
                "od": bearing_info.get("od"),
                "series": bearing_info.get("series")
            })
    
    return {
        "pipe_diameter": pipe_dia,
        "shaft_diameter": shaft_dia,
        "compatible_bearings": compatible_bearings,
        "all_bearings_for_shaft": all_bearings,
        "note": "Only bearings with OD matching available housing bores are compatible" if len(compatible_bearings) < len(all_bearings) else None
    }

@router.get("/compatible-housing/{pipe_dia}/{bearing}")
async def get_compatible_housing(
    pipe_dia: float,
    bearing: str,
    current_user: dict = Depends(get_current_user)
):
    """Get compatible housing for pipe diameter and bearing"""
    housing = rs.get_housing_for_pipe_and_bearing(pipe_dia, bearing)
    if not housing:
        raise HTTPException(
            status_code=404,
            detail=f"No compatible housing found for pipe {pipe_dia}mm and bearing {bearing}"
        )
    return {
        "pipe_diameter": pipe_dia,
        "bearing": bearing,
        "housing": housing
    }

class DetailedCostRequest(BaseModel):
    pipe_diameter: float
    pipe_length: float  # mm
    shaft_diameter: int
    bearing_number: str
    bearing_make: Optional[str] = "china"  # china, skf, fag, timken
    pipe_type: Optional[str] = "B"  # A (Light), B (Medium), C (Heavy)
    roller_type: Optional[str] = "carrying"  # carrying, impact, return
    rubber_diameter: Optional[float] = None  # For impact rollers with rubber lagging
    packing_type: Optional[str] = "none"  # none, standard (1%), pallet (4%), wooden_box (8%)
    belt_width: Optional[int] = None
    quantity: Optional[int] = 1  # Number of rollers
    freight_pincode: Optional[str] = None  # Destination pincode for freight calculation
    shaft_end_type: Optional[str] = "B"  # A (+26mm), B (+36mm), C (+56mm), custom
    custom_shaft_length: Optional[int] = None  # Total shaft length in mm (for custom type)

class DetailedCostResponse(BaseModel):
    configuration: Dict[str, Any]
    cost_breakdown: Dict[str, float]
    pricing: Dict[str, Any]  # Changed from Dict[str, float] to allow mixed types including packing_type string
    gst: Optional[Dict[str, Any]] = None  # GST breakdown (CGST/SGST or IGST)
    freight: Optional[Dict[str, Any]] = None  # Freight details if pincode provided
    grand_total: float  # Final price including GST and freight

@router.post("/calculate-detailed-cost", response_model=DetailedCostResponse)
async def calculate_detailed_cost(
    request: DetailedCostRequest,
    current_user: dict = Depends(get_current_user)
):
    """Calculate detailed cost breakdown using IS standards and exact formula"""
    
    # Validate inputs
    if request.pipe_diameter not in rs.PIPE_DIAMETERS:
        raise HTTPException(status_code=400, detail=f"Invalid pipe diameter. Must be one of {rs.PIPE_DIAMETERS}")
    
    if request.shaft_diameter not in rs.SHAFT_DIAMETERS:
        raise HTTPException(status_code=400, detail=f"Invalid shaft diameter. Must be one of {rs.SHAFT_DIAMETERS}")
    
    if request.bearing_number not in rs.BEARING_OPTIONS.get(request.shaft_diameter, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bearing for shaft {request.shaft_diameter}mm. Must be one of {rs.BEARING_OPTIONS.get(request.shaft_diameter, [])}"
        )
    
    # Get housing
    housing = rs.get_housing_for_pipe_and_bearing(request.pipe_diameter, request.bearing_number)
    if not housing:
        raise HTTPException(
            status_code=400,
            detail=f"No compatible housing for pipe {request.pipe_diameter}mm and bearing {request.bearing_number}"
        )
    
    # Validate rubber diameter for impact rollers
    if request.rubber_diameter:
        pipe_code = rs.get_pipe_code(request.pipe_diameter)
        valid_rubber_options = rs.RUBBER_LAGGING_OPTIONS.get(pipe_code, [])
        
        if not valid_rubber_options:
            raise HTTPException(
                status_code=400,
                detail=f"No rubber ring options available for pipe {request.pipe_diameter}mm"
            )
        
        if int(request.rubber_diameter) not in valid_rubber_options:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rubber ring diameter {int(request.rubber_diameter)}mm for pipe {pipe_code}mm. Valid options: {valid_rubber_options}"
            )
        
        # Also verify rubber ring cost exists
        rubber_key = f"{pipe_code}/{int(request.rubber_diameter)}"
        if rubber_key not in rs.RUBBER_RING_COSTS:
            raise HTTPException(
                status_code=400,
                detail=f"No pricing available for rubber ring combination {rubber_key}. Valid options for {pipe_code}mm pipe: {valid_rubber_options}"
            )
    
    # Get shaft end type parameters
    shaft_end_type = request.shaft_end_type or "B"
    custom_shaft_length = request.custom_shaft_length  # Total shaft length (for custom type)
    
    # Calculate shaft length based on type
    if shaft_end_type == "custom" and custom_shaft_length is not None:
        # User provided total shaft length directly
        shaft_length = custom_shaft_length
    else:
        # Calculate using standard extensions
        shaft_length = rs.calculate_shaft_length(request.pipe_length, shaft_end_type, None)
    
    # Calculate raw material costs with shaft end type
    cost_breakdown = rs.calculate_raw_material_cost(
        request.pipe_diameter,
        request.pipe_length,
        request.shaft_diameter,
        request.bearing_number,
        request.bearing_make or "china",
        request.rubber_diameter,
        request.pipe_type or "B",
        shaft_end_type,
        custom_shaft_length  # Pass total length for custom
    )
    
    # Generate product code - use roller_type from request, fallback to impact if rubber_diameter present
    roller_type = request.roller_type or ("impact" if request.rubber_diameter else "carrying")
    product_code = rs.generate_product_code(
        roller_type,
        request.shaft_diameter,
        request.pipe_diameter,
        request.pipe_length,
        request.pipe_type or "B",
        request.bearing_number,
        request.bearing_make or "china",
        request.rubber_diameter
    )
    
    # Calculate quantity
    quantity = request.quantity or 1
    
    # Calculate final pricing (no system discount - admin sets discount during approval)
    pricing = rs.calculate_final_price(
        cost_breakdown["total_raw_material"],
        request.packing_type or "none",
        quantity
    )
    
    # Always calculate weight of single roller
    single_roller_weight = rs.calculate_roller_weight(
        request.pipe_diameter,
        request.pipe_length,
        request.shaft_diameter,
        request.pipe_type or "B",
        request.rubber_diameter
    )
    total_weight = single_roller_weight * quantity
    
    # Add weight to cost_breakdown
    cost_breakdown["single_roller_weight_kg"] = round(single_roller_weight, 3)
    cost_breakdown["total_weight_kg"] = round(total_weight, 3)
    
    # Initialize freight data
    freight_data = None
    total_freight_charges = 0.0
    
    # Calculate freight if destination pincode is provided
    if request.freight_pincode:
        # Calculate freight charges
        freight_calc = rs.calculate_freight_charges(total_weight, request.freight_pincode)
        
        freight_data = {
            "destination_pincode": request.freight_pincode,
            "dispatch_pincode": rs.DISPATCH_PINCODE,
            "distance_km": freight_calc["distance_km"],
            "single_roller_weight_kg": single_roller_weight,
            "total_weight_kg": round(total_weight, 2),
            "freight_rate_per_kg": freight_calc["freight_rate_per_kg"],
            "freight_charges": freight_calc["freight_charges"]
        }
        total_freight_charges = freight_calc["freight_charges"]
    
    # Calculate GST based on destination state
    # GST is applied on price after discount + packing (before freight)
    taxable_amount = pricing["final_price"]
    gst_data = rs.calculate_gst(taxable_amount, request.freight_pincode)
    
    # Calculate grand total (final_price + GST + freight)
    grand_total = pricing["final_price"] + gst_data["total_gst"] + total_freight_charges
    
    return DetailedCostResponse(
        configuration={
            "product_code": product_code,
            "roller_type": roller_type,
            "pipe_diameter_mm": request.pipe_diameter,
            "pipe_length_mm": request.pipe_length,
            "pipe_type": request.pipe_type or "B",
            "shaft_diameter_mm": request.shaft_diameter,
            "shaft_length_mm": shaft_length,
            "shaft_end_type": shaft_end_type,
            "bearing": request.bearing_number,
            "bearing_make": request.bearing_make or "china",
            "housing": housing,
            "belt_width_mm": request.belt_width,
            "rubber_diameter_mm": request.rubber_diameter,
            "quantity": quantity
        },
        cost_breakdown=cost_breakdown,
        pricing=pricing,
        gst=gst_data,
        freight=freight_data,
        grand_total=round(grand_total, 2)
    )

@router.get("/export-raw-materials")
async def export_raw_materials(
    current_user: dict = Depends(get_current_user)
):
    """Export raw material pricing data to Excel file (authenticated)"""
    # Generate fresh Excel file
    import subprocess
    result = subprocess.run(
        ["python", "export_raw_materials.py"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True
    )
    
    file_path = ROOT_DIR / "raw_materials_pricing.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Failed to generate Excel file")
    
    return FileResponse(
        path=str(file_path),
        filename="raw_materials_pricing.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/download/raw-materials-pricing")
async def download_raw_materials_public():
    """Public download link for raw material pricing Excel file"""
    # Generate fresh Excel file
    import subprocess
    result = subprocess.run(
        ["python", "export_raw_materials.py"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True
    )
    
    file_path = ROOT_DIR / "raw_materials_pricing.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Failed to generate Excel file")
    
    return FileResponse(
        path=str(file_path),
        filename="Conveyor_Roller_Raw_Materials_Pricing.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ============= SEARCH ROUTES =============

def parse_product_code(code: str):
    """
    Parse a full product code like 'CR20 89 1000A 63S' or 'IR25 114 800B 62F'
    Returns dict with extracted components or None if invalid
    Format: {TYPE}{SHAFT} {PIPE} {LENGTH}{PIPE_TYPE} {SERIES}{MAKE}
    """
    import re
    code = code.upper().strip()
    
    # Known pipe diameter prefixes (without decimal)
    known_pipe_prefixes = ['60', '76', '88', '89', '114', '127', '139', '140', '152', '159', '165']
    
    # Try to match with known pipe prefixes - NEW FORMAT with space between pipe and length
    for pipe_prefix in sorted(known_pipe_prefixes, key=len, reverse=True):  # Try longer prefixes first
        # Pattern: CR20 {pipe_prefix} {LENGTH}{PIPE_TYPE} {SERIES}{MAKE}
        # New format with space: CR20 89 1000A 62S
        pattern = rf'^(CR|IR)(\d{{2}})\s+({pipe_prefix})\s+(\d{{3,4}})([ABC])\s+(\d{{2}})([CSFT])$'
        match = re.match(pattern, code)
        
        if match:
            make_map = {'C': 'china', 'S': 'skf', 'F': 'fag', 'T': 'timken'}
            return {
                'roller_type': 'carrying' if match.group(1) == 'CR' else 'impact',
                'type_code': match.group(1),
                'shaft_diameter': int(match.group(2)),
                'pipe_diameter_prefix': match.group(3),
                'pipe_length': int(match.group(4)),
                'pipe_type': match.group(5),
                'bearing_series': match.group(6),
                'bearing_make': make_map.get(match.group(7), 'china'),
                'make_code': match.group(7)
            }
    
    return None


def find_pipe_diameter(prefix: str):
    """Find actual pipe diameter from prefix like '88' -> 88.9"""
    prefix_map = {
        '60': 60.8, '608': 60.8,
        '76': 76.1, '761': 76.1,
        '88': 88.9, '889': 88.9, '89': 88.9,
        '114': 114.3, '1143': 114.3,
        '127': 127.0, '1270': 127.0,
        '139': 139.7, '1397': 139.7, '140': 139.7,
        '152': 152.4, '1524': 152.4,
        '159': 159.0, '1590': 159.0,
        '165': 165.0, '1650': 165.0
    }
    return prefix_map.get(prefix)


@router.get("/search/product-catalog")
async def search_product_catalog(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Search through available product configurations (product range/catalog).
    Supports:
    - Full product code: 'CR20 88465A 63S', 'IR25 114800B 62F'
    - Partial search: 'CR', 'IR', '25', 'SKF', '6205'
    """
    if not query or len(query) < 1:
        raise HTTPException(status_code=400, detail="Search query required")
    
    query = query.upper().strip()
    results = []
    
    # Try to parse as full product code first
    parsed = parse_product_code(query)
    
    if parsed:
        # Full product code search - return exact match
        pipe_dia = find_pipe_diameter(parsed['pipe_diameter_prefix'])
        if pipe_dia:
            shaft_dia = parsed['shaft_diameter']
            pipe_length = parsed['pipe_length']
            pipe_type = parsed['pipe_type']
            bearing_make = parsed['bearing_make']
            bearing_series = parsed['bearing_series']
            
            # Find matching bearing for this shaft and series
            bearings = rs.BEARING_OPTIONS.get(shaft_dia, [])
            matching_bearing = None
            for b in bearings:
                if b.startswith(bearing_series):
                    # Check if this bearing is available in the requested make
                    if bearing_make in rs.BEARING_COSTS.get(b, {}):
                        matching_bearing = b
                        break
            
            if matching_bearing:
                housing = rs.get_housing_for_pipe_and_bearing(pipe_dia, matching_bearing)
                if housing:
                    try:
                        cost = rs.calculate_raw_material_cost(
                            pipe_dia, pipe_length, shaft_dia, matching_bearing, 
                            bearing_make, None, pipe_type
                        )
                        pricing = rs.calculate_final_price(cost["total_raw_material"], "none", 1)
                        base_price = pricing["unit_price"]
                    except:
                        base_price = 0
                    
                    make_code = {'china': 'C', 'skf': 'S', 'fag': 'F', 'timken': 'T'}.get(bearing_make, 'C')
                    pipe_display = rs.get_pipe_code(pipe_dia)
                    product_code = f"{parsed['type_code']}{shaft_dia} {pipe_display} {pipe_length}{pipe_type} {bearing_series}{make_code}"
                    
                    # Calculate weight for exact match
                    try:
                        rubber_dia = parsed.get('rubber_diameter')
                        base_weight = rs.calculate_roller_weight(pipe_dia, pipe_length, shaft_dia, pipe_type, rubber_dia)
                    except:
                        base_weight = 0
                    
                    results.append({
                        "product_code": product_code,
                        "roller_type": parsed['roller_type'],
                        "type_code": parsed['type_code'],
                        "shaft_diameter": shaft_dia,
                        "pipe_diameter": pipe_dia,
                        "pipe_length": pipe_length,
                        "pipe_type": pipe_type,
                        "bearing": matching_bearing,
                        "bearing_make": bearing_make,
                        "bearing_series": bearing_series,
                        "housing": housing,
                        "base_price": round(base_price, 2),
                        "base_weight_kg": round(base_weight, 2),
                        "weight_kg": round(base_weight, 2),
                        "available_lengths": [pipe_length],
                        "length_details": [{
                            "length_mm": pipe_length,
                            "weight_kg": round(base_weight, 2),
                            "price": round(base_price, 2),
                            "product_code": product_code,
                            "belt_widths": rs.get_belt_widths_for_length(pipe_length, parsed['roller_type']) if pipe_length else []
                        }],
                        "description": f"{parsed['roller_type'].title()} Roller - {shaft_dia}mm shaft, {pipe_dia}mm x {pipe_length}mm pipe, {matching_bearing} ({bearing_make.upper()})",
                        "exact_match": True
                    })
        
        return {
            "results": results,
            "count": len(results),
            "query": query,
            "search_type": "exact_product_code",
            "truncated": False
        }
    
    # Partial search - search through all configurations
    pipe_types = ["A", "B", "C"]
    bearing_makes = ["china", "skf", "fag", "timken"]
    bearing_make_codes = {"china": "C", "skf": "S", "fag": "F", "timken": "T"}
    
    # Generate product configurations
    for roller_type in ["carrying", "impact", "return"]:
        type_code = {"carrying": "CR", "impact": "IR", "return": "RR"}.get(roller_type, "CR")
        
        # Use appropriate lengths based on roller type
        if roller_type == "return":
            # Return rollers use RETURN_ROLLER_LENGTHS
            return_lengths = []
            for lengths in rs.RETURN_ROLLER_LENGTHS.values():
                return_lengths.extend(lengths)
            standard_lengths = sorted(set(return_lengths))
        else:
            # Carrying and Impact rollers use ROLLER_LENGTHS
            is8598_lengths = []
            for lengths in rs.ROLLER_LENGTHS.values():
                is8598_lengths.extend(lengths)
            standard_lengths = sorted(set(is8598_lengths))
        
        for shaft_dia in rs.SHAFT_DIAMETERS:
            for pipe_dia in rs.PIPE_DIAMETERS:
                # Get compatible bearings for this shaft
                bearings = rs.BEARING_OPTIONS.get(shaft_dia, [])
                
                for bearing in bearings:
                    # Check if housing is compatible
                    housing = rs.get_housing_for_pipe_and_bearing(pipe_dia, bearing)
                    if not housing:
                        continue
                    
                    # Get available bearing makes for this bearing
                    available_makes = list(rs.BEARING_COSTS.get(bearing, {}).keys())
                    if not available_makes:
                        continue
                    
                    for make in available_makes:
                        for pipe_type in pipe_types:
                            # Get bearing series
                            series = "62" if bearing.startswith("62") else "63" if bearing.startswith("63") else "42"
                            pipe_display = rs.get_pipe_code(pipe_dia)
                            
                            # For impact rollers, generate with rubber diameter options
                            if roller_type == "impact":
                                # Get rubber lagging options for this pipe diameter
                                rubber_options = rs.RUBBER_LAGGING_OPTIONS.get(pipe_display, [])
                                if not rubber_options:
                                    continue
                                
                                for rubber_dia in rubber_options:
                                    # Impact roller: uppercase pipe type and make (same as carrying/return)
                                    make_code = bearing_make_codes.get(make, "C")
                                    
                                    # Product code format for impact: IR20 76/114 200B 62S
                                    pipe_with_rubber = f"{pipe_display}/{rubber_dia}"
                                    product_code = f"IR{shaft_dia} {pipe_with_rubber} {series}{make_code}"
                                    
                                    # Build search text with all standard lengths
                                    all_length_codes = " ".join([f"IR{shaft_dia} {pipe_with_rubber} {length}{pipe_type} {series}{make_code}" for length in standard_lengths])
                                    
                                    # Check if query matches this product
                                    search_text = f"{product_code} {all_length_codes} impact {shaft_dia}mm {pipe_dia}mm {rubber_dia}mm {bearing} {make}".upper()
                                    
                                    if query in search_text:
                                        # Build length details with belt width and weight
                                        length_details = []
                                        for length in standard_lengths:
                                            belt_widths = rs.get_belt_widths_for_length(length, "carrying")  # Impact uses carrying lengths
                                            try:
                                                weight = rs.calculate_roller_weight(pipe_dia, length, shaft_dia, pipe_type, rubber_dia)
                                                cost = rs.calculate_raw_material_cost(pipe_dia, length, shaft_dia, bearing, make, rubber_dia, pipe_type)
                                                pricing = rs.calculate_final_price(cost["total_raw_material"], "none", 1)
                                                price = round(pricing["unit_price"], 2)
                                            except:
                                                weight = 0
                                                price = 0
                                            length_details.append({
                                                "length_mm": length,
                                                "belt_widths": belt_widths,
                                                "weight_kg": round(weight, 2),
                                                "price": price,
                                                "product_code": f"IR{shaft_dia} {pipe_with_rubber} {length}{pipe_type} {series}{make_code}"
                                            })
                                        
                                        # Calculate base price for first available length
                                        base_length = standard_lengths[0] if standard_lengths else 200
                                        try:
                                            cost = rs.calculate_raw_material_cost(
                                                pipe_dia, base_length, shaft_dia, bearing, make, rubber_dia, pipe_type
                                            )
                                            pricing = rs.calculate_final_price(cost["total_raw_material"], "none", 1)
                                            base_price = pricing["unit_price"]
                                            base_weight = rs.calculate_roller_weight(pipe_dia, base_length, shaft_dia, pipe_type, rubber_dia)
                                        except:
                                            base_price = 0
                                            base_weight = 0
                                        
                                        result = {
                                            "product_code": f"IR{shaft_dia} {pipe_with_rubber} {series}{make_code}",
                                            "roller_type": "impact",
                                            "type_code": "IR",
                                            "shaft_diameter": shaft_dia,
                                            "pipe_diameter": pipe_dia,
                                            "rubber_diameter": rubber_dia,
                                            "pipe_type": pipe_type,
                                            "bearing": bearing,
                                            "bearing_make": make,
                                            "bearing_series": series,
                                            "housing": housing,
                                            "base_price": round(base_price, 2),
                                            "base_weight_kg": round(base_weight, 2),
                                            "available_lengths": standard_lengths,
                                            "length_details": length_details,
                                            "description": f"Impact Roller - {shaft_dia}mm shaft, {pipe_display}/{rubber_dia}mm pipe/rubber, {bearing} ({make.upper()})",
                                            "exact_match": False
                                        }
                                        results.append(result)
                                        
                                        if len(results) >= 50:
                                            return {
                                                "results": results, 
                                                "count": len(results), 
                                                "query": query,
                                                "search_type": "partial",
                                                "truncated": True
                                            }
                            else:
                                # Carrying/Return roller: uppercase pipe type and make
                                make_code = bearing_make_codes.get(make, "C")
                                
                                # Product code format: CR25 139 530B 62S
                                product_code = f"{type_code}{shaft_dia} {pipe_display} {series}{make_code}"
                                
                                # Build search text with ALL IS-8598 standard lengths
                                all_length_codes_with_type = " ".join([f"{type_code}{shaft_dia} {pipe_display} {length}{pipe_type} {series}{make_code}" for length in standard_lengths])
                                all_length_codes_without_type = " ".join([f"{type_code}{shaft_dia} {pipe_display} {length} {series}{make_code}" for length in standard_lengths])
                                all_length_codes_series_only = " ".join([f"{type_code}{shaft_dia} {pipe_display} {length} {series}" for length in standard_lengths])
                                
                                # Also add base product code without make: CR25 139 62
                                product_code_no_make = f"{type_code}{shaft_dia} {pipe_display} {series}"
                                
                                # Check if query matches this product
                                search_text = f"{product_code} {product_code_no_make} {all_length_codes_with_type} {all_length_codes_without_type} {all_length_codes_series_only} {roller_type} {shaft_dia}mm {pipe_dia}mm {bearing} {make}".upper()
                                
                                if query in search_text:
                                    # Build length details with belt width and weight
                                    length_details = []
                                    for length in standard_lengths:
                                        belt_widths = rs.get_belt_widths_for_length(length, roller_type)
                                        try:
                                            weight = rs.calculate_roller_weight(pipe_dia, length, shaft_dia, pipe_type, None)
                                            cost = rs.calculate_raw_material_cost(pipe_dia, length, shaft_dia, bearing, make, None, pipe_type)
                                            pricing = rs.calculate_final_price(cost["total_raw_material"], "none", 1)
                                            price = round(pricing["unit_price"], 2)
                                        except:
                                            weight = 0
                                            price = 0
                                        length_details.append({
                                            "length_mm": length,
                                            "belt_widths": belt_widths,
                                            "weight_kg": round(weight, 2),
                                            "price": price,
                                            "product_code": f"{type_code}{shaft_dia} {pipe_display} {length}{pipe_type} {series}{make_code}"
                                        })
                                    
                                    # Calculate base price and weight for first available length
                                    base_length = standard_lengths[0] if standard_lengths else 380
                                    try:
                                        cost = rs.calculate_raw_material_cost(
                                            pipe_dia, base_length, shaft_dia, bearing, make, None, pipe_type
                                        )
                                        pricing = rs.calculate_final_price(cost["total_raw_material"], "none", 1)
                                        base_price = pricing["unit_price"]
                                        base_weight = rs.calculate_roller_weight(pipe_dia, base_length, shaft_dia, pipe_type, None)
                                    except:
                                        base_price = 0
                                        base_weight = 0
                                    
                                    result = {
                                        "product_code": f"{type_code}{shaft_dia} {pipe_display} {series}{make_code}",
                                        "roller_type": roller_type,
                                        "type_code": type_code,
                                        "shaft_diameter": shaft_dia,
                                        "pipe_diameter": pipe_dia,
                                        "pipe_type": pipe_type,
                                        "bearing": bearing,
                                        "bearing_make": make,
                                        "bearing_series": series,
                                        "housing": housing,
                                        "base_price": round(base_price, 2),
                                        "base_weight_kg": round(base_weight, 2),
                                        "available_lengths": standard_lengths,
                                        "length_details": length_details,
                                        "description": f"{roller_type.title()} Roller - {shaft_dia}mm shaft, {pipe_dia}mm pipe, {bearing} ({make.upper()})",
                                        "exact_match": False
                                    }
                                    results.append(result)
                                    
                                    # Limit results to prevent too many
                                    if len(results) >= 50:
                                        return {
                                            "results": results, 
                                            "count": len(results), 
                                            "query": query,
                                            "search_type": "partial",
                                            "truncated": True
                                        }
    
    # Remove duplicates based on key specs (keep unique combinations)
    seen = set()
    unique_results = []
    for r in results:
        key = f"{r['type_code']}{r['shaft_diameter']}{r['pipe_diameter']}{r.get('rubber_diameter', '')}{r['bearing']}{r['bearing_make']}"
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return {
        "results": unique_results[:50], 
        "count": len(unique_results[:50]), 
        "query": query,
        "search_type": "partial",
        "truncated": len(unique_results) > 50
    }


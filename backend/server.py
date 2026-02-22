from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from bson import ObjectId
import roller_standards as rs

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# ============= MODELS =============

class UserRole:
    ADMIN = "admin"
    SALES = "sales"
    CUSTOMER = "customer"

class User(BaseModel):
    email: EmailStr
    name: str
    company: Optional[str] = None
    role: str = UserRole.CUSTOMER
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserInDB(User):
    id: str
    hashed_password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None
    role: str = UserRole.CUSTOMER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class RollerSpecs(BaseModel):
    diameter: float  # mm
    length: float  # mm
    shaft_diameter: float  # mm
    material: str  # Steel, Stainless Steel, HDPE, etc.
    bearing_type: str
    load_capacity: float  # kg
    surface_type: str  # Smooth, Grooved, Rubber-lagged
    application_type: str  # Carrying, Return, Impact, Self-aligning, Tapered, Guide
    rpm: Optional[float] = None
    temperature_rating: Optional[float] = None  # °C

class PricingFactors(BaseModel):
    base_formula_price: float
    quantity_discount_percent: float = 0.0
    custom_spec_premium: float = 0.0
    manual_adjustment: float = 0.0  # Can be positive or negative

class Product(BaseModel):
    name: str
    sku: str
    description: str
    category: str  # Standard, Special, Material Variant
    specifications: RollerSpecs
    base_price: float
    pricing_factors: Optional[PricingFactors] = None
    image: Optional[str] = None  # base64 image
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductInDB(Product):
    id: str

class ProductCreate(BaseModel):
    name: str
    sku: str
    description: str
    category: str
    specifications: RollerSpecs
    base_price: float
    pricing_factors: Optional[PricingFactors] = None
    image: Optional[str] = None

class QuoteProduct(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    specifications: Optional[Dict[str, Any]] = None
    calculated_discount: float = 0.0  # Quantity discount applied
    custom_premium: float = 0.0  # Premium for custom specs

class QuoteStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"

class Quote(BaseModel):
    customer_id: str
    customer_name: str
    customer_email: str
    products: List[QuoteProduct]
    subtotal: float
    total_discount: float = 0.0
    shipping_cost: float = 0.0
    delivery_location: Optional[str] = None
    total_price: float
    status: str = QuoteStatus.PENDING
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QuoteInDB(Quote):
    id: str

class QuoteCreate(BaseModel):
    products: List[QuoteProduct]
    delivery_location: Optional[str] = None
    notes: Optional[str] = None

class QuoteUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    shipping_cost: Optional[float] = None

class RollerQuoteCreate(BaseModel):
    """Create a quote from roller calculation"""
    customer_name: str
    configuration: Dict[str, Any]
    cost_breakdown: Dict[str, float]
    pricing: Dict[str, Any]
    freight: Optional[Dict[str, Any]] = None
    grand_total: float
    notes: Optional[str] = None

# ============= HELPER FUNCTIONS =============

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = await db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    user["id"] = str(user["_id"])
    del user["_id"]
    return user

def require_role(allowed_roles: List[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return role_checker

# ============= AUTH ROUTES =============

@api_router.post("/auth/register", response_model=Token)
async def register(user: UserRegister):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    del user_dict["password"]
    user_dict["hashed_password"] = hashed_password
    user_dict["created_at"] = datetime.utcnow()
    
    result = await db.users.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    
    # Create token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_dict["id"],
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "company": user.company
        }
    }

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": credentials.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "company": user.get("company")
        }
    }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "role": current_user["role"],
        "company": current_user.get("company")
    }

# ============= PRODUCT ROUTES =============

@api_router.get("/products", response_model=List[ProductInDB])
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
    
    products = await db.products.find(query).to_list(1000)
    result = []
    for product in products:
        product["id"] = str(product["_id"])
        del product["_id"]
        result.append(ProductInDB(**product))
    return result

@api_router.get("/products/{product_id}", response_model=ProductInDB)
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

@api_router.post("/products", response_model=ProductInDB)
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

@api_router.put("/products/{product_id}", response_model=ProductInDB)
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

@api_router.delete("/products/{product_id}")
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

@api_router.get("/categories")
async def get_categories(current_user: dict = Depends(get_current_user)):
    categories = await db.products.distinct("category")
    return {"categories": categories}

# ============= QUOTE ROUTES =============

@api_router.post("/quotes", response_model=QuoteInDB)
async def create_quote(
    quote: QuoteCreate,
    current_user: dict = Depends(get_current_user)
):
    # Calculate pricing with discounts and premiums
    subtotal = 0.0
    total_discount = 0.0
    
    processed_products = []
    for item in quote.products:
        # Calculate base line total
        line_total = item.quantity * item.unit_price
        
        # Apply quantity discount (example: 5% for 10+, 10% for 50+, 15% for 100+)
        discount = 0.0
        if item.quantity >= 100:
            discount = line_total * 0.15
        elif item.quantity >= 50:
            discount = line_total * 0.10
        elif item.quantity >= 10:
            discount = line_total * 0.05
        
        item.calculated_discount = discount
        total_discount += discount
        subtotal += line_total
        
        processed_products.append(item.dict())
    
    # Calculate total price
    total_price = subtotal - total_discount + (quote.delivery_location and 0 or 0)  # Shipping calculated later by admin
    
    quote_dict = {
        "customer_id": current_user["id"],
        "customer_name": current_user["name"],
        "customer_email": current_user["email"],
        "products": processed_products,
        "subtotal": subtotal,
        "total_discount": total_discount,
        "shipping_cost": 0.0,
        "delivery_location": quote.delivery_location,
        "total_price": total_price,
        "status": QuoteStatus.PENDING,
        "notes": quote.notes,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.quotes.insert_one(quote_dict)
    quote_dict["id"] = str(result.inserted_id)
    
    return QuoteInDB(**quote_dict)

@api_router.post("/quotes/roller")
async def create_roller_quote(
    quote_data: RollerQuoteCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a quote from roller calculation results"""
    
    config = quote_data.configuration
    pricing = quote_data.pricing
    
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
    
    quote_dict = {
        "customer_id": current_user["id"],
        "customer_name": quote_data.customer_name or current_user["name"],
        "customer_email": current_user["email"],
        "products": [product],
        "subtotal": pricing.get("order_value", 0),
        "total_discount": pricing.get("discount_amount", 0),
        "packing_charges": pricing.get("packing_charges", 0),
        "shipping_cost": quote_data.freight.get("freight_charges", 0) if quote_data.freight else 0,
        "delivery_location": quote_data.freight.get("destination_pincode") if quote_data.freight else None,
        "total_price": quote_data.grand_total,
        "status": QuoteStatus.PENDING,
        "notes": quote_data.notes,
        "cost_breakdown": quote_data.cost_breakdown,
        "pricing_details": quote_data.pricing,
        "freight_details": quote_data.freight,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.quotes.insert_one(quote_dict)
    quote_dict["id"] = str(result.inserted_id)
    
    return {
        "id": quote_dict["id"],
        "message": "Quote created successfully",
        "quote_number": f"QT-{quote_dict['id'][-6:].upper()}",
        "total_price": quote_dict["total_price"]
    }

@api_router.get("/quotes", response_model=List[QuoteInDB])
async def get_quotes(current_user: dict = Depends(get_current_user)):
    query = {}
    # Customers can only see their own quotes
    if current_user["role"] == UserRole.CUSTOMER:
        query["customer_id"] = current_user["id"]
    
    quotes = await db.quotes.find(query).sort("created_at", -1).to_list(1000)
    result = []
    for quote in quotes:
        quote["id"] = str(quote["_id"])
        del quote["_id"]
        result.append(QuoteInDB(**quote))
    return result

@api_router.get("/quotes/{quote_id}", response_model=QuoteInDB)
async def get_quote(quote_id: str, current_user: dict = Depends(get_current_user)):
    try:
        quote = await db.quotes.find_one({"_id": ObjectId(quote_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Check permissions
    if current_user["role"] == UserRole.CUSTOMER and quote["customer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this quote")
    
    quote["id"] = str(quote["_id"])
    del quote["_id"]
    return QuoteInDB(**quote)

@api_router.put("/quotes/{quote_id}", response_model=QuoteInDB)
async def update_quote(
    quote_id: str,
    quote_update: QuoteUpdate,
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))
):
    try:
        obj_id = ObjectId(quote_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quote ID")
    
    update_dict = quote_update.dict(exclude_unset=True)
    update_dict["updated_at"] = datetime.utcnow()
    
    # If shipping cost is updated, recalculate total
    if "shipping_cost" in update_dict:
        quote = await db.quotes.find_one({"_id": obj_id})
        if quote:
            new_total = quote["subtotal"] - quote["total_discount"] + update_dict["shipping_cost"]
            update_dict["total_price"] = new_total
    
    result = await db.quotes.update_one(
        {"_id": obj_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    updated_quote = await db.quotes.find_one({"_id": obj_id})
    updated_quote["id"] = str(updated_quote["_id"])
    del updated_quote["_id"]
    
    return QuoteInDB(**updated_quote)

# ============= STATS ROUTES (Admin only) =============

@api_router.get("/stats")
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

@api_router.post("/calculate-price", response_model=PriceCalculationResponse)
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

# ============= ROLLER CONFIGURATION ENDPOINTS =============

@api_router.get("/roller-standards")
async def get_roller_standards(current_user: dict = Depends(get_current_user)):
    """Get all IS standard options for roller configuration"""
    return {
        "pipe_diameters": rs.PIPE_DIAMETERS,
        "shaft_diameters": rs.SHAFT_DIAMETERS,
        "bearing_options": rs.BEARING_OPTIONS,
        "roller_lengths_by_belt_width": rs.ROLLER_LENGTHS
    }

@api_router.get("/compatible-bearings/{shaft_dia}")
async def get_compatible_bearings(shaft_dia: int, current_user: dict = Depends(get_current_user)):
    """Get compatible bearings for a shaft diameter"""
    bearings = rs.BEARING_OPTIONS.get(shaft_dia, [])
    if not bearings:
        raise HTTPException(status_code=404, detail=f"No bearings found for shaft diameter {shaft_dia}mm")
    return {"shaft_diameter": shaft_dia, "bearings": bearings}

@api_router.get("/compatible-housing/{pipe_dia}/{bearing}")
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

class DetailedCostResponse(BaseModel):
    configuration: Dict[str, Any]
    cost_breakdown: Dict[str, float]
    pricing: Dict[str, Any]  # Changed from Dict[str, float] to allow mixed types including packing_type string
    gst: Optional[Dict[str, Any]] = None  # GST breakdown (CGST/SGST or IGST)
    freight: Optional[Dict[str, Any]] = None  # Freight details if pincode provided
    grand_total: float  # Final price including GST and freight

@api_router.post("/calculate-detailed-cost", response_model=DetailedCostResponse)
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
    
    # Calculate shaft length
    shaft_length = rs.calculate_shaft_length(request.pipe_length)
    
    # Calculate raw material costs
    cost_breakdown = rs.calculate_raw_material_cost(
        request.pipe_diameter,
        request.pipe_length,
        request.shaft_diameter,
        request.bearing_number,
        request.bearing_make or "china",
        request.rubber_diameter,
        request.pipe_type or "B"
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
    
    # Calculate final pricing with discount and packing charges
    pricing = rs.calculate_final_price(
        cost_breakdown["total_raw_material"],
        request.packing_type or "none",
        quantity
    )
    
    # Initialize freight data
    freight_data = None
    total_freight_charges = 0.0
    
    # Calculate freight if destination pincode is provided
    if request.freight_pincode:
        # Calculate weight of single roller
        single_roller_weight = rs.calculate_roller_weight(
            request.pipe_diameter,
            request.pipe_length,
            request.shaft_diameter,
            request.pipe_type or "B",
            request.rubber_diameter
        )
        
        # Calculate total weight for all rollers
        total_weight = single_roller_weight * quantity
        
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

@api_router.get("/export-raw-materials")
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

@api_router.get("/download/raw-materials-pricing")
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


@api_router.get("/search/product-catalog")
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
                        "available_lengths": [pipe_length],
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
                            # Generate product code
                            make_code = bearing_make_codes.get(make, "C")
                            series = "62" if bearing.startswith("62") else "63" if bearing.startswith("63") else "42"
                            
                            # Product code format: CR25 139 530B 62S
                            pipe_display = rs.get_pipe_code(pipe_dia)
                            product_code = f"{type_code}{shaft_dia} {pipe_display} {series}{make_code}"
                            
                            # Build search text with ALL IS-8598 standard lengths
                            # Include multiple formats for flexible matching:
                            # 1. With pipe type and make: CR25 139 600A 62S
                            # 2. Without pipe type, with make: CR25 139 600 62S
                            # 3. Without pipe type, without make: CR25 139 600 62
                            all_length_codes_with_type = " ".join([f"{type_code}{shaft_dia} {pipe_display} {length}{pipe_type} {series}{make_code}" for length in standard_lengths])
                            all_length_codes_without_type = " ".join([f"{type_code}{shaft_dia} {pipe_display} {length} {series}{make_code}" for length in standard_lengths])
                            all_length_codes_series_only = " ".join([f"{type_code}{shaft_dia} {pipe_display} {length} {series}" for length in standard_lengths])
                            
                            # Also add base product code without make: CR25 139 62
                            product_code_no_make = f"{type_code}{shaft_dia} {pipe_display} {series}"
                            
                            # Check if query matches this product
                            search_text = f"{product_code} {product_code_no_make} {all_length_codes_with_type} {all_length_codes_without_type} {all_length_codes_series_only} {roller_type} {shaft_dia}mm {pipe_dia}mm {bearing} {make}".upper()
                            
                            if query in search_text:
                                # Calculate base price for 1000mm length
                                try:
                                    cost = rs.calculate_raw_material_cost(
                                        pipe_dia, 1000, shaft_dia, bearing, make, None, pipe_type
                                    )
                                    pricing = rs.calculate_final_price(cost["total_raw_material"], "none", 1)
                                    base_price = pricing["unit_price"]
                                except:
                                    base_price = 0
                                
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
                                    "available_lengths": standard_lengths,
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
        key = f"{r['type_code']}{r['shaft_diameter']}{r['pipe_diameter']}{r['bearing']}{r['bearing_make']}"
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

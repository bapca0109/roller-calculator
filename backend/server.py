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
from jose import jwt, JWTError
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

class Customer(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    gst_number: Optional[str] = None
    notes: Optional[str] = None

class CustomerInDB(Customer):
    id: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

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
    customer_details: Optional[Dict[str, Any]] = None  # Full customer details for PDF
    products: List[QuoteProduct]
    subtotal: float
    total_discount: float = 0.0
    shipping_cost: float = 0.0
    delivery_location: Optional[str] = None
    total_price: float
    status: str = QuoteStatus.PENDING
    notes: Optional[str] = None
    cost_breakdown: Optional[Dict[str, float]] = None
    pricing_details: Optional[Dict[str, Any]] = None
    freight_details: Optional[Dict[str, Any]] = None
    packing_charges: Optional[float] = 0.0
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
    customer_id: Optional[str] = None  # Reference to customer in database
    customer_details: Optional[Dict[str, Any]] = None  # Full customer details for PDF
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
    except JWTError:
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
    
    products = await db.products.find(query).limit(100).to_list(100)
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
        "customer_id": quote_data.customer_id or current_user["id"],
        "customer_name": quote_data.customer_name or current_user["name"],
        "customer_email": current_user["email"],
        "customer_details": quote_data.customer_details,  # Full customer info for PDF
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

@api_router.get("/quotes")
async def get_quotes(current_user: dict = Depends(get_current_user)):
    query = {}
    # Customers can only see their own quotes
    if current_user["role"] == UserRole.CUSTOMER:
        query["customer_id"] = current_user["id"]
    
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
        result.append(quote)
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
    shaft_end_type: Optional[str] = "B"  # A (+26mm), B (+36mm), C (+56mm), custom
    custom_shaft_length: Optional[int] = None  # Total shaft length in mm (for custom type)

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

# ============= ADMIN API - RAW MATERIAL PRICES =============

class PriceUpdateRequest(BaseModel):
    category: str  # bearing, seal, circlip, pipe, shaft, rubber_ring, locking_ring
    key: str  # e.g., "6204", "20", "89/140"
    sub_key: Optional[str] = None  # e.g., "china", "skf" for bearings; "A", "B", "C" for pipe weight
    value: float

@api_router.get("/admin/prices")
async def get_all_prices(current_user: dict = Depends(get_current_user)):
    """Get all raw material prices for admin panel"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if there are custom prices in database
    custom_prices = await db.custom_prices.find_one({"_id": "prices"})
    
    # Build the response with current prices (from DB or defaults)
    prices = {
        "basic_rates": {
            "pipe_cost_per_kg": custom_prices.get("pipe_cost_per_kg", rs.PIPE_COST_PER_KG) if custom_prices else rs.PIPE_COST_PER_KG,
            "shaft_cost_per_kg": custom_prices.get("shaft_cost_per_kg", rs.SHAFT_COST_PER_KG) if custom_prices else rs.SHAFT_COST_PER_KG,
        },
        "bearing_costs": custom_prices.get("bearing_costs", rs.BEARING_COSTS) if custom_prices else rs.BEARING_COSTS,
        "seal_costs": custom_prices.get("seal_costs", rs.SEAL_COSTS) if custom_prices else rs.SEAL_COSTS,
        "circlip_costs": custom_prices.get("circlip_costs", rs.CIRCLIP_COSTS) if custom_prices else rs.CIRCLIP_COSTS,
        "rubber_ring_costs": custom_prices.get("rubber_ring_costs", rs.RUBBER_RING_COSTS) if custom_prices else rs.RUBBER_RING_COSTS,
        "locking_ring_costs": custom_prices.get("locking_ring_costs", rs.LOCKING_RING_COSTS) if custom_prices else rs.LOCKING_RING_COSTS,
        "pipe_weight": custom_prices.get("pipe_weight", rs.PIPE_WEIGHT_PER_METER) if custom_prices else rs.PIPE_WEIGHT_PER_METER,
        "shaft_weight": custom_prices.get("shaft_weight", rs.SHAFT_WEIGHT_PER_METER) if custom_prices else rs.SHAFT_WEIGHT_PER_METER,
    }
    
    return prices

@api_router.post("/admin/prices/update")
async def update_price(request: PriceUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Update a specific raw material price"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get or create custom prices document
    custom_prices = await db.custom_prices.find_one({"_id": "prices"})
    if not custom_prices:
        custom_prices = {"_id": "prices"}
    
    # Update based on category
    if request.category == "pipe_cost":
        custom_prices["pipe_cost_per_kg"] = request.value
    elif request.category == "shaft_cost":
        custom_prices["shaft_cost_per_kg"] = request.value
    elif request.category == "bearing":
        if "bearing_costs" not in custom_prices:
            custom_prices["bearing_costs"] = dict(rs.BEARING_COSTS)
        if request.key not in custom_prices["bearing_costs"]:
            custom_prices["bearing_costs"][request.key] = {}
        custom_prices["bearing_costs"][request.key][request.sub_key] = request.value
    elif request.category == "seal":
        if "seal_costs" not in custom_prices:
            custom_prices["seal_costs"] = dict(rs.SEAL_COSTS)
        custom_prices["seal_costs"][request.key] = request.value
    elif request.category == "circlip":
        if "circlip_costs" not in custom_prices:
            custom_prices["circlip_costs"] = {str(k): v for k, v in rs.CIRCLIP_COSTS.items()}
        custom_prices["circlip_costs"][request.key] = request.value
    elif request.category == "rubber_ring":
        if "rubber_ring_costs" not in custom_prices:
            custom_prices["rubber_ring_costs"] = dict(rs.RUBBER_RING_COSTS)
        custom_prices["rubber_ring_costs"][request.key] = request.value
    elif request.category == "locking_ring":
        if "locking_ring_costs" not in custom_prices:
            custom_prices["locking_ring_costs"] = {str(k): v for k, v in rs.LOCKING_RING_COSTS.items()}
        custom_prices["locking_ring_costs"][request.key] = request.value
    elif request.category == "pipe_weight":
        if "pipe_weight" not in custom_prices:
            custom_prices["pipe_weight"] = {str(k): v for k, v in rs.PIPE_WEIGHT_PER_METER.items()}
        if request.key not in custom_prices["pipe_weight"]:
            custom_prices["pipe_weight"][request.key] = {}
        custom_prices["pipe_weight"][request.key][request.sub_key] = request.value
    elif request.category == "shaft_weight":
        if "shaft_weight" not in custom_prices:
            custom_prices["shaft_weight"] = {str(k): v for k, v in rs.SHAFT_WEIGHT_PER_METER.items()}
        custom_prices["shaft_weight"][request.key] = request.value
    else:
        raise HTTPException(status_code=400, detail=f"Unknown category: {request.category}")
    
    custom_prices["updated_at"] = datetime.utcnow().isoformat()
    custom_prices["updated_by"] = current_user.get("email")
    
    # Save to database
    await db.custom_prices.replace_one({"_id": "prices"}, custom_prices, upsert=True)
    
    # Invalidate price cache so calculations use new values immediately
    import price_loader
    price_loader.invalidate_cache()
    
    return {"message": "Price updated successfully", "category": request.category, "key": request.key}

@api_router.post("/admin/prices/reset")
async def reset_prices(current_user: dict = Depends(get_current_user)):
    """Reset all prices to default values"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await db.custom_prices.delete_one({"_id": "prices"})
    
    # Invalidate price cache so calculations use default values immediately
    import price_loader
    price_loader.invalidate_cache()
    
    return {"message": "All prices reset to default values"}

@api_router.post("/admin/make-admin")
async def make_user_admin(email: str, current_user: dict = Depends(get_current_user)):
    """Make a user an admin (only existing admins can do this)"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"email": email},
        {"$set": {"role": UserRole.ADMIN}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {email} is now an admin"}

# ============= ADMIN API - STANDARDS DATA (MongoDB) =============

@api_router.get("/admin/standards/{collection}")
async def get_standards_data(collection: str, current_user: dict = Depends(get_current_user)):
    """Get all documents from a standards collection"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_collections = [
        "pipe_diameters", "shaft_diameters", "shaft_end_types", "bearings", 
        "housings", "pipe_weights", "roller_lengths", "circlips", 
        "rubber_lagging", "rubber_rings", "locking_rings", "discount_slabs",
        "freight_rates", "packing_options", "gst_config", "raw_material_costs"
    ]
    
    if collection not in valid_collections:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Valid: {valid_collections}")
    
    cursor = db[collection].find({}, {"_id": 0})
    docs = await cursor.to_list(length=500)
    return {"collection": collection, "count": len(docs), "data": docs}

@api_router.post("/admin/standards/{collection}")
async def add_standards_item(collection: str, item: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    """Add a new item to a standards collection"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_collections = [
        "pipe_diameters", "shaft_diameters", "shaft_end_types", "bearings", 
        "housings", "pipe_weights", "roller_lengths", "circlips", 
        "rubber_lagging", "rubber_rings", "locking_rings", "discount_slabs",
        "freight_rates", "packing_options", "gst_config", "raw_material_costs"
    ]
    
    if collection not in valid_collections:
        raise HTTPException(status_code=400, detail=f"Invalid collection")
    
    item["created_at"] = datetime.utcnow()
    item["created_by"] = current_user.get("email")
    
    result = await db[collection].insert_one(item)
    return {"message": "Item added successfully", "id": str(result.inserted_id)}

@api_router.put("/admin/standards/{collection}")
async def update_standards_item(
    collection: str, 
    query: Dict[str, Any],
    update_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update an item in a standards collection"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_collections = [
        "pipe_diameters", "shaft_diameters", "shaft_end_types", "bearings", 
        "housings", "pipe_weights", "roller_lengths", "circlips", 
        "rubber_lagging", "rubber_rings", "locking_rings", "discount_slabs",
        "freight_rates", "packing_options", "gst_config", "raw_material_costs"
    ]
    
    if collection not in valid_collections:
        raise HTTPException(status_code=400, detail=f"Invalid collection")
    
    update_data["updated_at"] = datetime.utcnow()
    update_data["updated_by"] = current_user.get("email")
    
    result = await db[collection].update_one(query, {"$set": update_data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"message": "Item updated successfully", "modified": result.modified_count}

@api_router.delete("/admin/standards/{collection}")
async def delete_standards_item(
    collection: str,
    query: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Delete an item from a standards collection"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_collections = [
        "pipe_diameters", "shaft_diameters", "shaft_end_types", "bearings", 
        "housings", "pipe_weights", "roller_lengths", "circlips", 
        "rubber_lagging", "rubber_rings", "locking_rings", "discount_slabs",
        "freight_rates", "packing_options", "gst_config", "raw_material_costs"
    ]
    
    if collection not in valid_collections:
        raise HTTPException(status_code=400, detail=f"Invalid collection")
    
    result = await db[collection].delete_one(query)
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"message": "Item deleted successfully"}

@api_router.get("/admin/standards-summary")
async def get_standards_summary(current_user: dict = Depends(get_current_user)):
    """Get a summary of all standards collections"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    collections = [
        "pipe_diameters", "shaft_diameters", "shaft_end_types", "bearings", 
        "housings", "pipe_weights", "roller_lengths", "circlips", 
        "rubber_lagging", "rubber_rings", "locking_rings", "discount_slabs",
        "freight_rates", "packing_options", "gst_config", "raw_material_costs"
    ]
    
    summary = []
    for coll in collections:
        count = await db[coll].count_documents({})
        summary.append({"collection": coll, "count": count})
    
    return {"summary": summary, "total_collections": len(collections)}

# ============= CUSTOMER API =============

@api_router.post("/customers")
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

@api_router.get("/customers")
async def get_customers(current_user: dict = Depends(get_current_user)):
    """Get all customers for the current user"""
    customers = []
    cursor = db.customers.find({"created_by": current_user.get("email")}).limit(100)
    async for customer in cursor:
        customer["id"] = str(customer["_id"])
        del customer["_id"]
        customers.append(customer)
    
    return {"customers": customers}

@api_router.get("/customers/{customer_id}")
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

@api_router.put("/customers/{customer_id}")
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

@api_router.delete("/customers/{customer_id}")
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

@api_router.get("/customers/search/gstin/{gstin}")
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

# ============= GSTIN FORMAT VALIDATION (Local utility) =============

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

@api_router.get("/gst/validate/{gstin}")
async def validate_gstin(gstin: str, current_user: dict = Depends(get_current_user)):
    """Validate GSTIN format (local validation only, no external API)"""
    is_valid = validate_gstin_format(gstin)
    state = get_state_from_gstin(gstin) if is_valid else None
    
    return {
        "gstin": gstin.upper(),
        "is_valid_format": is_valid,
        "state": state
    }

# ============= FILE DOWNLOADS =============

@api_router.get("/download/raw-materials")
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

# ============= DRAWING GENERATOR =============

class DrawingRequest(BaseModel):
    product_code: str
    roller_type: str
    pipe_diameter: float
    pipe_length: float
    pipe_type: str
    shaft_diameter: float
    bearing: str
    bearing_make: str
    housing: str
    weight_kg: float
    unit_price: float = 0  # Optional, not displayed
    rubber_diameter: Optional[float] = None
    belt_widths: Optional[List[int]] = None
    quantity: int = 1
    shaft_end_type: Optional[str] = "B"  # A (+26mm), B (+36mm), C (+56mm), custom
    custom_shaft_extension: Optional[int] = None  # Custom shaft extension in mm

@api_router.get("/download/sample-drawing")
async def download_sample_drawing():
    """Download sample roller drawing PDF"""
    file_path = ROOT_DIR / "static" / "sample_drawing.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Sample drawing not found")
    return FileResponse(
        path=str(file_path),
        filename="Sample_Roller_Drawing.pdf",
        media_type="application/pdf"
    )

@api_router.post("/generate-drawing")
async def generate_drawing(request: DrawingRequest, current_user: dict = Depends(get_current_user)):
    """Generate a technical drawing PDF for a roller"""
    from drawing_generator import generate_roller_drawing
    from fastapi.responses import StreamingResponse
    
    try:
        pdf_buffer = generate_roller_drawing(
            product_code=request.product_code,
            roller_type=request.roller_type,
            pipe_diameter=request.pipe_diameter,
            pipe_length=request.pipe_length,
            pipe_type=request.pipe_type,
            shaft_diameter=request.shaft_diameter,
            bearing=request.bearing,
            bearing_make=request.bearing_make,
            housing=request.housing,
            weight_kg=request.weight_kg,
            unit_price=request.unit_price,
            rubber_diameter=request.rubber_diameter,
            belt_widths=request.belt_widths,
            quantity=request.quantity,
            shaft_end_type=request.shaft_end_type or "B",
            custom_shaft_extension=request.custom_shaft_extension
        )
        
        filename = f"Drawing_{request.product_code.replace(' ', '_').replace('/', '-')}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate drawing: {str(e)}")

@api_router.post("/generate-drawing-base64")
async def generate_drawing_base64(request: DrawingRequest, current_user: dict = Depends(get_current_user)):
    """Generate a technical drawing PDF and return as base64 for mobile apps"""
    from drawing_generator import generate_roller_drawing
    import base64
    
    try:
        pdf_buffer = generate_roller_drawing(
            product_code=request.product_code,
            roller_type=request.roller_type,
            pipe_diameter=request.pipe_diameter,
            pipe_length=request.pipe_length,
            pipe_type=request.pipe_type,
            shaft_diameter=request.shaft_diameter,
            bearing=request.bearing,
            bearing_make=request.bearing_make,
            housing=request.housing,
            weight_kg=request.weight_kg,
            unit_price=request.unit_price,
            rubber_diameter=request.rubber_diameter,
            belt_widths=request.belt_widths,
            quantity=request.quantity,
            shaft_end_type=request.shaft_end_type or "B",
            custom_shaft_extension=request.custom_shaft_extension
        )
        
        # Convert to base64
        pdf_bytes = pdf_buffer.getvalue()
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        return {
            "base64": base64_pdf,
            "filename": f"Drawing_{request.product_code.replace(' ', '_').replace('/', '-')}.pdf"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate drawing: {str(e)}")

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

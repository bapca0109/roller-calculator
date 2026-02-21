from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
    total_price: float
    status: str = QuoteStatus.PENDING
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QuoteInDB(Quote):
    id: str

class QuoteCreate(BaseModel):
    products: List[QuoteProduct]
    notes: Optional[str] = None

class QuoteUpdate(BaseModel):
    status: str
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
    # Calculate total price
    total_price = sum(item.quantity * item.unit_price for item in quote.products)
    
    quote_dict = {
        "customer_id": current_user["id"],
        "customer_name": current_user["name"],
        "customer_email": current_user["email"],
        "products": [p.dict() for p in quote.products],
        "total_price": total_price,
        "status": QuoteStatus.PENDING,
        "notes": quote.notes,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.quotes.insert_one(quote_dict)
    quote_dict["id"] = str(result.inserted_id)
    
    return QuoteInDB(**quote_dict)

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

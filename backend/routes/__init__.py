"""
Shared dependencies for all route modules.
Database connection, auth middleware, utility functions, and constants.
"""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import logging
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# IST Timezone
IST = timezone(timedelta(hours=5, minutes=30))

# MongoDB
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=10000, retryWrites=True, w='majority')
db = client[os.environ.get('DB_NAME', 'test_database')]

# Gmail
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
ADMIN_REGISTRATION_EMAILS = os.environ.get('ADMIN_REGISTRATION_EMAILS', 'info@convero.in,admin@convero.in').split(',')
ADMIN_RFQ_EMAILS = os.environ.get('ADMIN_RFQ_EMAILS', 'info@convero.in,design@convero.in').split(',')

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def get_ist_now():
    return datetime.now(IST)


def utc_to_ist(utc_dt):
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(IST)


def get_financial_year():
    now = get_ist_now()
    if now.month >= 4:
        start_year = now.year
    else:
        start_year = now.year - 1
    end_year = start_year + 1
    return f"{start_year % 100:02d}-{end_year % 100:02d}"


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"email": email}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")


def require_role(allowed_roles: List[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker


async def generate_quote_number():
    fy = get_financial_year()
    prefix = f"Q/{fy}/"
    last_quote = await db.quotes.find(
        {"quote_number": {"$regex": f"^{prefix.replace('/', '/')}"}},
        {"quote_number": 1}
    ).sort("quote_number", -1).limit(1).to_list(1)
    if last_quote:
        last_num = int(last_quote[0]["quote_number"].split("/")[-1])
        return f"{prefix}{last_num + 1:04d}"
    return f"{prefix}0001"


async def generate_rfq_number():
    fy = get_financial_year()
    prefix = f"RFQ/{fy}/"
    last_rfq = await db.quotes.find(
        {"quote_number": {"$regex": f"^{prefix.replace('/', '/')}"}},
        {"quote_number": 1}
    ).sort("quote_number", -1).limit(1).to_list(1)
    if last_rfq:
        last_num = int(last_rfq[0]["quote_number"].split("/")[-1])
        return f"{prefix}{last_num + 1:04d}"
    return f"{prefix}0001"


async def generate_customer_code() -> str:
    fy = get_financial_year()
    prefix = f"C/{fy}/"
    last_customer = await db.customers.find(
        {"customer_code": {"$regex": f"^{prefix}"}},
        {"customer_code": 1}
    ).sort("customer_code", -1).limit(1).to_list(1)
    if last_customer:
        try:
            last_num = int(last_customer[0]["customer_code"].split("/")[-1])
            return f"{prefix}{last_num + 1:04d}"
        except (ValueError, IndexError):
            pass
    return f"{prefix}0001"


# ============= SHARED MODELS =============

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
    customer_code: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


class QuoteStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"
    CANCELLED = "cancelled"


class UserRole:
    ADMIN = "admin"
    SALES = "sales"
    CUSTOMER = "customer"


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None
    designation: Optional[str] = None
    role: str = UserRole.CUSTOMER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RollerSpecs(BaseModel):
    pipe_diameter: float
    pipe_length: float
    shaft_diameter: int
    bearing_number: str
    bearing_make: Optional[str] = "china"
    pipe_type: Optional[str] = "B"
    rubber_diameter: Optional[float] = None
    belt_widths: Optional[List[int]] = None


class PricingFactors(BaseModel):
    quantity_discount: float = 0.0
    custom_premium: float = 0.0
    material_factor: float = 1.0


class ProductAttachment(BaseModel):
    name: str
    type: str
    base64: Optional[str] = None


class Product(BaseModel):
    name: str
    sku: str
    description: str
    category: str
    specifications: RollerSpecs
    base_price: float
    pricing_factors: Optional[PricingFactors] = None
    image: Optional[str] = None
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
    weight: Optional[float] = None
    weight_kg: Optional[float] = None
    specifications: Optional[Dict[str, Any]] = None
    calculated_discount: float = 0.0
    custom_premium: float = 0.0
    item_discount_percent: float = 0.0
    remark: Optional[str] = None
    attachments: Optional[List[ProductAttachment]] = []


class CommercialTerms(BaseModel):
    payment_terms: Optional[str] = "100% Advance against pro-forma"
    freight_terms: Optional[str] = "Ex-Works"
    color_finish: Optional[str] = "1+1 : Red oxide + finish paint black color approx 50-60 micron"
    delivery_timeline: Optional[str] = "25-30 working days"
    warranty: Optional[str] = "Warranty stands for 12 months from date of invoice considering L10 life."
    validity: Optional[str] = "This offer stands valid for 30 days."


class Quote(BaseModel):
    quote_number: Optional[str] = None
    quote_type: Optional[str] = None
    customer_id: str
    customer_name: str
    customer_email: str
    customer_code: Optional[str] = None
    customer_company: Optional[str] = None
    customer_rfq_no: Optional[str] = None
    customer_details: Optional[Dict[str, Any]] = None
    products: List[QuoteProduct]
    subtotal: float
    total_discount: float = 0.0
    use_item_discounts: bool = False
    discount_percent: Optional[float] = 0.0
    shipping_cost: float = 0.0
    delivery_location: Optional[str] = None
    packing_type: Optional[str] = None
    total_price: float
    status: str = QuoteStatus.PENDING
    notes: Optional[str] = None
    cost_breakdown: Optional[Dict[str, float]] = None
    pricing_details: Optional[Dict[str, Any]] = None
    freight_details: Optional[Dict[str, Any]] = None
    packing_charges: Optional[float] = 0.0
    commercial_terms: Optional[Dict[str, str]] = None
    read_by_admin: bool = False
    original_rfq_number: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    revision_history: Optional[List[Dict[str, Any]]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QuoteInDB(Quote):
    id: str


class QuoteCreate(BaseModel):
    products: List[QuoteProduct]
    customer_id: Optional[str] = None
    delivery_location: Optional[str] = None
    packing_type: Optional[str] = None
    shipping_cost: Optional[float] = 0.0
    freight_details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    customer_rfq_no: Optional[str] = None


class QuoteUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    shipping_cost: Optional[float] = None
    products: Optional[List[QuoteProduct]] = None
    subtotal: Optional[float] = None
    total_discount: Optional[float] = None
    use_item_discounts: Optional[bool] = None
    discount_percent: Optional[float] = None
    packing_charges: Optional[float] = None
    packing_type: Optional[str] = None
    delivery_location: Optional[str] = None
    total_price: Optional[float] = None
    freight_details: Optional[Dict[str, Any]] = None
    commercial_terms: Optional[Dict[str, str]] = None


class QuoteReject(BaseModel):
    reason: str
    custom_message: Optional[str] = None


class RollerQuoteCreate(BaseModel):
    customer_name: str
    customer_id: Optional[str] = None
    customer_details: Optional[Dict[str, Any]] = None
    configuration: Dict[str, Any]
    cost_breakdown: Dict[str, float]
    pricing: Dict[str, Any]
    freight: Optional[Dict[str, Any]] = None
    grand_total: float
    notes: Optional[str] = None


class RevisionHistoryEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    changed_by: str
    changed_by_name: Optional[str] = None
    action: str
    changes: Dict[str, Any] = {}
    summary: str = ""


def get_convero_logo_base64():
    """Get Convero logo as base64 string for PDF embedding"""
    import base64 as b64
    try:
        logo_path = ROOT_DIR / 'static' / 'convero-logo.png'
        if logo_path.exists():
            with open(logo_path, 'rb') as f:
                return b64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        logging.warning(f"Could not load logo: {e}")
    return None


def format_date_dmy(date_str):
    """Convert ISO date string to DD-MM-YYYY format"""
    if not date_str:
        return ""
    s = str(date_str)[:10]  # Get YYYY-MM-DD part
    parts = s.split("-")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return s

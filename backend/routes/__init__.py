"""
Shared dependencies for all route modules.
Database connection, auth middleware, utility functions, and constants.
"""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo import ReturnDocument
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



# ============= NUMBERING TEMPLATES =============
# Doc-type → default prefix template + pad width. Tokens in template:
#   {FY}   → "26-27" (current financial year short form)
#   {YYYY} → 4-digit year (calendar)
#   {MM}   → 2-digit month (01-12)
#   {DD}   → 2-digit day
# Admin can override these via `GET/PUT /api/admin/numbering-config`.
DEFAULT_NUMBERING_TEMPLATES = {
    "rfq": {"prefix": "RFQ/{FY}/", "pad": 4, "label": "RFQ (customer request)"},
    "q":   {"prefix": "Q/{FY}/",   "pad": 4, "label": "Quote"},
    "so":  {"prefix": "SO/{FY}/",  "pad": 4, "label": "Sales Order"},
    "wo":  {"prefix": "WO/{FY}/",  "pad": 4, "label": "Work Order"},
    "po":  {"prefix": "PO/{FY}/",  "pad": 4, "label": "Purchase Order"},
    "dc":  {"prefix": "DC/{FY}/",  "pad": 4, "label": "Delivery Challan"},
    "inv": {"prefix": "INV/{FY}/", "pad": 4, "label": "Tax Invoice"},
    "pi":  {"prefix": "PI/{FY}/",  "pad": 4, "label": "Proforma Invoice"},
    "c":   {"prefix": "C/{FY}/",   "pad": 4, "label": "Customer Code"},
}


def _resolve_tokens(template: str) -> str:
    """Replace {FY} / {YYYY} / {MM} / {DD} tokens in a template prefix."""
    now = datetime.now(IST)
    return (
        template
        .replace("{FY}", get_financial_year())
        .replace("{YYYY}", now.strftime("%Y"))
        .replace("{MM}", now.strftime("%m"))
        .replace("{DD}", now.strftime("%d"))
    )


async def get_numbering_config() -> dict:
    """Return merged templates: DB overrides on top of DEFAULT_NUMBERING_TEMPLATES."""
    stored = await db.numbering_config.find_one({"_id": "templates"}, {"_id": 0}) or {}
    overrides = stored.get("templates") or {}
    out = {}
    for k, v in DEFAULT_NUMBERING_TEMPLATES.items():
        out[k] = {**v, **(overrides.get(k) or {})}
    return out


async def format_number(doc_type: str, seq: int) -> str:
    """Render `{prefix}{seq:0{pad}d}` where prefix is token-resolved."""
    cfg = await get_numbering_config()
    tpl = cfg.get(doc_type) or DEFAULT_NUMBERING_TEMPLATES.get(doc_type) or {"prefix": f"{doc_type.upper()}/", "pad": 4}
    prefix = _resolve_tokens(tpl["prefix"])
    pad = int(tpl.get("pad") or 4)
    return f"{prefix}{seq:0{pad}d}"


async def _next_seq(counter_key: str, seed_value: int = 0) -> int:
    """Atomic monotonically-increasing counter stored in `counters` collection.

    - `counter_key`: e.g. "rfq:26-27", "so:26-27", "c:26-27"
    - `seed_value`: on first use (doc not present) the counter is initialised to
      this value using `$setOnInsert`; `$inc` then always returns the next.
    This is race-safe (single atomic `find_one_and_update`) and immune to
    renumbering/deletion patterns because the DB no longer has to be scanned.
    """
    # Idempotent seed: only sets `value` if the doc is new.
    await db.counters.update_one(
        {"_id": counter_key},
        {"$setOnInsert": {"value": seed_value}},
        upsert=True,
    )
    doc = await db.counters.find_one_and_update(
        {"_id": counter_key},
        {"$inc": {"value": 1}},
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["value"])


def _parse_suffix(value: str) -> int:
    """Return the trailing numeric portion of a code like 'RFQ/26-27/0042' -> 42.
    Returns 0 if not parseable."""
    try:
        return int((value or "").split("/")[-1])
    except (ValueError, IndexError):
        return 0


async def _max_suffix(collection, field: str, prefix: str) -> int:
    """Highest numeric suffix across all docs in `collection` whose `field`
    starts with `prefix`. Used only once (per FY) to seed the counter."""
    doc = await collection.find(
        {field: {"$regex": f"^{prefix}"}}, {field: 1}
    ).sort(field, -1).limit(1).to_list(1)
    return _parse_suffix(doc[0][field]) if doc else 0


async def generate_quote_number():
    fy = get_financial_year()
    # Seed from max of existing Q/FY/… suffixes (Q is its own sequence).
    seed = await _max_suffix(db.quotes, "quote_number", f"Q/{fy}/")
    n = await _next_seq(f"q:{fy}", seed_value=seed)
    return await format_number("q", n)


async def generate_rfq_number():
    fy = get_financial_year()
    # Seed from max across BOTH prefixes: every approved RFQ became a Q.
    rfq_max = await _max_suffix(db.quotes, "quote_number", f"RFQ/{fy}/")
    q_max = await _max_suffix(db.quotes, "quote_number", f"Q/{fy}/")
    seed = max(rfq_max, q_max)
    n = await _next_seq(f"rfq:{fy}", seed_value=seed)
    return await format_number("rfq", n)


async def generate_customer_code() -> str:
    fy = get_financial_year()
    seed = await _max_suffix(db.customers, "customer_code", f"C/{fy}/")
    n = await _next_seq(f"c:{fy}", seed_value=seed)
    return await format_number("c", n)


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
    SALES_MANAGER = "sales_manager"
    PRODUCTION_HEAD = "production_head"
    ACCOUNTS = "accounts"
    DISPATCH = "dispatch"

    @classmethod
    def all_staff(cls):
        return [cls.ADMIN, cls.SALES, cls.SALES_MANAGER, cls.PRODUCTION_HEAD, cls.ACCOUNTS, cls.DISPATCH]

    @classmethod
    def assignable(cls):
        # Roles an admin can assign (customer stays managed by signup flow)
        return [cls.ADMIN, cls.SALES_MANAGER, cls.PRODUCTION_HEAD, cls.ACCOUNTS, cls.DISPATCH, cls.CUSTOMER]


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

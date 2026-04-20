from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Header, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import warnings
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone

# Suppress passlib bcrypt version warning
warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

from passlib.context import CryptContext
from jose import jwt, JWTError
from bson import ObjectId
import roller_standards as rs
import pulley_standards as ps
from routes.pulley import router as pulley_router
from routes.customers import router as customers_router
from routes.analytics import router as analytics_router
from routes.exports import router as exports_router
from routes.auth import router as auth_router
from routes.quotes import router as quotes_router
from routes.products import router as products_router
from routes.admin import router as admin_router
from routes.crm import router as crm_router
from routes.orders import router as orders_router
from routes.workorders import router as workorders_router
from routes.suppliers import router as suppliers_router
from routes.inventory import router as inventory_router
from routes.price_history import router as price_history_router
from routes.dispatch import router as dispatch_router
from routes.final_inspection import router as final_inspection_router
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
import base64
import zipfile
import io
import tempfile
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# IST Timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Get current time in IST"""
    return datetime.now(IST)

def utc_to_ist(utc_dt):
    """Convert UTC datetime to IST"""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(IST)

def get_financial_year():
    """Get current financial year in format YY-YY (e.g., 25-26)"""
    now = get_ist_now()
    if now.month >= 4:  # April onwards
        start_year = now.year
    else:  # January to March
        start_year = now.year - 1
    end_year = start_year + 1
    return f"{start_year % 100:02d}-{end_year % 100:02d}"

async def generate_quote_number():
    """Generate sequential quote number like Q/25-26/0001"""
    fy = get_financial_year()
    
    # Get the counter collection for this financial year
    counter = await db.quote_counters.find_one_and_update(
        {"_id": f"quote_{fy}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    seq_num = counter.get("seq", 1)
    return f"Q/{fy}/{seq_num:04d}"

async def generate_rfq_number():
    """Generate sequential RFQ number like RFQ/25-26/0001 for customer requests"""
    fy = get_financial_year()
    
    # Get the counter collection for this financial year
    counter = await db.quote_counters.find_one_and_update(
        {"_id": f"rfq_{fy}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    seq_num = counter.get("seq", 1)
    return f"RFQ/{fy}/{seq_num:04d}"


def get_convero_logo_base64():
    """Get Convero logo as base64 string for PDF embedding"""
    try:
        logo_path = ROOT_DIR / 'static' / 'convero-logo.png'
        if logo_path.exists():
            with open(logo_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        logging.warning(f"Could not load logo: {e}")
    return None


def get_pdf_header_html(doc_title: str, doc_number: str, doc_date: str, rfq_ref: str = None):
    """Generate PDF header HTML with Convero logo and timestamp"""
    logo_base64 = get_convero_logo_base64()
    report_generated = get_ist_now().strftime("%d %b %Y at %I:%M:%S %p IST")
    
    if logo_base64:
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="height: 45px; width: auto;" alt="Convero" />'
    else:
        logo_html = '<div class="logo">C<span>O</span>NVER<span>O</span></div>'
    
    rfq_ref_html = f'<div class="doc-ref">Ref: {rfq_ref}</div>' if rfq_ref else ''
    
    return f'''
        <div class="header">
          <div class="logo-section">
            {logo_html}
            <div class="company-tagline">Rolling towards the future</div>
          </div>
          <div class="doc-type">
            <div class="doc-title">{doc_title}</div>
            <div class="doc-number">{doc_number}</div>
            {rfq_ref_html}
            <div class="doc-date">{doc_date}</div>
          </div>
        </div>
        <div class="company-info-header">
          <span>Plot No. 39, Swapnil Industrial Park, Beside Shiv Aaradhna Estate, Ahmedabad-Indore Highway, Village-Kuha, Ahmedabad, Gujarat 382433</span>
          <span>|</span>
          <span>info@convero.in</span>
          <span>|</span>
          <span>www.convero.in</span>
          <span>|</span>
          <span>GSTIN: 24BAUPP4310D2ZT</span>
        </div>
        <div class="report-generated">
          Report Generated: {report_generated}
        </div>
    '''


def get_pdf_footer_html():
    """Generate PDF footer HTML with company details"""
    generated_time = get_ist_now().strftime("%d %b %Y, %I:%M %p IST")
    return f'''
        <div class="footer">
          <div class="footer-left">
            <div class="footer-company">CONVERO SOLUTIONS</div>
            <div class="footer-tagline">Rolling towards the future</div>
            <div>Plot No. 39, Swapnil Industrial Park,</div>
            <div>Beside Shiv Aaradhna Estate, Ahmedabad-Indore Highway,</div>
            <div>Village-Kuha, Ahmedabad, Gujarat 382433</div>
            <div style="margin-top: 5px;">
              <strong>Email:</strong> info@convero.in | <strong>Web:</strong> www.convero.in
            </div>
            <div><strong>GSTIN:</strong> 24BAUPP4310D2ZT</div>
          </div>
          <div class="footer-right">
            <div class="footer-signature">Authorized Signature</div>
          </div>
        </div>
        <div class="footer-note">
          This is a computer-generated document. Generated on {generated_time}
        </div>
    '''


# MongoDB connection
mongo_url = os.environ['MONGO_URL']
# Add connection options for Atlas compatibility
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    retryWrites=True,
    w='majority'
)
db = client[os.environ['DB_NAME']]

# Gmail configuration
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
ADMIN_REGISTRATION_EMAILS = os.environ.get('ADMIN_REGISTRATION_EMAILS', 'info@convero.in,admin@convero.in').split(',')
ADMIN_RFQ_EMAILS = os.environ.get('ADMIN_RFQ_EMAILS', 'info@convero.in,design@convero.in').split(',')

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Create the main app
app = FastAPI()

# Add GZip compression for faster responses
app.add_middleware(GZipMiddleware, minimum_size=500)

api_router = APIRouter(prefix="/api")

# Root endpoint for health checks and basic info
@app.get("/")
async def root():
    """Root endpoint - confirms API is running"""
    return {"status": "ok", "app": "Roller Price Calculator API", "version": "1.0.0"}

# Privacy Policy endpoint
@app.get("/privacy-policy")
async def get_privacy_policy():
    """Serve the privacy policy page"""
    privacy_path = ROOT_DIR / 'static' / 'privacy-policy.html'
    if privacy_path.exists():
        return FileResponse(privacy_path, media_type='text/html')
    raise HTTPException(status_code=404, detail="Privacy policy not found")

# Also serve at /api/privacy-policy for API access
@api_router.get("/privacy-policy")
async def get_api_privacy_policy():
    """Serve the privacy policy page via API"""
    privacy_path = ROOT_DIR / 'static' / 'privacy-policy.html'
    if privacy_path.exists():
        return FileResponse(privacy_path, media_type='text/html')
    raise HTTPException(status_code=404, detail="Privacy policy not found")

# Terms of Service endpoint
@app.get("/terms")
async def get_terms_of_service():
    """Serve the terms of service page"""
    terms_path = ROOT_DIR / 'static' / 'terms-of-service.html'
    if terms_path.exists():
        return FileResponse(terms_path, media_type='text/html')
    raise HTTPException(status_code=404, detail="Terms of service not found")

# Also serve at /api/terms for API access
@api_router.get("/terms")
async def get_api_terms_of_service():
    """Serve the terms of service page via API"""
    terms_path = ROOT_DIR / 'static' / 'terms-of-service.html'
    if terms_path.exists():
        return FileResponse(terms_path, media_type='text/html')
    raise HTTPException(status_code=404, detail="Terms of service not found")

# Health check endpoint for deployment (also at root level for K8s probes)
@app.get("/health")
async def root_health_check():
    """Health check endpoint at root level for Kubernetes probes"""
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# Health check endpoint for deployment under /api
@api_router.get("/health")
async def api_health_check():
    """Health check endpoint for Kubernetes probes"""
    try:
        # Test database connection
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@api_router.get("/commercial-terms-options")
async def get_commercial_terms_options():
    """Get all available commercial terms options for dropdown selections"""
    return COMMERCIAL_TERMS_OPTIONS

# ============= MODELS =============

class UserRole:
    ADMIN = "admin"
    SALES = "sales"
    CUSTOMER = "customer"

class User(BaseModel):
    email: EmailStr
    name: str
    company: Optional[str] = None
    designation: Optional[str] = None
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
    designation: Optional[str] = None
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
    customer_code: Optional[str] = None  # Auto-generated code like C0001, C0002

class CustomerInDB(Customer):
    id: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

async def generate_customer_code() -> str:
    """Generate next customer code in sequence (C0001, C0002, etc.)"""
    # Find the highest customer code
    last_customer = await db.users.find_one(
        {"role": "customer", "customer_code": {"$exists": True, "$ne": None}},
        sort=[("customer_code", -1)]
    )
    
    if last_customer and last_customer.get("customer_code"):
        # Extract number from code like "C0001" -> 1
        try:
            last_num = int(last_customer["customer_code"][1:])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1
    
    # Format as C0001, C0002, etc. (4 digits with leading zeros)
    return f"C{next_num:04d}"

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

class ProductAttachment(BaseModel):
    name: str
    type: str
    base64: Optional[str] = None

class QuoteProduct(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    weight: Optional[float] = None  # Weight per unit in kg
    weight_kg: Optional[float] = None  # Weight per unit in kg (alias)
    specifications: Optional[Dict[str, Any]] = None
    calculated_discount: float = 0.0  # Quantity discount applied
    custom_premium: float = 0.0  # Premium for custom specs
    item_discount_percent: float = 0.0  # Per-item discount percentage (editable by admin)
    remark: Optional[str] = None  # Customer remark for this product
    attachments: Optional[List[ProductAttachment]] = []

class QuoteStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"

# Commercial Terms Options for Quote
COMMERCIAL_TERMS_OPTIONS = {
    "payment_terms": [
        "100% Advance against pro-forma",
        "100% Against pro-forma invoice before delivery",
        "50% Advance + 50% against pro-forma invoice before delivery",
        "25% Advance + 75% against pro-forma invoice before delivery",
        "10% Advance + 90% against pro-forma invoice before delivery",
        "7 days credit from date of invoice",
        "15 days credit from date of invoice",
        "30 days credit from date of invoice",
        "45 days credit from date of invoice",
    ],
    "freight_terms": [
        "Ex-Works",
        "FOR your site",
    ],
    "color_finish": [
        "0+1 : Standard finish paint black color approx 25-35 micron",
        "1+1 : Red oxide + finish paint black color approx 50-60 micron",
        "1+1 : Zinc rich primer + finish paint black color approx 60-70 micron",
        "1+1+1 : Zinc rich primer + intermediate + finish paint black color approx 110-130 micron",
        "1+2+1 : Zinc rich primer + 2 coat intermediate + finish paint black color approx 160-200 micron",
    ],
    "delivery_timeline": [
        "7-10 working days",
        "15-20 working days",
        "25-30 working days",
        "35-40 working days",
        "45-50 working days",
        "55-60 working days",
        "75-80 working days",
        "90-95 working days",
        "110-120 working days",
        "As per schedule",
        "Immediate",
    ],
    "warranty": "Warranty stands for 12 months from date of invoice considering L10 life.",
    "validity": "This offer stands valid for 30 days.",
}

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
    customer_code: Optional[str] = None  # Customer code like C0001
    customer_company: Optional[str] = None  # Customer company name
    customer_rfq_no: Optional[str] = None  # Customer's own reference number (optional)
    customer_details: Optional[Dict[str, Any]] = None  # Full customer details for PDF
    products: List[QuoteProduct]
    subtotal: float
    total_discount: float = 0.0
    use_item_discounts: bool = False  # If True, use per-item discounts instead of total discount
    discount_percent: Optional[float] = 0.0  # Overall discount percentage
    shipping_cost: float = 0.0
    delivery_location: Optional[str] = None
    packing_type: Optional[str] = None  # standard, pallet, wooden_box
    total_price: float
    status: str = QuoteStatus.PENDING
    notes: Optional[str] = None
    cost_breakdown: Optional[Dict[str, float]] = None
    pricing_details: Optional[Dict[str, Any]] = None
    freight_details: Optional[Dict[str, Any]] = None
    packing_charges: Optional[float] = 0.0
    commercial_terms: Optional[Dict[str, str]] = None  # Commercial terms selections
    read_by_admin: bool = False  # Track if admin has read the RFQ
    original_rfq_number: Optional[str] = None  # Original RFQ number if approved
    approved_at: Optional[datetime] = None  # When the RFQ was approved
    approved_by: Optional[str] = None  # Admin who approved
    rejected_at: Optional[datetime] = None  # When the RFQ was rejected
    rejected_by: Optional[str] = None  # Admin who rejected
    rejection_reason: Optional[str] = None  # Rejection reason code
    revision_history: Optional[List[Dict[str, Any]]] = []  # Track all changes made to this quote
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class QuoteInDB(Quote):
    id: str

class QuoteCreate(BaseModel):
    products: List[QuoteProduct]
    customer_id: Optional[str] = None  # Required for admin, null for customers
    delivery_location: Optional[str] = None
    packing_type: Optional[str] = None  # standard, pallet, wooden_box
    shipping_cost: Optional[float] = 0.0  # Freight calculated from pincode
    freight_details: Optional[Dict[str, Any]] = None  # Custom freight details from admin
    notes: Optional[str] = None
    customer_rfq_no: Optional[str] = None  # Customer's own reference number (optional)

class QuoteUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    shipping_cost: Optional[float] = None
    products: Optional[List[QuoteProduct]] = None
    subtotal: Optional[float] = None
    total_discount: Optional[float] = None
    use_item_discounts: Optional[bool] = None  # Toggle between item discounts and total discount
    discount_percent: Optional[float] = None  # Overall discount percentage
    packing_charges: Optional[float] = None
    packing_type: Optional[str] = None  # standard, pallet, wooden_box
    delivery_location: Optional[str] = None  # Freight pincode
    total_price: Optional[float] = None
    freight_details: Optional[Dict[str, Any]] = None  # Custom freight details from admin
    commercial_terms: Optional[Dict[str, str]] = None  # Commercial terms selections

class QuoteReject(BaseModel):
    """Reject an RFQ with a reason"""
    reason: str  # low_quantity, low_amount, not_in_range
    custom_message: Optional[str] = None

class RevisionHistoryEntry(BaseModel):
    """Track changes made to a quote"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    changed_by: str  # Email of user who made the change
    changed_by_name: Optional[str] = None  # Name of user
    action: str  # 'created', 'updated', 'approved', 'rejected', 'revised'
    changes: Dict[str, Any] = {}  # What was changed: {field_name: {old: x, new: y}}
    summary: str = ""  # Human-readable summary of changes

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

# # ============= AUTH ROUTES ============= (moved to routes/)

# # ============= PRODUCT ROUTES ============= (moved to routes/)

# ============= CUSTOMER ROUTES (moved to routes/customers.py) =============


# ============= FILE DOWNLOADS (moved to routes/customers.py) =============


# ============= PULLEY ROUTES (moved to routes/pulley.py) =============

# ============= CUSTOMER API (moved to routes/customers.py) =============

# # ============= DRAWING GENERATOR ============= (moved to routes/)

# ============= ANALYTICS & DASHBOARD (moved to routes/analytics.py) =============


# ============= EXPORT ENDPOINTS (moved to routes/exports.py) =============

# Include the router in the main app
api_router.include_router(pulley_router)
api_router.include_router(customers_router)
api_router.include_router(analytics_router)
api_router.include_router(exports_router)
api_router.include_router(auth_router)
api_router.include_router(quotes_router)
api_router.include_router(products_router)
api_router.include_router(admin_router)
api_router.include_router(crm_router)
api_router.include_router(orders_router)
api_router.include_router(workorders_router)
api_router.include_router(suppliers_router)
api_router.include_router(inventory_router)
api_router.include_router(price_history_router)
api_router.include_router(dispatch_router)
api_router.include_router(final_inspection_router)
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

@app.on_event("startup")
async def startup_db_indexes():
    """Create database indexes for faster queries"""
    try:
        # Quotes indexes
        await db.quotes.create_index("quote_number")
        await db.quotes.create_index("customer_id")
        await db.quotes.create_index("status")
        await db.quotes.create_index("created_at")
        await db.quotes.create_index([("customer_id", 1), ("status", 1)])
        
        # Users indexes
        await db.users.create_index("email", unique=True)
        await db.users.create_index("customer_code")
        await db.users.create_index("role")
        
        # Customers indexes (non-unique to avoid duplicates issue)
        await db.customers.create_index("customer_code")
        await db.customers.create_index("email")
        await db.customers.create_index("name")
        
        logging.info("Database indexes created successfully")
    except Exception as e:
        logging.warning(f"Index creation warning: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

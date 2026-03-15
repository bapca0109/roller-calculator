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

# ============= AUTH ROUTES =============

# OTP Configuration
OTP_EXPIRY_MINUTES = 10
OTP_COOLDOWN_SECONDS = 60

import random

class OTPRequest(BaseModel):
    email: EmailStr
    name: str
    mobile: str
    pincode: str
    city: str
    state: str
    company: str  # Required field
    designation: Optional[str] = None  # Optional designation field
    password: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str
    name: str
    mobile: str
    pincode: str
    city: str
    state: str
    company: str  # Required field
    designation: Optional[str] = None  # Optional designation field
    password: str

class ResendOTPRequest(BaseModel):
    email: EmailStr

def generate_otp():
    """Generate a 4-digit OTP"""
    return str(random.randint(1000, 9999))

async def send_otp_email(email: str, otp: str, name: str):
    """Send OTP email to the user"""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise HTTPException(status_code=500, detail="Email service not configured")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Your Verification Code - {otp}"
        msg['From'] = GMAIL_USER
        msg['To'] = email
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #1E293B; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .otp-box {{ background-color: #960018; color: white; font-size: 32px; font-weight: bold; letter-spacing: 8px; padding: 20px 40px; text-align: center; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">Convero Solutions</h1>
                    <p style="margin: 5px 0 0 0;">Roller Price Calculator</p>
                </div>
                <div class="content">
                    <p>Hello {name},</p>
                    <p>Your verification code for account registration is:</p>
                    <div class="otp-box">{otp}</div>
                    <p>This code will expire in <strong>10 minutes</strong>.</p>
                    <p>If you didn't request this code, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Convero Solutions. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hello {name},
        
        Your verification code for account registration is: {otp}
        
        This code will expire in 10 minutes.
        
        If you didn't request this code, please ignore this email.
        
        - Convero Solutions
        """
        
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, email, msg.as_string())
        
        return True
    except Exception as e:
        logging.error(f"Failed to send OTP email: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")

async def send_registration_notification_email(customer_data):
    """Send registration notification email to admin"""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logging.warning("Email service not configured, skipping registration notification")
        return False
    
    admin_emails = ADMIN_REGISTRATION_EMAILS
    ist_now = get_ist_now()
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"New Customer Registration - {customer_data.name} ({customer_data.company})"
        msg['From'] = GMAIL_USER
        msg['To'] = ", ".join(admin_emails)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #960018; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .info-table th {{ background-color: #1E293B; color: white; padding: 12px; text-align: left; }}
                .info-table td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
                .info-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .highlight {{ color: #960018; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">New Customer Registration</h1>
                    <p style="margin: 5px 0 0 0;">Convero Solutions - Roller Price Calculator</p>
                </div>
                <div class="content">
                    <p>A new customer has registered on the platform:</p>
                    
                    <table class="info-table">
                        <tr>
                            <th colspan="2">Customer Details</th>
                        </tr>
                        <tr>
                            <td><strong>Customer Name</strong></td>
                            <td class="highlight">{customer_data.name}</td>
                        </tr>
                        <tr>
                            <td><strong>Company Name</strong></td>
                            <td class="highlight">{customer_data.company}</td>
                        </tr>
                        <tr>
                            <td><strong>Designation</strong></td>
                            <td>{customer_data.designation or 'Not provided'}</td>
                        </tr>
                        <tr>
                            <td><strong>Email ID</strong></td>
                            <td>{customer_data.email}</td>
                        </tr>
                        <tr>
                            <td><strong>Mobile Number</strong></td>
                            <td>{customer_data.mobile}</td>
                        </tr>
                        <tr>
                            <td><strong>Pin Code</strong></td>
                            <td>{customer_data.pincode}</td>
                        </tr>
                        <tr>
                            <td><strong>City</strong></td>
                            <td>{customer_data.city}</td>
                        </tr>
                        <tr>
                            <td><strong>State</strong></td>
                            <td>{customer_data.state}</td>
                        </tr>
                        <tr>
                            <td><strong>Registration Time</strong></td>
                            <td>{ist_now.strftime("%d %b %Y, %I:%M %p IST")}</td>
                        </tr>
                    </table>
                    
                    <p style="color: #666;">This customer can now access the Roller Price Calculator app and create quotes.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Convero Solutions. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        New Customer Registration - Convero Solutions
        
        Customer Details:
        -----------------
        Customer Name: {customer_data.name}
        Company Name: {customer_data.company}
        Designation: {customer_data.designation or 'Not provided'}
        Email ID: {customer_data.email}
        Mobile Number: {customer_data.mobile}
        Pin Code: {customer_data.pincode}
        City: {customer_data.city}
        State: {customer_data.state}
        Registration Time: {ist_now.strftime("%d %b %Y, %I:%M %p IST")}
        
        This customer can now access the Roller Price Calculator app and create quotes.
        
        - Convero Solutions
        """
        
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            for admin_email in admin_emails:
                server.sendmail(GMAIL_USER, admin_email, msg.as_string())
        
        logging.info(f"Registration notification sent to admins for customer: {customer_data.email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send registration notification email: {str(e)}")
        return False  # Don't raise exception, just log the error

def generate_rfq_html(rfq_data: dict) -> str:
    """Generate HTML content for RFQ PDF - WITHOUT PRICES"""
    ist_now = get_ist_now()
    display_date = ist_now.strftime("%d %b %Y")
    quote_number = rfq_data.get('quote_number', 'N/A')
    
    # Get logo for PDF header
    logo_base64 = get_convero_logo_base64() or ""
    report_generated = get_ist_now().strftime("%d %b %Y at %I:%M:%S %p IST")
    
    # Generate products HTML - WITHOUT PRICES
    products = rfq_data.get('products', [])
    products_html = ""
    grand_total_weight = 0  # Track total weight for RFQ
    for idx, product in enumerate(products, 1):
        qty = product.get('quantity', 0)
        
        # Get weight information - check multiple possible field names
        unit_weight = (
            product.get('weight') or 
            product.get('weight_kg') or 
            product.get('specifications', {}).get('weight') or 
            product.get('specifications', {}).get('weight_kg') or 
            product.get('specifications', {}).get('single_roller_weight_kg') or 
            0
        )
        total_weight = unit_weight * qty
        grand_total_weight += total_weight
        
        # Format weight display
        unit_weight_str = f"{unit_weight:.2f}" if unit_weight > 0 else "-"
        total_weight_str = f"{total_weight:.2f}" if total_weight > 0 else "-"
        
        specs = product.get('specifications', {})
        specs_html = ""
        if specs:
            spec_parts = []
            if specs.get('roller_type'): spec_parts.append(f"Type: {specs['roller_type']}")
            if specs.get('pipe_diameter'): spec_parts.append(f"Pipe: {specs['pipe_diameter']}mm")
            if specs.get('shaft_diameter'): spec_parts.append(f"Shaft: {specs['shaft_diameter']}mm")
            if specs.get('bearing'): spec_parts.append(f"Bearing: {specs['bearing']}")
            if spec_parts:
                specs_html = f'<div style="font-size: 9px; color: #666; margin-top: 3px;">{" | ".join(spec_parts)}</div>'
        
        remark_html = ""
        if product.get('remark'):
            remark_html = f'<div style="font-size: 9px; color: #0066cc; margin-top: 3px; font-style: italic;">Note: {product["remark"]}</div>'
        
        products_html += f"""
        <tr>
            <td style="padding: 8px 10px; border-bottom: 1px solid #eee; text-align: center;">{idx}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left;">
                <div style="font-weight: 500; color: #1a1a1a;">{product.get('product_name', product.get('product_id', 'N/A'))}</div>
                {specs_html}
                {remark_html}
            </td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #eee; text-align: center;">{qty}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #eee; text-align: right;">{unit_weight_str}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #eee; text-align: right;">{total_weight_str}</td>
        </tr>
        """
    
    # Customer details
    customer_code = rfq_data.get('customer_code', '')
    customer_name = rfq_data.get('customer_name', 'N/A')
    customer_company = rfq_data.get('customer_company', '')
    customer_details = rfq_data.get('customer_details', {})
    
    customer_code_html = f'<div style="color: #960018; font-weight: bold; margin-bottom: 4px;">Customer Code: {customer_code}</div>' if customer_code else ''
    
    address_html = ""
    if customer_details.get('address'):
        address_parts = [customer_details['address']]
        if customer_details.get('city'): address_parts.append(customer_details['city'])
        if customer_details.get('state'): address_parts.append(customer_details['state'])
        if customer_details.get('pincode'): address_parts.append(f"- {customer_details['pincode']}")
        address_html = f'<div style="font-size: 10px; color: #555; margin-top: 4px; line-height: 1.5;">{", ".join(address_parts)}</div>'
    
    gst_html = f'<div style="display: inline-block; margin-top: 6px; padding: 3px 8px; background: #e8f4fc; border-radius: 3px; font-size: 9px; color: #0066cc; font-weight: 500;">GSTIN: {customer_details.get("gst_number")}</div>' if customer_details.get('gst_number') else ''
    
    contact_parts = []
    if customer_details.get('phone'): contact_parts.append(f"Ph: {customer_details['phone']}")
    if customer_details.get('email'): contact_parts.append(customer_details['email'])
    contact_html = f'<div style="font-size: 9px; color: #666; margin-top: 6px;">{" | ".join(contact_parts)}</div>' if contact_parts else ''
    
    # Notes
    notes_html = f'<div style="padding: 10px; background: #fff5f5; border-left: 3px solid #960018; border-radius: 4px; margin-bottom: 15px; font-size: 10px;"><strong>Notes:</strong> {rfq_data.get("notes")}</div>' if rfq_data.get('notes') else ''
    
    # Packing and Delivery details
    packing_type = rfq_data.get('packing_type')
    delivery_location = rfq_data.get('delivery_location')
    
    packing_type_labels = {
        'standard': 'Standard (1%)',
        'pallet': 'Pallet (4%)',
        'wooden_box': 'Wooden Box (8%)'
    }
    
    packing_delivery_html = ""
    if packing_type or delivery_location:
        packing_delivery_html = '<div style="padding: 10px; background: #f5f5f5; border-radius: 4px; margin-bottom: 15px; font-size: 10px; display: flex; gap: 40px; flex-wrap: wrap;">'
        if packing_type:
            # Handle custom packing types
            if packing_type.startswith('custom_'):
                try:
                    custom_percent = float(packing_type.replace('custom_', ''))
                    packing_label = f'Custom ({custom_percent:.1f}%)'
                except:
                    packing_label = packing_type_labels.get(packing_type, packing_type)
            else:
                packing_label = packing_type_labels.get(packing_type, packing_type)
            packing_delivery_html += f'<div><strong>Packing Type:</strong> {packing_label}</div>'
        if delivery_location:
            packing_delivery_html += f'<div><strong>Delivery Pincode:</strong> {delivery_location}</div>'
        packing_delivery_html += '</div>'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Arial, sans-serif; 
                color: #1a1a1a; 
                font-size: 11px;
                line-height: 1.4;
                padding: 15px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                padding-bottom: 15px;
                border-bottom: 2px solid #960018;
                margin-bottom: 15px;
            }}
            .logo {{ font-size: 26px; font-weight: 800; letter-spacing: -1px; color: #1a1a1a; }}
            .logo span {{ color: #960018; }}
            .logo-section img {{ height: 45px; width: auto; }}
            .company-tagline {{ font-size: 9px; color: #960018; letter-spacing: 2px; margin-top: 2px; font-style: italic; }}
            .company-info-header {{ font-size: 8px; color: #666; text-align: center; margin-bottom: 10px; padding: 5px; background: #f9f9f9; border-radius: 3px; }}
            .company-info-header span {{ margin: 0 3px; }}
            .report-generated {{ font-size: 8px; color: #666; text-align: right; margin-bottom: 10px; font-style: italic; }}
            .doc-type {{ text-align: right; }}
            .doc-title {{ font-size: 18px; font-weight: 700; color: #960018; letter-spacing: 1px; }}
            .doc-number {{ font-size: 13px; font-weight: 600; color: #333; margin-top: 3px; }}
            .doc-date {{ font-size: 10px; color: #666; margin-top: 2px; }}
            .info-section {{ display: flex; justify-content: space-between; margin-bottom: 15px; gap: 15px; }}
            .info-box {{ flex: 1; padding: 12px; border: 1px solid #e0e0e0; border-radius: 4px; background: #fafafa; }}
            .info-box-title {{ font-size: 8px; font-weight: 600; color: #960018; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; border-bottom: 1px solid #e0e0e0; padding-bottom: 4px; }}
            .info-company {{ font-size: 12px; font-weight: 600; color: #1a1a1a; }}
            .section-title {{ font-size: 10px; font-weight: 600; color: #960018; text-transform: uppercase; letter-spacing: 1px; padding: 8px 0; border-bottom: 1px solid #960018; margin-bottom: 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
            th {{ background: #960018; color: white; padding: 8px 10px; font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
            .footer {{ margin-top: 25px; padding-top: 15px; border-top: 2px solid #960018; display: flex; justify-content: space-between; align-items: flex-end; }}
            .footer-left {{ font-size: 9px; color: #666; }}
            .footer-company {{ font-weight: 600; color: #1a1a1a; font-size: 11px; }}
            .footer-note {{ font-size: 8px; color: #999; margin-top: 10px; text-align: center; }}
            .rfq-notice {{ padding: 15px; background: #FFF3CD; border: 1px solid #FFEEBA; border-radius: 8px; margin-top: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo-section">
                <img src="data:image/png;base64,{logo_base64}" style="height: 45px; width: auto;" alt="Convero" />
                <div class="company-tagline">Rolling towards the future</div>
            </div>
            <div class="doc-type">
                <div class="doc-title">REQUEST FOR QUOTATION</div>
                <div class="doc-number">{quote_number}</div>
                <div class="doc-date">{display_date}</div>
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
        <div class="report-generated">Report Generated: {report_generated}</div>

        <div class="info-section">
            <div class="info-box">
                <div class="info-box-title">From</div>
                <div class="info-company">CONVERO SOLUTIONS</div>
                <div style="font-size: 9px; color: #960018; font-style: italic; margin-bottom: 4px;">Rolling towards the future</div>
                <div style="font-size: 10px; color: #555; margin-top: 4px; line-height: 1.5;">
                    Plot No. 39, Swapnil Industrial Park,<br>
                    Beside Shiv Aaradhna Estate,<br>
                    Ahmedabad-Indore Highway,<br>
                    Village-Kuha, Ahmedabad,<br>
                    Gujarat 382433
                </div>
                <div style="font-size: 9px; color: #666; margin-top: 6px;">
                    <strong>Email:</strong> info@convero.in | <strong>Web:</strong> www.convero.in
                </div>
                <div style="font-size: 9px; color: #666; margin-top: 3px;">
                    <strong>GSTIN:</strong> 24BAUPP4310D2ZT
                </div>
            </div>
            <div class="info-box">
                <div class="info-box-title">Customer Details</div>
                {customer_code_html}
                <div class="info-company">{customer_company or customer_name}</div>
                {address_html}
                {gst_html}
                {contact_html}
            </div>
        </div>

        <div class="section-title">Products Requested</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 6%;">#</th>
                    <th style="width: 50%; text-align: left;">Description</th>
                    <th style="width: 10%;">Qty</th>
                    <th style="width: 14%; text-align: right;">Wt/Pc (kg)</th>
                    <th style="width: 14%; text-align: right;">Total Wt</th>
                </tr>
            </thead>
            <tbody>
                {products_html}
            </tbody>
            <tfoot>
                <tr style="background: #e8f4fc; font-weight: bold;">
                    <td colspan="4" style="padding: 8px 10px; text-align: right; color: #0066cc;">Grand Total Weight:</td>
                    <td style="padding: 8px 10px; text-align: right; color: #0066cc;">{grand_total_weight:.2f} kg</td>
                </tr>
            </tfoot>
        </table>

        {packing_delivery_html}

        {notes_html}

        <div class="rfq-notice">
            <strong>This is a Request for Quotation</strong><br>
            <span style="color: #666; font-size: 10px;">Pricing will be provided upon review by our team. You will receive a formal quotation via email.</span>
        </div>

        <div class="footer">
            <div class="footer-left">
                <div class="footer-company">CONVERO SOLUTIONS</div>
                <div style="font-size: 8px; color: #960018; font-style: italic;">Rolling towards the future</div>
                <div style="font-size: 8px; margin-top: 3px;">Plot No. 39, Swapnil Industrial Park, Village-Kuha, Ahmedabad, Gujarat 382433</div>
                <div style="font-size: 8px;"><strong>Email:</strong> info@convero.in | <strong>Web:</strong> www.convero.in | <strong>GSTIN:</strong> 24BAUPP4310D2ZT</div>
            </div>
        </div>
        
        <div class="footer-note">
            This is a computer-generated document. E&amp;OE (Errors and Omissions Excepted)
        </div>
    </body>
    </html>
    """
    return html

def generate_rfq_pdf(rfq_data: dict) -> bytes:
    """Generate PDF for RFQ using weasyprint with HTML template"""
    try:
        from weasyprint import HTML
        html_content = generate_rfq_html(rfq_data)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except ImportError:
        # Fallback to fpdf2 if weasyprint not available
        logging.warning("weasyprint not available, using fpdf2 fallback")
        return generate_rfq_pdf_fallback(rfq_data)

def generate_rfq_pdf_fallback(rfq_data: dict) -> bytes:
    """Fallback RFQ PDF generation using fpdf2"""
    from fpdf import FPDF
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    ist_now = get_ist_now()
    
    # Header with Carmine Red background
    pdf.set_fill_color(150, 0, 24)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, 'REQUEST FOR QUOTATION', align='C')
    pdf.set_font('Helvetica', '', 12)
    pdf.set_xy(10, 20)
    pdf.cell(0, 8, f'{rfq_data.get("quote_number", "N/A")}', align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_xy(10, 30)
    pdf.cell(0, 6, f'Date: {ist_now.strftime("%d %b %Y, %I:%M %p IST")}', align='C')
    
    # Reset text color
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(50)
    
    # Customer Details Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'Customer Details', fill=True, ln=True)
    pdf.ln(3)
    
    pdf.set_font('Helvetica', '', 10)
    details = [
        ('Customer Code', rfq_data.get('customer_code', 'N/A')),
        ('Name', rfq_data.get('customer_name', 'N/A')),
        ('Company', rfq_data.get('customer_company', 'N/A')),
        ('Email', rfq_data.get('customer_email', 'N/A')),
    ]
    
    # Add customer details from customer_details if available
    customer_details = rfq_data.get('customer_details', {})
    if customer_details:
        if customer_details.get('mobile'):
            details.append(('Mobile', customer_details.get('mobile')))
        if customer_details.get('gst'):
            details.append(('GST No.', customer_details.get('gst')))
        if customer_details.get('address'):
            details.append(('Address', customer_details.get('address')))
    
    for label, value in details:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(40, 6, f'{label}:')
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, str(value), ln=True)
    
    pdf.ln(5)
    
    # Products Table - WITHOUT PRICES
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'Products Requested', fill=True, ln=True)
    pdf.ln(3)
    
    # Table header
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(15, 8, '#', fill=True, border=1, align='C')
    pdf.cell(45, 8, 'Product Code', fill=True, border=1, align='C')
    pdf.cell(90, 8, 'Description', fill=True, border=1, align='C')
    pdf.cell(30, 8, 'Quantity', fill=True, border=1, align='C')
    pdf.ln()
    
    # Table rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 9)
    products = rfq_data.get('products', [])
    for idx, product in enumerate(products, 1):
        pdf.cell(15, 7, str(idx), border=1, align='C')
        pdf.cell(45, 7, str(product.get('product_id', 'N/A'))[:20], border=1, align='C')
        pdf.cell(90, 7, str(product.get('product_name', 'N/A'))[:45], border=1)
        pdf.cell(30, 7, str(product.get('quantity', 0)), border=1, align='C')
        pdf.ln()
    
    pdf.ln(5)
    
    # Notes section if any
    if rfq_data.get('notes'):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, 'Notes:', ln=True)
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(0, 5, rfq_data.get('notes'))
    
    pdf.ln(10)
    
    # Footer note
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, 'This is a Request for Quotation. Pricing will be provided upon review by our team.')
    
    # Footer
    pdf.set_y(-20)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5, 'Convero Solutions | info@convero.in', align='C')
    
    return pdf.output()

def generate_quote_html(quote_data: dict, hide_prices: bool = False) -> str:
    """Generate HTML content for Quote PDF - EXACT MATCH with frontend export"""
    from datetime import datetime
    
    # Use approved_at date if available, else use current time
    quote_date = quote_data.get('approved_at') or quote_data.get('created_at') or get_ist_now()
    if isinstance(quote_date, str):
        try:
            quote_date = datetime.fromisoformat(quote_date.replace('Z', '+00:00'))
        except:
            quote_date = get_ist_now()
    
    # Convert to IST if not already
    quote_date = utc_to_ist(quote_date) if quote_date else get_ist_now()
    
    display_date = quote_date.strftime("%d %b %Y, %I:%M %p")
    
    # Get logo for PDF header
    logo_base64 = get_convero_logo_base64() or ""
    report_generated = get_ist_now().strftime("%d %b %Y at %I:%M:%S %p IST")
    
    # Determine if RFQ or Quote
    quote_number = quote_data.get('quote_number', 'N/A')
    is_rfq = quote_number.startswith('RFQ')
    doc_label_full = 'REQUEST FOR QUOTATION' if is_rfq else 'QUOTATION'
    
    # ALWAYS use item-level discount format for PDF display
    # This shows: SR. | ITEM CODE | QTY | RATE | DISC % | VALUE AFTER DISC | TOTAL
    use_item_discounts = True  # Always show per-item discount columns in PDF
    
    # Generate products HTML with new table format
    products = quote_data.get('products', [])
    products_html = ""
    calculated_subtotal = 0
    total_item_discount = 0
    grand_total_weight = 0  # Track total weight
    
    # Calculate overall discount percentage for items without individual discounts
    subtotal_raw = quote_data.get('subtotal', 0)
    total_discount_raw = quote_data.get('total_discount', 0)
    overall_discount_percent = (total_discount_raw / subtotal_raw * 100) if subtotal_raw > 0 else 0
    has_per_item_discounts = quote_data.get('use_item_discounts', False)
    
    for idx, product in enumerate(products, 1):
        qty = product.get('quantity', 0)
        unit_price = product.get('unit_price', 0)
        
        # Get specifications safely (handle null/None values)
        specs = product.get('specifications') or {}
        
        # Get weight information - check multiple possible field names
        unit_weight = (
            product.get('weight') or 
            product.get('weight_kg') or 
            specs.get('weight') or 
            specs.get('weight_kg') or 
            specs.get('single_roller_weight_kg') or 
            0
        )
        total_weight = unit_weight * qty
        grand_total_weight += total_weight
        
        # Use individual item discount if available, otherwise use overall discount percentage
        if has_per_item_discounts and product.get('item_discount_percent') is not None:
            item_discount_percent = product.get('item_discount_percent', 0)
        else:
            item_discount_percent = overall_discount_percent
        
        # Calculate values
        value_after_discount = unit_price * (1 - item_discount_percent / 100)
        line_total = qty * value_after_discount
        original_amount = qty * unit_price
        item_discount_amount = original_amount - line_total
        
        calculated_subtotal += line_total
        total_item_discount += item_discount_amount
        specs_html = ""
        if specs:
            spec_parts = []
            if specs.get('roller_type'): spec_parts.append(f"Type: {specs['roller_type']}")
            if specs.get('pipe_diameter'): spec_parts.append(f"Pipe: {specs['pipe_diameter']}mm")
            if specs.get('shaft_diameter'): spec_parts.append(f"Shaft: {specs['shaft_diameter']}mm")
            if specs.get('bearing'): spec_parts.append(f"Bearing: {specs['bearing']}")
            if spec_parts:
                specs_html = f'<div class="product-specs">{" | ".join(spec_parts)}</div>'
        
        remark_html = ""
        if product.get('remark'):
            remark_html = f'<div class="product-remark">Note: {product["remark"]}</div>'
        
        # Format weight display
        unit_weight_str = f"{unit_weight:.2f}" if unit_weight > 0 else "-"
        total_weight_str = f"{total_weight:.2f}" if total_weight > 0 else "-"
        
        # Always show discount columns (use_item_discounts is always True for PDF)
        # Hide prices if hide_prices=True (for customer viewing RFQ)
        if hide_prices:
            price_display = "-"
            amount_display = "-"
        else:
            price_display = f"Rs. {value_after_discount:,.2f}"
            amount_display = f"<strong>Rs. {line_total:,.2f}</strong>"
        
        if use_item_discounts:
            products_html += f"""
                <tr>
                  <td class="cell-center">{idx}</td>
                  <td class="cell-left">
                    <div class="product-name">{product.get('product_id', 'N/A')}</div>
                    {specs_html}
                    {remark_html}
                  </td>
                  <td class="cell-center">{qty}</td>
                  <td class="cell-right">{unit_weight_str}</td>
                  <td class="cell-right">{total_weight_str}</td>
                  <td class="cell-right">{price_display}</td>
                  <td class="cell-right">{amount_display}</td>
                </tr>
            """
        else:
            if hide_prices:
                orig_price_display = "-"
                orig_amount_display = "-"
            else:
                orig_price_display = f"Rs. {unit_price:,.2f}"
                orig_amount_display = f"<strong>Rs. {original_amount:,.2f}</strong>"
            
            products_html += f"""
                <tr>
                  <td class="cell-center">{idx}</td>
                  <td class="cell-left">
                    <div class="product-name">{product.get('product_name', product.get('product_id', 'N/A'))}</div>
                    {specs_html}
                    {remark_html}
                  </td>
                  <td class="cell-center">{qty}</td>
                  <td class="cell-right">{unit_weight_str}</td>
                  <td class="cell-right">{total_weight_str}</td>
                  <td class="cell-right">{orig_price_display}</td>
                  <td class="cell-right">{orig_amount_display}</td>
                </tr>
            """
    
    # Calculate totals - use item-level discounts if enabled
    subtotal = quote_data.get('subtotal', 0)
    if use_item_discounts:
        # Subtotal is before item discounts, discount is sum of item discounts
        discount = total_item_discount
        subtotal_after_discount = calculated_subtotal
    else:
        discount = quote_data.get('total_discount', 0)
        subtotal_after_discount = subtotal - discount
    
    packing = quote_data.get('packing_charges', 0)
    shipping = quote_data.get('shipping_cost', 0)
    taxable_amount = subtotal_after_discount + packing + shipping
    cgst = taxable_amount * 0.09
    sgst = taxable_amount * 0.09
    grand_total = taxable_amount * 1.18
    
    # Customer details
    customer_code = quote_data.get('customer_code', '')
    customer_name = quote_data.get('customer_name', 'N/A')
    customer_company = quote_data.get('customer_company', '')
    customer_details = quote_data.get('customer_details') or {}
    
    customer_code_html = f'<div class="customer-code" style="color: #960018; font-weight: bold; margin-bottom: 4px;">Customer Code: {customer_code}</div>' if customer_code else ''
    
    # Customer RFQ Reference Number
    customer_rfq_no = quote_data.get('customer_rfq_no')
    customer_rfq_no_html = f'<div style="color: #1565C0; font-weight: bold; margin-bottom: 4px;">Customer Ref: {customer_rfq_no}</div>' if customer_rfq_no else ''
    
    address_html = ""
    if customer_details.get('address'):
        address_parts = [customer_details['address']]
        if customer_details.get('city'): address_parts.append(f"<br>{customer_details['city']}")
        if customer_details.get('state'): address_parts.append(f", {customer_details['state']}")
        if customer_details.get('pincode'): address_parts.append(f" - {customer_details['pincode']}")
        address_html = f'<div class="info-address">{"".join(address_parts)}</div>'
    
    gst_html = f'<div class="info-gst">GSTIN: {customer_details.get("gst_number")}</div>' if customer_details.get('gst_number') else ''
    
    contact_parts = []
    if customer_details.get('phone'): contact_parts.append(f"Ph: {customer_details['phone']}")
    if customer_details.get('email'): contact_parts.append(customer_details['email'])
    contact_html = f'<div class="info-contact">{" | ".join(contact_parts)}</div>' if contact_parts else ''
    
    # Original RFQ reference
    rfq_ref_html = f'<div class="doc-ref">Ref: {quote_data.get("original_rfq_number")}</div>' if quote_data.get('original_rfq_number') else ''
    
    # Delivery location
    delivery_html = f'''
          <div class="delivery-box">
            <strong>Delivery Location:</strong> PIN Code {quote_data.get("delivery_location")}
          </div>
    ''' if quote_data.get('delivery_location') else ''
    
    # Notes
    notes_html = f'''
          <div class="delivery-box" style="background: #fff5f5; border-left: 3px solid #960018;">
            <strong>Notes:</strong> {quote_data.get("notes")}
          </div>
    ''' if quote_data.get('notes') else ''
    
    # Discount row - show item discount summary if using item discounts
    discount_html = ""
    if discount > 0:
        if use_item_discounts:
            discount_html = f'''
                <div class="summary-row discount-row">
                  <span class="summary-label">Item Discounts (Total)</span>
                  <span class="summary-value">- Rs. {discount:,.2f}</span>
                </div>
            '''
        else:
            discount_percent = (discount / subtotal * 100) if subtotal > 0 else 0
            discount_html = f'''
                <div class="summary-row discount-row">
                  <span class="summary-label">Discount ({discount_percent:.1f}%)</span>
                  <span class="summary-value">- Rs. {discount:,.2f}</span>
                </div>
            '''
    
    # Packing row - with packing type percentage
    packing_html = ""
    if packing > 0:
        packing_type = quote_data.get('packing_type', '')
        packing_type_labels = {
            'standard': 'Standard (1%)',
            'pallet': 'Pallet (4%)',
            'wooden_box': 'Wooden Box (8%)'
        }
        # Handle custom packing types
        if packing_type and packing_type.startswith('custom_'):
            try:
                custom_percent = float(packing_type.replace('custom_', ''))
                packing_label = f'Custom ({custom_percent:.1f}%)'
            except:
                packing_label = packing_type_labels.get(packing_type, '')
        else:
            packing_label = packing_type_labels.get(packing_type, '')
        
        if packing_label:
            packing_html = f'''
            <div class="summary-row">
              <span class="summary-label">Packing Charges - {packing_label}</span>
              <span class="summary-value">Rs. {packing:,.2f}</span>
            </div>
        '''
        else:
            packing_html = f'''
            <div class="summary-row">
              <span class="summary-label">Packing Charges</span>
              <span class="summary-value">Rs. {packing:,.2f}</span>
            </div>
        '''
    
    # Shipping/Freight row
    if shipping > 0:
        shipping_html = f'''
            <div class="summary-row">
              <span class="summary-label">Freight Charges</span>
              <span class="summary-value">Rs. {shipping:,.2f}</span>
            </div>
        '''
    else:
        shipping_html = ''
    
    # Dynamic table header based on discount mode
    if use_item_discounts:
        table_header = '''
            <tr>
              <th style="width: 4%;">SR.</th>
              <th style="width: 22%; text-align: left;">ITEM CODE</th>
              <th style="width: 6%;">QTY</th>
              <th style="width: 10%; text-align: right;">WT/PC (kg)</th>
              <th style="width: 10%; text-align: right;">TOTAL WT</th>
              <th style="width: 14%; text-align: right;">PRICE/PC</th>
              <th style="width: 14%; text-align: right;">AMOUNT</th>
            </tr>
        '''
    else:
        table_header = '''
            <tr>
              <th style="width: 5%;">#</th>
              <th style="width: 30%; text-align: left;">Description</th>
              <th style="width: 8%;">Qty</th>
              <th style="width: 12%; text-align: right;">Wt/Pc (kg)</th>
              <th style="width: 12%; text-align: right;">Total Wt</th>
              <th style="width: 15%; text-align: right;">Unit Price</th>
              <th style="width: 18%; text-align: right;">Amount</th>
            </tr>
        '''
    
    html = f"""
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <style>
          * {{ margin: 0; padding: 0; box-sizing: border-box; }}
          body {{ 
            font-family: 'Segoe UI', Arial, sans-serif; 
            color: #1a1a1a; 
            font-size: 11px;
            line-height: 1.4;
            padding: 15px;
          }}
          
          /* Header */
          .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding-bottom: 15px;
            border-bottom: 2px solid #960018;
            margin-bottom: 10px;
          }}
          .logo-section {{ }}
          .logo-section img {{
            height: 45px;
            width: auto;
          }}
          .logo {{
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -1px;
            color: #1a1a1a;
          }}
          .logo span {{ color: #960018; }}
          .company-tagline {{
            font-size: 9px;
            color: #960018;
            letter-spacing: 2px;
            margin-top: 2px;
            font-style: italic;
          }}
          .company-info-header {{
            font-size: 8px;
            color: #666;
            text-align: center;
            margin-bottom: 10px;
            padding: 5px;
            background: #f9f9f9;
            border-radius: 3px;
          }}
          .company-info-header span {{
            margin: 0 3px;
          }}
          .report-generated {{
            font-size: 8px;
            color: #666;
            text-align: right;
            margin-bottom: 10px;
            font-style: italic;
          }}
          .doc-type {{
            text-align: right;
          }}
          .doc-title {{
            font-size: 18px;
            font-weight: 700;
            color: #960018;
            letter-spacing: 1px;
          }}
          .doc-number {{
            font-size: 13px;
            font-weight: 600;
            color: #333;
            margin-top: 3px;
          }}
          .doc-date {{
            font-size: 10px;
            color: #666;
            margin-top: 2px;
          }}
          .doc-ref {{
            font-size: 10px;
            color: #0066cc;
            margin-top: 3px;
            font-weight: 500;
          }}
          
          /* Info Boxes */
          .info-section {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            gap: 15px;
          }}
          .info-box {{
            flex: 1;
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background: #fafafa;
          }}
          .info-box-title {{
            font-size: 8px;
            font-weight: 600;
            color: #960018;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 4px;
          }}
          .info-company {{
            font-size: 12px;
            font-weight: 600;
            color: #1a1a1a;
          }}
          .info-address {{
            font-size: 10px;
            color: #555;
            margin-top: 4px;
            line-height: 1.5;
          }}
          .info-gst {{
            display: inline-block;
            margin-top: 6px;
            padding: 3px 8px;
            background: #e8f4fc;
            border-radius: 3px;
            font-size: 9px;
            color: #0066cc;
            font-weight: 500;
          }}
          .info-contact {{
            font-size: 9px;
            color: #666;
            margin-top: 6px;
          }}
          
          /* Products Table */
          .section-title {{
            font-size: 10px;
            font-weight: 600;
            color: #960018;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 8px 0;
            border-bottom: 1px solid #960018;
            margin-bottom: 0;
          }}
          table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
          }}
          th {{
            background: #960018;
            color: white;
            padding: 8px 10px;
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }}
          td {{
            padding: 8px 10px;
            border-bottom: 1px solid #eee;
            font-size: 10px;
          }}
          .cell-center {{ text-align: center; }}
          .cell-right {{ text-align: right; }}
          .cell-left {{ text-align: left; }}
          .product-name {{ font-weight: 500; color: #1a1a1a; }}
          .product-specs {{ font-size: 9px; color: #666; margin-top: 3px; }}
          .product-remark {{ font-size: 9px; color: #0066cc; margin-top: 3px; font-style: italic; }}
          
          /* Summary */
          .summary-section {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 15px;
          }}
          .summary-table {{
            width: 280px;
          }}
          .summary-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 10px;
            border-bottom: 1px solid #eee;
          }}
          .summary-label {{ color: #555; font-size: 10px; }}
          .summary-value {{ font-weight: 500; font-size: 10px; }}
          .discount-row {{ color: #28a745; }}
          .total-row {{
            background: #960018;
            color: white;
            border-radius: 4px;
            margin-top: 5px;
            padding: 10px;
          }}
          .total-row .summary-label,
          .total-row .summary-value {{
            color: white;
            font-size: 12px;
            font-weight: 600;
          }}
          
          /* Delivery */
          .delivery-box {{
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 10px;
          }}
          
          /* Terms Section */
          .terms-container {{
            margin-top: 20px;
            page-break-inside: avoid;
          }}
          .terms-section {{
            margin-bottom: 15px;
          }}
          .terms-title {{
            font-size: 11px;
            font-weight: 700;
            color: #960018;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 8px 0;
            border-bottom: 2px solid #960018;
            margin-bottom: 10px;
          }}
          .terms-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
          }}
          .term-item {{
            padding: 8px;
            background: #fafafa;
            border-left: 3px solid #960018;
            font-size: 9px;
            line-height: 1.5;
          }}
          .term-item-title {{
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
          }}
          .term-item-text {{
            color: #555;
          }}
          .terms-full-width {{
            grid-column: span 2;
          }}
          
          /* Footer */
          .footer {{
            margin-top: 25px;
            padding-top: 15px;
            border-top: 2px solid #960018;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
          }}
          .footer-left {{
            font-size: 9px;
            color: #666;
          }}
          .footer-company {{
            font-weight: 600;
            color: #1a1a1a;
            font-size: 11px;
          }}
          .footer-right {{
            text-align: right;
          }}
          .footer-signature {{
            border-top: 1px solid #333;
            padding-top: 5px;
            font-size: 9px;
            color: #333;
            font-weight: 500;
          }}
          .footer-note {{
            font-size: 8px;
            color: #999;
            margin-top: 10px;
            text-align: center;
          }}
          
          @media print {{
            body {{ padding: 10px; }}
            .terms-container {{ page-break-before: auto; }}
          }}
        </style>
      </head>
      <body>
        <!-- Header with Logo -->
        <div class="header">
          <div class="logo-section">
            <img src="data:image/png;base64,{logo_base64}" style="height: 45px; width: auto;" alt="Convero" />
            <div class="company-tagline">Rolling towards the future</div>
          </div>
          <div class="doc-type">
            <div class="doc-title">{doc_label_full}</div>
            <div class="doc-number">{quote_number}</div>
            {rfq_ref_html}
            <div class="doc-date">{display_date}</div>
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
        <div class="report-generated">Report Generated: {report_generated}</div>

        <!-- Info Section -->
        <div class="info-section">
          <div class="info-box">
            <div class="info-box-title">From</div>
            <div class="info-company">CONVERO SOLUTIONS</div>
            <div style="font-size: 9px; color: #960018; font-style: italic; margin-bottom: 4px;">Rolling towards the future</div>
            <div class="info-address">
              Plot No. 39, Swapnil Industrial Park,<br>
              Beside Shiv Aaradhna Estate,<br>
              Ahmedabad-Indore Highway,<br>
              Village-Kuha, Ahmedabad,<br>
              Gujarat 382433
            </div>
            <div class="info-contact">
              <strong>Email:</strong> info@convero.in | <strong>Web:</strong> www.convero.in
            </div>
            <div class="info-contact" style="margin-top: 3px;">
              <strong>GSTIN:</strong> 24BAUPP4310D2ZT
            </div>
          </div>
          <div class="info-box">
            <div class="info-box-title">Bill To</div>
            {customer_code_html}
            {customer_rfq_no_html}
            <div class="info-company">{customer_company or (customer_details.get('company') if customer_details else None) or (customer_details.get('name') if customer_details else None) or customer_name}</div>
            {address_html}
            {gst_html}
            {contact_html}
          </div>
        </div>

        <!-- Products Table -->
        <div class="section-title">Product Details</div>
        <table>
          <thead>
            {table_header}
          </thead>
          <tbody>
            {products_html}
          </tbody>
        </table>

        <!-- Summary -->
        <!-- Summary Section - Hidden for RFQs -->
        {'<div class="summary-section"><div class="summary-table"><div class="summary-row" style="background: #e8f4fc; border-top: 2px solid #0066cc;"><span class="summary-label" style="color: #0066cc;"><strong>TOTAL WEIGHT</strong></span><span class="summary-value" style="color: #0066cc;"><strong>' + f"{grand_total_weight:.2f}" + ' kg</strong></span></div></div></div>' if hide_prices else f'''
        <div class="summary-section">
          <div class="summary-table">
            <div class="summary-row">
              <span class="summary-label">Subtotal</span>
              <span class="summary-value">Rs. {subtotal_after_discount:,.2f}</span>
            </div>
            {packing_html}
            {shipping_html}
            <div class="summary-row" style="background: #f5f5f5;">
              <span class="summary-label"><strong>Taxable Amount</strong></span>
              <span class="summary-value"><strong>Rs. {taxable_amount:,.2f}</strong></span>
            </div>
            <div class="summary-row">
              <span class="summary-label">CGST @ 9%</span>
              <span class="summary-value">Rs. {cgst:,.2f}</span>
            </div>
            <div class="summary-row">
              <span class="summary-label">SGST @ 9%</span>
              <span class="summary-value">Rs. {sgst:,.2f}</span>
            </div>
            <div class="total-row">
              <span class="summary-label">GRAND TOTAL</span>
              <span class="summary-value">Rs. {grand_total:,.2f}</span>
            </div>
            <div class="summary-row" style="background: #e8f4fc; border-top: 2px solid #0066cc;">
              <span class="summary-label" style="color: #0066cc;"><strong>TOTAL WEIGHT</strong></span>
              <span class="summary-value" style="color: #0066cc;"><strong>{grand_total_weight:.2f} kg</strong></span>
            </div>
          </div>
        </div>
        '''}

        {delivery_html}
        {notes_html}

        <!-- Terms & Conditions -->
        <div class="terms-container">
          <div class="terms-section">
            <div class="terms-title">Commercial Terms</div>
            <div class="terms-grid">
              <div class="term-item">
                <div class="term-item-title">Payment Terms</div>
                <div class="term-item-text">{quote_data.get('commercial_terms', {}).get('payment_terms', '100% Advance against pro-forma')}</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Freight</div>
                <div class="term-item-text">{quote_data.get('commercial_terms', {}).get('freight_terms', 'Ex-Works')}</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Color/Finish</div>
                <div class="term-item-text">{quote_data.get('commercial_terms', {}).get('color_finish', '1+1 : Red oxide + finish paint black color approx 50-60 micron')}</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Delivery</div>
                <div class="term-item-text">{quote_data.get('commercial_terms', {}).get('delivery_timeline', '25-30 working days')}</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Warranty</div>
                <div class="term-item-text">{quote_data.get('commercial_terms', {}).get('warranty', 'Warranty stands for 12 months from date of invoice considering L10 life.')}</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Quotation Validity</div>
                <div class="term-item-text">{quote_data.get('commercial_terms', {}).get('validity', 'This offer stands valid for 30 days.')}</div>
              </div>
            </div>
          </div>

          <div class="terms-section">
            <div class="terms-title">Technical Specifications</div>
            <div class="terms-grid">
              <div class="term-item">
                <div class="term-item-title">Pipe</div>
                <div class="term-item-text">IS-9295 ERW steel tubes for idlers of belt conveyors. Tolerances as per relevant IS standards.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Shaft</div>
                <div class="term-item-text">Material grade EN8.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Bearing</div>
                <div class="term-item-text">As per selection made in the application.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Circlip</div>
                <div class="term-item-text">Conforming to IS-3075 standard.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Housing</div>
                <div class="term-item-text">Deep drawn CRCA sheet conforming to IS-513, thickness 3.15 mm.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Seal Set</div>
                <div class="term-item-text">Self-designed Nylon-6 seal with metal cap, filled with EP-2 lithium-based grease for water/dust protection.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Rubber Ring</div>
                <div class="term-item-text">Shore hardness: 50-60. Impact rubber ring thickness may vary from drawings.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Painting</div>
                <div class="term-item-text">One coat black synthetic enamel (40 microns). Rust preventive coating on machined parts.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">Packing</div>
                <div class="term-item-text">As per selection made in the application.</div>
              </div>
              <div class="term-item">
                <div class="term-item-title">TIR (Total Indicated Runout)</div>
                <div class="term-item-text">Shall not exceed 1.6 mm as per IS-8598.</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="footer">
          <div class="footer-left">
            <div class="footer-company">CONVERO SOLUTIONS</div>
            <div style="font-size: 8px; color: #960018; font-style: italic;">Rolling towards the future</div>
            <div style="font-size: 8px; margin-top: 3px;">Plot No. 39, Swapnil Industrial Park, Village-Kuha, Ahmedabad, Gujarat 382433</div>
            <div style="font-size: 8px;"><strong>Email:</strong> info@convero.in | <strong>Web:</strong> www.convero.in | <strong>GSTIN:</strong> 24BAUPP4310D2ZT</div>
          </div>
          <div class="footer-right">
            <div style="height: 40px;"></div>
            <div class="footer-signature">Authorized Signatory</div>
          </div>
        </div>
        
        <div class="footer-note">
          This is a computer-generated quotation. E&amp;OE (Errors and Omissions Excepted)
        </div>
      </body>
      </html>
    """
    return html

def generate_quote_pdf(quote_data: dict, hide_prices: bool = False) -> bytes:
    """Generate PDF for Quote using weasyprint with HTML template matching frontend exactly"""
    try:
        from weasyprint import HTML
        html_content = generate_quote_html(quote_data, hide_prices)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except ImportError:
        # Fallback to fpdf2 if weasyprint not available
        logging.warning("weasyprint not available, using fpdf2 fallback")
        return generate_quote_pdf_fallback(quote_data, hide_prices)

def generate_quote_pdf_fallback(quote_data: dict) -> bytes:
    """Fallback PDF generation using fpdf2"""
    from fpdf import FPDF
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Use approved_at date if available, else use current time
    quote_date = quote_data.get('approved_at') or get_ist_now()
    if isinstance(quote_date, str):
        try:
            quote_date = datetime.fromisoformat(quote_date.replace('Z', '+00:00'))
        except:
            quote_date = get_ist_now()
    
    # Convert to IST if not already
    quote_date = utc_to_ist(quote_date) if quote_date else get_ist_now()
    
    # Header with Carmine Red background
    pdf.set_fill_color(150, 0, 24)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, 'QUOTATION', align='C')
    pdf.set_font('Helvetica', '', 12)
    pdf.set_xy(10, 20)
    pdf.cell(0, 8, f'{quote_data.get("quote_number", "N/A")}', align='C')
    
    # Show original RFQ reference if available
    original_rfq = quote_data.get('original_rfq_number')
    if original_rfq:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_xy(10, 28)
        pdf.cell(0, 6, f'(Reference: {original_rfq})', align='C')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_xy(10, 34)
    pdf.cell(0, 6, f'Date: {quote_date.strftime("%d %b %Y")}', align='C')
    
    # Reset text color
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(50)
    
    # Customer Details Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'Customer Details', fill=True, ln=True)
    pdf.ln(3)
    
    pdf.set_font('Helvetica', '', 10)
    details = [
        ('Customer Code', quote_data.get('customer_code', 'N/A')),
        ('Name', quote_data.get('customer_name', 'N/A')),
        ('Company', quote_data.get('customer_company', 'N/A')),
        ('Email', quote_data.get('customer_email', 'N/A')),
    ]
    
    customer_details = quote_data.get('customer_details', {})
    if customer_details:
        if customer_details.get('mobile'):
            details.append(('Mobile', customer_details.get('mobile')))
        if customer_details.get('gst'):
            details.append(('GST No.', customer_details.get('gst')))
        if customer_details.get('address'):
            details.append(('Address', customer_details.get('address')))
    
    for label, value in details:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(40, 6, f'{label}:')
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, str(value), ln=True)
    
    pdf.ln(5)
    
    # Products Table - WITH PRICES
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'Products', fill=True, ln=True)
    pdf.ln(3)
    
    # Table header
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.cell(8, 8, '#', fill=True, border=1, align='C')
    pdf.cell(32, 8, 'Product Code', fill=True, border=1, align='C')
    pdf.cell(55, 8, 'Description', fill=True, border=1, align='C')
    pdf.cell(12, 8, 'Qty', fill=True, border=1, align='C')
    pdf.cell(30, 8, 'Price/Pc', fill=True, border=1, align='C')
    pdf.cell(32, 8, 'Amount', fill=True, border=1, align='C')
    pdf.ln()
    
    # Table rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 7)
    products = quote_data.get('products', [])
    subtotal = 0
    
    # Calculate overall discount percentage for fallback
    quote_subtotal = quote_data.get('subtotal', 0)
    total_discount = quote_data.get('total_discount', 0)
    overall_discount_percent = (total_discount / quote_subtotal * 100) if quote_subtotal > 0 else 0
    use_item_discounts = quote_data.get('use_item_discounts', False)
    
    for idx, product in enumerate(products, 1):
        qty = product.get('quantity', 0)
        unit_price = product.get('unit_price', 0)
        
        # Use item-level discount if available, otherwise use overall discount percentage
        if use_item_discounts and product.get('item_discount_percent') is not None:
            item_discount_percent = product.get('item_discount_percent', 0)
        else:
            item_discount_percent = overall_discount_percent
        
        # Calculate price after discount per piece
        price_after_discount = unit_price * (1 - item_discount_percent / 100)
        amount = qty * price_after_discount
        subtotal += amount
        
        pdf.cell(8, 7, str(idx), border=1, align='C')
        pdf.cell(32, 7, str(product.get('product_id', 'N/A'))[:17], border=1, align='C')
        pdf.cell(55, 7, str(product.get('product_name', 'N/A'))[:30], border=1)
        pdf.cell(12, 7, str(qty), border=1, align='C')
        pdf.cell(30, 7, f'Rs. {price_after_discount:,.2f}', border=1, align='R')
        pdf.cell(32, 7, f'Rs. {amount:,.2f}', border=1, align='R')
        pdf.ln()
    
    pdf.ln(3)
    
    # Pricing Summary
    pdf.set_font('Helvetica', '', 10)
    x_label = 130
    x_value = 160
    
    # Subtotal
    pdf.set_x(x_label)
    pdf.cell(30, 6, 'Subtotal:', align='R')
    pdf.cell(35, 6, f'Rs. {quote_data.get("subtotal", subtotal):,.2f}', align='R')
    pdf.ln()
    
    # Discount if any
    discount = quote_data.get('total_discount', 0)
    if discount > 0:
        pdf.set_x(x_label)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(30, 6, 'Discount:', align='R')
        pdf.cell(35, 6, f'- Rs. {discount:,.2f}', align='R')
        pdf.set_text_color(0, 0, 0)
        pdf.ln()
    
    # Packing charges if any
    packing = quote_data.get('packing_charges', 0)
    if packing > 0:
        pdf.set_x(x_label)
        pdf.cell(30, 6, 'Packing:', align='R')
        pdf.cell(35, 6, f'Rs. {packing:,.2f}', align='R')
        pdf.ln()
    
    # Shipping if any
    shipping = quote_data.get('shipping_cost', 0)
    if shipping > 0:
        pdf.set_x(x_label)
        pdf.cell(30, 6, 'Freight:', align='R')
        pdf.cell(35, 6, f'Rs. {shipping:,.2f}', align='R')
        pdf.ln()
    
    # Total
    pdf.ln(2)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(x_label)
    pdf.cell(30, 8, 'Total:', align='R')
    pdf.set_fill_color(150, 0, 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(35, 8, f'Rs. {quote_data.get("total_price", 0):,.2f}', align='R', fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln()
    
    # Notes section if any
    if quote_data.get('notes'):
        pdf.ln(5)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, 'Notes:', ln=True)
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(0, 5, quote_data.get('notes'))
    
    # Terms & Conditions
    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 7, 'Terms & Conditions', fill=True, ln=True)
    pdf.set_font('Helvetica', '', 8)
    pdf.ln(2)
    
    terms = [
        "1. Prices are valid for 30 days from the date of quotation.",
        "2. Payment terms: 100% advance or as mutually agreed.",
        "3. Delivery: Ex-works, subject to availability.",
        "4. GST extra as applicable.",
        "5. Any disputes subject to Pune jurisdiction.",
    ]
    
    for term in terms:
        pdf.cell(0, 4, term, ln=True)
    
    # Footer
    pdf.set_y(-20)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5, 'Convero Solutions | info@convero.in | www.convero.in', align='C')
    
    return pdf.output()

async def send_rfq_notification_email(rfq_data: dict, customer: dict):
    """Send RFQ notification email to admins and confirmation to customer - WITHOUT PRICES"""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logging.warning("Email service not configured, skipping RFQ notification")
        return False
    
    admin_emails = ADMIN_RFQ_EMAILS
    customer_email = rfq_data.get('customer_email') or customer.get('email')
    ist_now = get_ist_now()
    
    try:
        # Get product details - WITHOUT PRICES for RFQ
        products = rfq_data.get('products', [])
        products_html = ""
        products_text = ""
        
        # Build attachment list grouped by product for the email
        attachments_by_product_html = ""
        has_attachments = False
        
        for idx, product in enumerate(products, 1):
            qty = product.get('quantity', 0)
            unit_weight = (
                product.get('weight') or 
                product.get('weight_kg') or 
                product.get('specifications', {}).get('weight') or 
                product.get('specifications', {}).get('weight_kg') or 
                product.get('specifications', {}).get('single_roller_weight_kg') or 
                0
            )
            total_weight = unit_weight * qty
            unit_weight_str = f"{unit_weight:.2f}" if unit_weight > 0 else "-"
            total_weight_str = f"{total_weight:.2f}" if total_weight > 0 else "-"
            products_html += f"""
            <tr>
                <td>{idx}</td>
                <td>{product.get('product_id', 'N/A')}</td>
                <td>{product.get('product_name', 'N/A')}</td>
                <td>{qty}</td>
                <td style="text-align: right;">{unit_weight_str}</td>
                <td style="text-align: right;">{total_weight_str}</td>
            </tr>
            """
            products_text += f"{idx}. {product.get('product_id', 'N/A')} - {product.get('product_name', 'N/A')} x {qty}\n"
            
            # Group attachments by product
            product_attachments = product.get('attachments', [])
            if product_attachments:
                has_attachments = True
                attachment_names = [att.get('name', 'Unnamed') for att in product_attachments if att.get('base64')]
                if attachment_names:
                    attachments_by_product_html += f"""
                    <div style="margin-bottom: 10px;">
                        <strong>Item {idx} - {product.get('product_id', 'N/A')}:</strong>
                        <ul style="margin: 5px 0;">
                            {''.join(f'<li>{name}</li>' for name in attachment_names)}
                        </ul>
                    </div>
                    """
        
        # Build attachments section HTML
        attachments_section_html = ""
        if has_attachments:
            attachments_section_html = f"""
                <div style="background: #E3F2FD; border: 1px solid #90CAF9; padding: 15px; border-radius: 8px; margin-top: 20px;">
                    <h4 style="margin-top: 0; color: #1565C0;">Attachments by Product</h4>
                    {attachments_by_product_html}
                </div>
            """
        
        # Get customer reference number if provided
        customer_rfq_no = rfq_data.get('customer_rfq_no')
        customer_ref_html = ""
        customer_ref_text = ""
        if customer_rfq_no:
            customer_ref_html = f"""
                        <div class="info-box">
                            <div class="info-label">Customer Ref. No.</div>
                            <div class="info-value">{customer_rfq_no}</div>
                        </div>
            """
            customer_ref_text = f"Customer Ref. No.: {customer_rfq_no}\n"
        
        # Get packing type and delivery pincode
        packing_type = rfq_data.get('packing_type')
        delivery_location = rfq_data.get('delivery_location')
        
        packing_type_labels = {
            'standard': 'Standard (1%)',
            'pallet': 'Pallet (4%)',
            'wooden_box': 'Wooden Box (8%)'
        }
        packing_label = packing_type_labels.get(packing_type, packing_type) if packing_type else 'Not specified'
        
        packing_delivery_html = ""
        packing_delivery_text = ""
        if packing_type or delivery_location:
            if packing_type:
                packing_delivery_html += f"""
                        <div class="info-box">
                            <div class="info-label">Packing Type</div>
                            <div class="info-value">{packing_label}</div>
                        </div>
                """
                packing_delivery_text += f"Packing Type: {packing_label}\n"
            if delivery_location:
                packing_delivery_html += f"""
                        <div class="info-box">
                            <div class="info-label">Delivery Pincode</div>
                            <div class="info-value">{delivery_location}</div>
                        </div>
                """
                packing_delivery_text += f"Delivery Pincode: {delivery_location}\n"
        
        # ===== ADMIN EMAIL (internal notification) =====
        admin_msg = MIMEMultipart('mixed')
        admin_subject = f"New RFQ Received - {rfq_data.get('quote_number')}"
        if customer_rfq_no:
            admin_subject += f" (Ref: {customer_rfq_no})"
        admin_subject += f" from {rfq_data.get('customer_name')}"
        admin_msg['Subject'] = admin_subject
        admin_msg['From'] = GMAIL_USER
        admin_msg['To'] = ", ".join(admin_emails)
        
        admin_html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Calibri, Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #960018; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .rfq-number {{ font-size: 24px; font-weight: bold; color: #960018; }}
                .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
                .info-box {{ background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #960018; }}
                .info-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .info-value {{ font-size: 16px; font-weight: bold; color: #333; margin-top: 5px; }}
                .products-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .products-table th {{ background-color: #1E293B; color: white; padding: 12px; text-align: left; }}
                .products-table td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
                .products-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">New RFQ Received</h1>
                    <p style="margin: 5px 0 0 0;">Convero Solutions - Roller Price Calculator</p>
                </div>
                <div class="content">
                    <p class="rfq-number">{rfq_data.get('quote_number')}</p>
                    <p>A new Request for Quotation has been submitted:</p>
                    
                    <div class="info-grid">
                        <div class="info-box">
                            <div class="info-label">Customer Name</div>
                            <div class="info-value">{rfq_data.get('customer_name')}</div>
                        </div>
                        <div class="info-box">
                            <div class="info-label">Company</div>
                            <div class="info-value">{rfq_data.get('customer_company', 'N/A')}</div>
                        </div>
                        <div class="info-box">
                            <div class="info-label">Email</div>
                            <div class="info-value">{rfq_data.get('customer_email')}</div>
                        </div>
                        <div class="info-box">
                            <div class="info-label">Submission Time</div>
                            <div class="info-value">{ist_now.strftime("%d %b %Y, %I:%M %p IST")}</div>
                        </div>
                        {customer_ref_html}
                        {packing_delivery_html}
                    </div>
                    
                    <h3>Products Requested</h3>
                    <table class="products-table">
                        <tr>
                            <th>#</th>
                            <th>Product Code</th>
                            <th>Description</th>
                            <th>Qty</th>
                            <th style="text-align: right;">Wt/Pc (kg)</th>
                            <th style="text-align: right;">Total Wt (kg)</th>
                        </tr>
                        {products_html}
                    </table>
                    
                    {attachments_section_html}
                    
                    {f'<p style="margin-top: 20px;"><strong>Notes:</strong> {rfq_data.get("notes")}</p>' if rfq_data.get("notes") else ''}
                </div>
                <div class="footer">
                    <p>&copy; 2026 Convero Solutions. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        admin_text_content = f"""
        New RFQ Received - Convero Solutions
        
        RFQ Number: {rfq_data.get('quote_number')}
        {customer_ref_text}
        Customer Details:
        -----------------
        Customer Name: {rfq_data.get('customer_name')}
        Company: {rfq_data.get('customer_company', 'N/A')}
        Email: {rfq_data.get('customer_email')}
        Submission Time: {ist_now.strftime("%d %b %Y, %I:%M %p IST")}
        {packing_delivery_text}
        Products Requested:
        -------------------
        {products_text}
        
        {f'Notes: {rfq_data.get("notes")}' if rfq_data.get("notes") else ''}
        
        - Convero Solutions
        """
        
        # Create the admin email body
        admin_msg_alternative = MIMEMultipart('alternative')
        admin_part1 = MIMEText(admin_text_content, 'plain')
        admin_part2 = MIMEText(admin_html_content, 'html')
        admin_msg_alternative.attach(admin_part1)
        admin_msg_alternative.attach(admin_part2)
        admin_msg.attach(admin_msg_alternative)
        
        # Attach any product attachments to admin email
        attachment_count = 0
        for product in products:
            product_attachments = product.get('attachments', [])
            for att in product_attachments:
                if att.get('base64'):
                    try:
                        attachment_data = base64.b64decode(att['base64'])
                        attachment_name = att.get('name', f'attachment_{attachment_count + 1}')
                        
                        # Determine MIME type
                        if att.get('type') == 'image' or attachment_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            mime_type = 'image'
                            mime_subtype = 'jpeg' if attachment_name.lower().endswith(('.jpg', '.jpeg')) else 'png'
                        else:
                            mime_type = 'application'
                            mime_subtype = 'octet-stream'
                        
                        attachment_part = MIMEBase(mime_type, mime_subtype)
                        attachment_part.set_payload(attachment_data)
                        encoders.encode_base64(attachment_part)
                        attachment_part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{attachment_name}"'
                        )
                        admin_msg.attach(attachment_part)
                        attachment_count += 1
                    except Exception as att_error:
                        logging.error(f"Failed to attach file {att.get('name')}: {str(att_error)}")
        
        if attachment_count > 0:
            logging.info(f"Attached {attachment_count} files to admin RFQ email")
        
        # ===== CUSTOMER EMAIL (confirmation without prices) =====
        customer_msg = MIMEMultipart('mixed')
        customer_msg['Subject'] = f"RFQ Submitted Successfully - {rfq_data.get('quote_number')}"
        customer_msg['From'] = GMAIL_USER
        customer_msg['To'] = customer_email
        
        customer_html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Calibri, Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #960018; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .rfq-number {{ font-size: 24px; font-weight: bold; color: #960018; }}
                .info-box {{ background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #960018; margin: 15px 0; }}
                .info-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .info-value {{ font-size: 16px; font-weight: bold; color: #333; margin-top: 5px; }}
                .products-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .products-table th {{ background-color: #1E293B; color: white; padding: 12px; text-align: left; }}
                .products-table td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
                .products-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .note-box {{ background: #FFF3CD; border: 1px solid #FFEEBA; padding: 15px; border-radius: 8px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">RFQ Submitted Successfully</h1>
                    <p style="margin: 5px 0 0 0;">Convero Solutions - Roller Price Calculator</p>
                </div>
                <div class="content">
                    <p>Dear {rfq_data.get('customer_name')},</p>
                    <p>Thank you for submitting your Request for Quotation. We have received your request and our team will review it shortly.</p>
                    
                    <div class="info-box">
                        <div class="info-label">Your RFQ Number</div>
                        <div class="info-value">{rfq_data.get('quote_number')}</div>
                    </div>
                    
                    <div class="info-box">
                        <div class="info-label">Submission Time</div>
                        <div class="info-value">{ist_now.strftime("%d %b %Y, %I:%M %p IST")}</div>
                    </div>
                    
                    {f'''<div class="info-box">
                        <div class="info-label">Packing Type</div>
                        <div class="info-value">{packing_label}</div>
                    </div>''' if packing_type else ''}
                    
                    {f'''<div class="info-box">
                        <div class="info-label">Delivery Pincode</div>
                        <div class="info-value">{delivery_location}</div>
                    </div>''' if delivery_location else ''}
                    
                    <h3>Products Requested</h3>
                    <table class="products-table">
                        <tr>
                            <th>#</th>
                            <th>Product Code</th>
                            <th>Description</th>
                            <th>Qty</th>
                            <th style="text-align: right;">Wt/Pc (kg)</th>
                            <th style="text-align: right;">Total Wt (kg)</th>
                        </tr>
                        {products_html}
                    </table>
                    
                    {f'<p><strong>Your Notes:</strong> {rfq_data.get("notes")}</p>' if rfq_data.get("notes") else ''}
                    
                    <div class="note-box">
                        <strong>What happens next?</strong><br/>
                        Our team will review your request and send you a formal quotation with pricing details via email. This typically takes 1-2 business days.
                    </div>
                </div>
                <div class="footer">
                    <p>If you have any questions, please contact us at info@convero.in</p>
                    <p>&copy; 2026 Convero Solutions. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        customer_text_content = f"""
        RFQ Submitted Successfully - Convero Solutions
        
        Dear {rfq_data.get('customer_name')},
        
        Thank you for submitting your Request for Quotation. We have received your request and our team will review it shortly.
        
        Your RFQ Number: {rfq_data.get('quote_number')}
        Submission Time: {ist_now.strftime("%d %b %Y, %I:%M %p IST")}
        {packing_delivery_text}
        Products Requested:
        -------------------
        {products_text}
        
        {f'Your Notes: {rfq_data.get("notes")}' if rfq_data.get("notes") else ''}
        
        What happens next?
        Our team will review your request and send you a formal quotation with pricing details via email. This typically takes 1-2 business days.
        
        If you have any questions, please contact us at info@convero.in
        
        - Convero Solutions
        """
        
        # Create the customer email body
        customer_msg_alternative = MIMEMultipart('alternative')
        customer_part1 = MIMEText(customer_text_content, 'plain')
        customer_part2 = MIMEText(customer_html_content, 'html')
        customer_msg_alternative.attach(customer_part1)
        customer_msg_alternative.attach(customer_part2)
        customer_msg.attach(customer_msg_alternative)
        
        # Generate RFQ PDF (without prices) and attach to both emails
        try:
            rfq_pdf_bytes = generate_rfq_pdf(rfq_data)
            pdf_filename = f"{rfq_data.get('quote_number', 'RFQ').replace('/', '-')}.pdf"
            
            # Attach PDF to admin email
            admin_pdf_attachment = MIMEApplication(rfq_pdf_bytes, _subtype='pdf')
            admin_pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            admin_msg.attach(admin_pdf_attachment)
            
            # Attach PDF to customer email
            customer_pdf_attachment = MIMEApplication(rfq_pdf_bytes, _subtype='pdf')
            customer_pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            customer_msg.attach(customer_pdf_attachment)
            
            logging.info(f"RFQ PDF attached to emails: {pdf_filename}")
        except Exception as pdf_error:
            logging.error(f"Failed to generate/attach RFQ PDF: {str(pdf_error)}")
        
        # Send emails
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            # Send to admins
            for admin_email in admin_emails:
                server.sendmail(GMAIL_USER, admin_email, admin_msg.as_string())
            # Send to customer
            if customer_email:
                server.sendmail(GMAIL_USER, customer_email, customer_msg.as_string())
        
        logging.info(f"RFQ notification sent to admins and confirmation to customer for RFQ: {rfq_data.get('quote_number')}")
        return True
    except Exception as e:
        logging.error(f"Failed to send RFQ notification email: {str(e)}")
        return False

@api_router.post("/auth/send-otp")
async def send_otp(request: OTPRequest):
    """Send OTP to email for verification"""
    # Check if user already exists
    existing_user = await db.users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check cooldown - prevent spam
    existing_otp = await db.otp_verifications.find_one({"email": request.email})
    if existing_otp:
        last_sent = existing_otp.get("created_at")
        if last_sent:
            time_diff = (datetime.utcnow() - last_sent).total_seconds()
            if time_diff < OTP_COOLDOWN_SECONDS:
                remaining = int(OTP_COOLDOWN_SECONDS - time_diff)
                raise HTTPException(
                    status_code=429, 
                    detail=f"Please wait {remaining} seconds before requesting a new OTP"
                )
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP in database with expiry (including new fields)
    otp_data = {
        "email": request.email,
        "otp": otp,
        "name": request.name,
        "mobile": request.mobile,
        "pincode": request.pincode,
        "city": request.city,
        "state": request.state,
        "company": request.company,
        "password_hash": get_password_hash(request.password),
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "verified": False
    }
    
    # Upsert - update if exists, insert if not
    await db.otp_verifications.replace_one(
        {"email": request.email},
        otp_data,
        upsert=True
    )
    
    # Send OTP email
    await send_otp_email(request.email, otp, request.name)
    
    return {
        "message": "OTP sent successfully",
        "email": request.email,
        "expires_in_minutes": OTP_EXPIRY_MINUTES
    }

@api_router.post("/auth/verify-otp", response_model=Token)
async def verify_otp(request: OTPVerify):
    """Verify OTP and complete registration"""
    # Find OTP record
    otp_record = await db.otp_verifications.find_one({"email": request.email})
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP found. Please request a new one.")
    
    # Check if OTP is expired
    if datetime.utcnow() > otp_record["expires_at"]:
        await db.otp_verifications.delete_one({"email": request.email})
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    
    # Verify OTP
    if otp_record["otp"] != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP. Please try again.")
    
    # Check if user already exists (double check)
    existing_user = await db.users.find_one({"email": request.email})
    if existing_user:
        await db.otp_verifications.delete_one({"email": request.email})
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate customer code
    customer_code = await generate_customer_code()
    
    # Create user with stored password hash
    user_dict = {
        "email": request.email,
        "name": request.name,
        "company": request.company,
        "designation": request.designation,
        "mobile": request.mobile,
        "pincode": request.pincode,
        "city": request.city,
        "state": request.state,
        "role": UserRole.CUSTOMER,
        "hashed_password": otp_record["password_hash"],
        "created_at": datetime.utcnow(),
        "email_verified": True,
        "customer_code": customer_code
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    
    # Also create a customer record for this user
    customer_dict = {
        "name": request.name,
        "company": request.company,
        "designation": request.designation,
        "email": request.email,
        "phone": request.mobile,
        "address": f"{request.city}, {request.state}",
        "city": request.city,
        "state": request.state,
        "pincode": request.pincode,
        "gstin": "",  # Can be updated later
        "created_at": get_ist_now(),
        "user_id": str(result.inserted_id),  # Link to user account
        "customer_type": "registered",  # Mark as registered customer
        "customer_code": customer_code  # Same code as user
    }
    
    customer_result = await db.customers.insert_one(customer_dict)
    logging.info(f"Customer created with ID: {customer_result.inserted_id} for user: {request.email} with code: {customer_code}")
    
    # Send registration notification email to admin
    await send_registration_notification_email(request)
    
    # Delete OTP record
    await db.otp_verifications.delete_one({"email": request.email})
    
    # Create token
    access_token = create_access_token(data={"sub": request.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_dict["id"],
            "email": request.email,
            "name": request.name,
            "role": UserRole.CUSTOMER,
            "company": request.company,
            "designation": request.designation,
            "customer_code": customer_code
        }
    }

@api_router.post("/auth/resend-otp")
async def resend_otp(request: ResendOTPRequest):
    """Resend OTP to email"""
    # Find existing OTP record
    otp_record = await db.otp_verifications.find_one({"email": request.email})
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="No pending registration found. Please start registration again.")
    
    # Check cooldown
    last_sent = otp_record.get("created_at")
    if last_sent:
        time_diff = (datetime.utcnow() - last_sent).total_seconds()
        if time_diff < OTP_COOLDOWN_SECONDS:
            remaining = int(OTP_COOLDOWN_SECONDS - time_diff)
            raise HTTPException(
                status_code=429, 
                detail=f"Please wait {remaining} seconds before requesting a new OTP"
            )
    
    # Generate new OTP
    otp = generate_otp()
    
    # Update OTP record
    await db.otp_verifications.update_one(
        {"email": request.email},
        {
            "$set": {
                "otp": otp,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
            }
        }
    )
    
    # Send OTP email
    await send_otp_email(request.email, otp, otp_record["name"])
    
    return {
        "message": "OTP resent successfully",
        "email": request.email,
        "expires_in_minutes": OTP_EXPIRY_MINUTES
    }

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
    
    # Generate customer code for customer role
    if user.role == "customer":
        user_dict["customer_code"] = await generate_customer_code()
    
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
            "company": user.company,
            "designation": user.designation,
            "customer_code": user_dict.get("customer_code")
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
            "company": user.get("company"),
            "designation": user.get("designation"),
            "customer_code": user.get("customer_code")
        }
    }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "role": current_user["role"],
        "company": current_user.get("company"),
        "designation": current_user.get("designation"),
        "customer_code": current_user.get("customer_code")
    }

# ============= FORGOT PASSWORD =============

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

async def send_password_reset_otp_email(email: str, otp: str, name: str):
    """Send OTP email for password reset"""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise HTTPException(status_code=500, detail="Email service not configured")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Password Reset Code - {otp}"
        msg['From'] = GMAIL_USER
        msg['To'] = email
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #960018; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .otp-box {{ background-color: #1E293B; color: white; font-size: 32px; font-weight: bold; letter-spacing: 8px; padding: 20px 40px; text-align: center; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                .warning {{ background-color: #FEF3C7; padding: 15px; border-radius: 8px; margin-top: 15px; color: #92400E; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">Password Reset</h1>
                    <p style="margin: 5px 0 0 0;">Convero Solutions - Roller Price Calculator</p>
                </div>
                <div class="content">
                    <p>Hello {name},</p>
                    <p>We received a request to reset your password. Use the code below to reset it:</p>
                    <div class="otp-box">{otp}</div>
                    <p>This code will expire in <strong>10 minutes</strong>.</p>
                    <div class="warning">
                        <strong>Security Notice:</strong> If you didn't request a password reset, please ignore this email. Your password will remain unchanged.
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Convero Solutions. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hello {name},
        
        We received a request to reset your password.
        
        Your password reset code is: {otp}
        
        This code will expire in 10 minutes.
        
        If you didn't request a password reset, please ignore this email.
        
        - Convero Solutions
        """
        
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, email, msg.as_string())
        
        return True
    except Exception as e:
        logging.error(f"Failed to send password reset OTP email: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send password reset email")

@api_router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Send OTP for password reset"""
    # Check if user exists
    user = await db.users.find_one({"email": request.email})
    if not user:
        # Don't reveal if email exists or not for security
        return {
            "message": "If the email exists, you will receive a password reset code",
            "email": request.email
        }
    
    # Check cooldown
    existing_otp = await db.password_reset_otps.find_one({"email": request.email})
    if existing_otp:
        last_sent = existing_otp.get("created_at")
        if last_sent:
            time_diff = (datetime.utcnow() - last_sent).total_seconds()
            if time_diff < OTP_COOLDOWN_SECONDS:
                remaining = int(OTP_COOLDOWN_SECONDS - time_diff)
                raise HTTPException(
                    status_code=429, 
                    detail=f"Please wait {remaining} seconds before requesting a new code"
                )
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP
    otp_data = {
        "email": request.email,
        "otp": otp,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "used": False
    }
    
    await db.password_reset_otps.replace_one(
        {"email": request.email},
        otp_data,
        upsert=True
    )
    
    # Send OTP email
    await send_password_reset_otp_email(request.email, otp, user.get("name", "User"))
    
    return {
        "message": "Password reset code sent to your email",
        "email": request.email,
        "expires_in_minutes": OTP_EXPIRY_MINUTES
    }

@api_router.post("/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Verify OTP and reset password"""
    # Find OTP record
    otp_record = await db.password_reset_otps.find_one({"email": request.email})
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="No reset code found. Please request a new one.")
    
    # Check if OTP is expired
    if datetime.utcnow() > otp_record["expires_at"]:
        await db.password_reset_otps.delete_one({"email": request.email})
        raise HTTPException(status_code=400, detail="Reset code has expired. Please request a new one.")
    
    # Check if OTP was already used
    if otp_record.get("used"):
        raise HTTPException(status_code=400, detail="This reset code has already been used.")
    
    # Verify OTP
    if otp_record["otp"] != request.otp:
        raise HTTPException(status_code=400, detail="Invalid reset code. Please try again.")
    
    # Validate new password
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    
    # Update password
    hashed_password = get_password_hash(request.new_password)
    result = await db.users.update_one(
        {"email": request.email},
        {"$set": {"hashed_password": hashed_password, "updated_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Mark OTP as used and delete it
    await db.password_reset_otps.delete_one({"email": request.email})
    
    logging.info(f"Password reset successful for: {request.email}")
    
    return {
        "message": "Password reset successful. You can now login with your new password.",
        "success": True
    }

# ============= PUSH NOTIFICATION ROUTES =============

class PushTokenRequest(BaseModel):
    push_token: str

@api_router.post("/users/push-token")
async def save_push_token(request: PushTokenRequest, current_user: dict = Depends(get_current_user)):
    """Save push notification token for the current user"""
    try:
        await db.users.update_one(
            {"email": current_user["email"]},
            {"$set": {"push_token": request.push_token, "push_token_updated_at": datetime.utcnow()}}
        )
        logging.info(f"Push token saved for user: {current_user['email']}")
        return {"message": "Push token saved successfully"}
    except Exception as e:
        logging.error(f"Error saving push token: {e}")
        raise HTTPException(status_code=500, detail="Failed to save push token")

@api_router.delete("/users/push-token")
async def remove_push_token(current_user: dict = Depends(get_current_user)):
    """Remove push notification token for the current user"""
    try:
        await db.users.update_one(
            {"email": current_user["email"]},
            {"$unset": {"push_token": "", "push_token_updated_at": ""}}
        )
        logging.info(f"Push token removed for user: {current_user['email']}")
        return {"message": "Push token removed successfully"}
    except Exception as e:
        logging.error(f"Error removing push token: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove push token")

async def send_push_notification_to_admins(title: str, body: str, data: dict = None):
    """Send push notification to all admin users with registered tokens"""
    try:
        # Get all admin users with push tokens
        admins = await db.users.find(
            {"role": "admin", "push_token": {"$exists": True, "$ne": None}}
        ).to_list(length=100)
        
        if not admins:
            logging.info("No admin users with push tokens found")
            return
        
        # Prepare notification payload for Expo Push API
        messages = []
        for admin in admins:
            push_token = admin.get("push_token")
            if push_token and push_token.startswith("ExponentPushToken"):
                messages.append({
                    "to": push_token,
                    "sound": "default",
                    "title": title,
                    "body": body,
                    "data": data or {},
                    "channelId": "rfq",  # Android notification channel
                })
        
        if not messages:
            logging.info("No valid Expo push tokens found")
            return
        
        # Send to Expo Push API
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://exp.host/--/api/v2/push/send",
                json=messages,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                logging.info(f"Push notification sent to {len(messages)} admins: {result}")
                
    except Exception as e:
        logging.error(f"Error sending push notification: {e}")

async def send_push_notification_to_user(user_email: str, title: str, body: str, data: dict = None):
    """Send push notification to a specific user by email"""
    try:
        # Get user with push token
        user = await db.users.find_one(
            {"email": user_email, "push_token": {"$exists": True, "$ne": None}}
        )
        
        if not user:
            logging.info(f"No push token found for user: {user_email}")
            return
        
        push_token = user.get("push_token")
        if not push_token or not push_token.startswith("ExponentPushToken"):
            logging.info(f"Invalid push token for user: {user_email}")
            return
        
        # Prepare notification payload
        message = {
            "to": push_token,
            "sound": "default",
            "title": title,
            "body": body,
            "data": data or {},
            "channelId": "default",
        }
        
        # Send to Expo Push API
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://exp.host/--/api/v2/push/send",
                json=[message],
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                logging.info(f"Push notification sent to {user_email}: {result}")
                
    except Exception as e:
        logging.error(f"Error sending push notification to user: {e}")

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
        "customer_id": current_user["id"],
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

@api_router.post("/quotes/roller")
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
        "customer_id": quote_data.customer_id or current_user["id"],
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
@api_router.get("/quotes/unread/count")
async def get_unread_rfq_count(current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.SALES]))):
    """Get count of unread pending RFQs for admin notification badge"""
    count = await db.quotes.count_documents({
        "status": "pending",
        "read_by_admin": {"$ne": True}
    })
    return {"unread_count": count}

# Export quotes to Excel - MUST be before /quotes/{quote_id} routes
@api_router.get("/quotes/export/excel")
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
@api_router.get("/quotes/export/pdf")
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
        
        quotes = await db.quotes.find(query).sort("created_at", -1).to_list(1000)
        
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
@api_router.post("/quotes/{quote_id}/mark-read")
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

@api_router.get("/quotes/{quote_id}/history")
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
    is_quote_owner = quote.get("customer_id") == current_user["id"]
    
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

@api_router.get("/quotes/{quote_id}/pdf")
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

@api_router.post("/quotes/{quote_id}/approve")
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

@api_router.post("/quotes/{quote_id}/reject")
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

@api_router.put("/quotes/{quote_id}/discount")
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

@api_router.post("/quotes/{quote_id}/revise")
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


@api_router.post("/quotes/{quote_id}/save-and-mail")
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

@api_router.get("/quotes/{quote_id}/attachments")
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

@api_router.get("/quotes/{quote_id}/attachments/{product_idx}/{attachment_idx}/download")
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

@api_router.get("/quotes/{quote_id}/attachments/download-all")
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

@api_router.post("/calculate-freight", response_model=FreightCalculationResponse)
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

@api_router.get("/roller-standards")
async def get_roller_standards(current_user: dict = Depends(get_current_user)):
    """Get all IS standard options for roller configuration"""
    return {
        "pipe_diameters": rs.PIPE_DIAMETERS,
        "shaft_diameters": rs.SHAFT_DIAMETERS,
        "bearing_options": rs.BEARING_OPTIONS,
        "roller_lengths_by_belt_width": rs.ROLLER_LENGTHS,
        "pipe_shaft_compatibility": rs.PIPE_SHAFT_COMPATIBILITY,
    }

@api_router.get("/compatible-shafts/{pipe_dia}")
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

@api_router.get("/compatible-bearings/{shaft_dia}")
async def get_compatible_bearings(shaft_dia: int, current_user: dict = Depends(get_current_user)):
    """Get compatible bearings for a shaft diameter"""
    bearings = rs.BEARING_OPTIONS.get(shaft_dia, [])
    if not bearings:
        raise HTTPException(status_code=404, detail=f"No bearings found for shaft diameter {shaft_dia}mm")
    return {"shaft_diameter": shaft_dia, "bearings": bearings}

@api_router.get("/compatible-bearings-for-pipe/{pipe_dia}/{shaft_dia}")
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
        "housing_costs": custom_prices.get("housing_costs", rs.HOUSING_COSTS) if custom_prices else rs.HOUSING_COSTS,
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
            import copy
            custom_prices["bearing_costs"] = copy.deepcopy(rs.BEARING_COSTS)
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
    elif request.category == "housing":
        if "housing_costs" not in custom_prices:
            custom_prices["housing_costs"] = dict(rs.HOUSING_COSTS)
        custom_prices["housing_costs"][request.key] = request.value
    elif request.category == "pipe_weight":
        if "pipe_weight" not in custom_prices:
            import copy
            custom_prices["pipe_weight"] = copy.deepcopy({str(k): v for k, v in rs.PIPE_WEIGHT_PER_METER.items()})
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

# Set as Default - Send OTP for verification
@api_router.post("/admin/prices/set-default/send-otp")
async def send_set_default_otp(current_user: dict = Depends(get_current_user)):
    """Send OTP to admin email for setting prices as default"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    email = current_user.get("email")
    name = current_user.get("name", "Admin")
    
    # Check cooldown
    existing_otp = await db.price_otp_verifications.find_one({"email": email})
    if existing_otp:
        created_at = existing_otp.get("created_at")
        if created_at:
            # Make sure both datetimes are timezone-aware
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
            if elapsed < OTP_COOLDOWN_SECONDS:
                remaining = int(OTP_COOLDOWN_SECONDS - elapsed)
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {remaining} seconds before requesting a new OTP"
                )
    
    # Generate and store OTP
    otp = generate_otp()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    await db.price_otp_verifications.update_one(
        {"email": email},
        {
            "$set": {
                "otp": otp,
                "expires_at": expiry,
                "created_at": datetime.now(timezone.utc),
                "verified": False,
                "purpose": "set_default_prices"
            }
        },
        upsert=True
    )
    
    # Send OTP email
    try:
        if GMAIL_USER and GMAIL_APP_PASSWORD:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Price Update Verification Code - {otp}"
            msg['From'] = f"Convero Solutions <{GMAIL_USER}>"
            msg['To'] = email
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #960018; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 30px; background-color: #f9f9f9; }}
                    .otp-box {{ background-color: #960018; color: white; font-size: 32px; font-weight: bold; letter-spacing: 8px; padding: 20px 40px; text-align: center; border-radius: 8px; margin: 20px 0; }}
                    .warning {{ background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Price Update Verification</h1>
                    </div>
                    <div class="content">
                        <p>Dear {name},</p>
                        <p>You have requested to set current prices as default. Please use the following verification code:</p>
                        <div class="otp-box">{otp}</div>
                        <div class="warning">
                            <strong>⚠️ Warning:</strong> This action will update the default prices in the system. All future calculations will use these new rates.
                        </div>
                        <p>This code will expire in {OTP_EXPIRY_MINUTES} minutes.</p>
                        <p>If you did not request this, please ignore this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_USER, email, msg.as_string())
            
            logging.info(f"Set default OTP sent to {email}")
        else:
            logging.warning("Email not configured, OTP not sent")
            
    except Exception as e:
        logging.error(f"Failed to send OTP email: {e}")
        # Continue anyway for development
    
    return {"message": f"Verification code sent to {email}", "email": email}

# Set as Default - Verify OTP and update defaults
@api_router.post("/admin/prices/set-default/verify")
async def verify_and_set_default_prices(
    otp: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """Verify OTP and set current prices as new defaults"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    email = current_user.get("email")
    
    # Verify OTP
    otp_record = await db.price_otp_verifications.find_one({"email": email})
    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP request found. Please request a new code.")
    
    if otp_record.get("otp") != otp:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    expires_at = otp_record.get("expires_at")
    if expires_at:
        # Make sure both datetimes are timezone-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
    
    # Get current custom prices
    custom_prices = await db.custom_prices.find_one({"_id": "prices"})
    
    if not custom_prices:
        raise HTTPException(status_code=400, detail="No custom prices found. Current prices are already defaults.")
    
    # Update roller_standards.py with new default values
    try:
        import roller_standards as rs
        
        # Update basic rates
        if "pipe_cost_per_kg" in custom_prices:
            rs.PIPE_COST_PER_KG = custom_prices["pipe_cost_per_kg"]
        if "shaft_cost_per_kg" in custom_prices:
            rs.SHAFT_COST_PER_KG = custom_prices["shaft_cost_per_kg"]
        
        # Update bearing costs
        if "bearing_costs" in custom_prices:
            for bearing, makes in custom_prices["bearing_costs"].items():
                if bearing in rs.BEARING_COSTS:
                    rs.BEARING_COSTS[bearing].update(makes)
                else:
                    rs.BEARING_COSTS[bearing] = makes
        
        # Update housing costs
        if "housing_costs" in custom_prices:
            rs.HOUSING_COSTS.update(custom_prices["housing_costs"])
        
        # Update seal costs
        if "seal_costs" in custom_prices:
            rs.SEAL_COSTS.update(custom_prices["seal_costs"])
        
        # Update circlip costs
        if "circlip_costs" in custom_prices:
            for shaft, cost in custom_prices["circlip_costs"].items():
                rs.CIRCLIP_COSTS[int(shaft)] = cost
        
        # Update rubber ring costs
        if "rubber_ring_costs" in custom_prices:
            rs.RUBBER_RING_COSTS.update(custom_prices["rubber_ring_costs"])
        
        # Update locking ring costs
        if "locking_ring_costs" in custom_prices:
            for pipe, cost in custom_prices["locking_ring_costs"].items():
                rs.LOCKING_RING_COSTS[int(pipe)] = cost
        
        # Store the update in a permanent collection for persistence across restarts
        await db.default_prices.update_one(
            {"_id": "defaults"},
            {
                "$set": {
                    "prices": custom_prices,
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": email
                }
            },
            upsert=True
        )
        
        # Clear custom prices since they are now defaults
        await db.custom_prices.delete_one({"_id": "prices"})
        
        # Invalidate price cache
        import price_loader
        price_loader.invalidate_cache()
        
        # Delete OTP record
        await db.price_otp_verifications.delete_one({"email": email})
        
        logging.info(f"Default prices updated by {email}")
        
        return {
            "message": "Prices have been set as new defaults successfully!",
            "updated_by": email,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Failed to set default prices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update defaults: {str(e)}")

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

@api_router.get("/admin/prices/export")
async def export_prices_to_excel(token: Optional[str] = None):
    """Export all prices to Excel file. Accepts token as query param for browser downloads."""
    # Validate token from query param
    current_user = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email:
                user = await db.users.find_one({"email": email})
                if user:
                    current_user = user
        except Exception as e:
            logging.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
    
    if not current_user or current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    # Get current prices
    custom_prices = await db.custom_prices.find_one({"_id": "prices"}) or {}
    
    wb = Workbook()
    
    # Style definitions
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="960018", end_color="960018", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Sheet 1: Basic Rates
    ws_basic = wb.active
    ws_basic.title = "Basic Rates"
    ws_basic.append(["Item", "Cost (Rs)"])
    ws_basic.append(["Pipe Cost per kg", custom_prices.get("pipe_cost_per_kg", rs.PIPE_COST_PER_KG)])
    ws_basic.append(["Shaft Cost per kg", custom_prices.get("shaft_cost_per_kg", rs.SHAFT_COST_PER_KG)])
    for cell in ws_basic[1]:
        cell.font = header_font
        cell.fill = header_fill
    ws_basic.column_dimensions['A'].width = 25
    ws_basic.column_dimensions['B'].width = 15
    
    # Sheet 2: Bearing Costs
    ws_bearing = wb.create_sheet("Bearing Costs")
    ws_bearing.append(["Bearing Type", "Shaft Dia (mm)", "Cost (Rs)"])
    bearing_costs = custom_prices.get("bearing_costs", rs.BEARING_COSTS)
    for bearing_type, shaft_costs in bearing_costs.items():
        for shaft_dia, cost in shaft_costs.items():
            ws_bearing.append([bearing_type, shaft_dia, cost])
    for cell in ws_bearing[1]:
        cell.font = header_font
        cell.fill = header_fill
    ws_bearing.column_dimensions['A'].width = 15
    ws_bearing.column_dimensions['B'].width = 15
    ws_bearing.column_dimensions['C'].width = 15
    
    # Sheet 3: Housing Costs
    ws_housing = wb.create_sheet("Housing Costs")
    ws_housing.append(["Housing Config (OD/Bearing)", "Cost (Rs)"])
    housing_costs = custom_prices.get("housing_costs", rs.HOUSING_COSTS)
    for config, cost in housing_costs.items():
        ws_housing.append([config, cost])
    for cell in ws_housing[1]:
        cell.font = header_font
        cell.fill = header_fill
    ws_housing.column_dimensions['A'].width = 25
    ws_housing.column_dimensions['B'].width = 15
    
    # Sheet 4: Seal Costs
    ws_seal = wb.create_sheet("Seal Costs")
    ws_seal.append(["Seal Type", "Cost (Rs)"])
    seal_costs = custom_prices.get("seal_costs", rs.SEAL_COSTS)
    for seal_type, cost in seal_costs.items():
        ws_seal.append([seal_type, cost])
    for cell in ws_seal[1]:
        cell.font = header_font
        cell.fill = header_fill
    ws_seal.column_dimensions['A'].width = 15
    ws_seal.column_dimensions['B'].width = 15
    
    # Sheet 5: Circlip Costs
    ws_circlip = wb.create_sheet("Circlip Costs")
    ws_circlip.append(["Shaft Dia (mm)", "Cost (Rs)"])
    circlip_costs = custom_prices.get("circlip_costs", rs.CIRCLIP_COSTS)
    for shaft, cost in circlip_costs.items():
        ws_circlip.append([shaft, cost])
    for cell in ws_circlip[1]:
        cell.font = header_font
        cell.fill = header_fill
    ws_circlip.column_dimensions['A'].width = 15
    ws_circlip.column_dimensions['B'].width = 15
    
    # Sheet 6: Rubber Ring Costs
    ws_rubber = wb.create_sheet("Rubber Ring Costs")
    ws_rubber.append(["Pipe/Rubber Config", "Cost (Rs)"])
    rubber_costs = custom_prices.get("rubber_ring_costs", rs.RUBBER_RING_COSTS)
    for config, cost in rubber_costs.items():
        ws_rubber.append([config, cost])
    for cell in ws_rubber[1]:
        cell.font = header_font
        cell.fill = header_fill
    ws_rubber.column_dimensions['A'].width = 25
    ws_rubber.column_dimensions['B'].width = 15
    
    # Sheet 7: Locking Ring Costs
    ws_locking = wb.create_sheet("Locking Ring Costs")
    ws_locking.append(["Pipe Dia (mm)", "Cost (Rs)"])
    locking_costs = custom_prices.get("locking_ring_costs", rs.LOCKING_RING_COSTS)
    for pipe, cost in locking_costs.items():
        ws_locking.append([pipe, cost])
    for cell in ws_locking[1]:
        cell.font = header_font
        cell.fill = header_fill
    ws_locking.column_dimensions['A'].width = 15
    ws_locking.column_dimensions['B'].width = 15
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"convero_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/admin/prices/export/pdf")
async def export_prices_to_pdf(token: Optional[str] = None):
    """Export all prices to PDF file"""
    current_user = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email:
                user = await db.users.find_one({"email": email})
                if user:
                    current_user = user
        except Exception as e:
            logging.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
    
    if not current_user or current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    custom_prices = await db.custom_prices.find_one({"_id": "prices"}) or {}
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Price List</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; font-size: 11px; }}
            h1 {{ color: #960018; border-bottom: 2px solid #960018; padding-bottom: 10px; font-size: 24px; }}
            h2 {{ color: #960018; margin-top: 20px; font-size: 16px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th {{ background-color: #960018; color: white; padding: 8px; text-align: left; }}
            td {{ padding: 6px; border-bottom: 1px solid #ddd; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .two-col {{ display: flex; gap: 20px; }}
            .two-col > div {{ flex: 1; }}
            .footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 10px; }}
        </style>
    </head>
    <body>
        <h1>Convero Price List</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Basic Rates</h2>
        <table>
            <tr><th>Item</th><th>Cost (Rs)</th></tr>
            <tr><td>Pipe Cost per kg</td><td>{custom_prices.get("pipe_cost_per_kg", rs.PIPE_COST_PER_KG)}</td></tr>
            <tr><td>Shaft Cost per kg</td><td>{custom_prices.get("shaft_cost_per_kg", rs.SHAFT_COST_PER_KG)}</td></tr>
        </table>
        
        <div class="two-col">
            <div>
                <h2>Housing Costs</h2>
                <table>
                    <tr><th>Config</th><th>Cost (Rs)</th></tr>
    """
    
    housing_costs = custom_prices.get("housing_costs", rs.HOUSING_COSTS)
    for config, cost in list(housing_costs.items())[:10]:
        html_content += f"<tr><td>{config}</td><td>{cost}</td></tr>"
    
    html_content += """
                </table>
            </div>
            <div>
                <h2>Seal Costs</h2>
                <table>
                    <tr><th>Type</th><th>Cost (Rs)</th></tr>
    """
    
    seal_costs = custom_prices.get("seal_costs", rs.SEAL_COSTS)
    for seal_type, cost in seal_costs.items():
        html_content += f"<tr><td>{seal_type}</td><td>{cost}</td></tr>"
    
    html_content += """
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>Convero - Belt Conveyor Roller Solutions</p>
        </div>
    </body>
    </html>
    """
    
    from weasyprint import HTML
    pdf_bytes = HTML(string=html_content).write_pdf()
    
    filename = f"convero_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.post("/admin/prices/import")
async def import_prices_from_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Import prices from Excel file"""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Please upload an Excel file (.xlsx or .xls)")
    
    from openpyxl import load_workbook
    from io import BytesIO
    
    try:
        contents = await file.read()
        wb = load_workbook(BytesIO(contents))
        
        # Get existing custom prices or create new
        custom_prices = await db.custom_prices.find_one({"_id": "prices"}) or {"_id": "prices"}
        
        updates = {"basic": 0, "bearing": 0, "housing": 0, "seal": 0, "circlip": 0, "rubber": 0, "locking": 0}
        
        # Process Basic Rates sheet
        if "Basic Rates" in wb.sheetnames:
            ws = wb["Basic Rates"]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] and row[1] is not None:
                    item_name = str(row[0]).lower()
                    try:
                        cost = float(row[1])
                        if "pipe" in item_name:
                            custom_prices["pipe_cost_per_kg"] = cost
                            updates["basic"] += 1
                        elif "shaft" in item_name:
                            custom_prices["shaft_cost_per_kg"] = cost
                            updates["basic"] += 1
                    except (ValueError, TypeError):
                        continue
        
        # Process Bearing Costs sheet
        if "Bearing Costs" in wb.sheetnames:
            ws = wb["Bearing Costs"]
            if "bearing_costs" not in custom_prices:
                custom_prices["bearing_costs"] = {}
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] and row[1] and row[2] is not None:
                    bearing_type = str(row[0])
                    shaft_dia = str(row[1])
                    try:
                        cost = float(row[2])
                        if bearing_type not in custom_prices["bearing_costs"]:
                            custom_prices["bearing_costs"][bearing_type] = {}
                        custom_prices["bearing_costs"][bearing_type][shaft_dia] = cost
                        updates["bearing"] += 1
                    except (ValueError, TypeError):
                        continue
        
        # Process Housing Costs sheet
        if "Housing Costs" in wb.sheetnames:
            ws = wb["Housing Costs"]
            if "housing_costs" not in custom_prices:
                custom_prices["housing_costs"] = {}
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] and row[1] is not None:
                    config = str(row[0])
                    try:
                        cost = float(row[1])
                        custom_prices["housing_costs"][config] = cost
                        updates["housing"] += 1
                    except (ValueError, TypeError):
                        continue
        
        # Process Seal Costs sheet
        if "Seal Costs" in wb.sheetnames:
            ws = wb["Seal Costs"]
            if "seal_costs" not in custom_prices:
                custom_prices["seal_costs"] = {}
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] and row[1] is not None:
                    seal_type = str(row[0])
                    try:
                        cost = float(row[1])
                        custom_prices["seal_costs"][seal_type] = cost
                        updates["seal"] += 1
                    except (ValueError, TypeError):
                        continue
        
        # Process Circlip Costs sheet
        if "Circlip Costs" in wb.sheetnames:
            ws = wb["Circlip Costs"]
            if "circlip_costs" not in custom_prices:
                custom_prices["circlip_costs"] = {}
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] and row[1] is not None:
                    shaft = str(row[0])
                    try:
                        cost = float(row[1])
                        custom_prices["circlip_costs"][shaft] = cost
                        updates["circlip"] += 1
                    except (ValueError, TypeError):
                        continue
        
        # Process Rubber Ring Costs sheet
        if "Rubber Ring Costs" in wb.sheetnames:
            ws = wb["Rubber Ring Costs"]
            if "rubber_ring_costs" not in custom_prices:
                custom_prices["rubber_ring_costs"] = {}
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] and row[1] is not None:
                    config = str(row[0])
                    try:
                        cost = float(row[1])
                        custom_prices["rubber_ring_costs"][config] = cost
                        updates["rubber"] += 1
                    except (ValueError, TypeError):
                        continue
        
        # Process Locking Ring Costs sheet
        if "Locking Ring Costs" in wb.sheetnames:
            ws = wb["Locking Ring Costs"]
            if "locking_ring_costs" not in custom_prices:
                custom_prices["locking_ring_costs"] = {}
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] and row[1] is not None:
                    pipe = str(row[0])
                    try:
                        cost = float(row[1])
                        custom_prices["locking_ring_costs"][pipe] = cost
                        updates["locking"] += 1
                    except (ValueError, TypeError):
                        continue
        
        # Save to database
        await db.custom_prices.replace_one({"_id": "prices"}, custom_prices, upsert=True)
        
        # Invalidate price cache
        import price_loader
        price_loader.invalidate_cache()
        
        total_updates = sum(updates.values())
        
        return {
            "message": f"Successfully imported {total_updates} price entries",
            "details": updates
        }
        
    except Exception as e:
        logging.error(f"Error importing prices: {e}")
        raise HTTPException(status_code=400, detail=f"Error processing Excel file: {str(e)}")

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


@api_router.get("/customers/{customer_id}/quotes")
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


@api_router.post("/generate-drawing-download")
async def generate_drawing_download(request: DrawingRequest, current_user: dict = Depends(get_current_user)):
    """Generate and directly download a technical drawing PDF"""
    from drawing_generator import generate_roller_drawing
    from fastapi.responses import Response
    
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
        
        pdf_bytes = pdf_buffer.getvalue()
        filename = f"Drawing_{request.product_code.replace(' ', '_').replace('/', '-')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate drawing: {str(e)}")


class EmailDrawingRequest(BaseModel):
    product_code: str
    roller_type: str
    pipe_diameter: float
    pipe_length: int
    pipe_type: str
    shaft_diameter: int
    bearing: str
    bearing_make: str
    housing: str
    weight_kg: float
    unit_price: float
    rubber_diameter: Optional[float] = None
    belt_widths: Optional[List[int]] = None
    quantity: int = 1
    shaft_end_type: Optional[str] = "B"
    custom_shaft_extension: Optional[int] = None
    recipient_email: str


@api_router.post("/email-drawing")
async def email_drawing(request: EmailDrawingRequest, current_user: dict = Depends(get_current_user)):
    """Generate a drawing PDF and email it to the recipient"""
    from drawing_generator import generate_roller_drawing
    
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise HTTPException(status_code=500, detail="Email service not configured")
    
    try:
        # Generate the PDF
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
        
        pdf_bytes = pdf_buffer.getvalue()
        filename = f"Drawing_{request.product_code.replace(' ', '_').replace('/', '-')}.pdf"
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = request.recipient_email
        msg['Subject'] = f"Roller Drawing - {request.product_code}"
        
        # Email body
        body = f"""
Dear Customer,

Please find attached the technical drawing for your requested roller:

Product Code: {request.product_code}
Roller Type: {request.roller_type}
Pipe Diameter: {request.pipe_diameter}mm
Pipe Length: {request.pipe_length}mm
Shaft Diameter: {request.shaft_diameter}mm
Bearing: {request.bearing}
Weight: {request.weight_kg}kg

For any queries, please contact us.

Best Regards,
Convero Solutions
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(pdf_attachment)
        
        # Send email via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        return {"message": f"Drawing sent successfully to {request.recipient_email}"}
        
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=500, detail="Email authentication failed. Please check Gmail credentials.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


# ============= ANALYTICS & DASHBOARD =============

@api_router.get("/analytics/dashboard")
async def get_dashboard_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive dashboard analytics (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Parse date filters
        date_filter = {}
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                date_filter = {"created_at": {"$gte": start_dt, "$lte": end_dt}}
            except ValueError:
                pass
        
        # Get current date info
        now = get_ist_now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        # Get financial year dates
        if now.month >= 4:
            fy_start = now.replace(month=4, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            fy_start = now.replace(year=now.year-1, month=4, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Total quotes count
        quotes_filter = {**date_filter} if date_filter else {}
        total_quotes = await db.quotes.count_documents(quotes_filter)
        
        # Approved quotes count
        approved_filter = {"status": "approved", **date_filter} if date_filter else {"status": "approved"}
        approved_quotes = await db.quotes.count_documents(approved_filter)
        
        # Pending RFQs count
        pending_filter = {"status": {"$ne": "approved"}, **date_filter} if date_filter else {"status": {"$ne": "approved"}}
        pending_rfqs = await db.quotes.count_documents(pending_filter)
        
        # Total customers
        customer_filter = {"role": "customer", **date_filter} if date_filter else {"role": "customer"}
        total_customers = await db.users.count_documents({"role": "customer"})
        
        # New customers this month
        new_customers_this_month = await db.users.count_documents({
            "role": "customer",
            "created_at": {"$gte": current_month_start.replace(tzinfo=None)}
        })
        
        # Calculate total revenue from approved quotes
        revenue_match = {"status": "approved", **date_filter} if date_filter else {"status": "approved"}
        revenue_pipeline = [
            {"$match": revenue_match},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
        ]
        revenue_result = await db.quotes.aggregate(revenue_pipeline).to_list(1)
        total_revenue = revenue_result[0]["total"] if revenue_result else 0
        
        # Revenue this month
        monthly_revenue_pipeline = [
            {"$match": {
                "status": "approved",
                "created_at": {"$gte": current_month_start.replace(tzinfo=None)}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
        ]
        monthly_revenue_result = await db.quotes.aggregate(monthly_revenue_pipeline).to_list(1)
        monthly_revenue = monthly_revenue_result[0]["total"] if monthly_revenue_result else 0
        
        # Revenue last month for comparison
        last_month_revenue_pipeline = [
            {"$match": {
                "status": "approved",
                "created_at": {
                    "$gte": last_month_start.replace(tzinfo=None),
                    "$lt": current_month_start.replace(tzinfo=None)
                }
            }},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
        ]
        last_month_revenue_result = await db.quotes.aggregate(last_month_revenue_pipeline).to_list(1)
        last_month_revenue = last_month_revenue_result[0]["total"] if last_month_revenue_result else 0
        
        # Calculate revenue growth percentage
        if last_month_revenue > 0:
            revenue_growth = ((monthly_revenue - last_month_revenue) / last_month_revenue) * 100
        else:
            revenue_growth = 100 if monthly_revenue > 0 else 0
        
        # Average quote value
        avg_quote_value = total_revenue / approved_quotes if approved_quotes > 0 else 0
        
        # Conversion rate (approved / total)
        conversion_rate = (approved_quotes / total_quotes * 100) if total_quotes > 0 else 0
        
        return {
            "summary": {
                "total_quotes": total_quotes,
                "approved_quotes": approved_quotes,
                "pending_rfqs": pending_rfqs,
                "total_customers": total_customers,
                "new_customers_this_month": new_customers_this_month,
                "total_revenue": round(total_revenue, 2),
                "monthly_revenue": round(monthly_revenue, 2),
                "revenue_growth": round(revenue_growth, 1),
                "avg_quote_value": round(avg_quote_value, 2),
                "conversion_rate": round(conversion_rate, 1)
            }
        }
    except Exception as e:
        logging.error(f"Dashboard analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@api_router.get("/analytics/revenue-trend")
async def get_revenue_trend(
    months: int = 6,
    current_user: dict = Depends(get_current_user)
):
    """Get monthly revenue trend for the last N months"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        now = get_ist_now()
        trends = []
        
        for i in range(months - 1, -1, -1):
            # Calculate month start and end
            target_date = now - timedelta(days=30 * i)
            month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            # Get revenue for this month
            pipeline = [
                {"$match": {
                    "status": "approved",
                    "created_at": {
                        "$gte": month_start.replace(tzinfo=None),
                        "$lt": month_end.replace(tzinfo=None)
                    }
                }},
                {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
            ]
            result = await db.quotes.aggregate(pipeline).to_list(1)
            revenue = result[0]["total"] if result else 0
            
            # Get quote count for this month
            quote_count = await db.quotes.count_documents({
                "created_at": {
                    "$gte": month_start.replace(tzinfo=None),
                    "$lt": month_end.replace(tzinfo=None)
                }
            })
            
            trends.append({
                "month": month_start.strftime("%b"),
                "year": month_start.year,
                "revenue": round(revenue, 2),
                "quotes": quote_count
            })
        
        return {"trends": trends}
    except Exception as e:
        logging.error(f"Revenue trend error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch revenue trend: {str(e)}")


@api_router.get("/analytics/top-customers")
async def get_top_customers(
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """Get top customers by revenue"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        pipeline = [
            {"$match": {"status": "approved"}},
            {"$group": {
                "_id": "$customer_id",
                "total_revenue": {"$sum": "$total_price"},
                "quote_count": {"$sum": 1},
                "customer_name": {"$first": "$customer_name"},
                "company": {"$first": "$company"}
            }},
            {"$sort": {"total_revenue": -1}},
            {"$limit": limit}
        ]
        
        results = await db.quotes.aggregate(pipeline).to_list(limit)
        
        customers = []
        for r in results:
            customers.append({
                "customer_id": r["_id"],
                "customer_name": r.get("customer_name", "Unknown"),
                "company": r.get("company", "N/A"),
                "total_revenue": round(r["total_revenue"], 2),
                "quote_count": r["quote_count"]
            })
        
        return {"top_customers": customers}
    except Exception as e:
        logging.error(f"Top customers error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch top customers: {str(e)}")


@api_router.get("/analytics/quote-status")
async def get_quote_status_distribution(current_user: dict = Depends(get_current_user)):
    """Get distribution of quotes by status"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        pipeline = [
            {"$group": {
                "_id": {"$ifNull": ["$status", "pending"]},
                "count": {"$sum": 1}
            }}
        ]
        
        results = await db.quotes.aggregate(pipeline).to_list(10)
        
        distribution = {}
        for r in results:
            status = r["_id"] if r["_id"] else "pending"
            distribution[status] = r["count"]
        
        # Ensure both statuses exist
        if "approved" not in distribution:
            distribution["approved"] = 0
        if "pending" not in distribution:
            distribution["pending"] = 0
            
        return {"distribution": distribution}
    except Exception as e:
        logging.error(f"Quote status error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch quote status: {str(e)}")


@api_router.get("/analytics/recent-activity")
async def get_recent_activity(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get recent quotes and customer activity"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Recent quotes
        recent_quotes = await db.quotes.find(
            {},
            {"_id": 0, "quote_number": 1, "customer_name": 1, "company": 1, 
             "total_price": 1, "status": 1, "created_at": 1}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        # Format dates
        for quote in recent_quotes:
            if quote.get("created_at"):
                quote["created_at"] = quote["created_at"].isoformat()
        
        # Recent customers
        recent_customers = await db.users.find(
            {"role": "customer"},
            {"_id": 0, "name": 1, "email": 1, "company": 1, "created_at": 1}
        ).sort("created_at", -1).limit(5).to_list(5)
        
        # Format dates
        for customer in recent_customers:
            if customer.get("created_at"):
                customer["created_at"] = customer["created_at"].isoformat()
        
        return {
            "recent_quotes": recent_quotes,
            "recent_customers": recent_customers
        }
    except Exception as e:
        logging.error(f"Recent activity error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent activity: {str(e)}")


@api_router.get("/analytics/roller-type-distribution")
async def get_roller_type_distribution(current_user: dict = Depends(get_current_user)):
    """Get distribution of roller types in quotes"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        pipeline = [
            {"$unwind": "$products"},
            {"$group": {
                "_id": "$products.roller_type",
                "count": {"$sum": 1},
                "total_value": {"$sum": "$products.price"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        results = await db.quotes.aggregate(pipeline).to_list(10)
        
        distribution = []
        for r in results:
            if r["_id"]:
                distribution.append({
                    "roller_type": r["_id"],
                    "count": r["count"],
                    "total_value": round(r.get("total_value", 0), 2)
                })
        
        return {"distribution": distribution}
    except Exception as e:
        logging.error(f"Roller type distribution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch roller type distribution: {str(e)}")


@api_router.get("/analytics/export/excel")
async def export_analytics_excel(current_user: dict = Depends(get_current_user)):
    """Export dashboard analytics to Excel file"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Fetch all analytics data
        now = get_ist_now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Summary stats
        total_quotes = await db.quotes.count_documents({})
        approved_quotes = await db.quotes.count_documents({"status": "approved"})
        pending_rfqs = await db.quotes.count_documents({"status": {"$ne": "approved"}})
        total_customers = await db.users.count_documents({"role": "customer"})
        
        revenue_pipeline = [
            {"$match": {"status": "approved"}},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
        ]
        revenue_result = await db.quotes.aggregate(revenue_pipeline).to_list(1)
        total_revenue = revenue_result[0]["total"] if revenue_result else 0
        
        # Top customers
        top_customers_pipeline = [
            {"$match": {"status": "approved"}},
            {"$group": {
                "_id": "$customer_id",
                "total_revenue": {"$sum": "$total_price"},
                "quote_count": {"$sum": 1},
                "customer_name": {"$first": "$customer_name"},
                "company": {"$first": "$company"}
            }},
            {"$sort": {"total_revenue": -1}},
            {"$limit": 10}
        ]
        top_customers = await db.quotes.aggregate(top_customers_pipeline).to_list(10)
        
        # Recent quotes
        recent_quotes = await db.quotes.find(
            {},
            {"_id": 0, "quote_number": 1, "customer_name": 1, "company": 1, 
             "total_price": 1, "status": 1, "created_at": 1}
        ).sort("created_at", -1).limit(20).to_list(20)
        
        # Roller type distribution
        roller_pipeline = [
            {"$unwind": "$products"},
            {"$group": {
                "_id": "$products.roller_type",
                "count": {"$sum": 1},
                "total_value": {"$sum": "$products.price"}
            }},
            {"$sort": {"count": -1}}
        ]
        roller_types = await db.quotes.aggregate(roller_pipeline).to_list(10)
        
        # Create Excel workbook
        wb = Workbook()
        
        # Define styles
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="960018", end_color="960018", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Sheet 1: Summary
        ws_summary = wb.active
        ws_summary.title = "Summary"
        
        summary_data = [
            ["Dashboard Analytics Report", ""],
            ["Generated on", now.strftime("%d %b %Y, %I:%M %p IST")],
            ["", ""],
            ["Metric", "Value"],
            ["Total Revenue", f"₹{total_revenue:,.2f}"],
            ["Total Quotes", total_quotes],
            ["Approved Quotes", approved_quotes],
            ["Pending RFQs", pending_rfqs],
            ["Total Customers", total_customers],
            ["Conversion Rate", f"{(approved_quotes/total_quotes*100) if total_quotes > 0 else 0:.1f}%"],
            ["Average Quote Value", f"₹{(total_revenue/approved_quotes) if approved_quotes > 0 else 0:,.2f}"],
        ]
        
        for row_idx, row_data in enumerate(summary_data, 1):
            for col_idx, value in enumerate(row_data, 1):
                cell = ws_summary.cell(row=row_idx, column=col_idx, value=value)
                if row_idx == 1:
                    cell.font = Font(bold=True, size=16, color="960018")
                elif row_idx == 4:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                cell.border = thin_border
        
        ws_summary.column_dimensions['A'].width = 25
        ws_summary.column_dimensions['B'].width = 25
        
        # Sheet 2: Top Customers
        ws_customers = wb.create_sheet("Top Customers")
        customer_headers = ["Rank", "Customer Name", "Company", "Total Revenue", "Quote Count"]
        
        for col_idx, header in enumerate(customer_headers, 1):
            cell = ws_customers.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        for row_idx, customer in enumerate(top_customers, 2):
            ws_customers.cell(row=row_idx, column=1, value=row_idx-1).border = thin_border
            ws_customers.cell(row=row_idx, column=2, value=customer.get("customer_name", "Unknown")).border = thin_border
            ws_customers.cell(row=row_idx, column=3, value=customer.get("company", "N/A")).border = thin_border
            ws_customers.cell(row=row_idx, column=4, value=f"₹{customer['total_revenue']:,.2f}").border = thin_border
            ws_customers.cell(row=row_idx, column=5, value=customer["quote_count"]).border = thin_border
        
        for col_idx in range(1, 6):
            ws_customers.column_dimensions[get_column_letter(col_idx)].width = 20
        
        # Sheet 3: Recent Quotes
        ws_quotes = wb.create_sheet("Recent Quotes")
        quote_headers = ["Quote Number", "Customer", "Company", "Total Price", "Status", "Date"]
        
        for col_idx, header in enumerate(quote_headers, 1):
            cell = ws_quotes.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        for row_idx, quote in enumerate(recent_quotes, 2):
            ws_quotes.cell(row=row_idx, column=1, value=quote.get("quote_number", "")).border = thin_border
            ws_quotes.cell(row=row_idx, column=2, value=quote.get("customer_name", "")).border = thin_border
            ws_quotes.cell(row=row_idx, column=3, value=quote.get("company", "")).border = thin_border
            ws_quotes.cell(row=row_idx, column=4, value=f"₹{quote.get('total_price', 0):,.2f}").border = thin_border
            ws_quotes.cell(row=row_idx, column=5, value=quote.get("status", "pending").title()).border = thin_border
            created_at = quote.get("created_at")
            date_str = created_at.strftime("%d %b %Y") if created_at else ""
            ws_quotes.cell(row=row_idx, column=6, value=date_str).border = thin_border
        
        for col_idx in range(1, 7):
            ws_quotes.column_dimensions[get_column_letter(col_idx)].width = 18
        
        # Sheet 4: Roller Type Distribution
        ws_rollers = wb.create_sheet("Roller Types")
        roller_headers = ["Roller Type", "Count", "Total Value"]
        
        for col_idx, header in enumerate(roller_headers, 1):
            cell = ws_rollers.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        for row_idx, roller in enumerate(roller_types, 2):
            if roller["_id"]:
                ws_rollers.cell(row=row_idx, column=1, value=roller["_id"]).border = thin_border
                ws_rollers.cell(row=row_idx, column=2, value=roller["count"]).border = thin_border
                ws_rollers.cell(row=row_idx, column=3, value=f"₹{roller.get('total_value', 0):,.2f}").border = thin_border
        
        for col_idx in range(1, 4):
            ws_rollers.column_dimensions[get_column_letter(col_idx)].width = 20
        
        # Save to bytes
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        filename = f"Dashboard_Report_{now.strftime('%Y%m%d_%H%M')}.xlsx"
        
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logging.error(f"Excel export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export Excel: {str(e)}")


@api_router.get("/analytics/export/pdf")
async def export_analytics_pdf(current_user: dict = Depends(get_current_user)):
    """Export dashboard analytics to PDF file"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from fpdf import FPDF
        
        # Fetch all analytics data
        now = get_ist_now()
        
        # Summary stats
        total_quotes = await db.quotes.count_documents({})
        approved_quotes = await db.quotes.count_documents({"status": "approved"})
        pending_rfqs = await db.quotes.count_documents({"status": {"$ne": "approved"}})
        total_customers = await db.users.count_documents({"role": "customer"})
        
        revenue_pipeline = [
            {"$match": {"status": "approved"}},
            {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
        ]
        revenue_result = await db.quotes.aggregate(revenue_pipeline).to_list(1)
        total_revenue = revenue_result[0]["total"] if revenue_result else 0
        
        # Top customers
        top_customers_pipeline = [
            {"$match": {"status": "approved"}},
            {"$group": {
                "_id": "$customer_id",
                "total_revenue": {"$sum": "$total_price"},
                "quote_count": {"$sum": 1},
                "customer_name": {"$first": "$customer_name"},
                "company": {"$first": "$company"}
            }},
            {"$sort": {"total_revenue": -1}},
            {"$limit": 5}
        ]
        top_customers = await db.quotes.aggregate(top_customers_pipeline).to_list(5)
        
        # Recent quotes
        recent_quotes = await db.quotes.find(
            {},
            {"_id": 0, "quote_number": 1, "customer_name": 1, "total_price": 1, "status": 1, "created_at": 1}
        ).sort("created_at", -1).limit(10).to_list(10)
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header with Convero branding
        pdf.set_fill_color(150, 0, 24)  # Carmine Red
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_text_color(255, 255, 255)
        
        # Company name
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_xy(10, 8)
        pdf.cell(0, 8, 'CONVERO SOLUTIONS')
        
        # Report title
        pdf.set_font('Helvetica', 'B', 18)
        pdf.set_xy(10, 18)
        pdf.cell(0, 10, 'Dashboard Analytics Report', align='C')
        
        # Generated timestamp
        pdf.set_font('Helvetica', '', 9)
        pdf.set_xy(10, 30)
        pdf.cell(0, 8, f'Report Generated: {now.strftime("%d %b %Y at %I:%M:%S %p IST")}', align='C')
        
        # Reset text color
        pdf.set_text_color(0, 0, 0)
        pdf.set_y(45)
        
        # Summary Section
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, 'Summary', fill=True, ln=True)
        pdf.ln(5)
        
        # Summary metrics in a grid
        pdf.set_font('Helvetica', '', 11)
        col_width = 95
        
        def format_currency(val):
            if val >= 10000000:
                return f"Rs. {val/10000000:.2f} Cr"
            elif val >= 100000:
                return f"Rs. {val/100000:.2f} L"
            return f"Rs. {val:,.2f}"
        
        metrics = [
            ("Total Revenue", format_currency(total_revenue)),
            ("Total Quotes", str(total_quotes)),
            ("Approved Quotes", str(approved_quotes)),
            ("Pending RFQs", str(pending_rfqs)),
            ("Total Customers", str(total_customers)),
            ("Conversion Rate", f"{(approved_quotes/total_quotes*100) if total_quotes > 0 else 0:.1f}%"),
        ]
        
        for i, (label, value) in enumerate(metrics):
            if i % 2 == 0:
                x = 10
            else:
                x = 105
            
            pdf.set_x(x)
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(col_width, 6, label)
            
            if i % 2 == 1:
                pdf.ln()
            
            pdf.set_x(x)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_width, 8, value)
            
            if i % 2 == 1:
                pdf.ln(5)
        
        pdf.ln(10)
        
        # Top Customers Section
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, 'Top Customers by Revenue', fill=True, ln=True)
        pdf.ln(3)
        
        # Table header
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(150, 0, 24)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(10, 8, '#', border=1, fill=True, align='C')
        pdf.cell(60, 8, 'Customer', border=1, fill=True, align='C')
        pdf.cell(60, 8, 'Company', border=1, fill=True, align='C')
        pdf.cell(40, 8, 'Revenue', border=1, fill=True, align='C')
        pdf.cell(20, 8, 'Quotes', border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 9)
        for idx, customer in enumerate(top_customers, 1):
            pdf.cell(10, 7, str(idx), border=1, align='C')
            pdf.cell(60, 7, customer.get("customer_name", "Unknown")[:25], border=1)
            pdf.cell(60, 7, (customer.get("company", "N/A") or "N/A")[:25], border=1)
            pdf.cell(40, 7, f"Rs. {customer['total_revenue']:,.0f}", border=1, align='R')
            pdf.cell(20, 7, str(customer["quote_count"]), border=1, align='C')
            pdf.ln()
        
        pdf.ln(10)
        
        # Recent Quotes Section
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, 'Recent Quotes', fill=True, ln=True)
        pdf.ln(3)
        
        # Table header
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(150, 0, 24)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(40, 8, 'Quote #', border=1, fill=True, align='C')
        pdf.cell(50, 8, 'Customer', border=1, fill=True, align='C')
        pdf.cell(40, 8, 'Amount', border=1, fill=True, align='C')
        pdf.cell(30, 8, 'Status', border=1, fill=True, align='C')
        pdf.cell(30, 8, 'Date', border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 9)
        for quote in recent_quotes:
            pdf.cell(40, 7, quote.get("quote_number", "")[:15], border=1)
            pdf.cell(50, 7, (quote.get("customer_name", "")[:20]), border=1)
            pdf.cell(40, 7, f"Rs. {quote.get('total_price', 0):,.0f}", border=1, align='R')
            status = quote.get("status", "pending").title()
            pdf.cell(30, 7, status, border=1, align='C')
            created_at = quote.get("created_at")
            date_str = created_at.strftime("%d %b") if created_at else ""
            pdf.cell(30, 7, date_str, border=1, align='C')
            pdf.ln()
        
        # Footer
        pdf.set_y(-20)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 10, 'Convero Solutions - Roller Price Calculator', align='C')
        
        # Output PDF
        pdf_bytes = pdf.output()
        filename = f"Dashboard_Report_{now.strftime('%Y%m%d_%H%M')}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logging.error(f"PDF export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")

@api_router.post("/admin/migrate-customer-codes")
async def migrate_customer_codes(current_user: dict = Depends(get_current_user)):
    """Migrate existing customers to have customer codes - Admin only"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can run migrations")
    
    updated_count = 0
    
    # Find all users with role=customer and no customer_code
    users_cursor = db.users.find({
        "role": "customer",
        "$or": [
            {"customer_code": {"$exists": False}},
            {"customer_code": None}
        ]
    }).sort("created_at", 1)  # Sort by creation date to maintain order
    
    async for user in users_cursor:
        customer_code = await generate_customer_code()
        
        # Update user
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"customer_code": customer_code}}
        )
        
        # Also update corresponding customer record
        await db.customers.update_one(
            {"email": user["email"]},
            {"$set": {"customer_code": customer_code}}
        )
        
        updated_count += 1
        logging.info(f"Assigned customer code {customer_code} to user {user['email']}")
    
    # Also update customers collection entries that don't have codes
    customers_cursor = db.customers.find({
        "$or": [
            {"customer_code": {"$exists": False}},
            {"customer_code": None}
        ]
    }).sort("created_at", 1)
    
    async for customer in customers_cursor:
        # Check if this customer's email has a user with a code
        user = await db.users.find_one({"email": customer.get("email"), "customer_code": {"$exists": True}})
        
        if user and user.get("customer_code"):
            # Use the same code as the user
            await db.customers.update_one(
                {"_id": customer["_id"]},
                {"$set": {"customer_code": user["customer_code"]}}
            )
        else:
            # Generate a new code
            customer_code = await generate_customer_code()
            await db.customers.update_one(
                {"_id": customer["_id"]},
                {"$set": {"customer_code": customer_code}}
            )
            updated_count += 1
            logging.info(f"Assigned customer code {customer_code} to customer {customer.get('email', customer.get('name'))}")
    
    # Also update quotes that don't have customer_code
    quotes_updated = 0
    quotes_cursor = db.quotes.find({
        "$or": [
            {"customer_code": {"$exists": False}},
            {"customer_code": None}
        ]
    })
    
    async for quote in quotes_cursor:
        # Try to find customer_code from customer_id or customer_email
        customer_code = None
        
        # First check by customer_id in users
        if quote.get("customer_id"):
            try:
                from bson import ObjectId
                user = await db.users.find_one({"_id": ObjectId(quote["customer_id"])})
                if user:
                    customer_code = user.get("customer_code")
            except:
                pass
        
        # If not found, try by email
        if not customer_code and quote.get("customer_email"):
            user = await db.users.find_one({"email": quote["customer_email"]})
            if user:
                customer_code = user.get("customer_code")
        
        # If still not found, check customers collection
        if not customer_code and quote.get("customer_email"):
            customer = await db.customers.find_one({"email": quote["customer_email"]})
            if customer:
                customer_code = customer.get("customer_code")
        
        if customer_code:
            await db.quotes.update_one(
                {"_id": quote["_id"]},
                {"$set": {"customer_code": customer_code}}
            )
            quotes_updated += 1
    
    return {"message": f"Migration complete. Updated {updated_count} customers and {quotes_updated} quotes with codes."}


# ============== EXPORT ENDPOINTS ==============

@api_router.get("/quotes/export/excel")
async def export_quotes_excel(
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


@api_router.get("/quotes/export/pdf")
async def export_quotes_pdf(
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
        
        quotes = await db.quotes.find(query).sort("created_at", -1).to_list(1000)
        
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


@api_router.get("/customers/export/excel")
async def export_customers_excel(
    search: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Export customers to Excel file - Admin only"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        query = {"role": "customer"}
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"company": {"$regex": search, "$options": "i"}},
                {"customer_code": {"$regex": search, "$options": "i"}}
            ]
        
        customers = await db.users.find(query, {"_id": 0, "password": 0}).to_list(1000)
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Customers"
        
        headers = ["Customer Code", "Name", "Email", "Company", "Phone", "City", "State", "GST Number", "Created Date"]
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="960018", end_color="960018", fill_type="solid")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        for row, customer in enumerate(customers, 2):
            ws.cell(row=row, column=1, value=customer.get("customer_code", "N/A"))
            ws.cell(row=row, column=2, value=customer.get("name", "N/A"))
            ws.cell(row=row, column=3, value=customer.get("email", "N/A"))
            ws.cell(row=row, column=4, value=customer.get("company", "N/A"))
            ws.cell(row=row, column=5, value=customer.get("phone", "N/A"))
            ws.cell(row=row, column=6, value=customer.get("city", "N/A"))
            ws.cell(row=row, column=7, value=customer.get("state", "N/A"))
            ws.cell(row=row, column=8, value=customer.get("gst_number", "N/A"))
            created = customer.get("created_at")
            if created:
                ws.cell(row=row, column=9, value=created.strftime("%Y-%m-%d") if hasattr(created, 'strftime') else str(created)[:10])
        
        for col in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 30)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Customers_Export_{get_ist_now().strftime('%Y%m%d_%H%M')}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Customer Excel export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/customers/export/pdf")
async def export_customers_pdf(
    search: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Export customers to PDF file - Admin only"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        query = {}
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"company": {"$regex": search, "$options": "i"}}
            ]
        
        customers = await db.users.find({**query, "role": "customer"}).sort("created_at", -1).to_list(1000)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Customers Export</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #960018; border-bottom: 2px solid #960018; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background-color: #960018; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>Customer List</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total: {len(customers)} customers</p>
            <table>
                <thead>
                    <tr>
                        <th>Customer Code</th>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>Company</th>
                        <th>Joined</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for customer in customers:
            created = customer.get('created_at', datetime.now())
            if isinstance(created, str):
                created = datetime.fromisoformat(created.replace('Z', '+00:00'))
            
            html_content += f"""
                    <tr>
                        <td>{customer.get('customer_code', 'N/A')}</td>
                        <td>{customer.get('name', 'N/A')}</td>
                        <td>{customer.get('email', 'N/A')}</td>
                        <td>{customer.get('phone', 'N/A')}</td>
                        <td>{customer.get('company', 'N/A')}</td>
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
        
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        filename = f"customers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Customer PDF export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/products/export/excel")
async def export_products_excel(
    search: str = None,
    roller_type: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Export product catalog to Excel file"""
    try:
        query = {}
        if search:
            query["$or"] = [
                {"product_code": {"$regex": search, "$options": "i"}},
                {"product_name": {"$regex": search, "$options": "i"}}
            ]
        if roller_type:
            query["roller_type"] = roller_type
        
        products = await db.products.find(query, {"_id": 0}).to_list(5000)
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Products"
        
        headers = ["Product Code", "Product Name", "Roller Type", "Pipe OD", "Shaft Dia", "Bearing", "Face Length", "Weight", "Unit Price"]
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="960018", end_color="960018", fill_type="solid")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        for row, product in enumerate(products, 2):
            ws.cell(row=row, column=1, value=product.get("product_code", "N/A"))
            ws.cell(row=row, column=2, value=product.get("product_name", "N/A"))
            ws.cell(row=row, column=3, value=product.get("roller_type", "N/A"))
            ws.cell(row=row, column=4, value=product.get("pipe_od", "N/A"))
            ws.cell(row=row, column=5, value=product.get("shaft_dia", "N/A"))
            ws.cell(row=row, column=6, value=product.get("bearing", "N/A"))
            ws.cell(row=row, column=7, value=product.get("face_length", "N/A"))
            ws.cell(row=row, column=8, value=product.get("weight", 0))
            ws.cell(row=row, column=9, value=product.get("unit_price", 0))
        
        for col in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 30)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Products_Export_{get_ist_now().strftime('%Y%m%d_%H%M')}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Product Excel export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/products/export/pdf")
async def export_products_pdf(
    search: str = None,
    roller_type: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Export product catalog to PDF file"""
    try:
        query = {}
        if search:
            query["$or"] = [
                {"product_code": {"$regex": search, "$options": "i"}},
                {"product_name": {"$regex": search, "$options": "i"}}
            ]
        if roller_type:
            query["roller_type"] = roller_type
        
        products = await db.products.find(query).to_list(500)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Product Catalog</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #960018; border-bottom: 2px solid #960018; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 11px; }}
                th {{ background-color: #960018; color: white; padding: 8px; text-align: left; }}
                td {{ padding: 6px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>Product Catalog</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total: {len(products)} products</p>
            <table>
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Pipe Dia</th>
                        <th>Shaft</th>
                        <th>Length</th>
                        <th>Weight</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for product in products:
            html_content += f"""
                    <tr>
                        <td>{product.get('product_code', 'N/A')}</td>
                        <td>{product.get('product_name', 'N/A')}</td>
                        <td>{product.get('roller_type', 'N/A')}</td>
                        <td>{product.get('pipe_diameter', 'N/A')}mm</td>
                        <td>{product.get('shaft_diameter', 'N/A')}mm</td>
                        <td>{product.get('roller_length', 'N/A')}mm</td>
                        <td>{product.get('total_weight', 0):.2f}kg</td>
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
        
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        filename = f"products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Product PDF export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/cart/export/excel")
async def export_cart_excel(
    current_user: dict = Depends(get_current_user)
):
    """Export cart contents to Excel file"""
    try:
        user_id = current_user.get("user_id")
        cart = await db.carts.find_one({"user_id": user_id})
        
        if not cart or not cart.get("items"):
            raise HTTPException(status_code=404, detail="Cart is empty")
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Cart"
        
        headers = ["Product Code", "Product Name", "Roller Type", "Specifications", "Quantity", "Unit Price", "Total Price", "Weight"]
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="960018", end_color="960018", fill_type="solid")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        total_value = 0
        total_weight = 0
        for row, item in enumerate(cart.get("items", []), 2):
            specs = item.get("specifications", {})
            spec_str = f"Pipe: {specs.get('pipe_od', 'N/A')}, Shaft: {specs.get('shaft_dia', 'N/A')}, Bearing: {specs.get('bearing', 'N/A')}"
            
            ws.cell(row=row, column=1, value=item.get("product_code", "N/A"))
            ws.cell(row=row, column=2, value=item.get("product_name", "N/A"))
            ws.cell(row=row, column=3, value=item.get("roller_type", "N/A"))
            ws.cell(row=row, column=4, value=spec_str)
            ws.cell(row=row, column=5, value=item.get("quantity", 0))
            ws.cell(row=row, column=6, value=item.get("unit_price", 0))
            ws.cell(row=row, column=7, value=item.get("total_price", 0))
            ws.cell(row=row, column=8, value=item.get("weight", 0))
            
            total_value += item.get("total_price", 0)
            total_weight += item.get("weight", 0) * item.get("quantity", 0)
        
        # Add totals row
        last_row = len(cart.get("items", [])) + 2
        ws.cell(row=last_row, column=6, value="TOTAL:")
        ws.cell(row=last_row, column=7, value=total_value)
        ws.cell(row=last_row, column=8, value=total_weight)
        ws.cell(row=last_row, column=6).font = Font(bold=True)
        ws.cell(row=last_row, column=7).font = Font(bold=True)
        
        for col in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Cart_Export_{get_ist_now().strftime('%Y%m%d_%H%M')}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Cart Excel export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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

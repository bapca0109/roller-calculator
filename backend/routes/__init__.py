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

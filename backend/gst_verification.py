"""
GST Verification Module
Fetches GST details from multiple sources:
1. Primary: Appyflow API (no captcha required, 50 free requests)
2. Fallback: Official GST portal (requires captcha)
"""

import requests
import base64
import uuid
import os
from typing import Optional, Dict, Any

# Appyflow API (Primary - no captcha)
APPYFLOW_API_URL = "https://appyflow.in/api/verifyGST"
# Get API key from environment or use a default test key
APPYFLOW_API_KEY = os.environ.get("APPYFLOW_GST_KEY", "")

# GST Portal endpoints (Fallback - requires captcha)
GST_BASE_URL = "https://services.gst.gov.in/services/api"
GST_SEARCH_URL = f"{GST_BASE_URL}/search/tp"
GST_CAPTCHA_URL = f"{GST_BASE_URL}/captcha"

# Store sessions temporarily (in production, use Redis or similar)
gst_sessions: Dict[str, requests.Session] = {}


def verify_gstin_appyflow(gstin: str) -> Dict[str, Any]:
    """
    Verify GSTIN using Appyflow API (no captcha required)
    Free tier: 50 requests lifetime
    """
    if not APPYFLOW_API_KEY:
        return {
            "success": False,
            "error": "Appyflow API key not configured. Please add APPYFLOW_GST_KEY to environment.",
            "needs_captcha": True
        }
    
    try:
        response = requests.get(
            APPYFLOW_API_URL,
            params={
                "gstNo": gstin.upper(),
                "key_secret": APPYFLOW_API_KEY
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for API errors
            if data.get("error") or not data.get("taxpayerInfo"):
                return {
                    "success": False,
                    "error": data.get("message", "Invalid GSTIN or API error"),
                    "needs_captcha": True
                }
            
            # Parse the response
            taxpayer = data.get("taxpayerInfo", {})
            address_info = taxpayer.get("pradr", {}).get("addr", {})
            
            return {
                "success": True,
                "data": {
                    "gstin": taxpayer.get("gstin", gstin),
                    "legal_name": taxpayer.get("lgnm", ""),
                    "trade_name": taxpayer.get("tradeNam", ""),
                    "status": taxpayer.get("sts", ""),
                    "registration_date": taxpayer.get("rgdt", ""),
                    "cancellation_date": taxpayer.get("cxdt", ""),
                    "constitution_of_business": taxpayer.get("ctb", ""),
                    "taxpayer_type": taxpayer.get("dty", ""),
                    "state_jurisdiction": taxpayer.get("stj", ""),
                    "center_jurisdiction": taxpayer.get("ctj", ""),
                    "nature_of_business": taxpayer.get("nba", []),
                    "address": {
                        "full": format_address(address_info),
                        "building": address_info.get("bno", ""),
                        "street": address_info.get("st", ""),
                        "locality": address_info.get("loc", ""),
                        "city": address_info.get("dst", ""),
                        "state": address_info.get("stcd", ""),
                        "pincode": address_info.get("pncd", "")
                    }
                }
            }
        else:
            return {
                "success": False,
                "error": f"API returned status {response.status_code}",
                "needs_captcha": True
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "needs_captcha": True
        }


def format_address(addr: Dict) -> str:
    """Format address components into a single string"""
    parts = []
    if addr.get("bno"):
        parts.append(addr["bno"])
    if addr.get("flno"):
        parts.append(f"Floor {addr['flno']}")
    if addr.get("bnm"):
        parts.append(addr["bnm"])
    if addr.get("st"):
        parts.append(addr["st"])
    if addr.get("loc"):
        parts.append(addr["loc"])
    if addr.get("dst"):
        parts.append(addr["dst"])
    if addr.get("stcd"):
        parts.append(addr["stcd"])
    if addr.get("pncd"):
        parts.append(f"- {addr['pncd']}")
    
    return ", ".join(parts) if parts else ""


def get_captcha() -> Dict[str, Any]:
    """
    Get captcha image from GST portal
    Returns session_id and base64 encoded captcha image
    NOTE: This often fails due to GST portal bot detection
    """
    session_id = str(uuid.uuid4())
    session = requests.Session()
    
    try:
        # First visit the search page to get cookies
        session.get(
            "https://services.gst.gov.in/services/searchtp",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            timeout=30
        )
        
        # Get the captcha
        response = session.get(
            GST_CAPTCHA_URL,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://services.gst.gov.in/services/searchtp',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'image',
                'sec-fetch-mode': 'no-cors',
                'sec-fetch-site': 'same-origin',
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.content
            
            # Check if we got HTML instead of image (bot detection)
            if b'<!DOCTYPE' in content or b'<html' in content:
                return {
                    "success": False,
                    "error": "GST portal blocked the request. Please use GSTIN direct lookup instead.",
                    "blocked": True
                }
            
            # Store session for later use
            gst_sessions[session_id] = session
            
            # Get captcha as base64
            captcha_base64 = base64.b64encode(content).decode('utf-8')
            
            return {
                "success": True,
                "session_id": session_id,
                "captcha_image": f"data:image/png;base64,{captcha_base64}"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to fetch captcha: {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def verify_gstin(session_id: str, gstin: str, captcha: str) -> Dict[str, Any]:
    """
    Verify GSTIN using the captcha solution
    Returns taxpayer details from GST portal
    """
    session = gst_sessions.get(session_id)
    
    if not session:
        return {
            "success": False,
            "error": "Invalid or expired session. Please request a new captcha."
        }
    
    try:
        # Make the search request
        response = session.post(
            GST_SEARCH_URL,
            json={
                "gstin": gstin.upper(),
                "captcha": captcha
            },
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Referer': 'https://services.gst.gov.in/services/searchtp'
            },
            timeout=30
        )
        
        # Clean up session
        if session_id in gst_sessions:
            del gst_sessions[session_id]
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for errors in response
            if 'error' in data or 'errorMessage' in data:
                return {
                    "success": False,
                    "error": data.get('error') or data.get('errorMessage', 'Invalid GSTIN or captcha')
                }
            
            # Parse and return the data
            return {
                "success": True,
                "data": parse_gst_response(data)
            }
        else:
            return {
                "success": False,
                "error": f"GST Portal returned error: {response.status_code}"
            }
            
    except Exception as e:
        # Clean up session on error
        if session_id in gst_sessions:
            del gst_sessions[session_id]
        return {
            "success": False,
            "error": str(e)
        }


def parse_gst_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse GST portal response into a clean format
    """
    # Extract address components
    address_obj = data.get('pradr', {})
    address = address_obj.get('adr', '') if isinstance(address_obj, dict) else ''
    
    # Parse address into components
    address_parts = parse_address(address)
    
    return {
        "gstin": data.get('gstin', ''),
        "legal_name": data.get('lgnm', ''),
        "trade_name": data.get('tradeNam', ''),
        "status": data.get('sts', ''),
        "registration_date": data.get('rgdt', ''),
        "cancellation_date": data.get('cxdt', ''),
        "constitution_of_business": data.get('ctb', ''),
        "taxpayer_type": data.get('dty', ''),
        "state_jurisdiction": data.get('stj', ''),
        "center_jurisdiction": data.get('ctj', ''),
        "einvoice_status": data.get('einvoiceStatus', ''),
        "aadhaar_verified": data.get('adhrVFlag', ''),
        "ekyc_verified": data.get('ekycVFlag', ''),
        "nature_of_business": data.get('nba', []),
        "address": {
            "full": address,
            **address_parts
        }
    }


def parse_address(address: str) -> Dict[str, str]:
    """
    Try to parse address string into components
    This is a best-effort parsing since GST addresses vary in format
    """
    result = {
        "street": "",
        "city": "",
        "state": "",
        "pincode": ""
    }
    
    if not address:
        return result
    
    # Try to extract pincode (6 digit number)
    import re
    pincode_match = re.search(r'\b(\d{6})\b', address)
    if pincode_match:
        result["pincode"] = pincode_match.group(1)
    
    # Common Indian states
    states = [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
        'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
        'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
        'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Puducherry', 'Chandigarh',
        'Andaman and Nicobar', 'Dadra and Nagar Haveli', 'Daman and Diu', 'Lakshadweep'
    ]
    
    address_upper = address.upper()
    for state in states:
        if state.upper() in address_upper:
            result["state"] = state
            break
    
    # The rest is street/city - simplified parsing
    parts = address.split(',')
    if len(parts) >= 2:
        result["street"] = ', '.join(parts[:-2]).strip() if len(parts) > 2 else parts[0].strip()
        result["city"] = parts[-2].strip() if len(parts) > 1 else ''
    else:
        result["street"] = address
    
    return result


def validate_gstin_format(gstin: str) -> bool:
    """
    Validate GSTIN format (basic validation)
    Format: 2 digit state code + 10 char PAN + 1 entity code + 1 check digit
    Example: 27AAACE8661R1Z5
    """
    import re
    if not gstin or len(gstin) != 15:
        return False
    
    # Basic pattern check
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}[Z]{1}[A-Z0-9]{1}$'
    return bool(re.match(pattern, gstin.upper()))


def get_state_from_gstin(gstin: str) -> Optional[str]:
    """
    Extract state from GSTIN (first 2 digits are state code)
    """
    state_codes = {
        '01': 'Jammu and Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab',
        '04': 'Chandigarh', '05': 'Uttarakhand', '06': 'Haryana',
        '07': 'Delhi', '08': 'Rajasthan', '09': 'Uttar Pradesh',
        '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh',
        '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram',
        '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam',
        '19': 'West Bengal', '20': 'Jharkhand', '21': 'Odisha',
        '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
        '25': 'Daman and Diu', '26': 'Dadra and Nagar Haveli',
        '27': 'Maharashtra', '28': 'Andhra Pradesh', '29': 'Karnataka',
        '30': 'Goa', '31': 'Lakshadweep', '32': 'Kerala',
        '33': 'Tamil Nadu', '34': 'Puducherry', '35': 'Andaman and Nicobar',
        '36': 'Telangana', '37': 'Andhra Pradesh (New)', '38': 'Ladakh'
    }
    
    if gstin and len(gstin) >= 2:
        return state_codes.get(gstin[:2])
    return None

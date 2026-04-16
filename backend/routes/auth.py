"""Auth Routes — Login, Register, OTP, Forgot Password, Push Notifications"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from routes import (db, get_current_user, require_role, verify_password, get_password_hash,
                    create_access_token, get_ist_now, utc_to_ist, IST, pwd_context, 
                    SECRET_KEY, ALGORITHM, GMAIL_USER, GMAIL_APP_PASSWORD,
                    ADMIN_REGISTRATION_EMAILS, ADMIN_RFQ_EMAILS, ROOT_DIR,
                    generate_customer_code, Token, UserRegister, UserLogin, UserRole,
                    get_convero_logo_base64)
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
import base64
import random
import string
import logging

router = APIRouter()

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
    gst_number: str  # Required GSTIN field
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
    gst_number: str  # Required GSTIN field
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
                <div style="font-size: 10px; color: #960018; font-weight: 600;">Code: {product.get('product_id', '')}</div>
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
                    <div style="font-size:9px;color:#960018;font-weight:600">Code: {product.get('product_id', '')}</div>
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
        pdf.cell(37, 7, str(product.get('product_id', 'N/A'))[:22], border=1, align='C')
        pdf.cell(50, 7, str(product.get('product_name', 'N/A'))[:28], border=1)
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

@router.post("/auth/send-otp")
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

class AdminRequest(BaseModel):
    email: EmailStr
    name: str
    mobile: str
    pincode: str
    city: str
    state: str
    company: str
    designation: Optional[str] = None
    password: str

@router.post("/auth/request-admin")
async def request_admin_account(request: AdminRequest):
    """Request admin account - sends approval email to info@convero.in"""
    
    # Check if email already registered
    existing_user = await db.users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if there's a pending request
    existing_request = await db.admin_requests.find_one({
        "email": request.email,
        "status": "pending"
    })
    if existing_request:
        raise HTTPException(status_code=400, detail="You already have a pending admin request")
    
    # Hash password
    hashed_password = get_password_hash(request.password)
    
    # Generate approval token
    import secrets
    approval_token = secrets.token_urlsafe(32)
    
    # Store the request in database
    request_doc = {
        "email": request.email,
        "name": request.name,
        "mobile": request.mobile,
        "pincode": request.pincode,
        "city": request.city,
        "state": request.state,
        "company": request.company,
        "designation": request.designation,
        "hashed_password": hashed_password,
        "status": "pending",
        "approval_token": approval_token,
        "created_at": datetime.utcnow()
    }
    
    await db.admin_requests.insert_one(request_doc)
    
    # Send approval email to admin
    await send_admin_approval_request_email(request, approval_token)
    
    return {
        "message": "Admin registration request submitted successfully. You will be notified once approved.",
        "email": request.email
    }

async def send_admin_approval_request_email(request: AdminRequest, approval_token: str):
    """Send email to info@convero.in for admin approval"""
    try:
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        
        if not smtp_username or not smtp_password:
            logging.warning("SMTP credentials not configured, skipping admin approval email")
            return
        
        # Get the backend URL for approval link - MUST be set via environment variable
        backend_url = os.environ.get('BACKEND_URL')
        if not backend_url:
            backend_url = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '')
        if not backend_url:
            logging.error("BACKEND_URL environment variable not set")
            return
        approval_link = f"{backend_url}/api/auth/approve-admin/{approval_token}"
        reject_link = f"{backend_url}/api/auth/reject-admin/{approval_token}"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Admin Registration Request - {request.name}'
        msg['From'] = smtp_username
        msg['To'] = 'info@convero.in'
        
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #960018 0%, #6b0012 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #fff; padding: 20px; border: 1px solid #e0e0e0; }}
                .info-row {{ padding: 10px 0; border-bottom: 1px solid #f0f0f0; }}
                .label {{ font-weight: bold; color: #666; }}
                .value {{ color: #333; }}
                .btn {{ display: inline-block; padding: 12px 24px; margin: 10px 5px; border-radius: 6px; text-decoration: none; font-weight: bold; }}
                .btn-approve {{ background: #059669; color: white; }}
                .btn-reject {{ background: #DC2626; color: white; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>New Admin Registration Request</h2>
                </div>
                <div class="content">
                    <p>A new admin account registration request has been submitted:</p>
                    
                    <div class="info-row">
                        <span class="label">Name:</span>
                        <span class="value">{request.name}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Email:</span>
                        <span class="value">{request.email}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Mobile:</span>
                        <span class="value">{request.mobile}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Company:</span>
                        <span class="value">{request.company}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Designation:</span>
                        <span class="value">{request.designation or 'Not specified'}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Location:</span>
                        <span class="value">{request.city}, {request.state} - {request.pincode}</span>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{approval_link}" class="btn btn-approve">Approve</a>
                        <a href="{reject_link}" class="btn btn-reject">Reject</a>
                    </div>
                </div>
                <div class="footer">
                    <p>Convero Solutions - Roller Calculator App</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, 'info@convero.in', msg.as_string())
        
        logging.info(f"Admin approval request email sent for: {request.email}")
        
    except Exception as e:
        logging.error(f"Error sending admin approval email: {e}")

@router.get("/auth/approve-admin/{token}")
async def approve_admin_request(token: str):
    """Approve admin registration request"""
    
    # Find the request
    request = await db.admin_requests.find_one({
        "approval_token": token,
        "status": "pending"
    })
    
    if not request:
        return Response(
            content="<html><body style='font-family:Arial;text-align:center;padding:50px;'><h2>Invalid or expired approval link</h2><p>This request may have already been processed.</p></body></html>",
            media_type="text/html"
        )
    
    # Create the admin user
    user_dict = {
        "email": request["email"],
        "name": request["name"],
        "company": request["company"],
        "designation": request.get("designation"),
        "mobile": request["mobile"],
        "pincode": request["pincode"],
        "city": request["city"],
        "state": request["state"],
        "role": UserRole.ADMIN,
        "hashed_password": request["hashed_password"],
        "created_at": datetime.utcnow(),
        "email_verified": True
    }
    
    await db.users.insert_one(user_dict)
    
    # Update request status
    await db.admin_requests.update_one(
        {"_id": request["_id"]},
        {"$set": {"status": "approved", "approved_at": datetime.utcnow()}}
    )
    
    # Send approval notification to user
    await send_admin_approved_email(request["email"], request["name"])
    
    logging.info(f"Admin account approved: {request['email']}")
    
    return Response(
        content=f'''
        <html>
        <body style="font-family:Arial;text-align:center;padding:50px;background:#f8f9fa;">
            <div style="max-width:400px;margin:0 auto;background:white;padding:40px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
                <div style="width:60px;height:60px;background:#059669;border-radius:50%;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;">
                    <span style="color:white;font-size:30px;">✓</span>
                </div>
                <h2 style="color:#059669;">Admin Approved!</h2>
                <p style="color:#666;">{request["name"]}'s admin account has been approved.</p>
                <p style="color:#888;font-size:14px;">They will receive an email notification.</p>
            </div>
        </body>
        </html>
        ''',
        media_type="text/html"
    )

@router.get("/auth/reject-admin/{token}")
async def reject_admin_request(token: str):
    """Reject admin registration request"""
    
    # Find the request
    request = await db.admin_requests.find_one({
        "approval_token": token,
        "status": "pending"
    })
    
    if not request:
        return Response(
            content="<html><body style='font-family:Arial;text-align:center;padding:50px;'><h2>Invalid or expired link</h2><p>This request may have already been processed.</p></body></html>",
            media_type="text/html"
        )
    
    # Update request status
    await db.admin_requests.update_one(
        {"_id": request["_id"]},
        {"$set": {"status": "rejected", "rejected_at": datetime.utcnow()}}
    )
    
    # Send rejection notification to user
    await send_admin_rejected_email(request["email"], request["name"])
    
    logging.info(f"Admin request rejected: {request['email']}")
    
    return Response(
        content=f'''
        <html>
        <body style="font-family:Arial;text-align:center;padding:50px;background:#f8f9fa;">
            <div style="max-width:400px;margin:0 auto;background:white;padding:40px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
                <div style="width:60px;height:60px;background:#DC2626;border-radius:50%;margin:0 auto 20px;display:flex;align-items:center;justify-content:center;">
                    <span style="color:white;font-size:30px;">✕</span>
                </div>
                <h2 style="color:#DC2626;">Request Rejected</h2>
                <p style="color:#666;">{request["name"]}'s admin request has been rejected.</p>
                <p style="color:#888;font-size:14px;">They will receive an email notification.</p>
            </div>
        </body>
        </html>
        ''',
        media_type="text/html"
    )

async def send_admin_approved_email(email: str, name: str):
    """Send email to user that their admin account has been approved"""
    try:
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        
        if not smtp_username or not smtp_password:
            return
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Admin Account Has Been Approved - Roller Calculator'
        msg['From'] = smtp_username
        msg['To'] = email
        
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #059669; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Account Approved!</h2>
                </div>
                <div class="content">
                    <p>Hello {name},</p>
                    <p>Your admin account request for Roller Calculator has been approved.</p>
                    <p>You can now log in with your email and password to access admin features.</p>
                    <p style="margin-top: 30px;"><strong>Welcome to Convero!</strong></p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, email, msg.as_string())
        
    except Exception as e:
        logging.error(f"Error sending admin approved email: {e}")

async def send_admin_rejected_email(email: str, name: str):
    """Send email to user that their admin request has been rejected"""
    try:
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        
        if not smtp_username or not smtp_password:
            return
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Admin Account Request Update - Roller Calculator'
        msg['From'] = smtp_username
        msg['To'] = email
        
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #6b7280; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #fff; padding: 30px; border: 1px solid #e0e0e0; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Request Update</h2>
                </div>
                <div class="content">
                    <p>Hello {name},</p>
                    <p>Your admin account request for Roller Calculator could not be approved at this time.</p>
                    <p>If you believe this is an error, please contact us at info@convero.in.</p>
                    <p>You can still register as a customer to browse products and submit quotes.</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, email, msg.as_string())
        
    except Exception as e:
        logging.error(f"Error sending admin rejected email: {e}")

@router.post("/auth/verify-otp", response_model=Token)
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
        "gst_number": request.gst_number,
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
        "gstin": request.gst_number,
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

@router.post("/auth/resend-otp")
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

@router.post("/auth/register", response_model=Token)
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

@router.post("/auth/login", response_model=Token)
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

@router.get("/auth/me")
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

@router.post("/auth/forgot-password")
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

@router.post("/auth/reset-password")
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

@router.post("/users/push-token")
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

@router.delete("/users/push-token")
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

@router.delete("/account/delete")
async def delete_account(current_user: dict = Depends(get_current_user)):
    """Delete the current user's account and all associated data"""
    try:
        user_email = current_user["email"]
        user_role = current_user.get("role")
        
        # Prevent admin from deleting their own account if they're the only admin
        if user_role == "admin":
            admin_count = await db.users.count_documents({"role": "admin"})
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot delete the only admin account. Please create another admin first."
                )
        
        # Delete user's quotes if they're a customer
        if user_role == "customer":
            # Get customer record
            customer = await db.customers.find_one({"email": user_email})
            if customer:
                customer_id = str(customer["_id"])
                # Delete associated quotes
                await db.quotes.delete_many({"customer_id": customer_id})
                # Delete customer record
                await db.customers.delete_one({"email": user_email})
        
        # Delete the user account
        result = await db.users.delete_one({"email": user_email})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        logging.info(f"Account deleted successfully: {user_email}")
        return {"message": "Account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting account: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")

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


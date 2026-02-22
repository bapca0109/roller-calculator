# Belt Conveyor Roller Price Calculator - PRD

## Original Problem Statement
Create a mobile application to calculate the price of belt conveyor rollers, functioning as a comprehensive engineering and quoting tool with complex pricing logic, freight, value-based discounts, GST, a multi-product quote builder, PDF exports, and company branding.

## Core Features

### Pricing & Calculation
- Calculate prices for Standard (Carrying) and Impact belt conveyor rollers
- Formula: `(Total Raw Material Cost) * 1.32 (layout) * 1.60 (profit)`
- Value-based discounts (5% to 35%) based on order value
- Packing charges: Standard (1%), Pallet (4%), Wooden Box (8%)
- Freight calculation based on distance from dispatch pincode (382433)
- GST: CGST/SGST (9% each) for Gujarat, IGST (18%) for other states

### Quoting System
- Multi-product quote builder
- Save and view quotes in dedicated "Quotes" tab
- Export quotes to PDF

### UI/UX
- Company logo ("CONVERO SOLUTIONS")
- Real-time form validation with inline error messages
- Mobile-first design with React Native/Expo

## What's Been Implemented

### Completed Features (Dec 2025)
- Full calculator with all roller configurations
- Value-based discount system
- GST calculation (CGST/SGST vs IGST)
- Freight calculation
- Multi-product quote builder
- Quote saving and viewing
- PDF export
- Company branding
- Form validation

### NEW: Search Tab - Product Catalog (Feb 2026)
- Search through available roller configurations (product range)
- Search by roller type (CR=Carrying, IR=Impact)
- Search by shaft diameter (20, 25, 30, 35, 40, 45, 50mm)
- Search by pipe diameter (60.8, 76.1, 88.9, 114.3mm, etc.)
- Search by bearing number (6204, 6205, 6305, etc.)
- Search by bearing make (SKF, FAG, China, Timken)
- Quick search buttons for common searches
- Shows base price for 1000mm length
- "Configure" button to go to calculator with specs

## Architecture

### Backend (FastAPI)
- `/app/backend/server.py` - Main API endpoints
- `/app/backend/roller_standards.py` - Pricing data (hardcoded)
- `/app/backend/export_raw_materials.py` - Excel export

### Frontend (Expo/React Native)
- `/app/frontend/app/(tabs)/calculator.tsx` - Main calculator
- `/app/frontend/app/(tabs)/search.tsx` - **NEW** Search by product code
- `/app/frontend/app/(tabs)/quotes.tsx` - Quote listing
- `/app/frontend/app/(tabs)/profile.tsx` - User profile

### Key API Endpoints
- `POST /api/calculate-detailed-cost` - Calculate roller price
- `POST /api/quotes/roller` - Save quote
- `GET /api/quotes` - List quotes
- `GET /api/search/product-code?query=CR` - **NEW** Search by product code
- `GET /api/download/raw-materials-pricing` - Excel export

## Database Schema (MongoDB)
- **users**: `{email, name, company, role, hashed_password}`
- **quotes**: `{customer_id, products[], pricing_details, status, created_at}`

## Prioritized Backlog

### P0 - Critical
1. **Admin Panel for Price Management** - Migrate hardcoded prices to MongoDB with CRUD admin interface

### P1 - High Priority
2. Customer Management - Save customer details with quotes

### P2 - Medium Priority
3. Quote Approval Workflow - Status system (Pending/Approved/Rejected)
4. Email Integration - Send PDF quotes to customers

### P3 - Low Priority
5. Dashboard & Analytics - Sales analytics and reporting

## Technical Notes
- All pricing data is currently hardcoded in `roller_standards.py`
- Expo tunnel can be unstable - restart with `sudo supervisorctl restart expo`
- Uses external API `api.postalpincode.in` for location data

## Test Credentials
- Create new users via Sign Up on login page
- Test user: `testuser@example.com` / `test123`

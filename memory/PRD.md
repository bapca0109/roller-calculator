# Belt Conveyor Roller Price Calculator - PRD

## Original Problem Statement
Mobile application to calculate the price of belt conveyor rollers, functioning as a comprehensive engineering and quoting tool with complex pricing logic, freight, value-based discounts, GST, multi-product quote builder, PDF exports, and company branding.

## Core Features Implemented

### 1. Roller Types (3 types)
- **Carrying (CR)** - Standard carrying rollers for 3-roll troughed idlers
- **Impact (IR)** - Impact rollers with rubber lagging
- **Return (RR)** - Return idler rollers (single piece & 2-piece)

### 2. IS-8598:2019 Standard Pipe Lengths

**Carrying Idler Pipe Lengths (3-roll troughed):**
| Belt Width | Pipe Length |
|------------|-------------|
| 500mm | 200mm |
| 650mm | 250mm |
| 800mm | 315mm |
| 1000mm | 380mm |
| 1200mm | 465mm |
| 1400mm | 530mm |
| 1600mm | 600mm |
| 1800mm | 670mm |
| 2000mm | 750mm |

**Return Idler Lengths:**
| Belt Width | Single Piece | 2-Piece (each) |
|------------|--------------|----------------|
| 500mm | 600mm | 250mm |
| 650mm | 750mm | 380mm |
| 800mm | 950mm | 465mm |
| 1000mm | 1150mm | 600mm |
| 1200mm | 1400mm | 700mm |
| 1400mm | 1600mm | 800mm |
| 1600mm | 1800mm | 900mm |
| 1800mm | 2000mm | 1000mm |
| 2000mm | 2200mm | 1100mm |

### 3. Pipe Diameter Codes (IS-9295)
| Actual OD | Display Code |
|-----------|--------------|
| 60.8mm | 60 |
| 76.1mm | 76 |
| 88.9mm | 89 |
| 114.3mm | 114 |
| 127.0mm | 127 |
| 139.7mm | 139 |
| 152.4mm | 152 |
| 159.0mm | 159 |
| 165.0mm | 165 |

### 4. Product Code Format
`{TYPE}{SHAFT} {PIPE} {LENGTH}{PIPE_TYPE} {SERIES}{MAKE}`

Examples:
- `CR20 89 200A 62S` - Carrying roller, 20mm shaft, 89mm pipe, 200mm length, Type A, 62 series, SKF
- `RR25 114 700 62F` - Return roller, 25mm shaft, 114mm pipe, 700mm length, 62 series, FAG

### 5. Search Functionality
- Partial search: `CR20`, `89`, `CR20 89`
- With length: `CR20 89 200`, `RR25 114 700`
- Without bearing make: `CR25 139 600 62`
- Full exact codes: `CR20 89 200A 62S`

### 6. Pricing Formula
`(Total Raw Material Cost) × 1.32 (layout) × 1.60 (profit)`

### 7. Additional Features
- Value-based discounts (5% to 35%)
- Packing charges (Optional)
- Freight (distance-based via pincode)
- GST calculation (CGST/SGST intra-state, IGST inter-state)
- Multi-product quote builder
- PDF export
- Company branding (CONVERO SOLUTIONS)

## Tech Stack
- **Frontend**: React Native, Expo, Expo Router, TypeScript
- **Backend**: FastAPI, Python
- **Database**: MongoDB

## Key Files
- `/app/backend/roller_standards.py` - All roller specifications and pricing data
- `/app/backend/server.py` - API endpoints including search
- `/app/frontend/app/(tabs)/calculator.tsx` - Calculator UI with 3 roller types
- `/app/frontend/app/(tabs)/search.tsx` - Product search UI

## API Endpoints
- `GET /api/products/search` - Search product catalog
- `POST /api/calculate-detailed-cost` - Calculate roller price
- `POST /api/quotes/roller` - Save quote
- `GET /api/quotes` - Fetch user quotes
- `GET /api/roller-options` - Get dropdown options

## Pending Tasks
1. ~~**Admin Panel** - Migrate hardcoded prices to MongoDB with CRUD UI~~ ✅ COMPLETED
2. ~~**Customer Management** - Save customer details with quotes~~ ✅ COMPLETED
3. ~~**Print Customer Data in Quotes** - Render customer details on quote PDF~~ ✅ COMPLETED
4. ~~**Formula-Based Pipe Weights** - Calculate pipe weights using engineering formula~~ ✅ COMPLETED (Feb 2026)
5. **Full Data Migration to DB** - Migrate hardcoded product data from roller_standards.py to MongoDB (P1)
6. **Quote Approval Workflow** - Status system (Pending/Approved/Rejected) (P2)
7. **Email Integration** - Email quote PDFs (P2)
8. **Dashboard & Analytics** - Sales analytics (P3)

## Recently Completed (Feb 2026)

### GST Verification Feature ✅ (NEW)
- Quick GSTIN search - checks database first for existing customers
- GSTIN format validation with state code extraction
- Features:
  - `GET /api/customers/search/gstin/{gstin}` - Quick search existing customers
  - `GET /api/gst/validate/{gstin}` - Validate GSTIN format + extract state
- Available in:
  - Customers tab: "GST" button for lookup  
  - Calculator: "Fetch from GSTIN" in customer picker
- Flow:
  1. User enters GSTIN (15 chars)
  2. System immediately searches database for existing customer
  3. If found: Shows green "Customer Found!" card with option to select/edit
  4. If not found: Shows option to add customer manually with GSTIN pre-filled
- Note: GST portal auto-fetch is disabled due to bot detection. Users manually enter customer details.

### Admin Panel for Price Management ✅
- Full CRUD UI for managing raw material prices
- Prices stored in `custom_prices` collection in MongoDB
- Admin-only access (role-based)
- API endpoints: `GET/POST /api/admin/prices/*`

### Customer Management System ✅
- Full CRUD for customers (`/api/customers` endpoints)
- Customer model: name, company, email, phone, address, city, state, pincode, gst_number, notes
- Customers tab in app with search functionality
- Customer selector dropdown in calculator before saving quotes
- Customer details (customer_details field) saved with roller quotes

### UI Updates ✅
- Applied carmine red theme (#960018) across all pages
- Removed non-functional "Configure" button from Search tab
- Added "Return" as third roller type in calculator

## Test Credentials
- Email: `test@test.com`
- Password: `test123`
- Role: `admin`

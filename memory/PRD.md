# Roller Price Calculator - Product Requirements Document

## Original Problem Statement
Mobile application to calculate the price of belt conveyor rollers, serving as an engineering and quoting tool. Features include product catalog search, full admin panel for price management, customer database for quote association, GSTIN lookup, and engineering drawing generation.

## Target Audience
Sales teams, engineers, and industrial professionals in the conveyor equipment industry.

## Tech Stack
- **Frontend**: React Native (Expo), TypeScript
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **PDF Generation**: fpdf2 with Pillow
- **Email**: Python smtplib with Gmail SMTP

## Core Features

### 1. Roller Price Calculator
- Calculate prices for Carrying, Impact, and Return belt conveyor rollers
- Selectable shaft end types (A/B/C/Custom)
- Role-based cost breakdown visibility (admin only)
- Editable custom discount feature

### 2. Product Catalog Search
- Search by partial terms or full codes
- Display roller length, weight, belt width, and price
- Quick search filters (CR, IR, 25, 30, etc.)
- Add items to quote directly from results
- Email and PDF download for search results

### 3. Quote Management
- Associate quotes with customers
- Edit quantity and discount
- GST calculation and display
- Print customer details on final quote PDF

### 4. Customer Management
- CRUD operations for customer information
- GSTIN lookup from local database

### 5. Admin Panel
- Secure interface for managing raw material prices
- Read-only standards view
- Excel export of raw material costs

### 6. Engineering Drawings
- Generate PDF engineering drawings for any roller configuration
- Email drawing feature as alternative to direct download

## UI/UX Design

### Design System (Updated March 2026)
- **Style**: Corporate Professional
- **Primary Color**: Carmine Red (#960018)
- **Dark Accent**: Slate (#1E293B)
- **Background**: Light Slate (#F8FAFC)
- **Typography**: Clean, professional with uppercase section labels
- **Cards**: White backgrounds with subtle shadows and borders

### Key Visual Elements
- Dark slate headers with white text
- Professional card layouts with proper spacing
- Carmine red accent for prices and CTAs
- Green/Blue/Orange tags for roller type identification
- Improved tab bar with better active state indication

## Completed Work

### March 2026
- **UI/UX Redesign**: Applied professional corporate look to Calculator and Search screens
  - Updated color palette (Carmine Red + Slate)
  - Improved typography with uppercase section labels
  - Enhanced card designs with better shadows and borders
  - Professional tab bar styling
  - Login page styling improvements

### Previous Sessions
- Fixed core price calculation bug (now data-driven from MongoDB)
- Admin panel UX improvement (read-only standards)
- Fixed price reset functionality
- Search functionality with Add to Quote
- Email drawing feature
- Quote editing (quantity/discount)
- GST display in quotes
- Role-based access control for cost breakdown
- Logout functionality fix

## Known Issues

### P1 - In Progress
1. **Expo Tunnel Instability** (ERR_NGROK_3200) - Environmental issue, use web preview as workaround
2. **PDF Download on iOS** - Native share/download not working in Expo Go; workarounds available (browser tab, email)

### P0 - Pending Verification
1. **Email Button in Search Actions** - Added but needs user verification

## Security Considerations
- **CRITICAL**: Email SMTP credentials are hardcoded in `backend/server.py` - Should be moved to environment variables

## Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123
- **Email Account**: info@convero.in (App password configured)

## API Endpoints

### Authentication
- `POST /api/auth/login`
- `POST /api/auth/register`

### Pricing
- `POST /api/admin/prices/reset`
- `PUT /api/admin/prices/update`
- `GET /api/admin/prices`

### Quotes
- `GET /api/quotes`
- `POST /api/quotes`
- `PUT /api/quotes/{quote_id}`

### Search
- `GET /api/search/product-catalog?query=`

### Drawings
- `POST /api/email-drawing`
- `GET /api/generate-drawing-download/{product_code}`

## File Structure
```
/app
├── backend/
│   ├── server.py (main API endpoints)
│   ├── roller_standards.py (calculation logic)
│   ├── drawing_generator.py (PDF generation)
│   └── price_loader.py (cached price lookups)
├── frontend/
│   ├── app/
│   │   ├── (tabs)/ (main screens)
│   │   └── auth/ (login/register)
│   ├── constants/
│   │   └── Colors.ts (design tokens)
│   └── contexts/
└── memory/
    └── PRD.md
```

## Upcoming Tasks

### P0 - Critical
1. Move hardcoded SMTP credentials to .env file

### P1 - Important
1. User acceptance testing for Quote Editing
2. User acceptance testing for Custom Discounts
3. Verify Email button visibility in all contexts

### P2 - Future
1. Quote Approval Workflow (Pending/Approved/Rejected)
2. Dashboard & Analytics
3. Update Raw Material Costs from Excel import

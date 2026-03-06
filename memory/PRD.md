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

### 7. User Authentication (NEW - March 2026)
- **OTP-based Email Verification** for customer signup
  - 4-digit OTP sent to email
  - 10-minute expiry time
  - Resend OTP with 60-second cooldown
  - Professional email template with Convero branding
- JWT-based authentication for login
- Role-based access control (Admin, Sales, Customer)

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

### March 6, 2026 (Latest Session)
- **Dashboard Export to PDF/Excel** - COMPLETED
  - Added PDF and Excel export buttons to Dashboard header
  - PDF report: Summary metrics, Top Customers table, Recent Quotes table
  - Excel report: 4 sheets (Summary, Top Customers, Recent Quotes, Roller Types)
  - Professional formatting with company branding (Carmine Red theme)
  - Download functionality working on web

- **Dashboard & Analytics** - COMPLETED
  - Created new Dashboard tab (admin-only)
  - Summary cards: Total Revenue, Total Quotes, Customers, Conversion Rate
  - Revenue Trend line chart (6 months)
  - Monthly Quotes bar chart
  - Quote Status pie chart (Approved vs Pending)
  - Top Customers by Revenue list
  - Roller Type Distribution with progress bars
  - Recent Quotes activity list
  - Pull-to-refresh functionality
  - Backend analytics APIs: dashboard summary, revenue trend, top customers, quote status, roller distribution

- **Forgot Password Feature** - COMPLETED
  - Added "Forgot Password?" link on login page
  - Created forgot-password screen with 3-step flow: Email → OTP → Success
  - Backend endpoints: `/api/auth/forgot-password` and `/api/auth/reset-password`
  - OTP sent via email with 10-minute expiry
  - Password reset with validation (min 6 chars)
  - Cooldown timer for OTP resend (60 seconds)

- **RFQ Tab Rename** - COMPLETED
  - Changed "Pending RFQ" to "RFQ" in quotes tab

- **iOS/Android Fixes** - COMPLETED  
  - Fixed approval popup not working (replaced `window.confirm` with `Alert.alert`)
  - Fixed logout crash (added navigation delay)
  - Shaft end type now defaults to 'A'

- **Auto-logout Feature** - COMPLETED
  - Customers auto-logout after 7 days of inactivity
  - Activity tracking stored in AsyncStorage
  - Checked on app load and when app returns from background

- **RFQ Approval Success Popup** - COMPLETED
  - Added success popup modal that appears when admin clicks "Approve & Generate Quote"
  - Popup displays: green checkmark, "Approved & Submitted!" title, new quote number, "View Approved Quotes" button
  - Clicking "View Approved Quotes" automatically switches to the Approved tab
  - Approved RFQs are automatically moved from "RFQ" tab to "Approved" tab
  - Testing agent verified 100% success rate across all 7 test scenarios

### March 2, 2026 (Previous Session)
- **CRITICAL FIX: Authentication Race Condition** - Resolved the recurring bug where components rendered before auth state was fully loaded
  - Root Layout (`_layout.tsx`): Added splash screen that blocks navigation until auth loading completes
  - AuthContext: Enhanced with detailed logging, proper state management, `isAuthenticated` flag, and `refreshUser` method
  - This fix ensures `isCustomer` and `isAdmin` always evaluate correctly before dependent components render
  
- **Attachment Download Feature Complete**:
  - Backend endpoints: `/api/quotes/{id}/attachments/{pIdx}/{aIdx}/download` (single) and `/api/quotes/{id}/attachments/download-all` (ZIP)
  - Frontend: Added authenticated download functions using `fetch` with Bearer token
  - UI: Added proper styling for attachments section, showing attachment icons and download buttons
  
- **Admin Portal Unified with Customer Portal**:
  - Attachments section now available for admin users (previously customer-only)
  - Admin gets popup flow after "Add to Quote" with "Add More" and "Generate Quote" options
  - Green "Generate Quote" button (#4CAF50) with success popup showing "Quote Generated!"
  - Admin retains all exclusive features: visible prices, Admin tab, Customer management, Quote approval/revision
  
- **Testing Agent Verification**: All tests passed (100% success rate across 2 test runs)
  - Iteration 6: Role-based UI tests (customer vs admin views)
  - Iteration 7: Admin portal changes (attachments, popup flow, green button, success popup)

### March 2026 (Previous Sessions)
- **RFQ Feature Complete**: Customer users now generate RFQ (Request for Quote) while Admin users generate Quotes
  - Backend: `generate_rfq_number()` creates `RFQ/YY-YY/XXXX` for customers
  - Backend: `generate_quote_number()` creates `Q/YY-YY/XXXX` for admins  
  - Frontend: Dynamic `docLabel` variable shows "RFQ" or "Quote" based on user role
  - PDF: Document title shows "REQUEST FOR QUOTATION" or "QUOTATION" based on quote_number prefix
  - Email notifications sent to admins when customers submit RFQs

- **Price Hiding for Customers**: Customer users cannot see prices in any screen
  - Calculator: Pricing, GST, Freight, Grand Total, and Configuration sections hidden
  - Search: Price column hidden, only product specs visible
  - Quotes: Price totals hidden in list view
  - "Calculate Price" button renamed to "Generate RFQ"

- **Customer RFQ Popup Flow**:
  - After clicking "Generate RFQ", a popup appears with two options:
    - "Add More Items" - add current item to RFQ and continue adding
    - "Submit RFQ" - submit the RFQ immediately
  - Bottom "Add to RFQ" and "Submit RFQ" buttons removed for customers
  - Product Configuration section hidden for customers

- **RFQ Approval Workflow**:
  - Admin sees filter tabs: All / Pending RFQ / Approved
  - Admin can click "Approve & Generate Quote" (RED button) on pending RFQs
  - After approval, shows "Approved" badge (GREEN)
  - Email sent to customer + info@convero.in + design@convero.in on approval
  - Approved quotes visible to both customer and admin

- **Security Fix**: Moved hardcoded admin emails to environment variables
  - `ADMIN_REGISTRATION_EMAILS` - Recipients for new customer registration alerts
  - `ADMIN_RFQ_EMAILS` - Recipients for new RFQ submissions

- **OTP-based Email Verification**: Implemented 4-digit OTP verification for customer signup
  - Backend: `/api/auth/send-otp`, `/api/auth/verify-otp`, `/api/auth/resend-otp` endpoints
  - Frontend: New verify-otp.tsx screen with 4-digit input boxes
  - Email: Professional HTML email template with OTP code
  - Features: 10-minute expiry, 60-second resend cooldown
  
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

### ✅ Resolved (March 2, 2026)
1. **Authentication Race Condition** - FIXED: Components no longer render before auth state is resolved. Splash screen blocks rendering until `loading=false`.

### P1 - In Progress
1. **Expo Tunnel Instability** (ERR_NGROK_3200) - Environmental issue, use web preview as workaround
2. **PDF Download on iOS** - Native share/download not working in Expo Go; workarounds available (browser tab, email)

### P2 - Minor
1. **Email Button in Search Actions** - Added but needs user verification

## API Endpoints

### Authentication
- `POST /api/auth/send-otp` - Send OTP for registration
- `POST /api/auth/verify-otp` - Verify OTP and create account
- `POST /api/auth/resend-otp` - Resend OTP with cooldown
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - Direct registration (legacy)

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
│   ├── server.py (main API endpoints including OTP)
│   ├── roller_standards.py (calculation logic)
│   ├── drawing_generator.py (PDF generation)
│   └── price_loader.py (cached price lookups)
├── frontend/
│   ├── app/
│   │   ├── (tabs)/ (main screens)
│   │   └── auth/
│   │       ├── login.tsx
│   │       ├── register.tsx (updated with OTP flow)
│   │       └── verify-otp.tsx (NEW)
│   ├── constants/
│   │   └── Colors.ts (design tokens)
│   └── contexts/
└── memory/
    └── PRD.md
```

## Upcoming Tasks

### P1 - Important
1. User acceptance testing for RFQ flow (customer creates RFQ)
2. User acceptance testing for Quote Editing
3. Verify Email button visibility in all search contexts

### P2 - Future
1. Dashboard & Analytics
2. Update Raw Material Costs from Excel import
3. More quote statuses (Rejected, Processing)

## Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123
- **Email Account**: info@convero.in (App password in backend/.env)

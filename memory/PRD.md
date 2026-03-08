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

### March 8, 2026 (Latest Session - Current)
- **5 New Feature Requests** - COMPLETED ✅
  1. **Customer RFQ No. (Optional)**: Added optional reference field for customers in Calculator and Search tabs. Displays in emails and PDFs as "Customer Ref: XXX"
  2. **Hide Prices from Customers**: Prices hidden in Search tab for customers until RFQ is approved (unit price, line total, grand total all hidden)
  3. **Combined Cart**: Note - Search and Calculator still have separate carts. Would need shared context to combine (future task)
  4. **Removed "No Packing" Option**: Removed from packing type dropdown. Default is now "Standard (1%)"
  5. **Attachments Grouped by Product**: Admin email now shows "Attachments by Product" section with attachments listed under each product name

### March 7, 2026
- **Freight Charges Feature** - COMPLETED ✅
  - PDF now always shows Freight Charges row (0.0% if no pincode)
  - Admin Approve RFQ modal with freight options:
    - Toggle between "Freight %" and "Custom Amount" modes
    - Input freight percentage or enter custom amount
    - Real-time calculation of freight amount
    - "Approve & Convert to Quote" button saves freight and approves
  - Freight details stored in `freight_details` field (percent, amount, custom flag)

- **PDF Format Standardization** - COMPLETED ✅
  - ALL PDFs now use per-item discount format: SR. | ITEM CODE | QTY | RATE | DISC % | VALUE AFTER DISC | TOTAL
  - Uppercase headers to match exact export format
  - IST timestamp (converted from UTC)
  - Freight row always shown with percentage

- **Email PDF Matching Frontend PDF - FINAL FIX** - COMPLETED ✅
  - Root cause: `use_item_discounts` flag was not being passed to email functions
  - Fixed `send_quote_approval_email` call (line 3162) to include `use_item_discounts`
  - Fixed `send_quote_revision_email` call (line 3454) to include `use_item_discounts`
  - Testing agent verified 100% (16/16 tests passed):
    - Backend PDF HTML matches Frontend PDF HTML structurally
    - Table headers identical for both Total Discount and Per-Item Discount modes
    - CSS styles identical between backend and frontend
    - All customer fields properly included
  - This issue has been reported 3 times and is now definitively resolved

- **Per-Item Discounts Feature** - COMPLETED ✅
  - Added per-item discount capability with new PDF table format: Sr. No. | Item Code | Qty | Rate | Disc % | Value After Disc | Total
  - Admin can toggle between "Total Discount" and "Per-Item Discount" modes per quote
  - When Per-Item Discount enabled:
    - Each product has editable Discount % input
    - Total Discount input is hidden
    - Summary shows "Item Discounts (Total)" instead of percentage
    - **"Apply to All Items"** feature: Enter discount % and apply to all products at once
  - Backend updates:
    - `QuoteProduct` model: Added `item_discount_percent` field
    - `Quote` model: Added `use_item_discounts` boolean flag
    - `QuoteUpdate` model: Added `use_item_discounts` and `discount_percent` fields
    - `generate_quote_html`: Dynamic table header/format based on discount mode
  - Frontend updates:
    - Edit Quote modal with Discount Mode toggle
    - Per-product discount inputs with live total calculation
    - Bulk "Apply to All" discount feature
    - PDF generation respects discount mode
  - Testing: Backend 100% (9/9), Frontend verified with screenshots

- **Email PDF Matching Frontend PDF** - COMPLETED ✅
  - Fixed critical issue where PDFs attached to quote approval emails didn't match frontend-exported PDFs
  - Root causes identified and fixed:
    1. Quote Pydantic model was missing `customer_code`, `customer_company`, `original_rfq_number`, `approved_at`, `approved_by` fields
    2. `generate_quote_html` function didn't use `customer_company` when `customer_details` was None
    3. `send_quote_approval_email` and `send_quote_revision_email` weren't receiving complete quote data
    4. Bug fix: `customer_details = quote_data.get('customer_details') or {}` to handle explicit None values
  - All PDFs now contain: Customer Code (C0001), Company Name, Original RFQ Reference, Approval Date, Full Pricing Breakdown, T&Cs
  - Testing agent verified 100% success rate (9/9 tests passed)

- **Customer Codes Feature** - COMPLETED
  - Auto-generated customer codes (C0001, C0002, etc.) for all customers
  - Customer codes displayed in:
    1. Customers list with red badge
    2. Quotes list with red badge next to customer name
    3. RFQ and Quote PDFs (backend generated)
    4. Frontend Quote PDF exports
    5. Email templates (RFQ and Quote approval)
  - Migration endpoint to assign codes to existing customers and quotes
  - Customer codes stored in users, customers, and quotes collections

- **Quote Date Fix** - COMPLETED
  - Approved quotes now show the approval date (`approved_at`) instead of the RFQ creation date
  - Fixed in 3 locations:
    1. Quote card display - shows approval date for approved quotes
    2. Quote detail modal - shows "Approved: [date]" instead of "Created: [date]"
    3. PDF generation - uses approval date in the header
  - Testing agent verified 100% success rate

### March 6, 2026 (Previous Session)
- **RFQ Traceability in Quotes** - COMPLETED
  - Added original RFQ number reference in Quote PDF (e.g., "Ref: RFQ/25-26/0045")
  - RFQ reference shown in quote detail modal
  - RFQ reference displayed in quote card list view (in blue)
  - Enables tracking which RFQ was converted to which Quote

- **Professional Quote PDF Redesign** - COMPLETED
  - Clean, minimalist design with modern typography
  - Header: Logo, Document type, Quote number, Date
  - Info boxes: From (Convero) and Bill To (Customer) sections
  - Product table with specifications and remarks
  - Summary section aligned to right with clear breakdown
  - **Commercial Terms**: Payment (25% advance, 75% before dispatch), Freight, Color charges (2%), 30-day validity
  - **Technical Specs**: Pipe (IS-9295), Shaft (EN8), Bearing, Circlip (IS-3075), Housing (CRCA 3.15mm), Seal Set (Nylon-6), Rubber Ring (Shore 50-60), Painting (40 microns), TIR (1.6mm per IS-8598)
  - Footer with authorized signatory space
  - Print-optimized layout

- **Export Search Results Feature** - COMPLETED
  - **Quotes Tab**: Export button appears when searching, exports filtered quotes to CSV
  - **Customers Tab**: Export button in header, exports customer list to CSV
  - **Search Tab**: Export button appears when products found, exports product search results to CSV
  - All exports include relevant columns (name, company, status, price, date, etc.)
  - CSV format for easy import into Excel/Google Sheets

- **Quote Search Feature** - COMPLETED
  - Added search bar in Quotes tab (admin only)
  - Search by: quote number, customer name, company, email, phone, GST, city, state, product names, status
  - Real-time filtering with result count display
  - Clear button to reset search
  - Works across all tabs (All, RFQ, Approved)

- **Customer Quote Management** - COMPLETED
  - Customers automatically move to "Quoted" tab after receiving an approved quote
  - Admin can click on any customer to see all their quotes in a modal
  - "View Quotes" button shows on customers in the Quoted tab
  - Quote modal displays: quote number, status (Approved/Pending), amount, date, item count
  - Backend endpoint: GET /api/customers/{customer_id}/quotes

- **Dashboard Date Range Filters** - COMPLETED
  - Added filter pills: 7 Days, 30 Days, 3 Months, 6 Months, 1 Year, All Time
  - Dashboard data refreshes based on selected filter
  - Backend APIs updated to accept start_date and end_date parameters
  - Active filter highlighted in carmine red

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

### ✅ Resolved (March 7, 2026)
1. **Quote Date Display** - FIXED: Approved quotes now show approval date (`approved_at`) instead of RFQ creation date (`created_at`) in cards, modals, and PDFs.

### ✅ Resolved (March 2, 2026)
1. **Authentication Race Condition** - FIXED: Components no longer render before auth state is resolved. Splash screen blocks rendering until `loading=false`.

### P1 - Pending User Verification
1. **iOS Logout** - May still have issues. The fix (navigation delay) needs user verification on physical iOS device.

### P2 - Environmental/Known Limitations
1. **Expo Tunnel Instability** (ERR_NGROK_3200) - Environmental issue, use web preview as workaround
2. **PDF Download on iOS** - Native share/download not working in Expo Go; workarounds available (browser tab, email)

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

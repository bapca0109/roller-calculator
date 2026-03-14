# Belt Conveyor Roller Price Calculator - PRD

## Original Problem Statement
Create a mobile application to calculate the price of belt conveyor rollers, serving as an engineering and quoting tool with product catalog search, admin panel for price management, customer database, and complete quote/RFQ workflow.

## Architecture
```
/app
├── backend
│   ├── server.py           # FastAPI backend with MongoDB + Auto-freight calculation
│   ├── roller_standards.py # Pricing data & freight calculation logic
│   └── tests/              # Backend test files
└── frontend
    ├── app
    │   ├── auth/login.tsx      # REDESIGNED: Modern industrial login
    │   └── (tabs)
    │       ├── _layout.tsx     # Tab navigation (Products tab)
    │       ├── cart.tsx        # Shopping cart + Export button (REDESIGNED)
    │       ├── calculator.tsx  # Product calculator (REDESIGNED header)
    │       ├── quotes.tsx      # Quote management + Export (REDESIGNED header)
    │       ├── customers.tsx   # Customer management (REDESIGNED)
    │       ├── admin.tsx       # Admin panel (REDESIGNED)
    │       ├── profile.tsx     # User profile (REDESIGNED)
    │       ├── dashboard.tsx   # Admin dashboard (REDESIGNED)
    │       └── search.tsx      # Product search + Attachments (UPDATED)
    ├── components
    │   ├── quotes/             # Extracted quote components
    │   └── shared/
    │       └── ExportButtons.tsx  # Reusable export component
    └── theme/index.ts          # Design system theme (ENHANCED)
```

## What's Been Implemented

### Core Features (Previous Sessions)
- [x] Full-stack application setup with Expo + FastAPI + MongoDB
- [x] User authentication with OTP-based signup/login
- [x] Role-based access control (Admin vs Customer)
- [x] Product calculator for Carrying, Impact, and Return rollers
- [x] Customer management system with auto-incrementing codes
- [x] Quote/RFQ workflow with approval process
- [x] PDF generation for quotes with company logo and weight details
- [x] Email notifications for quote status changes
- [x] Export to PDF/Excel functionality
- [x] Tab renamed from "Calculator" to "Products"
- [x] Component refactoring (QuoteCard, modals extracted)
- [x] Push notifications for admins (requires APK build for testing)

### March 10, 2026 (Previous Session) - P0 Completions
- [x] **Search Tab Attachments**: Added Camera, Gallery, Document buttons to the "Add to Quote" modal in search.tsx
  - Attachment state management with reset on modal close
  - Proper base64 encoding for cart integration
  - Styles for attachment preview and removal
- [x] **Auto-Freight Calculation**: Implemented automatic freight calculation during RFQ approval
  - Calculates total weight from products
  - Uses delivery_location (pincode) to calculate distance
  - Auto-applies freight charges and updates total price
  - Returns `freight_auto_calculated` flag in API response
- [x] **Bug Fix**: Fixed NoneType error in approve_rfq when product.specifications is null

### December 9, 2025 (This Session) - Deployment Fix & Refactoring
- [x] **Fixed Deployment-Blocking Syntax Error**: Removed 14 instances of escaped template literal syntax (`\${...}` → `${...}`) in `frontend/app/(tabs)/quotes.tsx`
  - Lines 1605-1608: Header doc-type section
  - Lines 1644-1660: Customer info section (Bill To)
  - Error was: `SyntaxError: Expecting Unicode escape sequence \uXXXX`
  - Deployment agent verified: Application ready for production deployment

- [x] **quotes.tsx Refactoring - Phase 1**: Extracted ~700 lines of code from quotes.tsx (4828 → 4119 lines)
  - **New files created in `/app/frontend/components/quotes/`**:
    - `utils.ts`: Extracted `getStatusColor`, `getStatusIcon`, `formatDate`, `getPackingPercent`, `calculateTotals`
    - `generatePdfHtml.ts`: Extracted PDF HTML generation logic (~500 lines)
    - `styles.ts`: Extracted shared modal and component styles
    - Updated `index.ts` to export new utilities
  - Removed duplicate `generatePdfHtml` function definition
  - Updated quotes.tsx to import utilities from components/quotes

- [x] **Rubber Ring Weight Calculation**: Implemented accurate ring weight calculation based on ID/OD
  - Added `calculate_rubber_ring_weight()` function using volume formula: π × ((OD² - ID²) / 4) × width
  - Added `calculate_total_rubber_weight()` to calculate total weight based on number of rings (35mm each)
  - Created Excel template for user to provide actual ring weights: `/app/frontend/public/ring_weights_template.xlsx`

- [x] **Pipe-Shaft Compatibility Filtering**: Implemented filtering to show only compatible shafts for selected pipe
  - Added `PIPE_SHAFT_COMPATIBILITY` mapping in `roller_standards.py`
  - Added `PIPES_WITHOUT_HOUSING` for warning about shafts that work without housing (60.8mm, 76.1mm pipes)
  - Added API endpoint: `GET /api/compatible-shafts/{pipe_dia}`
  - Updated frontend calculator to filter shaft dropdown based on selected pipe
  - Added warning message when selected shaft works without housing


### March 14, 2026 (Current Session) - Modal Close Buttons & Major Refactoring
- [x] **Added "X" Close Buttons to All Modals (P0)**:
  - `customers.tsx`: Add/Edit Customer Modal - Changed "Cancel" text to X icon
  - `customers.tsx`: Customer Quotes Modal - Changed "Close" text to X icon  
  - `search.tsx`: Quantity Modal - Added header with title and X close button
  - Added new styles `quantityModalHeader` and `quantityModalTitle` for consistent UI
  - All other modals already had X buttons (verified: quotes, cart, admin, shared components)
- [x] **Completed `quotes.tsx` Refactoring - QuoteDetailModal (P1-CRITICAL)**:
  - Created `/app/frontend/components/quotes/QuoteDetailModal.tsx` (1271 lines)
  - Fully integrated and wired up the component in `quotes.tsx`
  - Tested and verified working (100% pass rate)
- [x] **Completed `quotes.tsx` Refactoring - EditQuoteModal (P1-CRITICAL)**:
  - Created `/app/frontend/components/quotes/EditQuoteModal.tsx` (844 lines)
  - Fully integrated with all 25+ props connected
  - Tested and verified working (100% pass rate)
  - **Total Reduction: `quotes.tsx` went from 4762 lines to 3607 lines (1155 lines removed!)**
- [x] **Started `calculator.tsx` Refactoring (P1)**:
  - Created `/app/frontend/components/calculator/types.ts` - Extracted types and constants
  - Updated imports in `calculator.tsx`
  - **Reduction: `calculator.tsx` went from 3645 lines to 3543 lines (102 lines removed)**

### March 13, 2026 (Previous Session) - Designation Field & iOS Logout Fix
- [x] **Designation Field for Customer Signup (P0)**: 
  - Added optional "Designation" field to customer registration form
  - Backend: Updated `OTPRequest` and `OTPVerify` models to include designation
  - Backend: User creation in `verify_otp` saves designation to both users and customers collections
  - Backend: Added designation to `/api/auth/me`, `/api/auth/login`, and `/api/auth/verify-otp` responses
  - Backend: Admin registration notification email includes designation
  - Frontend: Added designation input field to `register.tsx` (between Company Name and Password)
  - Frontend: Updated `verify-otp.tsx` to pass designation to backend
  - **Tested**: 9/9 backend tests passed, frontend UI verified

- [x] **Fixed iOS Logout Bug** (recurring issue, 6x reports): 
  - **Root Cause**: Race condition where navigation happened before state was cleared, and setTimeout was unreliable on iOS
  - **Fix in AuthContext.tsx**: 
    - Clear state (`setUserState(null)`, `setIsAuthenticated(false)`) FIRST before any async operations
    - Use `Promise.all()` for parallel AsyncStorage clearing
    - Make `removePushToken()` fire-and-forget (non-blocking)
  - **Fix in profile.tsx**: 
    - Removed `setTimeout` hack - now properly await logout() before navigating
    - Added error recovery to still navigate to login even if logout fails
  - **Fix in _layout.tsx**: 
    - Return `null` when user is not authenticated to prevent crash during transition
  - **Status**: Code fix complete, requires native iOS build to fully test

- [x] **Added Help & Support Section to Profile**:
  - FAQs button with popup showing common questions (quote creation, price calculation)
  - Contact Us button with support email and phone info
  - App Version display (1.0.0)
  - Clean card-based UI matching app design system

- [x] **Extended Push Notifications**:
  - Added `send_push_notification_to_user()` function for individual user notifications
  - **Quote Approved**: Customer receives push notification with quote number and total price
  - **RFQ Rejected**: Customer receives push notification with reason for rejection
  - All notifications include actionable data (quote_id, type) for deep linking

- [x] **Packing % Display Everywhere**:
  - **Quote Cards**: Shows packing type (Standard/Pallet/Wooden Box/Custom with %) in blue text
  - **Quote Detail Modal**: Always shows packing with type and percentage
  - **PDF Generation**: Shows packing type in both summary section and info box
  - Supports custom packing percentages (stored as `custom_X` format)
  - Helper function `getPackingPercentLabel()` for consistent display across components

- [x] **Housing Rates in Admin Panel**:
  - Added `housing_costs` to backend GET/POST admin prices API
  - Added Housing tab with home icon in admin panel
  - Shows all 20+ housing OD/Bearing OD configurations with editable prices

- [x] **Bulk Price Import/Export**:
  - **Export to Excel**: `GET /api/admin/prices/export` generates Excel with 7 sheets (Basic, Bearing, Housing, Seal, Circlip, Rubber, Locking)
  - **Import from Excel**: `POST /api/admin/prices/import` reads Excel and updates all prices
  - Frontend buttons: Blue "Export to Excel" and Green "Import from Excel"
  - Excel has professional styling with carmine headers

### Previous Session - UI Redesign
- [x] **Login Page**: Complete redesign with modern two-tone layout
- [x] **Theme System**: Enhanced design tokens
- [x] **Header Redesign (All Main Screens)**: Dark slate headers
- [x] **Card Styling Updates**: White background with subtle borders

## Design System

### Colors
| Token | Value | Usage |
|-------|-------|-------|
| Primary | #960018 | Buttons, accents, active states |
| Primary Light | #C41E3A | Hover states |
| Secondary/Dark | #0F172A | Headers, dark backgrounds |
| Background | #F8FAFC | Page backgrounds |
| Surface | #FFFFFF | Cards, modals |
| Text Primary | #0F172A | Headings |
| Text Secondary | #64748B | Body text |
| Text Muted | #94A3B8 | Captions, labels |
| Border | #E2E8F0 | Input borders |
| Border Light | #F1F5F9 | Card borders |

### Typography
- H1: 28px / 700 weight / -0.5 letter spacing
- H2: 24px / 600 weight / -0.3 letter spacing
- H3: 20px / 600 weight
- Body: 16px / 400 weight / 24px line height
- Caption: 12px / 400 weight / 16px line height
- Label: 12px / 600 weight / uppercase / 0.5 letter spacing

## Known Issues

### P1 - High Priority
- [x] **iOS logout functionality**: FIXED - Resolved race condition by clearing state before async operations (was recurring issue, 6x)
- [ ] **Android navigation bar overlap**: System nav bar overlaps bottom tab bar

### P2 - Medium Priority
- [ ] Login background image doesn't load on web view (may be obsolete with new design)

### P3 - Low Priority
- [ ] Expo Tunnel instability (ERR_NGROK_3200) - environment issue

## Prioritized Backlog

### P0 - Critical (COMPLETED)
- [x] Search tab attachments - DONE
- [x] Automate freight calculation - DONE

### P0 - Critical (PENDING)
- [ ] Complete refactoring of quotes.tsx (4700+ lines)
- [ ] Complete refactoring of calculator.tsx (3600+ lines)

### P1 - Important
- [ ] Test Export to PDF/Excel functionality end-to-end
- [ ] Refactor backend/server.py into FastAPI routers
- [ ] Test Push Notifications (requires APK build)
- [ ] Fix Android navigation bar overlap
- [ ] Test iOS logout fix on native build (requires successful EAS build)

### P2 - Nice to Have
- [ ] CRM features (leads, activity timeline, follow-ups)
- [ ] Excel upload for raw material costs
- [ ] Show original RFQ number on quote cards
- [ ] Code cleanup - delete unused files

## Files Modified This Session
- `/app/frontend/app/(tabs)/customers.tsx` - Added X close buttons to Add/Edit Customer Modal and Customer Quotes Modal
- `/app/frontend/app/(tabs)/search.tsx` - Added header with X close button to Quantity Modal
- `/app/frontend/components/quotes/QuoteDetailModal.tsx` - NEW: Extracted Quote Detail Modal component (1271 lines)
- `/app/frontend/components/quotes/EditQuoteModal.tsx` - NEW: Extracted Edit Quote Modal component (844 lines)
- `/app/frontend/components/quotes/index.ts` - Updated barrel export to include QuoteDetailModal and EditQuoteModal
- `/app/frontend/app/(tabs)/quotes.tsx` - MAJOR REFACTOR: Replaced inline modals with extracted components (reduced from 4762 to 3607 lines)

## Previous Files Modified
- `/app/frontend/app/(tabs)/search.tsx` - Added attachment UI and styles
- `/app/backend/server.py` - Auto-freight calculation in approve_rfq, NoneType fix
- `/app/backend/tests/test_approve_rfq_auto_freight.py` - New test file

## Test Reports
- `/app/test_reports/iteration_22.json` - P0 features tested, 12/12 backend tests passed

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

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
- [ ] **iOS logout functionality**: Not working (recurring issue, 4x)
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
- [ ] Fix iOS logout functionality
- [ ] Fix Android navigation bar overlap

### P2 - Nice to Have
- [ ] CRM features (leads, activity timeline, follow-ups)
- [ ] Excel upload for raw material costs
- [ ] Show original RFQ number on quote cards
- [ ] Code cleanup - delete unused files

## Files Modified This Session
- `/app/frontend/app/(tabs)/search.tsx` - Added attachment UI and styles
- `/app/backend/server.py` - Auto-freight calculation in approve_rfq, NoneType fix
- `/app/backend/tests/test_approve_rfq_auto_freight.py` - New test file

## Test Reports
- `/app/test_reports/iteration_22.json` - P0 features tested, 12/12 backend tests passed

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

# Belt Conveyor Roller Price Calculator - PRD

## Original Problem Statement
The user wants to create a mobile application to calculate the price of belt conveyor rollers, serving as an engineering and quoting tool. The scope has expanded to include a product catalog search, a full admin panel for price management, a customer database, and a complete quote/RFQ generation and approval workflow with file attachments and product-specific remarks.

## Core Requirements
- **Core Function**: Calculate prices for Carrying, Impact, and Return belt conveyor rollers.
- **Admin Panel**: Secure interface for CRUD operations, customer management, and sales analytics.
- **Customer Management**: System to manage customers with unique, auto-incrementing customer codes.
- **Professional UI**: A corporate look and feel with a Carmine Red color scheme.
- **Authentication**: Secure OTP-based signup and login.
- **Role-Based Access Control (RBAC)**: Prices are hidden from customers until a quote is formally approved.
- **RFQ & Quote Workflow**: Full lifecycle from customer RFQ submission to admin review, edit, approval, or rejection.

## Architecture
```
/app
├── backend
│   └── server.py        # FastAPI backend with MongoDB
└── frontend
    ├── app
    │   ├── (tabs)
    │   │   ├── _layout.tsx      # Tab navigation layout (Products tab)
    │   │   ├── cart.tsx         # Shopping cart
    │   │   ├── calculator.tsx   # Product calculator 
    │   │   ├── quotes.tsx       # Quote management (REFACTORED)
    │   │   └── search.tsx       # Product search
    │   └── auth
    │       └── login.tsx        # REDESIGNED: New industrial minimalist login
    ├── components
    │   └── quotes/              # EXTRACTED: Quote components
    │       ├── types.ts         
    │       ├── QuoteCard.tsx    
    │       ├── RevisionHistoryModal.tsx  
    │       ├── ApprovalSuccessModal.tsx  
    │       ├── RejectReasonModal.tsx     
    │       └── index.ts         
    └── theme
        └── index.ts             # NEW: Design system theme file
```

## Completed Features (as of Dec 9, 2025)

### This Session:
1. ✅ **Tab Rename**: "Calculator" → "Products" with new cube icon
2. ✅ **Refactoring Phase 2**: 
   - Extracted 4 components from monolithic quotes.tsx
   - Reduced quotes.tsx from 5113 → 4747 lines (366 lines / 7.2%)
   - All tests passed (100% success rate)
3. ✅ **Design System Created**: 
   - `/app/frontend/theme/index.ts` - Centralized theme with colors, typography, spacing
   - `/app/design_guidelines.json` - Complete design guidelines for "Industrial Minimalist" aesthetic
4. ✅ **Login Page Redesigned**: 
   - New two-tone background (Carmine Red top + Dark slate bottom)
   - Floating white form card with enhanced inputs
   - Password visibility toggle
   - Modern typography and spacing
   - Professional "RollerQuote Pro" branding

### Design System Highlights:
- **Primary Color**: Carmine Red (#960018)
- **Background**: Slate tones (#F8FAFC, #F1F5F9, #0F172A)
- **Typography**: Clean sans-serif with uppercase labels
- **Cards**: White with subtle shadows, rounded corners (12-20px)
- **Inputs**: Light gray backgrounds with focus states
- **Buttons**: Solid Carmine Red with hover states

## Known Issues
- **Expo Tunnel (ERR_NGROK_3200)**: Recurring environment issue causing preview unavailability. This is a platform-level issue, not code-related.

## Pending User Verification
1. Weight in cart bug fix - items from Search tab
2. iOS logout functionality
3. Android system nav bar overlap

## Backlog (Prioritized)

### P0 - Critical (Refactoring)
- [x] Tab rename ✅
- [x] Extract quote components ✅
- [x] Design system + Login redesign ✅
- [ ] Redesign remaining screens (Dashboard, Products, Quotes, etc.)
- [ ] Continue extracting quote modals (EditQuoteModal, ApproveModal, QuoteDetailModal)
- [ ] Refactor calculator.tsx

### P1 - CRM Features (User Suggested)
- [ ] Sales Pipeline/Funnel Dashboard
- [ ] Lead Management
- [ ] Follow-up & Task System
- [ ] Customer 360° View
- [ ] Communication Hub (WhatsApp, Email)

### P2 - Other
- [ ] Excel upload for raw material costs
- [ ] Refactor backend/server.py

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

## Design Files Created
- `/app/design_guidelines.json` - Complete design guidelines
- `/app/frontend/theme/index.ts` - Theme constants and colors
- `/app/frontend/app/auth/login.tsx` - Redesigned login screen

## Test Reports
- `/app/test_reports/iteration_21.json` - Refactoring Phase 2 tests (100% PASS)

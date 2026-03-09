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
- **Pincode Validation**: Pincodes entered by customers or admins should be validated.
- **Discount Flexibility**: Admins must be able to apply discounts either item-wise or on the total value.
- **Search**: Users (admin and customer) should be able to search for products by code and add them to the cart.
- **Editable Approved Quotes**: Admins must be able to edit quotes even after they have been approved.
- **Quote Revision History**: Admins need to see a history of all changes made to a quote after it's approved.

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
    │   │   ├── quotes.tsx       # Quote management
    │   │   └── search.tsx       # Product search
    │   └── _layout.tsx
    └── components
        └── quotes/              # NEW: Extracted quote components
            ├── types.ts         # Shared TypeScript interfaces
            ├── QuoteCard.tsx    # Quote list item component
            ├── RevisionHistoryModal.tsx  # History viewer
            ├── ApprovalSuccessModal.tsx  # Success popup
            ├── RejectReasonModal.tsx     # Rejection modal
            └── index.ts         # Barrel export
```

## Completed Features (as of Dec 9, 2025)
- [x] Complete authentication system with OTP
- [x] Role-based access control (admin/customer)
- [x] Product calculator for Carrying, Impact, Return rollers
- [x] Product search functionality
- [x] Shopping cart with weight tracking
- [x] RFQ submission and approval workflow
- [x] Quote revision history
- [x] Editable packing type in Edit Quote modal
- [x] Real-time calculation updates in approval flow
- [x] PDF quote generation
- [x] Email notifications for approved/revised quotes
- [x] Tab rename: "Calculator" → "Products" (Dec 9, 2025)
- [x] **REFACTORING STARTED**: Extracted quote components (Dec 9, 2025)
  - types.ts - Shared interfaces for Quote, QuoteProduct, RevisionHistoryEntry
  - QuoteCard.tsx - Reusable quote list item component
  - RevisionHistoryModal.tsx - Standalone history viewer
  - ApprovalSuccessModal.tsx - Success popup component
  - RejectReasonModal.tsx - Rejection flow component

## Pending User Verification
1. Weight in cart bug fix - items from Search tab should show weight correctly
2. iOS logout functionality - needs testing on physical iOS device
3. Android system nav bar overlap - needs testing on physical Android device

## Backlog (Prioritized)

### P0 - Critical (Refactoring - IN PROGRESS)
- [x] Created shared types.ts for quote interfaces
- [x] Extracted QuoteCard component
- [x] Extracted RevisionHistoryModal component
- [x] Extracted ApprovalSuccessModal component  
- [x] Extracted RejectReasonModal component
- [ ] Integrate extracted components into quotes.tsx
- [ ] Extract EditQuoteModal component
- [ ] Extract ApproveModal component
- [ ] Extract QuoteDetailModal component
- [ ] Refactor calculator.tsx into smaller components

### P1 - High Priority
- [ ] Refactor `backend/server.py` into proper FastAPI structure with routers

### P2 - Medium Priority
- [ ] Excel upload feature for updating raw material costs

### P3 - Low Priority
- [ ] Show original RFQ number on quote cards
- [ ] Code cleanup - delete unused files

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

## 3rd Party Integrations
- api.postalpincode.in - Address/pincode validation
- weasyprint - Server-side PDF generation
- Gmail SMTP - Email notifications
- Expo/EAS - Mobile app builds (APK/IPA)

## Refactoring Notes
The refactoring is being done incrementally to avoid breaking the application. Components are being extracted to `/app/frontend/components/quotes/` directory. The original `quotes.tsx` file (5113 lines) will be updated to use these extracted components once all modals are extracted.

### Extracted Component Summary:
| Component | Lines | Status |
|-----------|-------|--------|
| types.ts | ~170 | ✅ Created |
| QuoteCard.tsx | ~265 | ✅ Created |
| RevisionHistoryModal.tsx | ~220 | ✅ Created |
| ApprovalSuccessModal.tsx | ~115 | ✅ Created |
| RejectReasonModal.tsx | ~160 | ✅ Created |
| EditQuoteModal.tsx | ~TBD | ⏳ Pending |
| ApproveModal.tsx | ~TBD | ⏳ Pending |
| QuoteDetailModal.tsx | ~TBD | ⏳ Pending |

Total lines extracted so far: ~930 lines (potential reduction from 5113)

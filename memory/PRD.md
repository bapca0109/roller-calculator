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
    │   │   ├── quotes.tsx       # Quote management (REFACTORED: 5113 → 4747 lines)
    │   │   └── search.tsx       # Product search
    │   └── _layout.tsx
    └── components
        └── quotes/              # EXTRACTED: Quote components (891 lines total)
            ├── types.ts         # Shared TypeScript interfaces (170 lines)
            ├── QuoteCard.tsx    # Quote list item component (294 lines) ✅ INTEGRATED
            ├── RevisionHistoryModal.tsx  # History viewer (277 lines) ✅ INTEGRATED
            ├── ApprovalSuccessModal.tsx  # Success popup (138 lines) ✅ INTEGRATED
            ├── RejectReasonModal.tsx     # Rejection modal (182 lines) ✅ INTEGRATED
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
- [x] Tab rename: "Calculator" → "Products" (Dec 9, 2025) ✅
- [x] **REFACTORING Phase 2 COMPLETE** (Dec 9, 2025) ✅
  - Extracted and integrated QuoteCard component
  - Extracted and integrated RevisionHistoryModal component
  - Extracted and integrated ApprovalSuccessModal component  
  - Extracted and integrated RejectReasonModal component
  - Reduced quotes.tsx from 5113 → 4747 lines (366 lines reduction)
  - All tests PASSED (100% success rate)

## Pending User Verification
1. Weight in cart bug fix - items from Search tab should show weight correctly
2. iOS logout functionality - needs testing on physical iOS device
3. Android system nav bar overlap - needs testing on physical Android device

## Backlog (Prioritized)

### P0 - Critical (Refactoring - IN PROGRESS)
- [x] Created shared types.ts for quote interfaces
- [x] Extracted and integrated QuoteCard component
- [x] Extracted and integrated RevisionHistoryModal component
- [x] Extracted and integrated ApprovalSuccessModal component  
- [x] Extracted and integrated RejectReasonModal component
- [ ] Extract EditQuoteModal component (~300 lines)
- [ ] Extract ApproveModal component (~300 lines)
- [ ] Extract QuoteDetailModal component (~500 lines)
- [ ] Refactor calculator.tsx into smaller components (3683 lines)

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

## Refactoring Progress Summary

| Component | Lines | Status | Tests |
|-----------|-------|--------|-------|
| types.ts | ~170 | ✅ Created | PASS |
| QuoteCard.tsx | 294 | ✅ Integrated | PASS |
| RevisionHistoryModal.tsx | 277 | ✅ Integrated | PASS |
| ApprovalSuccessModal.tsx | 138 | ✅ Integrated | PASS |
| RejectReasonModal.tsx | 182 | ✅ Integrated | PASS |
| EditQuoteModal.tsx | TBD | ⏳ Pending | - |
| ApproveModal.tsx | TBD | ⏳ Pending | - |
| QuoteDetailModal.tsx | TBD | ⏳ Pending | - |

**Total lines extracted so far:** 891 lines
**quotes.tsx reduction:** 5113 → 4747 lines (366 lines = 7.2% reduction)
**Target:** Continue extracting remaining modals to achieve ~50% reduction

## Test Reports
- `/app/test_reports/iteration_21.json` - Refactoring Phase 2 tests (100% PASS)

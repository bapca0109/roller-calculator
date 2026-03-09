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
    └── app
        ├── (tabs)
        │   ├── _layout.tsx      # Tab navigation layout
        │   ├── cart.tsx         # Shopping cart
        │   ├── calculator.tsx   # Product calculator (renamed to "Products" in tab)
        │   ├── quotes.tsx       # Quote management
        │   └── search.tsx       # Product search
        └── _layout.tsx
```

## Completed Features (as of Dec 2025)
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

## Pending User Verification
1. Weight in cart bug fix - items from Search tab should show weight correctly
2. iOS logout functionality - needs testing on physical iOS device
3. Android system nav bar overlap - needs testing on physical Android device

## Backlog (Prioritized)
### P0 - Critical
- [ ] Refactor `quotes.tsx` and `calculator.tsx` into smaller components

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

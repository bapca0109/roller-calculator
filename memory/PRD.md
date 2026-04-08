# Belt Conveyor Roller & Pulley Price Calculator - PRD

## Original Problem Statement
Create a mobile application to calculate the price of belt conveyor rollers and pulleys, serving as an engineering and quoting tool with product catalog search, admin panel for price management, customer database, complete quote/RFQ workflow, CRM, and sales order management.

## Architecture
```
/app
├── backend
│   ├── server.py               # App setup, middleware (684 lines)
│   ├── routes/
│   │   ├── __init__.py         # Shared deps, DB, auth, models (365 lines)
│   │   ├── auth.py             # Login, register, OTP, forgot password (3,080 lines)
│   │   ├── quotes.py           # Quote CRUD, RFQ approval, revision (1,972 lines)
│   │   ├── orders.py           # Sales orders, payments, invoicing (290 lines)
│   │   ├── admin.py            # Price management, standards (1,295 lines)
│   │   ├── products.py         # Product CRUD, pricing calc, search (945 lines)
│   │   ├── customers.py        # Customer CRUD, GSTIN (276 lines)
│   │   ├── crm.py              # Leads, follow-ups, activity timeline (280 lines)
│   │   ├── analytics.py        # Dashboard analytics (839 lines)
│   │   ├── exports.py          # Excel/PDF exports (633 lines)
│   │   └── pulley.py           # Pulley calculator (124 lines)
│   ├── pulley_standards.py     # Pulley constants & calculation logic
│   ├── roller_standards.py     # Roller pricing data
│   └── price_loader.py         # Sync MongoDB price fetcher
├── frontend
│   ├── app/(tabs)/
│   │   ├── _layout.tsx         # Tab nav (Pulley hidden, merged into Products)
│   │   ├── calculator.tsx      # Products: Roller/Pulley toggle + calculator
│   │   ├── pulley.tsx          # Pulley calculator
│   │   ├── quotes.tsx          # Sales: Quotes/Orders toggle
│   │   ├── dashboard.tsx       # CRM: Leads, follow-ups, activity
│   │   ├── cart.tsx            # Shared cart
│   │   ├── customers.tsx       # Customer management
│   │   ├── admin.tsx           # Admin panel
│   │   └── profile.tsx         # User profile
│   └── theme/index.ts          # Premium glass design system
└── memory/
    └── PRD.md
```

## What's Been Implemented

### April 8, 2026
- [x] Pulley Calculator with real pricing (Pipe, Shaft, End Plate, Hub, Rubber)
- [x] Pricing formula: Raw Material × 1.3 (Labour) × 1.6 (Profit)
- [x] Merged Products + Pulley into single tab with toggle
- [x] Premium glass UI redesign across ALL screens
- [x] Server.py refactored from 9,729 → 684 lines (93% reduction)
- [x] CRM: Lead management, follow-ups, activity timeline
- [x] Sales Orders: Convert quote → SO, payment tracking, invoicing
- [x] Orders frontend: Merged into Quotes tab as "Sales" with Quotes/Orders toggle
- [x] Android nav bar overlap fix

### Previous Sessions
- [x] Full Roller calculator with IS standards
- [x] Quote/RFQ workflow with approval
- [x] Customer management with GST lookup
- [x] Admin price import/export

## Design System
- Primary: #960018 (Carmine)
- Accent: #C5964A (Gold)
- Background: #F0F4F8
- Glass cards: rgba(255,255,255,0.78)
- Dark header: #0F172A
- Tab bar: Dark with gold active

## Known Issues
- [ ] KLA pricing pending (hidden from UI)

## Prioritized Backlog
### P0
- [ ] Invoice PDF generation with company details & bank info
- [ ] "Convert to SO" button on approved quote cards

### P1
- [ ] Inventory & Production tracking
- [ ] Low stock alerts
- [ ] Purchase Orders

### P2
- [ ] Finance: Accounts receivable, GST reports
- [ ] WhatsApp integration
- [ ] Tally/Zoho export

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

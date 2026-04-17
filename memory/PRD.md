# Belt Conveyor Roller & Pulley ERP - PRD

## Original Problem Statement
Full ERP mobile application for belt conveyor engineering — roller/pulley pricing, quoting, CRM, sales orders, work orders, invoicing, and production tracking.

## Architecture
```
/app
├── backend
│   ├── server.py               # App setup, middleware (690 lines)
│   ├── routes/
│   │   ├── __init__.py         # Shared deps, DB, auth, models
│   │   ├── auth.py             # Login, register, OTP, forgot password
│   │   ├── quotes.py           # Quote CRUD, RFQ approval, revision
│   │   ├── orders.py           # Sales orders, payments, invoicing, SO PDF
│   │   ├── workorders.py       # Work orders, BOM, WO PDF
│   │   ├── admin.py            # Roller price management, standards
│   │   ├── products.py         # Product CRUD, pricing calc, search
│   │   ├── customers.py        # Customer CRUD, GSTIN
│   │   ├── crm.py              # Leads, follow-ups, activity timeline
│   │   ├── analytics.py        # Dashboard analytics
│   │   ├── exports.py          # Excel/PDF exports
│   │   └── pulley.py           # Pulley calculator + pricing display
│   ├── pulley_standards.py     # Pulley constants & calculation (HARDCODED prices)
│   ├── roller_standards.py     # Roller pricing data
│   └── price_loader.py         # Sync MongoDB price fetcher
├── frontend
│   ├── app/(tabs)/
│   │   ├── _layout.tsx         # Tab nav
│   │   ├── calculator.tsx      # Products: Roller/Pulley toggle
│   │   ├── pulley.tsx          # Pulley calculator
│   │   ├── quotes.tsx          # Sales: Quotes/Orders/Work Orders
│   │   ├── dashboard.tsx       # CRM
│   │   ├── cart.tsx, customers.tsx, admin.tsx, profile.tsx
│   └── theme/index.ts          # Premium glass design system
└── memory/PRD.md
```

## What's Implemented (as of April 17, 2026)
- [x] Roller Calculator with IS standards
- [x] Pulley Calculator with real pricing (pipe, shaft, end plate, hub, rubber)
- [x] Pulley: stress relieving toggle, pipe weight thk+2mm, large pipe surcharge
- [x] Quote/RFQ workflow with approval + PDF attachments in emails
- [x] CRM: Lead management, follow-ups, activity timeline
- [x] Sales Orders: Convert from quote with delivery date (calendar picker)
- [x] Work Orders: Create from SO with production details + auto BOM
- [x] WO PDF: Items summary table, consolidated BOM by component, paint details (RAL code, paint type, paint spec from quote)
- [x] SO PDF: Full commercial terms, pricing with GST, delivery date, total weight
- [x] Invoice PDF: Proforma + Tax with company details, bank info, payment history
- [x] All date formats: DD-MM-YYYY across entire app
- [x] Premium glass UI with gold accents
- [x] Server.py refactored: 9,729 → 690 lines (11 route modules)
- [x] Admin panel: Roller/Pulley toggle (Pulley shows read-only prices)
- [x] Export: Excel + PDF across all modules
- [x] Pulley items skip technical details (shaft slot etc.) during WO creation
- [x] BOM: Housing=CRC, Shaft=EN-8, Circlip=A{dia}, correct pipe thk by class A/B/C
- [x] Roller BOM: Pipe, Shaft, Bearing+make, Housing+size, Seal, Circlip, Grease, Rubber Ring (impact)

## P0 — Next Priority
- [ ] **Pulley Admin Editable Prices** — Store pulley prices in MongoDB (like roller), add edit/save/import/export/reset/set-default functionality. Same UI as roller price management.

## P1 — Important
- [ ] KLA pricing (when user provides data)
- [ ] Inventory tracking (deduct from BOM)
- [ ] Convert to SO button reliability on all browsers

## P2 — Future
- [ ] WhatsApp integration
- [ ] E-way bill generation
- [ ] Delivery challan
- [ ] Tally/Zoho export

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

## Company Details (in .env)
- CONVERO SOLUTIONS, Ahmedabad, Gujarat
- GSTIN: 24BAUPP4310D2ZT
- ICICI Bank, A/C: 777705908098, IFSC: ICIC0004942
- HSN: 84313910

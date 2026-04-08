# Belt Conveyor Roller & Pulley Price Calculator - PRD

## Original Problem Statement
Create a mobile application to calculate the price of belt conveyor rollers and pulleys, serving as an engineering and quoting tool with product catalog search, admin panel for price management, customer database, and complete quote/RFQ workflow.

## Architecture
```
/app
├── backend
│   ├── server.py               # FastAPI backend (9700+ lines - needs refactoring)
│   ├── pulley_standards.py     # Pulley constants, pricing & calculation logic
│   ├── roller_standards.py     # Roller pricing data & freight calculation
│   ├── price_loader.py         # Sync MongoDB price fetcher
│   └── static/
│       └── pulley_pricing_template.xlsx
├── frontend
│   ├── utils/api.ts            # API config with cache-busting
│   ├── app/(tabs)/
│   │   ├── _layout.tsx         # Tab navigation (Pulley hidden, merged into Products)
│   │   ├── calculator.tsx      # Products tab: Roller/Pulley toggle + Roller calculator
│   │   ├── pulley.tsx          # Pulley calculator (navigated from Products toggle)
│   │   ├── cart.tsx            # Shared cart (Roller + Pulley)
│   │   ├── quotes.tsx          # Quote management
│   │   ├── customers.tsx       # Customer management
│   │   ├── admin.tsx           # Admin panel
│   │   ├── dashboard.tsx       # Analytics dashboard
│   │   └── profile.tsx         # User profile
│   └── components/
│       ├── calculator/         # Roller types & constants
│       ├── quotes/             # Quote components
│       └── shared/             # Reusable components
└── memory/
    └── PRD.md
```

## What's Been Implemented

### April 8, 2026 — Pulley Calculator + Pricing + UI Refinement
- [x] **Pulley Calculator**: Full backend + frontend with real pricing
- [x] **Real Pricing Data**: Pipe (₹70-99/kg), Shaft (₹60-92.8/kg), End Plate (₹65-76/kg slab), Hub (₹62-69/kg), Rubber Plain (₹3,300-6,400/sqm), Rubber Ceramic (₹20,000-30,000/sqm)
- [x] **Pricing Formula**: Raw Material × 1.3 (Labour) × 1.6 (Profit)
- [x] **BOM**: Pipe 1pc, Shaft 1pc, End Plate 2/3/4 (selectable dropdown), Hub 2pc, KLA 2pc
- [x] **Pipe Weight**: Always uses thickness + 2mm for weight calculation
- [x] **Large Pipe Surcharge**: 630/800/1000mm pipes get +₹8/kg when face length > 1250mm
- [x] **Rubber Lagging Area**: π × Pipe Dia × Face Length (no rubber thickness added)
- [x] **Merged Roller + Pulley** into single "Products" tab with toggle
- [x] **Customer Flow**: Matches Roller — "Add to Cart" button, no prices visible
- [x] **Attachments + Remark + Save Single Quote** added to Pulley
- [x] **KLA Hidden**: Temporarily hidden until user provides pricing data
- [x] **Customer Account**: Created customer@test.com / test123

### Previous Sessions (summarized)
- [x] Full Roller calculator with IS standards
- [x] Quote/RFQ workflow with approval
- [x] PDF generation, email notifications
- [x] Cache-busting, pull-to-refresh
- [x] Customer management with GST lookup
- [x] Admin price import/export (Excel)
- [x] Push notifications (requires native build)
- [x] iOS logout fix, designation field, contact us modal

## Design System
| Token | Value | Usage |
|-------|-------|-------|
| Primary | #960018 | Buttons, accents |
| Secondary/Dark | #0F172A | Headers |
| Background | #F8FAFC | Page backgrounds |
| Surface | #FFFFFF | Cards |
| Text Primary | #0F172A | Headings |
| Text Secondary | #64748B | Body text |

## Known Issues
- [ ] Android navigation bar overlap
- [ ] KLA pricing pending (hidden from UI)

## Prioritized Backlog

### P0 - Next
- [ ] **Premium UI redesign** — Modern glass style across ALL screens

### P1 - Important
- [ ] Refactor server.py into modular FastAPI routers
- [ ] KLA pricing (when user provides data)
- [ ] Test Push Notifications on native build

### P2 - Nice to Have
- [ ] CRM features
- [ ] Show original RFQ number on Quote cards

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

## Test Reports
- `/app/test_reports/iteration_27.json` — Pulley Calculator: 23/23 backend + 100% frontend

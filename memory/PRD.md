# Belt Conveyor Roller Price Calculator - PRD

## Original Problem Statement
The user wants to create a mobile application to calculate the price of belt conveyor rollers, serving as an engineering and quoting tool.

## Architecture
```
/app
├── backend
│   └── server.py        # FastAPI backend with MongoDB + NEW Export endpoints
└── frontend
    ├── app
    │   ├── auth/login.tsx      # REDESIGNED: Industrial minimalist login
    │   └── (tabs)
    │       ├── _layout.tsx     # Tab navigation (Products tab)
    │       ├── cart.tsx        # Shopping cart + Export button
    │       ├── calculator.tsx  # Product calculator 
    │       ├── quotes.tsx      # Quote management + Export button
    │       └── search.tsx      # Product search + Export button
    ├── components
    │   ├── quotes/             # Extracted quote components
    │   └── shared/
    │       └── ExportButtons.tsx  # NEW: Reusable export component
    └── theme/index.ts          # Design system theme
```

## What's Been Implemented in This Session

### 1. Tab Rename ✅
- "Calculator" → "Products" with cube icon

### 2. Refactoring Phase 2 ✅ (100% tests passed)
- Extracted 4 components from quotes.tsx
- Created `/app/frontend/components/quotes/` directory
- Reduced quotes.tsx from 5113 → 4747 lines

### 3. Login Page Redesign ✅
- Two-tone background (Carmine Red + Dark slate)
- "RollerQuote Pro" branding with analytics icon
- "INDUSTRIAL PRICING SOLUTIONS" tagline
- Floating white card with modern inputs
- Password visibility toggle
- Uppercase labels (EMAIL, PASSWORD)

### 4. Export to PDF/Excel Feature ✅
**Backend endpoints added:**
- `GET /api/quotes/export/excel` - Export quotes list
- `GET /api/customers/export/excel` - Export customer list (Admin)
- `GET /api/products/export/excel` - Export product catalog
- `GET /api/cart/export/excel` - Export cart contents

**Frontend components:**
- Created reusable `ExportButtons` component at `/app/frontend/components/shared/ExportButtons.tsx`
- Added export buttons to:
  - Quotes page header (green Excel button)
  - Cart page header (when items present)
  - Search/Product Catalog page header

### Export Features Summary:
| Page | Export Type | Endpoint |
|------|-------------|----------|
| Quotes | Excel | /api/quotes/export/excel |
| Cart | Excel | /api/cart/export/excel |
| Products/Search | Excel | /api/products/export/excel |
| Customers (Admin) | Excel | /api/customers/export/excel |
| Dashboard | Excel + PDF | /api/analytics/export/excel, /api/analytics/export/pdf |

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

## Pending User Verification
1. Weight in cart bug fix
2. iOS logout functionality
3. Android system nav bar overlap

## Backlog
### P0 - Critical
- [ ] Continue extracting quote modals
- [ ] Refactor calculator.tsx

### P1 - CRM Features (User Suggested)
- [ ] Sales Pipeline/Funnel Dashboard
- [ ] Lead Management
- [ ] Follow-up & Task System

### P2 - Other
- [ ] Refactor backend/server.py
- [ ] Excel upload for raw material costs

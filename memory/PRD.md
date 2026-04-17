# Belt Conveyor Roller & Pulley ERP - PRD

## Original Problem Statement
Full ERP mobile application for belt conveyor engineering — roller/pulley pricing, quoting, CRM, sales orders, work orders, invoicing, inventory/store management, and production tracking.

## What's Implemented

### Inventory/Store Backend (April 17, 2026) — NEW
- [x] `routes/inventory.py` — Full store management (300+ lines)
- [x] `routes/suppliers.py` — Supplier database CRUD
- [x] Stock Items: CRUD with categories, units (meters/kg/nos), reorder levels
- [x] Purchase Orders: Create PO with supplier, items, rates → PO/26-27/0001 format
- [x] QC: Pass/Fail/Partial with accepted/rejected qty, auto-adds to stock on pass
- [x] Stock Issue: Manual issue against Work Orders, deducts from stock, logs transactions
- [x] Stock Transactions Log: In/Out with reference (PO/WO), who, when
- [x] Low Stock Alerts: Items below reorder level
- [x] Store Dashboard: Total items, POs, pending POs, low stock count, categories, recent transactions
- [x] All APIs verified working end-to-end

### Backend APIs
- `GET/POST /api/store/items` — Stock items CRUD
- `GET/POST /api/store/purchase-orders` — Purchase orders
- `POST /api/store/qc` — Quality check (pass/fail/partial)
- `POST /api/store/issue` — Issue stock against WO
- `GET /api/store/transactions` — Transaction log
- `GET /api/store/alerts` — Low stock alerts
- `GET /api/store/dashboard` — Store summary
- `GET /api/store/options` — Categories, statuses, units
- `GET/POST/PUT/DELETE /api/suppliers` — Supplier management

### MongoDB Collections
- `stock_items` — inventory items with current stock
- `purchase_orders` — POs with QC status per item
- `stock_transactions` — in/out transaction log
- `suppliers_master` — supplier database

## P0 — Next Priority
- [ ] **Store Frontend** — New "Store" tab with: Dashboard, Stock Levels, Purchase Orders, QC, Issue, Suppliers, Alerts
- [ ] Pulley Admin Editable Prices (MongoDB-backed)

## P1 — Important
- [ ] KLA pricing
- [ ] Convert to SO button reliability

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

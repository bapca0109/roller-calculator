# Belt Conveyor ERP - PRD

## Architecture
- Backend: FastAPI with 13 route modules (690 line server.py)
- Frontend: Expo React Native (iOS + Android + Web)
- Database: MongoDB
- Tabs: CRM, Products, Cart, Sales, Customers, Admin, Store, Profile

## Completed Features
- Roller + Pulley calculators with real pricing
- Quote/RFQ workflow with approval + PDF email attachments
- CRM: Leads, Follow-ups, Activity Timeline
- Sales Orders with delivery date, SO PDF
- Work Orders with production details, auto BOM (8 components for roller), WO PDF
- Invoicing: Proforma + Tax Invoice PDFs with company/bank details
- Payment tracking
- Inventory/Store: 251 stock items, POs, QC, Issue, Shortages, Alerts
- Supplier management with PO PDF
- Stock Adjustment (opening balance, damage, audit)
- Analytics Dashboard (revenue trends, order pipeline, WO stats)
- Stock-BOM linking via bom_match_key
- Excel/PDF exports across all modules
- Premium glass UI, DD-MM-YYYY dates, full product codes in PDFs
- Pulley prices migrated to MongoDB (editable via API)
- **Pulley Admin Frontend [2026-02-17]**: Editable TextInputs for Pipe/Shaft/End-Plate/Hub/Rubber rates in Admin Prices tab. Includes Reset-to-Default and Save-as-Default buttons. 347 editable rows, tested end-to-end.
- **Bulk Edit Mode for Pulley Prices [2026-02-17]**: Toggle bulk edit to show all 347 prices as persistent TextInputs, edit many, Save All persists in one PUT.
- **Price Change History [2026-02-17]**: New `price_history` collection logs every roller + pulley rate change (user, timestamp, old→new, delta). History tab in Admin with All/Roller/Pulley filter chips. Endpoint: `GET /api/price-history?product_type=&limit=&offset=`.
- **User Roles & Tab-Level Access Control [2026-02-17]**: Extended `UserRole` enum with `sales_manager`, `production_head`, `accounts`, `dispatch`. New Admin → Users tab to list/manage user roles via colored pill dropdown. Tab visibility auto-adapts in `_layout.tsx` per role matrix. Sales tab applies within-tab filtering: production_head locked to WO, accounts/dispatch locked to SO view (Quotes/Orders toggle hidden). Endpoints: `GET /api/admin/users`, `PUT /api/admin/users/role`. Seeded 4 test accounts (one per role).
- **Delivery Challan (Dispatch) [2026-02-17]**: New `/app/backend/routes/dispatch.py` with `delivery_challans` collection and `DC/FY/####` numbering. Endpoints: `POST /api/delivery-challans` (creates DC + updates SO stage to "dispatched"), `GET /api/delivery-challans`, `GET /{id}/pdf` (token-auth query param). Captures vehicle, transporter, driver, phone, e-way bill, dispatch date, remarks. **E-way bill enforced as mandatory above ₹50,000** (413 error with clear message). Frontend: "Create Challan" + "Download DC PDF" buttons on order detail modal (visible to admin/dispatch); full DC form modal with inline warning for ₹50k+ consignments. DC PDF renders as branded A4 HTML (company header, consignee block, dispatch details, items table with HSN/qty/weight, signature lines).
- **Admin User Onboarding [2026-02-17]**: `POST /api/admin/users` with email/password/name/role/company. Admin → Users → "+ New User" button opens slide-up modal with role pill chooser (6 role options). Server validates role, checks duplicate email, hashes password, auto-generates customer_code for customer role.
- **Configurable Numbering Templates [2026-02-17]**: Admin → **Numbering** tab lets you customize prefix & pad width for every doc type (RFQ/Q/SO/WO/PO/DC/INV/PI/Customer). Supports tokens `{FY}`, `{YYYY}`, `{MM}`, `{DD}`. Live preview per row. Reset to factory defaults button. Endpoints: `GET/PUT /api/admin/numbering-config`, `POST /reset`. All 7 generators refactored to pass through `format_number()` so template changes apply instantly to the next number issued.

## P0 — Next
- [x] User Roles (Sales, Production, Accounts, Dispatch) — done 2026-02-17

## P1
- [ ] Inventory auto-deduct on WO processing/completion
- [ ] Dispatch/Delivery Challan
- [ ] Tax Invoice auto-gen on dispatch
- [ ] Accounts Receivable
- [ ] GST Reports
- [ ] KLA pricing (BLOCKED: waiting user data)

## Credentials
- Admin: test@test.com / test123
- Customer: customer@test.com / test123

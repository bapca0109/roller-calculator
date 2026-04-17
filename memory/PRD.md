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

## P0 — Next
- [ ] Pulley Admin Frontend (editable prices in Admin UI)
- [ ] User Roles (Sales, Production, Accounts, Dispatch)

## P1
- [ ] Dispatch/Delivery Challan
- [ ] Tax Invoice auto-gen on dispatch
- [ ] Accounts Receivable
- [ ] GST Reports
- [ ] KLA pricing

## Credentials
- Admin: test@test.com / test123
- Customer: customer@test.com / test123

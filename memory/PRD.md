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

## P0 — Next
- [ ] User Roles (Sales, Production, Accounts, Dispatch)

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

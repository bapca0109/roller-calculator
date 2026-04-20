# Belt Conveyor ERP - PRD

## Standing UX Rules (apply to EVERY new module / list screen going forward)
1. **Top Search Bar** — use `<SearchBar>` from `/app/frontend/components/shared/SearchBar.tsx` with a `testID` of `<screen>-search`. Filter the main list client-side on relevant fields (name, code, customer, status, dates, etc.).
2. **Export to Excel + PDF** — use `<ExportButtons ... showExcel showPdf pdfEndpoint="..." />` in the header. Always ship BOTH formats. Backend endpoints: add `/...export/excel` and `/...export/pdf` (use `_build_table_excel` / `_build_table_pdf` helpers in `/app/backend/routes/exports.py`).
3. **Confirmations** — every mutating action wrapped in `confirmAction()` from `/app/frontend/components/shared/confirm.ts`.
4. **Test IDs** — every interactive element and every critical data element gets a `data-testid` / `testID`.

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
- **Quality Inspector Role + Finished-Goods QC [2026-02-17]**: New role `quality_inspector` can view Sales (WO-locked) + Store (QC on PO inward goods). Added `POST /api/work-orders/{id}/qc` endpoint capturing status (passed/failed), remarks, inspector email, timestamp. **Dispatch gate**: DC creation (`POST /api/delivery-challans`) blocked with clear 400 error if any linked WO is not QC-passed ("Finished-goods QC not passed for WO/… — Quality Inspector must stamp 'passed' before dispatch."). Frontend: QC badge (green ✓ / red ✗ / amber pending) on each completed WO card + inline "QC Pass" / "QC Fail" action buttons for admin & QI, with prompt for remarks.
- **QC Inspection Report PDF [2026-02-17]**: New `GET /api/work-orders/{id}/qc-report` (token auth) renders a branded A4 HTML report with diagonal PASSED/FAILED verdict stamp, inspector details (name + date), item-by-item measured specs table, remarks block, and 3 signature lines (Quality Inspector, Production Head, Authorized Signatory). Frontend: teal "QC Report" button auto-appears on WO cards once stamped; opens PDF in new tab for any admin/QI/dispatch user.
- **Convert-to-SO captures Customer PO + per-item Drawing [2026-02-18]**: `ConvertToSORequest` now accepts `customer_po_number`, `customer_po_date`, and `item_drawings[]` (list of `{item_index, drawing_number}`). SO doc persists PO fields at top-level and drawing numbers on `products[i].production_details.drawing_number`. SO PDF header and item rows show these. WO creation auto-fills drawings from SO (Drawing field is now read-only during Create-WO, removed the re-entry requirement).
- **Delivery Date flows into WO [2026-02-18]**: WO doc copies `delivery_date`, `customer_po_number`, `customer_po_date` from its parent SO. WO PDF header shows Delivery Date, Customer PO #, and PO Date in a new info row.
- **Partial / Multi-WO per Sales Order [2026-02-18]**: `BulkCreateWorkOrder` accepts `selected_item_indexes[]`. Previously only one WO per SO was allowed; now an SO can have N WOs, each covering a subset of items. Each product records its owning `wo_number`; SO tracks `work_orders[]`. Server blocks re-creating a WO for items already assigned. Frontend Create-WO modal adds per-item checkboxes (locked for items already in a WO), submit button label is dynamic ("Create WO for N Item(s)"), and the SO card's Create-WO action shows remaining-items count.
- **BOM Weights populated — Bearings + Rubber Rings [2026-02-18]**: Added `BEARING_WEIGHT_KG` master map in `roller_standards.py` (6204–6310, 420204–420206) sourced from SKF/FAG datasheets — used as `weight_per_unit_kg` in auto-generated BOM for rollers. Rubber ring weight now **looked up from the user-provided `RUBBER_RING_WEIGHTS` master sheet** (via `get_rubber_ring_weight(pipe_dia, rubber_dia)`) — no formula/density calc. Verified: 88.9mm pipe × 127mm rubber → 0.245 kg/ring → 13.72 kg total for 2 rollers × 28 rings.
- **Global Confirmation Dialogs [2026-02-18]**: Added a cross-platform `confirmAction(title, message)` helper at `/app/frontend/components/shared/confirm.ts` (uses `window.confirm` on web, `Alert.alert` on native). Every mutating / process-advancing button now shows a "Yes, Proceed / Cancel" confirmation with a one-line summary of what will happen. Applied to: Convert-to-SO, Create WO (partial + full), QC stamp Pass/Fail, WO stage update, Order stage update, Record Payment, Create Delivery Challan, Generate Proforma/Tax Invoice, Approve/Reject Quote, Save-and-Mail Quote, Update Quote Status, Admin → Pulley price save/bulk save, Change User Role, Create User, Save Numbering Templates, Update Price, Update Standards, Create Stock/Supplier/PO, Stock QC Accept/Reject, Issue Stock to WO, Create Lead, Move Lead Stage, Schedule/Complete Follow-up, Create/Update Customer, Submit RFQ (cart / calculator / search / RfqSubmissionModal). Pure reads, filters, navigation and PDF downloads are unaffected.
- **Sub-Work Orders for Pipe & Shaft [2026-02-18]**: Auto-generation of Pipe Job Cards (`/P`) and Shaft Job Cards (`/S`) for Rollers (skipped for Pulleys). Added PDF endpoints and UI buttons per WO card.
- **Pipe WIP QC Module [2026-02-18]**: Tolerance engine + dynamic sample modal capturing Pipe Dia (Yes/No), Pipe Length (±1mm), Pipe Thickness (±10%). Auto-evaluates Pass/Fail per sample with running pass/fail counts. Endpoints: `GET/POST /api/sub-work-orders/{id}/wip-qc`.
- **RFQ Approve Fix [2026-02-18]**: Fixed Approve RFQ button silently failing. Root cause: `onPress={confirmApproveRfq}` passed the synthetic press event as the `quoteOverride` argument, triggering the "Invalid quote - missing ID" early-exit. Wrapped in arrow function `() => confirmApproveRfq()`. Added `data-testid="approve-rfq-confirm-btn"`. Verified end-to-end: RFQ/2026/00028 → Q/26-27/0032 success dialog.
- **Shaft WIP QC Module [2026-02-18]**: Mirror of Pipe QC for Shaft job cards. Dynamic sample modal captures Shaft Dia (Yes/No + remarks), Shaft Length (±1mm), and End Slot fields that adapt to the slot type from the WO: Type A → Width (-0.2/+0), Dimension (±0.5); Type B5/B7/B10 → adds Notch (B-number mm, ±0.5); Type C30/C35 → adds Centre (C-number mm, ±1). Endpoints refactored to a unified `GET/POST /api/sub-work-orders/{id}/wip-qc` that dispatches by type (pipe | shaft). Includes back-compat parser (`_ensure_shaft_slot_details`) that reconstructs slot structure from legacy `end_slot` display string for sub-WOs created before this release. New shaft sub-WOs now persist `shaft_slot_details` alongside `end_slot`. Teal "Shaft QC" button added to every non-pulley WO card. Verified curl + Playwright: 2-sample Type-A run → sample 1 PASS, sample 2 FAIL (dia No, length 355 out of ±1, width 13.7 below tol) → status FAILED persisted.
- **QC Tab (Sales screen) [2026-02-18]**: New "QC" top-nav tab beside Orders showing every roller WO with its Pipe QC + Shaft QC status. Backend endpoint `GET /api/wip-qc/overview` aggregates all WOs with their pipe/shaft sub-WO IDs and status (pending | passed | failed, pass/fail counts, inspector). Frontend shows summary cards (pending · done counts), status / type filters (All/Pending/Completed × P+S/Pipe/Shaft), and clickable Pipe/Shaft status chips that open the respective WIP QC modal inline. Pipe/Shaft QC modals extracted into reusable `usePipeQC` / `useShaftQC` hooks at `/app/frontend/components/quotes/QCModals.tsx` so the same UX is shared between the Work-Orders view and the new QC tab.
- **Raise PO Item Picker — Search Mode [2026-02-20]**: Replaced the horizontal floating-chip stock-item list inside each PO line with a proper search input (`po-item-search-{idx}`). User types 1+ character → top 8 matching items (by name or category) render as a tappable vertical list showing name, category, and current stock. Works identically for manually added lines via "Add Line" and prefilled lines from Shortages (where picker stays locked to the prefilled item). Per-line search state auto-resets on line remove/close. File: `/app/frontend/app/(tabs)/store.tsx`.
- **Raise PO Search — Keyboard Navigation [2026-02-20]**: Added full keyboard control to the PO line item-search dropdown. ↑/↓ move the amber highlight through the 8 result rows, Enter selects the highlighted item, Esc clears the query. Mouse hover also moves the highlight for consistent UX. Typing resets highlight to the top match. Verified end-to-end via Playwright (search "bearing" → ↓↓ → Enter → "Bearing 420204 ZZ China" locked).
- **Unified SearchPicker component [2026-02-20]**: Extracted the search-driven picker into a shared `/app/frontend/components/shared/SearchPicker.tsx` component (generic `SearchItem = {id, label, sublabel?, right?}`). Rolled it out to **Supplier picker** (Raise PO modal — search by name or city), **Stock Item picker** (Raise PO line items), and **Work Order picker** (Issue Stock modal — search by WO number or customer). Consistent UX across all three: ↑/↓/Enter/Esc keyboard nav, amber hover highlight, green-pill "selected" state with `Change` button, and friendly empty state. PO line items with a shortage-driven prefill (prefill_name) stay locked per business rule. Verified end-to-end: supplier search → Enter → line 1 shaft search → ↓↓ Enter → Add Line → line 2 bearing search → Enter → all three picked correctly.

## P0 — Next
- [ ] **Final Inspection Report** — consolidated PDF combining Pipe WIP QC, Shaft WIP QC, and remaining testing parameters (runout, water, dust, friction, painting) into a single printable sheet per WO for customer/audit sign-off.
- [ ] **Production Dashboard redesign** (reminder noted 2026-02-18) — shortlist below, to be prioritised later:
  * 🟢 Production Kanban (swimlanes per WO stage, drag-to-advance, delivery-urgency dot)
  * 🟢 Delivery timeline / Gantt strip for next 30 days
  * 🟢 WIP QC Health strip (Pipe/Shaft pending+failed tiles → click to QC tab)
  * 🟢 Daily Output Tracker (rollers/day last 14 days with target line)
  * 🟡 Stage Aging / Bottleneck Radar (median & max days per stage)
  * 🟡 Shop-Floor big-screen mode (TV view, auto-refresh, progress rings)
  * 🟡 Material Shortage Dashboard (required vs available per in-progress WO)
  * 🟡 QC Pass-Rate trend (30-day line chart)
  * 🔵 Operator/Machine performance grouping (uses `inspected_by`)
  * 🔵 On-Time Delivery % (last 90 days)
  * 🔵 Revenue-vs-Plan mini chart
  * 🔵 Predictive ETA from historical stage durations

## P1
- [ ] Tax Invoice auto-gen on dispatch
- [ ] Pulley Sub-WOs / Job Cards (unique params, different from rollers)
- [ ] Accounts Receivable / Aging
- [ ] GST Reports (GSTR-1, GSTR-3B)
- [ ] WhatsApp integration (quotes/invoices)
- [ ] E-way bill generation
- [ ] KLA pricing (BLOCKED: waiting user data)
- [ ] ~~Inventory auto-deduct~~ — REJECTED by user; manual Issue Stock flow retained

## P2 — Quality-of-life
- [ ] **Supplier memory on Raise PO** — when user selects a supplier for a stock item, remember & auto-prefill the same supplier the next time that item is ordered (reduces 4–5 clicks for repeat POs).
- [ ] **Final Inspection Report** PDF (Pipe WIP QC + Shaft WIP QC + runout / water / dust / friction / painting tests) for customer & audit sign-off.
- [ ] **Deep-link** 🔴 / 🟡 Material-Status chip on a WO card → Store → Shortages (By Work Order) filtered to that WO.
- [ ] **Production Dashboard** (12 shortlisted ideas — Kanban, Gantt, QC Health strip, Stage Aging, Shop-Floor TV view, Material Shortage dashboard, QC pass-rate trend, Operator performance, On-Time-Delivery KPI, Revenue-vs-Plan, Predictive ETA).
- [ ] **Unresolved BOM Rows → one-click Add to Stock Register** button (auto-fills derived key + sensible name).

## Credentials
- Admin: test@test.com / test123
- Customer: customer@test.com / test123

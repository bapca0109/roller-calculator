# Belt Conveyor Roller Price Calculator - PRD

## Original Problem Statement
Create a mobile application to calculate the price of belt conveyor rollers, serving as an engineering and quoting tool with product catalog search, admin panel for price management, customer database, and complete quote/RFQ workflow.

## Architecture
```
/app
├── backend
│   └── server.py        # FastAPI backend with MongoDB + Export endpoints
└── frontend
    ├── app
    │   ├── auth/login.tsx      # REDESIGNED: Modern industrial login
    │   └── (tabs)
    │       ├── _layout.tsx     # Tab navigation (Products tab)
    │       ├── cart.tsx        # Shopping cart + Export button (REDESIGNED)
    │       ├── calculator.tsx  # Product calculator (REDESIGNED header)
    │       ├── quotes.tsx      # Quote management + Export (REDESIGNED header)
    │       ├── customers.tsx   # Customer management (REDESIGNED)
    │       ├── admin.tsx       # Admin panel (REDESIGNED)
    │       ├── profile.tsx     # User profile (REDESIGNED)
    │       ├── dashboard.tsx   # Admin dashboard (REDESIGNED)
    │       └── search.tsx      # Product search + Export (REDESIGNED)
    ├── components
    │   ├── quotes/             # Extracted quote components
    │   └── shared/
    │       └── ExportButtons.tsx  # Reusable export component
    └── theme/index.ts          # Design system theme (ENHANCED)
```

## What's Been Implemented

### Core Features (Previous Sessions)
- [x] Full-stack application setup with Expo + FastAPI + MongoDB
- [x] User authentication with OTP-based signup/login
- [x] Role-based access control (Admin vs Customer)
- [x] Product calculator for Carrying, Impact, and Return rollers
- [x] Customer management system with auto-incrementing codes
- [x] Quote/RFQ workflow with approval process
- [x] PDF generation for quotes with company logo and weight details
- [x] Email notifications for quote status changes
- [x] Export to PDF/Excel functionality
- [x] Tab renamed from "Calculator" to "Products"
- [x] Component refactoring (QuoteCard, modals extracted)

### March 2026 (This Session) - UI Redesign
- [x] **Login Page**: Complete redesign with modern two-tone layout
  - Carmine Red (#960018) header section
  - White form card with rounded top corners
  - Modern input fields with icons and labels
  - Clean Sign In button design
- [x] **Theme System**: Enhanced `/app/frontend/theme/index.ts`
  - Comprehensive color palette with primary/secondary/status colors
  - Typography system with h1-h3, body, caption styles
  - Component presets for buttons, cards, inputs
  - Common styles exported for header consistency
- [x] **Header Redesign (All Main Screens)**:
  - Dark slate (#0F172A) background
  - 20px border radius on bottom corners
  - Consistent 56px top padding for status bar
  - White titles with 24px font size
  - Slate gray (#94A3B8) subtitles
- [x] **Card Styling Updates**:
  - White background with subtle border (#F1F5F9)
  - 12px border radius
  - Subtle shadow with 0.05 opacity
- [x] **Design Guidelines Created**: `/app/design_guidelines.json`

## Design System

### Colors
| Token | Value | Usage |
|-------|-------|-------|
| Primary | #960018 | Buttons, accents, active states |
| Primary Light | #C41E3A | Hover states |
| Secondary/Dark | #0F172A | Headers, dark backgrounds |
| Background | #F8FAFC | Page backgrounds |
| Surface | #FFFFFF | Cards, modals |
| Text Primary | #0F172A | Headings |
| Text Secondary | #64748B | Body text |
| Text Muted | #94A3B8 | Captions, labels |
| Border | #E2E8F0 | Input borders |
| Border Light | #F1F5F9 | Card borders |

### Typography
- H1: 28px / 700 weight / -0.5 letter spacing
- H2: 24px / 600 weight / -0.3 letter spacing
- H3: 20px / 600 weight
- Body: 16px / 400 weight / 24px line height
- Caption: 12px / 400 weight / 16px line height
- Label: 12px / 600 weight / uppercase / 0.5 letter spacing

### Component Patterns
- **Headers**: Dark background, 20px bottom radius, 56px top padding
- **Cards**: White, 12px radius, 1px border, subtle shadow
- **Buttons**: 12px radius, 54px height, primary color
- **Inputs**: 12px radius, 52px height, light border

## Known Issues

### P1 - High Priority
- [ ] **Login button click issue on web**: TouchableOpacity events not firing reliably in React Native Web. Workaround: JavaScript click() method works.
- [ ] **iOS logout functionality**: Not working (recurring issue, 3x)

### P2 - Medium Priority
- [ ] Android navigation bar overlaps bottom tab bar
- [ ] Login background image doesn't load on web view

### P3 - Low Priority
- [ ] Expo Tunnel instability (ERR_NGROK_3200) - environment issue

## Prioritized Backlog

### P0 - Critical
- [ ] Investigate and fix login button click events for React Native Web
- [ ] Complete refactoring of quotes.tsx (4700+ lines)
- [ ] Complete refactoring of calculator.tsx (3600+ lines)

### P1 - Important
- [ ] Automate freight calculation based on weight
- [ ] Test Export to PDF/Excel functionality end-to-end
- [ ] Refactor backend/server.py into FastAPI routers

### P2 - Nice to Have
- [ ] CRM features (leads, activity timeline, follow-ups)
- [ ] Excel upload for raw material costs
- [ ] Show original RFQ number on quote cards

## Files Modified This Session
- `/app/frontend/theme/index.ts` - Enhanced with comprehensive design tokens
- `/app/frontend/app/auth/login.tsx` - Complete UI redesign
- `/app/frontend/app/(tabs)/calculator.tsx` - Header styling updated
- `/app/frontend/app/(tabs)/quotes.tsx` - Header styling updated
- `/app/frontend/app/(tabs)/cart.tsx` - Header styling updated
- `/app/frontend/app/(tabs)/customers.tsx` - Header styling updated
- `/app/frontend/app/(tabs)/admin.tsx` - Header/tab styling updated
- `/app/frontend/app/(tabs)/profile.tsx` - Card styling updated
- `/app/frontend/app/(tabs)/search.tsx` - Header styling updated
- `/app/frontend/app/(tabs)/dashboard.tsx` - Header styling updated
- `/app/design_guidelines.json` - New file with detailed design specs

## Test Credentials
- **Admin**: test@test.com / test123
- **Customer**: customer@test.com / test123

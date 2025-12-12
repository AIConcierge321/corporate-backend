# 📊 Visual Project Summary

## 🎯 What This Platform Does (One Sentence)

**A complete corporate travel management platform that automates booking, enforces policies, monitors disruptions, issues virtual cards, and provides AI-powered assistance for business travelers.**

---

## 🔄 Complete User Journey (Visual Flow)

```
┌─────────────────────────────────────────────────────────────────┐
│                     1. DISCOVERY PHASE                           │
│                                                                   │
│  User Opens App → Explores Destinations OR Uses AI Concierge     │
│         ↓                                     ↓                   │
│  Browses: London (145 trips/yr, $1850 avg)   "Book London trip"  │
│  Sees: Weather alerts, preferred hotels      AI suggests options │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     2. SEARCH & SELECT                           │
│                                                                   │
│  Search: JFK → LHR, Oct 18-22                                   │
│         ↓                                                         │
│  System calls:                                                    │
│    • Duffel API (50 flight options)                             │
│    • Hotelbeds API (30 hotel options)                           │
│    • Policy Engine (tags each option)                           │
│         ↓                                                         │
│  Results shown:                                                   │
│    ✅ BA 178 Economy - $1,850 (Compliant)                       │
│    ⚠️  BA 178 Business - $3,200 (Requires approval)             │
│    ✅ Hilton Metropole - $245/night (Preferred)                 │
│         ↓                                                         │
│  User selects: Economy flight + Hilton hotel                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     3. DRAFT & POLICY CHECK                      │
│                                                                   │
│  System creates draft:                                           │
│    • INSERT INTO bookings (status='draft', total=$2,830)        │
│    • INSERT INTO booking_segments (flight, hotel)               │
│         ↓                                                         │
│  Policy Engine evaluates:                                        │
│    ✅ Advance booking: 14 days (Pass)                           │
│    ✅ Daily rate: $245 < $300 limit (Pass)                      │
│    ✅ Preferred vendor: Yes (Pass)                              │
│         ↓                                                         │
│  Result: OK (No approval needed)                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     4. CONFIRMATION                              │
│                                                                   │
│  User clicks "Confirm Booking"                                   │
│         ↓                                                         │
│  System executes:                                                │
│    1. Create virtual card (Stripe: $2,830 limit)                │
│    2. Book flight (Duffel: BA178ABC confirmed)                  │
│    3. Book hotel (Hotelbeds: HLT-456 confirmed)                 │
│    4. UPDATE bookings SET status='confirmed'                    │
│    5. PUBLISH booking.created event                             │
│    6. Send confirmation email                                    │
│         ↓                                                         │
│  User receives: Itinerary PDF + Email + SMS                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  5. POST-BOOKING MONITORING                      │
│                                                                   │
│  Background Workers:                                             │
│    • Analytics Worker → Updates spend ($2,830 to Sales dept)   │
│    • Check-In Scheduler → Reminder 24h before departure         │
│    • Disruption Monitor → Polls flight status every 5 min       │
│    • Payment Reconciliation → Matches transactions to invoices  │
│         ↓                                                         │
│  Booking appears in dashboard:                                   │
│    Status: Confirmed | Policy: Compliant | Invoice: Sent        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│          6. DISRUPTION (if it happens)                           │
│                                                                   │
│  Flight BA178 CANCELED (crew strike)                            │
│         ↓                                                         │
│  System responds:                                                │
│    1. INSERT INTO disruption_events                             │
│    2. Send urgent SMS to traveler                               │
│    3. Auto-search alternative flights                           │
│    4. Re-evaluate policies on alternatives                      │
│    5. Present 3 compliant options to traveler                   │
│         ↓                                                         │
│  Traveler selects: UA 1548 (next morning, +$200)                │
│         ↓                                                         │
│  If within policy → Auto-rebook                                 │
│  If over budget → Send approval request                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    7. POST-TRIP                                  │
│                                                                   │
│  • Expense report generated                                     │
│  • Transactions reconciled                                       │
│  • Compliance score updated (+0.5 for on-policy booking)        │
│  • Analytics updated (CO₂: 450kg tracked)                       │
│  • Booking status → 'completed'                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ System Architecture (Simple View)

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Dashboard │  │ Explore  │  │ Bookings │  │   AI     │        │
│  │          │  │          │  │          │  │ Concierge│        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                      Next.js + TypeScript                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓ API Calls
┌─────────────────────────────────────────────────────────────────┐
│                       API GATEWAY LAYER                          │
│                   FastAPI (Port 8000)                            │
│         Authentication • Rate Limiting • Routing                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC LAYER                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Booking  │  │  Policy  │  │ Payment  │  │ Approval │        │
│  │ Service  │  │  Engine  │  │ Service  │  │ Service  │        │
│  │ (8001)   │  │ (8002)   │  │ (8003)   │  │ (8004)   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Duffel  │  │Hotelbeds │  │  Stripe  │  │ OpenAI   │        │
│  │  (Flights)│  │ (Hotels) │  │(Payments)│  │   (AI)   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │   Celery     │          │
│  │  (Database)  │  │ (Cache+Queue)│  │   Workers    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Database At a Glance

**Core Tables:**
```
bookings (main booking records)
  ├─ booking_segments (flights, hotels, cars)
  ├─ policy_evaluations (compliance checks)
  ├─ approval_workflows (multi-step approvals)
  ├─ virtual_cards (payment methods)
  └─ disruption_events (cancellations, delays)

employees (travelers)
policies (rules)
analytics_spend (aggregated metrics)
organizations (multi-tenant)
```

**Relationships:**
```
organizations 1──→ ∞ employees
employees 1──→ ∞ bookings
bookings 1──→ ∞ booking_segments
bookings 1──→ 1 approval_workflow (optional)
bookings 1──→ 1 virtual_card (optional)
bookings 1──→ ∞ disruption_events (optional)
```

---

## 🎨 UI Pages Overview

| Page | Purpose | Key Features |
|------|---------|--------------|
| **Dashboard** | Control center for admins | Critical alerts, pending approvals, budget tracking, traveler status |
| **Explore** | Discover destinations | Destinations list, preferred hotels, travel insights, policy-aware info |
| **Bookings** | Manage all trips | List view, filters, disruption alerts, rebook flow, invoice status |
| **Employees** | Traveler management | Compliance scores, travel preferences, delegates, passport/visa tracking |
| **Payments** | Financial controls | Virtual cards, transactions, reconciliation, flagged expenses |
| **Analytics** | Reporting & insights | Spend charts, compliance metrics, sustainability, top destinations |
| **Policies** | Configure rules | Policy editor, violation tracking, regional rules, approval thresholds |
| **Permissions** | Access control | Roles, delegates, SSO/SCIM integration |
| **AI Concierge** | Natural language booking | Chat interface, context-aware suggestions, policy compliance |

---

## 🔑 Key Workflows

### 1. **Booking Approval Workflow**
```
Employee books Business class ($3,200) for 3hr flight
      ↓
Policy Engine: SOFT_WARNING (requires approval)
      ↓
System creates approval workflow:
  Step 1: Manager (Auto-notified via Email + Slack)
  Step 2: VP Finance (if Manager approves)
      ↓
Manager approves with justification
      ↓
Booking confirmed automatically
      ↓
Employee receives confirmation
```

### 2. **Disruption Auto-Rebook**
```
Flight BA178 canceled (webhook from airline)
      ↓
System detects 4 affected bookings
      ↓
For each booking:
  1. Send urgent SMS to traveler
  2. Search alternative flights (same route, nearby times)
  3. Filter by policy compliance
  4. Rank by: timing > price > convenience
  5. Present top 3 options via email/SMS
      ↓
Traveler clicks option 2 (UA 1548, +$150)
      ↓
IF price increase < 10% → Auto-approve & rebook
ELSE → Send approval request to manager
```

### 3. **Payment Reconciliation**
```
Nightly Job (3:00 AM):
  1. Fetch all unreconciled transactions from Stripe
  2. Match each transaction to booking via virtual_card_id
  3. Compare transaction amount vs booking amount
      ↓
IF amounts match → Mark as reconciled
IF amounts differ → Flag for manual review
  (e.g., unexpected baggage fee, seat upgrade)
      ↓
Finance team reviews flagged transactions
Approve legitimate or dispute fraudulent
```

---

## 📈 Analytics KPIs

**Executive Dashboard shows:**
- Total Spend: $3.6M (5.4% under budget)
- Total Savings: $519K (12.5% savings rate)
- Policy Compliance: 87.3% (+2.3% vs last quarter)
- CO₂ Emissions: 972 tons (6.2% vs target)
- Average Trip Cost: $1,963 (12% below market)

**Department Breakdown:**
- Sales: $198K (89% budget utilization)
- Engineering: $145K (73% utilization)
- Marketing: $87K (67% utilization)

**Booking Distribution:**
- Economy: 68% (1,248 bookings, avg $850)
- Premium Economy: 15% (287 bookings, avg $1,450)
- Business: 16% (298 bookings, avg $3,200)
- First: 1% (18 bookings, avg $5,800)

---

## 🚦 Implementation Priority (What to Build First)

### **Phase 1: MVP (Weeks 1-8)** ⭐ START HERE
- ✅ Basic booking flow (search → select → draft → confirm)
- ✅ Simple policy checks (hard stop only)
- ✅ One flight provider (Duffel)
- ✅ One hotel provider (Hotelbeds)
- ✅ Virtual card issuance (Stripe)
- ✅ Email notifications
- ✅ Basic dashboard

**Deliverable:** End-to-end booking without approvals

---

### **Phase 2: Approvals & Policies (Weeks 9-11)**
- ✅ Multi-step approval workflows
- ✅ Soft warnings
- ✅ Regional policies
- ✅ SMS notifications

**Deliverable:** Policy-aware bookings with approvals

---

### **Phase 3: Disruption Management (Weeks 12-14)**
- ✅ Flight status monitoring
- ✅ Auto-rebook engine
- ✅ Disruption alerts

**Deliverable:** Real-time disruption handling

---

### **Phase 4: Analytics (Weeks 15-17)**
- ✅ Spend aggregation
- ✅ Compliance metrics
- ✅ CO₂ tracking
- ✅ Executive reports

**Deliverable:** Full analytics dashboard

---

### **Phase 5: Advanced Features (Weeks 18-25)**
- Payment reconciliation
- Employee management
- AI Concierge
- Platform admin

**Deliverable:** Complete platform

---

## 🛠️ Tech Stack Summary

**Frontend Stack:**
```
Next.js 14 (React framework)
  └─ TypeScript (type safety)
     └─ Tailwind CSS (styling)
        └─ Zustand (state management)
           └─ React Query (API calls)
```

**Backend Stack:**
```
FastAPI (Python framework)
  └─ SQLAlchemy (ORM)
     └─ Alembic (migrations)
        └─ Pydantic (validation)
           └─ Celery (background jobs)
```

**Infrastructure Stack:**
```
AWS (hosting)
  ├─ EC2 (compute)
  ├─ RDS (PostgreSQL database)
  ├─ ElastiCache (Redis)
  ├─ S3 (file storage)
  └─ CloudWatch (monitoring)
```

---

## 📦 Quick Start Checklist

**To run this project locally:**

- [ ] Install Docker
- [ ] Install Python 3.11+
- [ ] Install Node.js 18+
- [ ] Clone repository
- [ ] Start PostgreSQL (via Docker)
- [ ] Start Redis (via Docker)
- [ ] Run backend migrations
- [ ] Seed database with test data
- [ ] Start FastAPI server (port 8000)
- [ ] Start Next.js dev server (port 3000)
- [ ] Start Celery workers
- [ ] Login with test credentials
- [ ] Make a test booking!

**Total setup time:** ~15 minutes

---

## 🎯 Success Metrics

**After full implementation, this platform will:**

✅ **Automate 87%** of bookings (no manual intervention)  
✅ **Save 12.5%** vs market rates through supplier negotiations  
✅ **Reduce policy violations** by 40% via real-time enforcement  
✅ **Resolve 94%** of disruptions automatically  
✅ **Cut booking time** from 45 minutes to 5 minutes  
✅ **Provide 100%** visibility into travel spend  
✅ **Track & offset** 100% of CO₂ emissions  

---

## 📞 Need Help?

- **Documentation**: `/docs` folder
- **Architecture**: `ARCHITECTURE.md`
- **Sequence Diagrams**: `docs/SEQUENCE_DIAGRAMS.md`
- **Service Details**: `docs/SERVICE_ARCHITECTURE.md`
- **Data Flow**: `docs/DATA_FLOW.md`

**Happy Building! 🚀**

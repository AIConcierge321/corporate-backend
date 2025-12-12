# Corporate Travel Management Platform

> **Complete end-to-end corporate travel booking and management platform with AI-powered concierge, disruption monitoring, and comprehensive analytics.**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Architecture Overview](#architecture-overview)
4. [Documentation](#documentation)
5. [Tech Stack](#tech-stack)
6. [Getting Started](#getting-started)
7. [Project Structure](#project-structure)
8. [Development Workflow](#development-workflow)
9. [API Documentation](#api-documentation)
10. [Deployment](#deployment)
11. [Contributing](#contributing)

---

## 🎯 Overview

This platform revolutionizes corporate travel management by:

- **Automating bookings** across flights, hotels, and ground transportation
- **Enforcing travel policies** with real-time compliance checking & approvals
- **Monitoring disruptions** with auto-rebooking capabilities
- **Tracking spending** with analytics, budgets, and savings attribution
- **Ensuring duty of care** with traveler tracking and alerts
- **Issuing virtual cards** for secure, controlled payments
- **Providing AI assistance** through natural language booking

### User Personas

1. **Travelers** - Book trips via AI Concierge or Explore page
2. **Travel Admins** - Manage bookings, handle disruptions
3. **Approvers** - Review and approve policy exceptions
4. **Finance Teams** - Track spending, reconcile payments
5. **Platform Admins** - Manage multiple client organizations

---

## ✨ Key Features

### 🔍 **Intelligent Search & Booking**
- Multi-provider aggregation (flights, hotels, cars)
- Policy-aware filtering (compliant options highlighted)
- Vendor ranking (preferred suppliers first)
- Real-time pricing
- Weather alerts integration

### 🛡️ **Policy Engine**
- **Hard Stop**: Block non-compliant bookings
- **Soft Warning**: Require approval for exceptions
- **Track Only**: Monitor for reporting
- Regional & department-specific rules
- Version management

### ✅ **Approval Workflows**
- Multi-step approvals (Manager → VP → Executive)
- SLA tracking & auto-escalation
- Delegate booking on behalf of others
- Mobile-friendly approval interface
- Audit trail

### 🚨 **Disruption Management**
- Real-time flight status monitoring
- Automated disruption detection
- Auto-rebooking suggestions
- Traveler notifications (SMS, Email, Push)
- Travel ops dashboard

### 💳 **Payment Management**
- Virtual card issuance (Stripe Issuing)
- Corporate card management
- Transaction reconciliation
- Fraud detection
- Spend controls

### 📊 **Analytics & Reporting**
- Department & employee spend tracking
- Savings vs market rates
- Policy compliance metrics
- CO2 emissions tracking
- Custom reports & exports

### 🤖 **AI Travel Concierge**
- Natural language booking
- Context-aware suggestions
- Policy-compliant recommendations
- Conversation history
- Function calling (search, book, check policy)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACES                         │
│  Next.js Web App  │  Mobile App (Future)  │  Admin Portal   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY                             │
│                   FastAPI (Port 8000)                        │
│              Authentication • Rate Limiting                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    CORE SERVICES                             │
│  Booking  │  Policy  │  Payment  │  Approval  │  AI  │  ... │
│  (8001)   │  (8002)  │  (8003)   │  (8004)    │ (8007) │    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  EXTERNAL INTEGRATIONS                       │
│  Duffel  │ Amadeus │ Hotelbeds │ Stripe │ Twilio │ OpenAI  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   DATA & INFRASTRUCTURE                      │
│  PostgreSQL  │  Redis  │  S3  │  Celery Workers  │  Logs   │
└─────────────────────────────────────────────────────────────┘
```

**Key Architectural Principles:**

- **Microservices**: Each service has a single responsibility
- **Event-Driven**: Asynchronous processing via Redis/Celery
- **Idempotent**: Safe retries for all booking operations
- **Multi-Tenant**: Organization-level data isolation
- **Resilient**: Circuit breakers, retries, fallbacks

👉 **[See detailed architecture →](./ARCHITECTURE.md)**

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Complete system architecture, database schema, API specs |
| **[SEQUENCE_DIAGRAMS.md](./docs/SEQUENCE_DIAGRAMS.md)** | Detailed sequence diagrams for all critical flows |
| **[SERVICE_ARCHITECTURE.md](./docs/SERVICE_ARCHITECTURE.md)** | Service breakdown, responsibilities, implementation checklist |
| **[DATA_FLOW.md](./docs/DATA_FLOW.md)** | UI state machines, API payloads, database transactions |

### Quick Links

- [End-to-End Booking Flow](./ARCHITECTURE.md#end-to-end-user-flow)
- [Database Schema](./ARCHITECTURE.md#database-schema)
- [API Endpoints](./ARCHITECTURE.md#api-specifications)
- [Implementation Roadmap](./ARCHITECTURE.md#implementation-roadmap)
- [Sequence Diagrams](./docs/SEQUENCE_DIAGRAMS.md)

---

## 🛠️ Tech Stack

### **Frontend**
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS / Custom CSS
- **State Management**: Zustand
- **API Client**: React Query (TanStack Query)
- **Charts**: Chart.js / Recharts
- **Forms**: React Hook Form + Zod

### **Backend**
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Cache**: Redis 7
- **Queue**: Celery + Redis
- **Validation**: Pydantic v2

### **External APIs**
- **Flights**: Duffel, Amadeus
- **Hotels**: Hotelbeds, Expedia
- **Cars**: Avis, Hertz
- **Payments**: Stripe Issuing
- **Notifications**: Twilio (SMS), SendGrid (Email)
- **Weather**: OpenWeatherMap
- **Visa**: Sherpa
- **HR**: Workday (SCIM)
- **AI**: OpenAI GPT-4

### **Infrastructure**
- **Hosting**: AWS (EC2, RDS, S3, SQS)
- **Containers**: Docker + Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoring**: CloudWatch, New Relic, Datadog
- **Logging**: CloudWatch Logs / ELK Stack

---

## 🚀 Getting Started

### Prerequisites

```bash
# Install required tools
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL client (psql)
- Redis client (redis-cli)
```

### Local Development Setup

#### 1. Clone repository
```bash
git clone https://github.com/yourorg/corporate-travel.git
cd corporate-travel
```

#### 2. Backend setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start database & Redis via Docker
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed_db.py

# Start API server
uvicorn app.main:app --reload --port 8000
```

**Backend will be available at:** `http://localhost:8000`  
**API Docs:** `http://localhost:8000/docs`

#### 3. Frontend setup
```bash
cd ../frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local

# Update .env.local with:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Start development server
npm run dev
```

**Frontend will be available at:** `http://localhost:3000`

#### 4. Start background workers (separate terminal)
```bash
cd backend
celery -A app.workers worker --loglevel=info
```

#### 5. Access the app
- **Web App**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:3000/admin

**Default Login:**
- Email: `admin@example.com`
- Password: `admin123`

---

## 📁 Project Structure

```
corporate-travel/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── api/
│   │   │   ├── bookings.py         # Booking endpoints
│   │   │   ├── policies.py         # Policy endpoints
│   │   │   ├── payments.py         # Payment endpoints
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── booking_service.py  # Business logic
│   │   │   ├── policy_engine.py
│   │   │   ├── payment_service.py
│   │   │   └── ...
│   │   ├── adapters/
│   │   │   ├── flights/
│   │   │   │   ├── duffel_adapter.py
│   │   │   │   └── amadeus_adapter.py
│   │   │   ├── hotels/
│   │   │   │   ├── hotelbeds_adapter.py
│   │   │   │   └── expedia_adapter.py
│   │   │   └── ...
│   │   ├── models/
│   │   │   ├── booking.py          # SQLAlchemy models
│   │   │   ├── policy.py
│   │   │   └── ...
│   │   ├── schemas/
│   │   │   ├── booking.py          # Pydantic schemas
│   │   │   └── ...
│   │   └── workers/
│   │       ├── analytics_worker.py
│   │       ├── disruption_monitor.py
│   │       └── ...
│   ├── alembic/                    # Database migrations
│   ├── tests/
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx            # Main dashboard
│   │   │   ├── explore/
│   │   │   ├── bookings/
│   │   │   ├── employees/
│   │   │   ├── payments/
│   │   │   ├── analytics/
│   │   │   ├── policies/
│   │   │   └── ai-concierge/
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                     # Reusable UI components
│   │   ├── BookingCard.tsx
│   │   ├── DisruptionAlert.tsx
│   │   └── ...
│   ├── stores/
│   │   ├── bookingsStore.ts        # Zustand stores
│   │   ├── dashboardStore.ts
│   │   └── ...
│   ├── lib/
│   │   ├── api.ts                  # API client
│   │   └── utils.ts
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
│
├── docs/
│   ├── SEQUENCE_DIAGRAMS.md
│   ├── SERVICE_ARCHITECTURE.md
│   └── DATA_FLOW.md
│
├── ARCHITECTURE.md
└── README.md (this file)
```

---

## 🔄 Development Workflow

### Feature Development

1. **Create feature branch**
```bash
git checkout -b feature/add-car-rental-support
```

2. **Backend development**
```bash
# Create new service/adapter
touch backend/app/adapters/cars/avis_adapter.py

# Add routes
# Edit backend/app/api/bookings.py

# Write tests
touch backend/tests/test_car_booking.py

# Run tests
pytest backend/tests/

# Check linting
ruff check backend/
black backend/
```

3. **Frontend development**
```bash
# Create new component
touch frontend/components/CarSelection.tsx

# Update page
# Edit frontend/app/(dashboard)/bookings/page.tsx

# Run type check
npm run type-check

# Run linting
npm run lint
```

4. **Run locally & test**
```bash
# Backend
uvicorn app.main:app --reload

# Frontend
npm run dev

# Workers
celery -A app.workers worker --loglevel=info
```

5. **Commit & push**
```bash
git add .
git commit -m "feat: add car rental booking support"
git push origin feature/add-car-rental-support
```

6. **Create pull request**
- Open PR on GitHub
- Wait for CI checks (tests, linting)
- Request review from team
- Merge after approval

---

## 📖 API Documentation

### Interactive API Docs

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### **Bookings**
```
POST   /bookings/search          Search flights, hotels, cars
POST   /bookings/draft           Create draft booking
POST   /bookings/{id}/confirm    Confirm booking
GET    /bookings                 List bookings
GET    /bookings/{id}            Get booking details
PATCH  /bookings/{id}/cancel     Cancel booking
POST   /bookings/{id}/rebook     Rebook after disruption
```

#### **Policies**
```
POST   /policies/evaluate        Evaluate single booking
POST   /policies/bulk-evaluate   Evaluate multiple options
GET    /policies                 List policies
POST   /policies                 Create policy
PATCH  /policies/{id}            Update policy
```

#### **Payments**
```
POST   /payments/virtual-cards   Create virtual card
GET    /payments/virtual-cards   List cards
GET    /payments/transactions    List transactions
POST   /payments/reconcile       Manual reconciliation
```

#### **Approvals**
```
POST   /approvals/start          Create approval workflow
POST   /approvals/{id}/approve   Approve step
POST   /approvals/{id}/reject    Reject booking
GET    /approvals/pending        List pending approvals
```

#### **Analytics**
```
GET    /analytics/spend          Spend summary
GET    /analytics/compliance     Compliance metrics
GET    /analytics/destinations   Top destinations
POST   /analytics/reports/export Export PDF report
```

### Example Requests

**Search flights:**
```bash
curl -X POST http://localhost:8000/bookings/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 42,
    "origin": "JFK",
    "destination": "LHR",
    "depart_date": "2025-10-18",
    "return_date": "2025-10-22"
  }'
```

**Create draft:**
```bash
curl -X POST http://localhost:8000/bookings/draft \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 42,
    "org_id": "org-abc",
    "selections": {
      "flight": "FL-001",
      "hotel": "HT-001"
    }
  }'
```

---

## 🚢 Deployment

### Docker Build

```bash
# Build backend
docker build -t corporate-travel-api ./backend

# Build frontend
docker build -t corporate-travel-web ./frontend

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### AWS Deployment (Terraform)

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply
terraform apply
```

**Infrastructure includes:**
- ECS Fargate for API & workers
- RDS PostgreSQL
- ElastiCache Redis
- S3 for documents
- CloudFront CDN
- ALB for load balancing
- Route53 for DNS

### Environment Variables

**Backend (.env):**
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/corporate_travel
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
DUFFEL_API_KEY=your-duffel-key
STRIPE_SECRET_KEY=sk_test_...
SENDGRID_API_KEY=SG....
TWILIO_ACCOUNT_SID=AC...
OPENAI_API_KEY=sk-...
```

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_booking_service.py

# Run specific test
pytest tests/test_booking_service.py::test_create_booking
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm run test

# Run E2E tests (Playwright)
npm run test:e2e

# Run with coverage
npm run test:coverage
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Duffel](https://duffel.com) for flight APIs
- [Stripe](https://stripe.com) for payment infrastructure
- [OpenAI](https://openai.com) for AI capabilities
- [FastAPI](https://fastapi.tiangolo.com) for backend framework
- [Next.js](https://nextjs.org) for frontend framework

---

## 📞 Support

- **Documentation**: See `/docs` folder
- **Issues**: [GitHub Issues](https://github.com/yourorg/corporate-travel/issues)
- **Email**: support@example.com
- **Slack**: [Join our workspace](https://example.slack.com)

---

**Built with ❤️ by the Travel Platform Team**

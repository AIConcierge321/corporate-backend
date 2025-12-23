# Corporate Travel Platform - Backend API

High-performance asynchronous backend for the Corporate Travel Management Platform, built with modern Python tools.

## 🚀 Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Async)
- **Database:** PostgreSQL (with [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) + `asyncpg`)
- **Caching & Queues:** Redis (with `redis-py` async)
- **Authentication:** OAuth2/SSO with JWT, SCIM user provisioning
- **Package Manager:** [uv](https://github.com/astral-sh/uv) (Blazing fast Python package installer)
- **Migrations:** Alembic
- **Testing:** Pytest (100% passing)

---

## ✅ Features Implemented

### Core Platform
| Feature | Status | Description |
|---------|--------|-------------|
| **Authentication & SSO** | ✅ | Google/Microsoft SSO, JWT tokens |
| **SCIM Provisioning** | ✅ | Auto-sync users from HR systems |
| **Role-Based Access Control** | ✅ | 6 role templates, dynamic permissions |
| **Booking Workflow** | ✅ | Full lifecycle with state machine |
| **Approval System** | ✅ | Manager approvals, policy enforcement |
| **Audit Logging** | ✅ | Full action history |
| **Notifications** | ✅ | Basic notifications (console) |

### Travel Services
| Service | Status | API Provider |
|---------|--------|--------------|
| **Train Booking** | ✅ Real API | All Aboard (30+ operators, 17K+ stations) |
| **Flight Search** | 🔶 Mock | Needs Duffel/Amadeus |
| **Hotel Search** | 🔶 Mock | Needs Booking.com/Expedia |
| **Airport Transfers** | 🔶 Mock | Ready for AirportTransfer.com |
| **Destinations** | ✅ | Static curated data |

### Train API (All Aboard Integration)
- **Station Search** - 17,000+ European stations
- **Journey Search** - Real-time via GraphQL WebSocket streaming
- **30+ Rail Operators** - Deutsche Bahn, SNCF, Eurostar, Trenitalia, SJ, Thalys, etc.
- **15+ Countries** - Germany, France, UK, Italy, Spain, Sweden, and more

---

## 🛠️ Setup & Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 1. Clone the repository
```bash
git clone https://github.com/AIConcierge321/corporate-backend.git
cd corporate-backend/backend
```

### 2. Environment Setup
Create a `.env` file:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5435/corporate_travel
REDIS_URL=redis://localhost:6385/0
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# External APIs
ALLABOARD_API_KEY=your-allaboard-api-key          # Train booking
AIRPORT_TRANSFER_API_KEY=your-transfer-api-key    # Airport transfers
```

### 3. Start Infrastructure
```bash
docker compose up -d
```

### 4. Install Dependencies & Run Migrations
```bash
uv sync
uv run alembic upgrade head
uv run python scripts/seed_roles.py  # Seed default roles
```

### 5. Run the Server
```bash
uv run uvicorn app.main:app --reload
```

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health

---

## 📡 API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/sso/callback` | POST | SSO login |
| `/auth/me` | GET | Current user profile |

### Roles & Permissions
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/roles/templates` | GET/POST | List/create role templates |
| `/roles/assign` | POST | Assign role to employee |
| `/roles/permissions` | GET | List available permissions |

### Bookings
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/bookings` | GET/POST | List/create bookings |
| `/bookings/{id}` | GET/PUT | Get/update booking |
| `/bookings/{id}/submit` | POST | Submit for approval |
| `/approvals` | GET | Pending approvals |
| `/approvals/{id}/approve` | POST | Approve booking |

### Train Booking (All Aboard)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/trains/status` | GET | API status (production/test) |
| `/trains/stations` | GET | Search train stations |
| `/trains/search` | POST | Search train journeys |
| `/trains/offers` | POST | Get journey pricing |
| `/trains/book` | POST | Create booking |
| `/trains/booking/{id}` | PUT | Update passenger details |
| `/trains/booking/{id}/confirm` | POST | Confirm order |
| `/trains/order/{id}/finalize` | POST | Issue tickets |
| `/trains/order/{id}` | GET | Get order status |

### Airport Transfers
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/transfers/status` | GET | API status (mock/real) |
| `/transfers/airports` | GET | Search airports |
| `/transfers/quotes` | POST | Get transfer quotes |
| `/transfers/book` | POST | Create booking |

### Search (Mock)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search/flights` | POST | Search flights |
| `/search/hotels` | POST | Search hotels |
| `/search/airports` | GET | Search airports |

---

## 📂 Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/    # Route handlers
│   │   ├── auth.py          # Authentication
│   │   ├── roles.py         # Role management
│   │   ├── bookings.py      # Booking CRUD
│   │   ├── approvals.py     # Approval workflow
│   │   ├── trains.py        # Train booking (All Aboard)
│   │   ├── transfers.py     # Airport transfers
│   │   ├── search.py        # Flight/Hotel search
│   │   └── destinations.py  # Destination intelligence
│   ├── core/                # Config, security, access control
│   ├── db/                  # Database session
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   └── services/
│       ├── suppliers/       # External API clients
│       │   ├── allaboard_client.py      # Train API
│       │   ├── airport_transfer_client.py
│       │   ├── mock_flight_client.py
│       │   └── mock_hotel_client.py
│       ├── booking_workflow.py  # State machine
│       └── notification_service.py
├── alembic/                 # Database migrations
├── scripts/
│   └── seed_roles.py        # Default role templates
└── docker-compose.yml
```

---

## 🔮 Roadmap (Remaining)

| Priority | Feature |
|----------|---------|
| High | Real Flight API (Duffel/Amadeus) |
| High | Real Hotel API (Booking.com) |
| High | Payment Gateway (Stripe) |
| High | Booking Confirmation (PNR storage) |
| Medium | Expense Management (Concur/SAP) |
| Medium | Disruption Alerts & Rebooking |
| Medium | Reporting Dashboards |
| Low | Calendar Sync (Outlook/Google) |
| Low | Multi-Currency & FX |
| Low | Traveler Profiles |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch
5. Open a Pull Request

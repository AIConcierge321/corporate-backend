# Corporate Travel Platform - Backend API

High-performance asynchronous backend for the Corporate Travel Management Platform, built with modern Python tools.

## 🚀 Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Async)
- **Database:** PostgreSQL (with [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) + `asyncpg`)
- **Caching & Queues:** Redis (with `redis-py` async)
- **Authentication:** OAuth2 with JWT (Access + Refresh Tokens), Argon2 hashing, and Redis-based token blacklisting.
- **Package Manager:** [uv](https://github.com/astral-sh/uv) (Blazing fast Python package installer)
- **Migrations:** Alembic
- **Testing:** Pytest (Planned)

---

## 🛠️ Setup & Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 1. clone the repository
```bash
git clone https://github.com/AIConcierge321/corporate-backend.git
cd corporate-backend/backend
```

### 2. Environment Setup
Create a `.env` file in the `backend/` directory (or use default for local dev):

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5435/corporate_travel
REDIS_URL=redis://localhost:6385/0
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3. Start Infrastructure (Postgres & Redis)
Reference the `docker-compose.yml` to start local services.
**Note:** Ports are mapped to `5435` (Postgres) and `6385` (Redis) to avoid conflicts with default local services.

```bash
docker compose up -d
```

### 4. Install Dependencies
```bash
uv sync
```

### 5. Run Migrations
apkpply database schema:
```bash
uv run alembic upgrade head
```

### 6. Run the Server
```bash
uv run uvicorn app.main:app --reload
```

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health

---

## 🔐 Authentication Features

The system implements a secure, stateless authentication flow:

1.  **Register:** `POST /api/v1/auth/register` (Hashes password with Argon2)
2.  **Login:** `POST /api/v1/auth/login` (Returns Access + Refresh Tokens)
3.  **Refresh:** `POST /api/v1/auth/refresh` (Get new Access Token, rotates security)
4.  **Logout:** `POST /api/v1/auth/logout` (Blacklists tokens in Redis)
5.  **Profile:** `GET /api/v1/auth/me` (Protected route)

**Security Measures:**
- **Argon2id:** Memory-hard password hashing to prevent GPU cracking.
- **Redis Blacklist:** Immediate token revocation upon logout.
- **JWT:** Stateless validation for high scaling.

---

## 📂 Project Structure

```
backend/
├── app/
│   ├── api/            # Route handlers (v1/endpoints/...)
│   ├── core/           # Config & Security (JWT, Hashing)
│   ├── db/             # Database session & base models
│   ├── models/         # SQLAlchemy Database Models
│   ├── schemas/        # Pydantic Schemas (Request/Response)
│   ├── services/       # Business Logic (Auth, Redis, etc.)
│   └── main.py         # App Entrypoint
├── alembic/            # Database Migrations
├── pyproject.toml      # Dependencies (uv managed)
└── docker-compose.yml  # Local Infrastructure
```

## 🤝 Contributing

1. Fork the repo.
2. Create a feature branch.
3. Commit changes (`git commit -m 'feat: add amazing feature'`).
4. Push to branch.
5. Open a Pull Request.

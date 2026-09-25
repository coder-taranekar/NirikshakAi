# Tech Stack & Build System

## Backend (Python 3.11)

| Component | Library / Version |
|---|---|
| API Framework | FastAPI 0.111.0 |
| ASGI Server | Uvicorn 0.29.0 (with standard extras) |
| Database | PostgreSQL 15 (via psycopg2-binary 2.9.9) |
| ORM | SQLAlchemy 2.0.30 (declarative, synchronous) |
| Migrations | Alembic 1.13.1 |
| Settings | pydantic-settings 2.2.1 + python-dotenv 1.0.1 |
| Object Storage | MinIO 7.2.7 (S3-compatible) |
| Cache / Queue | Redis 5.0.4 |
| Auth | python-jose[cryptography] 3.3.0 (JWT) + passlib[bcrypt] 1.7.4 |
| Rate Limiting | slowapi 0.1.9 |
| Logging | structlog 24.1.0 (structured JSON) |
| OCR Primary | google-cloud-vision 3.7.2 |
| OCR Fallback | easyocr 1.7.1 (en + hi/Devanagari) + torch 2.2.2 (CPU) |
| Image Processing | Pillow 10.3.0 + opencv-python-headless 4.9.0.80 + numpy 1.26.4 |
| PDF Reports | WeasyPrint 62.3 + Jinja2 3.1.4 |
| Excel Reports | openpyxl 3.1.2 |
| DOCX Reports | python-docx 1.1.2 |
| URL Scraping | httpx 0.27.0 + beautifulsoup4 4.12.3 + lxml 5.2.1 |
| Testing | pytest 8.2.0 + pytest-cov 5.0.0 |

All dependency versions are **pinned exactly** in `backend/requirements.txt`. Never use open version ranges.

## Frontend — Web (planned, not yet scaffolded)

React (Vite) · TailwindCSS · Recharts · Axios · React Router v6 · Zustand · react-pdf

## Mobile (planned, not yet scaffolded)

React Native (Expo SDK) · React Navigation · expo-camera · expo-secure-store · AsyncStorage · @react-native-community/netinfo · expo-haptics

## Infrastructure

- **Docker Compose** — 5 services: `db` (PostgreSQL 15-alpine), `minio`, `minio_init` (bucket setup), `redis` (7-alpine), `backend`
- **Nginx** — reverse proxy (nginx.conf in project root)
- All services connected via `labelguard_net` bridge network
- Backend hot-reloads in dev via volume mount (`./backend:/app`)

## Common Commands

### Start full stack (first time)
```bash
cp .env.example .env   # fill in values
docker-compose up --build
```

### Start (subsequent)
```bash
docker-compose up
```

### Stop
```bash
docker-compose down
```

### Stop and remove volumes (full reset)
```bash
docker-compose down -v
```

### Backend only (local dev without Docker)
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m app.utils.seed
uvicorn app.main:app --reload --port 8000
```

### Run database migrations
```bash
# From backend/ directory (or inside container)
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description_of_change"
```

### Run tests
```bash
cd backend
pytest
pytest --cov=app tests/
```

## Service URLs (default dev)

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## Environment Variables

All config is in `.env` (copy from `.env.example`). Key groups:

- `APP_ENV`, `APP_PORT`, `SECRET_KEY`
- `DATABASE_URL`, `POSTGRES_USER/PASSWORD/DB`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET_IMAGES`, `MINIO_BUCKET_REPORTS`
- `REDIS_URL`
- `JWT_SECRET_KEY`, `JWT_ALGORITHM` (HS256), `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- `GOOGLE_CLOUD_VISION_API_KEY`
- `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (seeded on first startup)
- `CORS_ORIGINS` (comma-separated list)

Settings are loaded via `app.config.Settings` (pydantic-settings) and cached with `@lru_cache()`. Use `Depends(get_settings)` for dependency injection; `from app.config import settings` for module-level access.

## Backend Startup Sequence (Dockerfile CMD)
```
alembic upgrade head → python -m app.utils.seed → uvicorn app.main:app
```

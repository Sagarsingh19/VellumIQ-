# VellumIQ: Production-Grade Multi-Modal Document Intelligence SaaS

VellumIQ is a high-fidelity, production-grade **Document Intelligence platform** designed to reliably convert financial documents (starting with invoices) into validated, structured JSON data with confidence scoring and human-in-the-loop manual correction workflows.

It is built as a commercial-ready SaaS architecture rather than a simple LLM wrapper, featuring asynchronous job scheduling, multi-tenant database designs, and zero-config local development setups.

---

## 🚀 Key Architectural Features

- **Multi-Tenant Isolation**: Enforces tenant-level data security where resource requests (documents, extractions, audits) are strictly checked against user organization memberships.
- **Asynchronous Task Workers**: PDF ingestion, page rasterization, layout extraction, and parsing jobs are executed in background worker queues (Celery + Redis) to maintain responsive, low-latency API connections.
- **Modular Object Storage Abstraction**: Supports S3-compliant providers (e.g. AWS S3, MinIO) in production while falling back seamlessly to a local directory backend (`storage_local/`) for quick offline development onboarding.
- **High-Fidelity OCR Engine**: Integrates a layout-aware PDF parser (using `pdfplumber`) that reconstructs horizontal word baselines, sequences reading order, and extracts coordinate-level bounding boxes.
- **Pre-processing Rasterizer**: Converts PDF pages programmatically at 150 DPI into clean PNG page images (using `PyMuPDF`) for rendering coordinate highlights on the front-end.
- **Testing Portability**: Zero-config test suite runs fully on an in-memory SQLite setup using dedicated drop/create test database tables, verifying auth scopes and end-to-end task pipelines.

---

## 🛠 Tech Stack

- **Backend**: Python 3.11, FastAPI (async routing), Pydantic (data validations).
- **ORM & Migrations**: SQLAlchemy 2.0, Alembic.
- **Queue & Worker**: Celery, Redis.
- **Database**: PostgreSQL (dev/prod), SQLite (testing/local fallback).
- **Storage**: S3-compatible (MinIO / AWS S3) or Local Directory.
- **Libraries**: pdfplumber (layout parsing), PyMuPDF / fitz (page rendering), google-genai (Gemini SDK).

---

## 📂 Project Structure

```text
├── backend/
│   ├── alembic/              # Database version control & migrations
│   ├── app/
│   │   ├── api/              # Route endpoints & authentication guards
│   │   ├── core/             # Settings, Database engines, Security, Storage backends
│   │   ├── models/           # SQLAlchemy database entities (multi-tenant)
│   │   ├── schemas/          # Pydantic schemas (auth, documents, OCR data)
│   │   ├── services/         # Core business logic & OCR engines
│   │   ├── tasks/            # Celery asynchronous parsing pipelines
│   │   └── tests/            # Pytest test suite (auth flow & document uploads)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
└── docker-compose.yml        # Multi-service configuration (Postgres, Redis, MinIO)
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Environment Configuration
Create a `.env` file in the `backend/` directory by copying `.env.example`:
```bash
cp backend/.env.example backend/.env
```

### 3. Initialize Virtual Environment & Install Dependencies
```bash
python -m venv .venv
.venv\Scripts\activate      # On Windows
pip install -r backend/requirements.txt
```

### 4. Run the API locally (using SQLite & Local Storage fallback)
```bash
cd backend
python -m uvicorn app.main:app --reload
```

---

## 🧪 Testing Verification

Run the integration tests to verify database migrations, token auth, file size limits, and asynchronous queue state transitions:
```bash
cd backend
python -m pytest -v
```
All tests run against a localized SQLite environment and cleanup test databases/files on teardown.

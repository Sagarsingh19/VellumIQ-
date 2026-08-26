# VellumIQ: Production-Grade Multi-Modal Document Intelligence SaaS

VellumIQ is a high-fidelity, commercial-ready **Document Intelligence platform** designed to reliably convert financial documents (starting with invoices) into validated, structured JSON data with multi-signal confidence scoring, developer API key authentication, and human-in-the-loop manual review dashboards.

It features a multi-tenant backend architecture and a modern, responsive single-page client interface built for commercial portfolios.

---

## 🚀 Key Architectural Features

- **Multi-Tenant Isolation**: Enforces tenant-level data security where resource requests (documents, extractions, audits, API keys) are strictly checked against user organization memberships.
- **Dual-Authentication Core**: Authorizes requests using EITHER web-based JWT Bearer Tokens or developer-facing `X-API-Key` headers for headless scanner/CLI ingestion scripts.
- **Asynchronous Task Workers**: PDF ingestion, page rasterization, layout extraction, and parsing jobs are executed in background worker queues (Celery + Redis) to maintain responsive, low-latency API connections.
- **High-Fidelity OCR Engine**: Integrates a layout-aware PDF parser (using `pdfplumber`) that reconstructs horizontal word baselines, sequences reading order, and extracts coordinate-level bounding boxes.
- **Pre-processing Rasterizer**: Converts PDF pages programmatically at 150 DPI into clean PNG page images (using `PyMuPDF`) for rendering coordinate highlights on the front-end canvas.
- **Interactive Review Canvas**: A side-by-side frontend split panel mapping backend character pixel coordinates onto a responsive HTML overlay, providing interactive tooltips on line hover.
- **Deterministic Math & Validation Checks**: Implements programmatic rules confirming grand totals (`subtotal + tax - discount == total` with rounding tolerance), date order, and line-item math checks.
- **Multi-Signal Confidence Engine**: Calculates overall document and field-level confidence scores based on OCR word coordinates and validation math results. Low scores (<0.85) or invalid math route files automatically to `REVIEW_REQUIRED`.
- **Human-in-the-Loop Review Panel**: Exposes routes enabling human correction of parsed fields. Submissions overwrite extractions, reset field confidence metrics to `1.0`, trigger validation checks, and log detailed entries to the `reviews` and `audit_logs` history tables.
- **Stripe Billing & Quotas**: Features checkout upgrades and Stripe Webhook event listeners supporting pricing tiers (`FREE`, `GROWTH`, `ENTERPRISE`). Page limits are enforced per organization billing cycle.

---

## 🛠 Tech Stack

- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons, Axios.
- **Backend**: Python 3.11, FastAPI (async routing), Pydantic (data validations), SQLAlchemy 2.0, Alembic.
- **Queue & Worker**: Celery, Redis.
- **Database**: PostgreSQL (dev/prod), SQLite (testing/local fallback).
- **Storage**: S3-compatible (MinIO / AWS S3) or Local Directory.
- **Libraries**: `pdfplumber` (layout parsing), `PyMuPDF` / `fitz` (page rendering), `google-genai` (Gemini SDK).

---

## 📂 Project Structure

```text
├── backend/                  # FastAPI Backend Application
│   ├── alembic/              # Database version control & migrations
│   ├── app/
│   │   ├── api/              # Route endpoints & authentication guards
│   │   ├── core/             # Settings, Database engines, Security, Storage backends
│   │   ├── models/           # SQLAlchemy database entities (multi-tenant)
│   │   ├── schemas/          # Pydantic schemas (auth, documents, OCR data)
│   │   ├── services/         # Core business logic & OCR engines
│   │   ├── tasks/            # Celery asynchronous parsing pipelines
│   │   └── tests/            # Pytest test suite (auth flow & document uploads)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # Next.js Client Application
│   ├── src/
│   │   ├── app/              # Next.js page routers (auth, dashboard console)
│   │   ├── components/       # Dropzone uploader, DocumentViewer, FieldEditor Form
│   │   ├── context/          # Auth state & active organization context
│   │   ├── services/         # Axios API clients (documents, auth, billing)
│   │   └── types/            # TypeScript interface contracts
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── next.config.mjs       # Proxy configurations mapping client requests to FastAPI
└── docker-compose.yml        # Multi-service configuration (Postgres, Redis, MinIO)
```

---

## 🚀 Local Development Setup

Follow these instructions to run VellumIQ locally on your system.

### 1. Run the Backend API

#### Environment Configuration
Create a `.env` file in the `backend/` directory by copying `.env.example`:
```bash
cp backend/.env.example backend/.env
```

#### Install Dependencies
Create a virtual environment and install backend packages:
```bash
python -m venv .venv
.venv\Scripts\activate      # On Windows
# source .venv/bin/activate # On macOS/Linux
pip install -r backend/requirements.txt
```

#### Run the Server
Run the FastAPI application (falls back to local SQLite and storage folder automatically):
```bash
cd backend
python -m uvicorn app.main:app --reload
```
The backend API documentation is now live at `http://localhost:8000/docs`.

---

### 2. Run the Frontend Client

Ensure you have Node.js 18+ installed on your system.

#### Install Node Packages
```bash
cd frontend
npm install
```

#### Run the Dev Client
```bash
npm run dev
```
The client dashboard console is now running at **`http://localhost:3000`**.

Next.js automatically proxies all requests made to `/api/v1` directly to your local FastAPI backend running on port `8000`.

---

## 🧪 Testing Verification

Run the integration tests verifying authentication, OCR parses, validation rules, Stripe billing upgrades, and developer API key access:
```bash
cd backend
python -m pytest -v
```
All tests run against a localized SQLite environment and clean up test databases/files on teardown.

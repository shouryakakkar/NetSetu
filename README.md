# 🛡️ NetSetu — AI-Driven Multi-Vendor Network Security Compliance Auditor

> **NetSetu** is an enterprise-grade, vendor-agnostic network security and compliance platform. It automates the ingestion and normalization of heterogeneous network device configurations, evaluates compliance posture against industry standards (**CIS Benchmark**, **NIST SP 800-53**, and **DISA STIG**), generates actionable remediation runbooks with downloadable executive PDF reports, and features an embedded AI NLP zero-shot loop to classify and learn unknown syntax dynamically.

---

## 📑 Table of Contents

- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Docker Architecture & Services](#-docker-architecture--services)
- [Prerequisites](#-prerequisites)
- [Comprehensive Docker Build & Deployment Guide](#-comprehensive-docker-build--deployment-guide)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Environment Configuration](#step-2-environment-configuration)
  - [Step 3: Build & Start Services](#step-3-build--start-services)
  - [Step 4: Verify Service Health & Logs](#step-4-verify-service-health--logs)
  - [Step 5: Access Web UI & API Documentation](#step-5-access-web-ui--api-documentation)
- [Docker Management & Common Operations](#-docker-management--common-operations)
- [Troubleshooting & FAQ](#-troubleshooting--faq)
- [Algorithmic & Parsing Pipeline](#-algorithmic--parsing-pipeline)
- [REST API Reference](#-rest-api-reference)
- [Security Considerations](#-security-considerations)
- [License](#-license)

---

## 🚀 Key Features

- **Multi-Vendor Configuration Parsing**: Native support for Cisco IOS, Cisco NX-OS, Palo Alto PAN-OS, Juniper JunOS, and SONiC.
- **Hierarchical AST Parsing**: Whitespace indentation trees for Cisco/SONiC and brace descent parsing for Juniper/Palo Alto.
- **Dual-Engine Normalization**: TextFSM and Genie/pyATS fallback mapping into a unified `SecurityBaselineModel` (50+ security parameters).
- **Embedded AI Learning Loop**: Local zero-shot classification via HuggingFace `facebook/bart-large-mnli` to classify unrecognized device directives without cloud dependencies or external API costs.
- **Heuristic Rule Hot-Reloading**: Admin training GUI to approve AI suggestions into live heuristic rules without server restarts.
- **Automated Compliance Engine**: Evaluates rule expressions (`eq`, `ne`, `is_true`, `gte`, `lte`, `in`, `not_null`) producing PASS / FAIL / WARN / N/A statuses.
- **Remediation CLI Runbooks**: Reverse-maps non-compliant findings directly into vendor-specific CLI remediation scripts.
- **Executive PDF Generation**: Downloadable reports featuring compliance score gauges, executive summaries, findings matrices, and normalized config appendices.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   React 18 + Vite Frontend (Port 3000)                │
│       Dashboard │ Upload Wizard │ AI Training GUI │ PDF Reports        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Reverse Proxy /api/v1/*
┌───────────────────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend Server (Port 8000)                   │
│   Auth (JWT) │ Ingestion & Sanitizer │ Normalization │ AI │ Compliance │
└──────────────┬────────────────────┬────────────────────┬───────────────┘
               │                    │                    │
               ▼                    ▼                    ▼
     PostgreSQL 16 (Relational)   MongoDB 7 (Docs)      Redis 7 (Queue)
     - Users & RBAC               - Raw Configs         - Scan Job Queue
     - Scan Jobs & Metadata       - Normalized JSON     - Cache Store
     - AI Heuristic Rules         - Audit Findings
```

---

## 🛠️ Tech Stack

| Layer | Technology & Tools |
|---|---|
| **Frontend** | React 18, Vite, Zustand, Recharts, Axios, Nginx Alpine |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy (Async/asyncpg), Motor (Async MongoDB) |
| **Databases & Cache** | PostgreSQL 16 (Alpine), MongoDB 7, Redis 7 (Alpine) |
| **Parsing & AST** | TextFSM, pyATS / Genie, custom Indentation/Brace AST builders |
| **AI / Machine Learning** | HuggingFace Transformers (`facebook/bart-large-mnli`, PyTorch CPU) |
| **PDF Reporting** | ReportLab PDF engine |
| **Containerization** | Docker Engine, Multi-Stage Dockerfiles, Docker Compose |

---

## 🐳 Docker Architecture & Services

The application is fully containerized using **Docker Compose** across an isolated network (`netsec_net`):

| Service | Container Name | Base Image / Dockerfile | Exposed Ports | Persistent Volume |
|---|---|---|---|---|
| **frontend** | `netsec_frontend` | `./frontend/Dockerfile` (Node 20 build -> Nginx Alpine) | `3000:80` | None |
| **backend** | `netsec_backend` | `./backend/Dockerfile` (Python 3.11 multi-stage) | `8000:8000` | `hf_model_cache`, `upload_tmp` |
| **postgres** | `netsec_postgres` | `postgres:16-alpine` | `5432:5432` | `postgres_data` |
| **mongo** | `netsec_mongo` | `mongo:7` | `27017:27017` | `mongo_data` |
| **redis** | `netsec_redis` | `redis:7-alpine` | `6379:6379` | `redis_data` |

---

## 📋 Prerequisites

Ensure your host environment has the following installed:

1. **Docker Engine**: Version `24.0+` or **Docker Desktop** (`4.20+`)
2. **Docker Compose**: Version `v2.20+` (included with modern Docker Desktop)
3. **Hardware Requirements**:
   - Minimum: 4 GB RAM, 2 CPU cores
   - Recommended: 8 GB RAM, 4 CPU cores (for HuggingFace model inference)
   - Disk space: At least 5 GB free disk space for container images and AI weights

Verify installation:
```bash
docker --version
docker compose version
```

---

## 📖 Comprehensive Docker Build & Deployment Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/shouryakakkar/NetSetu.git
cd NetSetu
```

### Step 2: Environment Configuration

Create a secure `.env` file from the provided `.env.example`:

**On Linux / macOS:**
```bash
cp .env.example .env
```

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

#### Generate a Strong Secret Key
Generate a 256-bit cryptographic secret for JWT authentication:

```bash
openssl rand -hex 32
```
*(On Windows PowerShell without OpenSSL: `python -c "import secrets; print(secrets.token_hex(32))"`)*

#### Edit `.env` Values
Open `.env` in your preferred editor and configure your secrets:

```env
# ── Auth Configuration ─────────────────────────────────────────────────────────
SECRET_KEY=<paste_your_generated_hex_key_here>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── PostgreSQL Credentials ─────────────────────────────────────────────────────
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=netsec
POSTGRES_PASSWORD=EnterStrongPostgresPasswordHere
POSTGRES_DB=netsec_auditor

# ── MongoDB Credentials ────────────────────────────────────────────────────────
MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_USER=netsec
MONGO_PASSWORD=EnterStrongMongoPasswordHere
MONGO_DB=netsec_auditor

# ── Redis ──────────────────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── AI / Model Configuration ───────────────────────────────────────────────────
HF_MODEL_NAME=facebook/bart-large-mnli
MODEL_CACHE_DIR=/root/.cache/huggingface

# ── File Upload ────────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB=50
UPLOAD_DIR=/tmp/uploads
```

> ⚠️ **IMPORTANT**: Never commit `.env` to Git. The project `.gitignore` is preconfigured to prevent secret leaks.

---

### Step 3: Build & Start Services

Run Docker Compose to build the multi-stage images and start all 5 containers:

```bash
docker compose up --build -d
```

> 💡 **First-Time Build Note**:
> - The backend builds PyTorch CPU and Python dependencies using multi-stage caching.
> - The frontend performs an optimized production bundle via Vite and serves it through Nginx.
> - On first run, the backend initializes database schemas and downloads the HuggingFace `facebook/bart-large-mnli` model (~1.6 GB) into the persistent volume `hf_model_cache`.

---

### Step 4: Verify Service Health & Logs

Check the status of all containers:
```bash
docker compose ps
```

You should see all 5 containers running in a `healthy` state:
```
NAME              IMAGE              COMMAND                  SERVICE    STATUS
netsec_backend    netsec_backend     "uvicorn app.main:ap…"   backend    Up (healthy)
netsec_frontend   netsec_frontend    "/docker-entrypoint.…"   frontend   Up
netsec_mongo      mongo:7            "docker-entrypoint.s…"   mongo      Up (healthy)
netsec_postgres   postgres:16-alpine "docker-entrypoint.s…"   postgres   Up (healthy)
netsec_redis      redis:7-alpine     "docker-entrypoint.s…"   redis      Up (healthy)
```

To tail real-time application logs:
```bash
# All logs
docker compose logs -f

# Specific service logs
docker compose logs -f backend
docker compose logs -f frontend
```

---

### Step 5: Access Web UI & API Documentation

Once containers are up and healthy, access the platform in your browser:

| Portal | URL | Purpose |
|---|---|---|
| **NetSetu Web Dashboard** | [http://localhost:3000](http://localhost:3000) | Main auditor and admin application |
| **Interactive Swagger Docs** | [http://localhost:8000/api/docs](http://localhost:8000/api/docs) | Interactive OpenAPI exploration |
| **ReDoc Documentation** | [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc) | Alternative API documentation |
| **Health Check Endpoint** | [http://localhost:8000/health](http://localhost:8000/health) | System health & DB ping |

#### Initial Admin Setup
1. Navigate to `http://localhost:3000`.
2. Click **Register** to create your user account.
3. The **first user registered** is automatically granted the **Admin** role (subsequent signups are assigned the **Auditor** role).

---

## 🔧 Docker Management & Common Operations

### Stopping the Services
```bash
docker compose down
```

### Stopping Services & Removing Volumes (Fresh Reset)
> ⚠️ This deletes stored users, database records, uploaded configurations, and cached models.
```bash
docker compose down -v
```

### Rebuilding a Single Service
If you made changes to the backend or frontend:
```bash
# Rebuild and restart only backend
docker compose up --build -d backend

# Rebuild and restart only frontend
docker compose up --build -d frontend
```

### Accessing Container Shells
```bash
# Backend container shell
docker compose exec backend bash

# PostgreSQL CLI
docker compose exec postgres psql -U netsec -d netsec_auditor

# MongoDB Shell
docker compose exec mongo mongosh -u netsec -p <your_mongo_password> --authenticationDatabase admin netsec_auditor

# Redis CLI
docker compose exec redis redis-cli ping
```

---

## 🔍 Troubleshooting & FAQ

<details>
<summary><b>1. Backend fails health check during initial startup</b></summary>
The backend container includes a 60-second start period for initial model download and database migrations. If your internet connection is slow, run <code>docker compose logs -f backend</code> to track the HuggingFace model download progress.
</details>

<details>
<summary><b>2. Port conflict (Port 3000, 8000, 5432, or 27017 already in use)</b></summary>
If local PostgreSQL, MongoDB, or Node services are already using these ports on your host, edit the host mapping in <code>docker-compose.yml</code> (e.g., change <code>"5432:5432"</code> to <code>"5433:5432"</code>).
</details>

<details>
<summary><b>3. Database connection errors</b></summary>
Ensure the passwords set in <code>.env</code> under <code>POSTGRES_PASSWORD</code> and <code>MONGO_PASSWORD</code> match what was created on the first initialization of the Docker volume. If credentials changed, reset volumes using <code>docker compose down -v</code>.
</details>

---

## ⚙️ Algorithmic & Parsing Pipeline

```
Raw Network Config File (.cfg / .txt)
                 │
                 ▼
     [Config Sanitizer & Scrubber]
     ├── Strips terminal pagination artifacts ("-- More --")
     ├── Redacts Type-5 / Type-7 / Type-8 passwords, BGP keys, SNMP strings
     └── Heuristic Vendor Detection (Cisco IOS, NX-OS, Palo Alto, Junos, SONiC)
                 │
                 ▼
      [Hierarchical AST Parser]
     ├── IndentationParser (Whitespace depth for Cisco/SONiC)
     └── BraceParser (Recursive block parser for Junos/PAN-OS)
                 │
                 ▼
     [Multi-Engine Normalizer]
     ├── Primary: TextFSM vendor templates
     ├── Fallback: Genie / pyATS parsers
     └── Unknown Syntax: HuggingFace Zero-Shot Classification
                 │
                 ▼
     [Unified Schema Mapping]
     └── Normalized SecurityBaselineModel (50+ parameter attributes)
                 │
                 ▼
     [Rule-Based Compliance Engine]
     └── Evaluates against CIS / NIST / STIG framework JSON rules
                 │
                 ▼
   ┌─────────────┴─────────────┐
   ▼                           ▼
[Remediation Generator]     [ReportLab PDF Engine]
Reverse-maps failed rules    Produces comprehensive PDF
to vendor CLI commands       with score gauges & charts
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a new user (First user = Admin) |
| `POST` | `/api/v1/auth/token` | Authenticate and obtain JWT access & refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh an expired access token |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile and role |
| `POST` | `/api/v1/upload` | Upload a configuration file for parsing |
| `GET` | `/api/v1/upload/jobs` | List all historical scan jobs |
| `GET` | `/api/v1/upload/jobs/{id}` | Check scan job status and progress |
| `POST` | `/api/v1/compliance/check` | Execute compliance check against chosen framework |
| `GET` | `/api/v1/compliance/{job_id}` | Retrieve compliance findings and scores |
| `POST` | `/api/v1/remediation/generate`| Generate remediation CLI script for detected failures |
| `GET` | `/api/v1/report/pdf/{job_id}` | Generate and stream executive PDF audit report |
| `GET` | `/api/v1/ai/pending` | Fetch unmapped syntax items awaiting AI review |
| `POST` | `/api/v1/ai/suggest` | Query NLP zero-shot classification for syntax tokens |
| `POST` | `/api/v1/ai/validate` | Confirm AI mapping to hot-reload as a production rule |
| `GET` | `/api/v1/ai/rules` | List active heuristic parsing rules |
| `DELETE`| `/api/v1/ai/rules/{id}` | Deactivate a heuristic parsing rule |

---

## 🔒 Security Considerations

- **Secret Redaction**: Config files are scrubbed in-memory prior to AST parsing, database persistence, and AI inference.
- **Principle of Least Privilege**: The backend Docker container executes under an unprivileged user (`appuser`, UID `1001`).
- **Cryptographic Protections**: Passwords are saved using `bcrypt` salting. Authentication uses signed JWT tokens with strict lifetimes.
- **Isolated Network**: All database and queue services are isolated on the internal Docker network. Only necessary ports are mapped to localhost.

---

## 📄 License

This project is licensed under the **MIT License**.

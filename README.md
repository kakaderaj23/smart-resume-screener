# 📄 Smart Resume Screener

> **AI-powered resume screening system** that ingests candidate resumes, extracts structured profiles, and evaluates them against job descriptions using deterministic rule matching and LLM-based semantic analysis.

**Assignment**: Smart Resume Screener — Unthinkable Solutions

---

## ✨ Feature Highlights

- **Secure PDF Upload** — Multi-layer validation (extension, MIME type, magic bytes) with UUID collision-resistant storage
- **Intelligent Text Extraction** — High-fidelity PDF parsing via `pdfplumber` with spatial layout awareness
- **Deterministic Profile Parsing** — Regex-based extraction of contact info, skills, education, and experience
- **AI-Powered Semantic Matching** — LLM-driven candidate evaluation against job requirements with structured JSON output
- **Deterministic Rule Engine** — Case-insensitive skill overlap calculation with factual evidence reporting
- **Recommendation Engine** — Business-rule-based hiring recommendations (Strong Hire / Shortlist / Consider / Reject)
- **Interactive Dashboard** — React + Vite frontend with resume upload, screening, and results visualization
- **Full REST API** — FastAPI with auto-generated Swagger UI and ReDoc documentation

---

## 🏗️ Architecture Overview

The application follows **Clean / Layered Architecture** with strict separation between HTTP ingestion, domain business logic, data persistence, and AI inference:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                      │
│                   Recruiter Dashboard — Upload & Screen             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP (REST)
┌───────────────────────────────▼─────────────────────────────────────┐
│                        API Layer (FastAPI)                           │
│           /resume/upload    /screen    /screenings    /about         │
└──────┬──────────┬────────────┬──────────────────┬───────────────────┘
       │          │            │                  │
       ▼          ▼            ▼                  ▼
  ┌─────────┐ ┌────────┐ ┌──────────────┐  ┌───────────────┐
  │  Upload  │ │  PDF   │ │  Screening   │  │  Metadata /   │
  │  & Save  │ │Extract │ │  Pipeline    │  │  Health       │
  └─────────┘ └────────┘ └──────┬───────┘  └───────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                  ▼
      ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐
      │ Rule Evidence │  │   Prompt    │  │  Recommendation  │
      │   Builder     │  │  Builder    │  │     Engine       │
      └──────────────┘  └──────┬──────┘  └──────────────────┘
                               │
                        ┌──────▼──────┐
                        │ LLM Service │
                        │ (Groq SDK)  │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   SQLite    │
                        │  Database   │
                        └─────────────┘
```

---

## 🔄 End-to-End Workflow

```
Resume PDF ──► Upload & Validate ──► Extract Text (pdfplumber)
                                            │
                                            ▼
                                   Parse Profile (Regex)
                                            │
                                            ▼
                                   Persist to SQLite
                                            │
                                            ▼
Job Description ──► Parse Skills ──► Build Rule Evidence
                                            │
                                            ▼
                                   Render LLM Prompt
                                            │
                                            ▼
                                   LLM Semantic Match (Groq)
                                            │
                                            ▼
                                   Apply Business Rules
                                            │
                                            ▼
                                   Return ScreeningResult
```

---

## 🛠️ Tech Stack

| Layer         | Technology                                  |
|---------------|---------------------------------------------|
| **Backend**   | Python 3.10+, FastAPI, Uvicorn              |
| **Database**  | SQLite via SQLAlchemy ORM                   |
| **AI/LLM**    | Groq SDK (`llama-3.3-70b-versatile`)        |
| **PDF**       | pdfplumber (pdfminer.six engine)            |
| **Schemas**   | Pydantic v2 (validation & serialization)    |
| **Frontend**  | React 18, TypeScript, Vite                  |
| **Styling**   | Custom CSS with Inter & Outfit fonts        |

---

## 📁 Project Structure

```
smart-resume-screener/
├── app/
│   ├── api/
│   │   ├── about.py                # GET / and GET /about metadata endpoints
│   │   ├── resume.py               # POST /resume/upload endpoint
│   │   └── screening.py            # POST /screen, GET /screenings endpoints
│   ├── models/
│   │   └── resume_record.py        # SQLAlchemy ORM model & ProcessingStatus enum
│   ├── schemas/
│   │   ├── candidate.py            # CandidateProfile, PersonalInfo, ProfessionalInfo
│   │   ├── match.py                # JobRequirements, RuleEvidence, MatchResult, PromptPackage
│   │   └── screening.py            # ScreeningResult canonical output contract
│   ├── services/
│   │   ├── pdf_service.py          # PDF text extraction with domain exceptions
│   │   ├── extractor_service.py    # Deterministic regex-based profile extraction
│   │   ├── job_parser.py           # Job description skill keyword parser
│   │   ├── rule_evidence_builder.py# Deterministic skill overlap comparison
│   │   ├── prompt_builder.py       # Dynamic LLM prompt assembly
│   │   ├── llm_execution_service.py# LLM provider orchestration
│   │   ├── response_parser.py      # LLM JSON response parsing & validation
│   │   ├── resume_screening_service.py # End-to-end screening pipeline orchestrator
│   │   └── recommendation_engine.py# Business rule recommendation mapping
│   ├── providers/
│   │   ├── base_provider.py        # Abstract LLM provider interface
│   │   ├── groq_provider.py        # Groq SDK adapter
│   │   └── xai_provider.py         # xAI (Grok) OpenAI-compatible adapter
│   ├── prompts/
│   │   ├── system_prompt.py        # LLM system role instructions
│   │   └── matching_prompt.py      # User prompt template with placeholders
│   ├── repositories/
│   │   └── resume_repository.py    # Database CRUD operations for ResumeRecord
│   ├── config.py                   # Centralized Pydantic Settings
│   ├── database.py                 # SQLAlchemy engine, session, and dependency
│   └── main.py                     # FastAPI application entry point & lifespan
├── frontend/
│   ├── src/
│   │   ├── components/             # React UI components
│   │   ├── services/               # API client services
│   │   ├── types/                  # TypeScript type definitions
│   │   ├── App.tsx                 # Root application component
│   │   ├── main.tsx                # React DOM entry point
│   │   └── index.css               # Global styles
│   ├── index.html                  # HTML entry point
│   ├── package.json                # Frontend dependencies
│   ├── vite.config.ts              # Vite bundler configuration
│   └── tsconfig.json               # TypeScript configuration
├── tests/                          # pytest test suite
├── docs/                           # Documentation and screenshots
├── uploads/                        # Runtime PDF storage directory
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── LICENSE                         # MIT License
└── README.md
```

---

## 🤖 AI Pipeline

The screening pipeline combines **deterministic** and **semantic** analysis:

1. **Deterministic Extraction** — Regex-based parsing extracts emails, phone numbers, LinkedIn/GitHub URLs, skills (via dictionary matching), education, experience, and certifications from raw resume text.

2. **Job Description Parsing** — A keyword dictionary maps common technical terms to canonical skill names using word-boundary regex matching.

3. **Rule Evidence Building** — Case-insensitive comparison of candidate skills against job requirements produces factual overlap metrics (matched/missing skills, overlap percentage).

4. **LLM Semantic Matching** — A structured prompt package (system instructions + candidate profile + raw resume text + job requirements + rule evidence + few-shot example + JSON schema) is sent to the Groq LLM. The model returns a validated `MatchResult` JSON with semantic score, confidence, strengths, weaknesses, evidence citations, and justification.

5. **Recommendation Engine** — Deterministic business rules map the semantic score to a hiring recommendation:
   - **9–10**: `STRONG_HIRE`
   - **7–8**: `SHORTLIST`
   - **5–6**: `CONSIDER`
   - **1–4**: `REJECT`

---

## 📡 REST API Documentation

### Metadata

| Method | Endpoint   | Description                          |
|--------|------------|--------------------------------------|
| GET    | `/`        | Application status and version       |
| GET    | `/about`   | Detailed system metadata             |
| GET    | `/health`  | Health check                         |

### Resume

| Method | Endpoint          | Description                               |
|--------|-------------------|-------------------------------------------|
| POST   | `/resume/upload`  | Upload and process a PDF resume            |

### Screening

| Method | Endpoint                  | Description                                    |
|--------|---------------------------|------------------------------------------------|
| POST   | `/screen`                 | Screen a resume against a job description      |
| GET    | `/screenings`             | List all completed screening summaries         |
| GET    | `/screenings/{resume_id}` | Retrieve detailed screening result by ID       |

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- A Groq API key ([console.groq.com](https://console.groq.com))

### 1. Clone the Repository

```bash
git clone https://github.com/kakaderaj23/smart-resume-screener.git
cd smart-resume-screener
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env and add your Groq API key
```

### 3. Backend Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Run the Backend

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 📖 Swagger Documentation

| URL                          | Description       |
|------------------------------|-------------------|
| `http://localhost:8000/docs`  | Swagger UI        |
| `http://localhost:8000/redoc` | ReDoc             |

---

## 🎯 Design Principles

- **Clean Architecture** — Strict separation between API, service, repository, and provider layers
- **Domain-Driven Schemas** — Pydantic v2 models serve as canonical contracts across all tiers
- **Provider Abstraction** — LLM providers are swappable via abstract base class interface
- **Deterministic + Semantic** — Hybrid pipeline combining reliable regex extraction with AI-powered semantic analysis
- **Security-First Uploads** — Multi-layer PDF validation preventing malicious file injection
- **Framework Agnostic Services** — Domain services have zero dependency on FastAPI or HTTP contexts

---

## 🔮 Future Improvements

- OCR fallback for scanned/image-only PDFs (`pytesseract` integration)
- Batch resume upload and processing
- Background task queue (Celery/Redis) for async processing
- PostgreSQL support for production deployments
- Vector embeddings for semantic skill matching
- User authentication and role-based access
- Resume comparison and ranking dashboard
- Export screening reports (PDF/CSV)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 👤 Author

**Eraj Kakade**

Built as part of the Smart Resume Screener assignment for **Unthinkable Solutions**.

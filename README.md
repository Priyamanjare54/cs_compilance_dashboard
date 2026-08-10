# CS Compliance Dashboard

An enterprise-grade SaaS platform for Company Secretaries (CS) to track and manage Registrar of Companies (ROC) compliance obligations across multiple client firms — with an integrated AI chatbot for querying compliance notices in natural language.

---

## Services

The default application runs as two services plus MongoDB. The compliance assistant is integrated into the backend API.

| Service | Stack | Port | Purpose |
|---|---|---|---|
| **Backend API** | FastAPI, Beanie ODM, Motor, APScheduler | `8000` | Core compliance tracking, client management, scheduling |
| **Frontend** | React, Vite, Tailwind CSS, TanStack Query | `5173` | Dashboard UI |
| **Compliance Assistant** | Integrated FastAPI + Gemini | `8000` | Source-backed answers and review-first client email drafts |

Database: **MongoDB**. The assistant does not require a separate service or vector database. Generated answers and client email drafts require a Gemini API key in `backend/.env`.

The built-in Regulatory Intelligence library automatically discovers compatible `*_scraped_data.json` and `*_scrapped_data.json` files in `backend/`. It currently indexes 5,116 deduplicated records from 11 sources: IBBI, ICSI, IP India, India Registration Online, MCA, Ministry of Labour & Employment, NSE, RBI, SEBI, Udyam, and Vayana.

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB Community Server, running locally on port `27017`
- A Gemini API key for generated assistant answers and email drafts — [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

---

## Setup

### Recommended: Docker

Start MongoDB, the backend, and the frontend together:

```bash
docker compose up --build -d
```

Open [localhost:5173](http://localhost:5173). To stop the project, run `docker compose down`.

### Manual setup

Each service is set up the same general way: create a virtual environment (Python services), install dependencies, and run. Details below.

### 1. Backend API

\`\`\`bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # Windows; use cp on macOS/Linux
# Set GEMINI_API_KEY in .env
python seed.py                  # initializes MongoDB collections
uvicorn app.main:app --reload --port 8000
\`\`\`

Runs at [localhost:8000](http://localhost:8000) · Interactive docs at [localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend

\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

Runs at [localhost:5173](http://localhost:5173)

### 3. AI Chatbot API

\`\`\`bash
cd ai_module
python3 -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env

# Build the vector index (one-time; re-run when scraped data changes)
python load_and_chunk.py
python embed_and_store.py

uvicorn main:app --reload --port 8001
\`\`\`

Runs at [localhost:8001](http://localhost:8001) · Interactive docs at [localhost:8001/docs](http://localhost:8001/docs)

Full architecture, module breakdown, and re-indexing details: [\`ai_module/README.md\`](./ai_module/README.md)

---

## AI Chatbot — Quick Reference

\`\`\`bash
curl -X POST http://localhost:8001/chat \\
  -H "Content-Type: application/json" \\
  -d '{"question": "What is the procedure for transfer of interest of a member in a company not having share capital?"}'
\`\`\`

\`\`\`json
{
  "answer": "string",
  "sources": [{ "title": "string", "source": "string", "url": "string", "date": "string" }],
  "confidence": "answered | not_found"
}
\`\`\`

---

## Seed Login Credentials

| Role | Email | Password |
|---|---|---|
| Administrator | \`admin@csdashboard.com\` | \`Admin@123\` |
| Staff User 1 | \`staff1@csdashboard.com\` | \`Staff@123\` |
| Staff User 2 | \`staff2@csdashboard.com\` | \`Staff@123\` |
| Partner | \`partner@csdashboard.com\` | \`Partner@123\` |

# NYC Government Transparency Tool

A semantic search and natural language Q&A tool over New York City government data. Ask questions like *"what did the health committee vote on last month"* or *"which council members sponsored rent stabilization bills"* and get cited answers drawn from real legislative records, spending data, and meeting minutes.

> 🚧 In active development — see [ROADMAP.md](./ROADMAP.md) for progress.

---

## Why

NYC government data is public but not accessible. A resident trying to understand what happened to a bill, how their council member voted, or where budget money went has to navigate a dozen disconnected portals across the City Council, Comptroller's Office, and 59 community boards. This tool puts it all in one place with natural language search.

---

## Live Demo

*Coming soon — link will be added on deployment.*

---

## Architecture

```
Data Sources
├── Legistar API       → legislation, hearings, votes, sponsors
├── NYC Open Data      → permits, contracts, payroll (Socrata)
├── Checkbook NYC      → spending, budgets (XML API)
└── PDF scraping       → community board minutes, agency publications

Ingestion Pipeline (Python)
└── fetch → raw store → parse → normalize → chunk → embed

Storage
├── PostgreSQL         → documents + chunks tables
└── pgvector           → embedding vectors per chunk

Search Layer (Go)
└── /search, /document/:id, /health
    ├── BM25 keyword fallback
    └── semantic search proxy → Python embedding service

RAG Layer (Python)
└── retrieval chain → LLM → cited answer with source links

Frontend
└── search UI + Q&A panel + document viewer
```

---

## Data Sources

| Source | Type | Access | Covers |
|---|---|---|---|
| NYC Council Legistar API | REST/JSON | Free token | Legislation, hearings, votes, sponsors |
| NYC Open Data (Socrata) | REST/JSON | Free app token | Permits, contracts, payroll, 311 |
| Checkbook NYC | XML POST | No key required | Spending, budgets, vendor contracts |
| NYC Gov Publications Portal | Scrape | Public | Agency reports, mayoral directives |
| Community Board minutes | Scrape | Public | 59 boards, meeting minutes as PDFs |

### Key Legistar endpoints

```
GET /v1/nyc/bodies                                → committee lookup table
GET /v1/nyc/persons                               → council member lookup table
GET /v1/nyc/matters?$top=1000&$skip=0             → paginated legislation
GET /v1/nyc/matters/{id}/texts                    → full bill text
GET /v1/nyc/matters/{id}/attachments              → linked documents
GET /v1/nyc/matters/{id}/attachments/{id}/file    → PDF bytes (no scraping needed)
GET /v1/nyc/matters/{id}/histories                → action timeline
GET /v1/nyc/matters/{id}/sponsors                 → sponsor list
GET /v1/nyc/events?$top=1000&$skip=0              → hearings and meetings
GET /v1/nyc/events/{id}/eventitems?AgendaNote=1&MinutesNote=1
```

Base URL: `https://webapi.legistar.com/v1/nyc`
Token: request at [council.nyc.gov/legislation/api](https://council.nyc.gov/legislation/api/)

---

## Database Schema

```sql
CREATE TABLE documents (
  id           TEXT PRIMARY KEY,   -- e.g. "legistar-matter-17075"
  source       TEXT,               -- "legistar" | "socrata" | "checkbook"
  type         TEXT,               -- "legislation" | "contract" | "permit" | ...
  title        TEXT,
  date         DATE,
  url          TEXT,
  metadata     JSONB,
  ingested_at  TIMESTAMPTZ
);

CREATE TABLE chunks (
  id           SERIAL PRIMARY KEY,
  document_id  TEXT REFERENCES documents(id),
  chunk_index  INT,
  body         TEXT,
  embedding    VECTOR(1536),
  token_count  INT
);

CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops);
```

Every source normalizes to a unified document shape before storage. The `body` field is synthesized from full bill text + title + committee + action history narrative, then chunked at 512 tokens with 50-token overlap before embedding.

---

## Local Setup

> Prerequisites: Python 3.11+, Go 1.22+, PostgreSQL 15+ with pgvector, Docker (optional)

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/nyc-transparency-tool.git
cd nyc-transparency-tool
```

**2. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**3. Set environment variables**
```bash
cp .env.example .env
# fill in:
# LEGISTAR_TOKEN=your_token_here
# SOCRATA_APP_TOKEN=your_token_here
# DATABASE_URL=postgresql://localhost:5432/transparency
# OPENAI_API_KEY=your_key_here
```

**4. Set up the database**
```bash
psql -d transparency -f schema/001_create_tables.sql
```

**5. Run ingestion**
```bash
python ingestion/fetch_legistar.py     # fetch and store raw data
python ingestion/normalize.py          # normalize to unified schema
python ingestion/chunk_and_embed.py    # chunk, embed, and store
```

**6. Start the Go search service**
```bash
cd search-service
go run main.go
```

**7. Start the frontend**
```bash
cd frontend
npm install && npm run dev
```

---

## Stack

| Layer | Technology |
|---|---|
| Ingestion | Python, requests, pdfplumber, sodapy |
| Storage | PostgreSQL, pgvector |
| Search service | Go, Gin |
| Embeddings | OpenAI text-embedding-3-small |
| LLM | OpenAI GPT-4o |
| Frontend | (TBD) |
| Deployment | Fly.io (Go + Python), Vercel (frontend) |

---

## Status

See [ROADMAP.md](./ROADMAP.md) for the full phase breakdown and task checklist.

**Current phase:** Phase 01 — Data ingestion

---

## References

- [NYC Council Legistar API](https://council.nyc.gov/legislation/api/)
- [Legistar Web API docs](https://webapi.legistar.com/Help)
- [NYC Open Data](https://opendata.cityofnewyork.us/)
- [Checkbook NYC API](https://www.checkbooknyc.com/api-page)
- [jehiah/nyc_legislation](https://github.com/jehiah/nyc_legislation) — flat file mirror of NYC legislation
- [jehiah/legislator](https://github.com/jehiah/legislator) — Go client for Legistar API
- [opencivicdata/python-legistar-scraper](https://github.com/opencivicdata/python-legistar-scraper)
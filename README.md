# Local Government Transparency Tool
> NYC-focused RAG pipeline over public legislative, financial, and civic data

![Status](https://img.shields.io/badge/status-in%20progress-amber) ![Stack](https://img.shields.io/badge/stack-Python%20%7C%20Go%20%7C%20PostgreSQL-blue)

---

## Overview

A semantic search and Q&A tool over NYC government data — legislation, spending, contracts, permits, and meeting records. Built on a hybrid ingestion layer (Legistar API + Socrata + Checkbook + PDF scraping), a Go search microservice, and a RAG answer layer backed by pgvector.

**Why this exists:** Most NYC government data is public but not accessible. A resident trying to understand what happened to a bill, how their council member voted, or where budget money went has to navigate a dozen disconnected portals. This tool puts it all in one place with natural language search.

---

## Architecture

```
Data Sources
├── Legistar API       → legislation, hearings, votes, sponsors
├── NYC Open Data      → permits, contracts, payroll (Socrata)
├── Checkbook NYC      → spending, budgets (XML API)
└── PDF scraping       → community board minutes, publications

Ingestion Pipeline (Python)
└── fetch → raw store → parse → normalize → chunk → embed

Storage
├── PostgreSQL         → documents + chunks tables
└── pgvector           → embedding vectors on chunks

Search Layer (Go)
└── /search, /document/:id, /health
    ├── BM25 keyword fallback
    └── semantic search proxy → Python embedding service

RAG Layer (Python)
└── retrieval chain → LLM → cited answer

Frontend
└── search UI + Q&A panel + document viewer
```

---

## Data Sources

| Source | Type | Access | Covers |
|---|---|---|---|
| NYC Council Legistar API | REST/JSON | Token (free) | Legislation, hearings, votes, sponsors |
| NYC Open Data (Socrata) | REST/JSON | App token (free) | Permits, contracts, payroll, 311 |
| Checkbook NYC | XML POST | No key required | Spending, budgets, vendor contracts |
| NYC Gov Publications Portal | Scrape | Public | Agency reports, mayoral directives |
| Community Board minutes | Scrape | Public | 59 boards, meeting minutes as PDFs |

### Key Legistar endpoints

```
GET /v1/nyc/bodies                              → committee lookup table
GET /v1/nyc/persons                             → council member lookup table
GET /v1/nyc/matters?$top=1000&$skip=0           → paginated legislation
GET /v1/nyc/matters/{id}/texts                  → full bill text
GET /v1/nyc/matters/{id}/attachments            → linked documents
GET /v1/nyc/matters/{id}/attachments/{id}/file  → download PDF bytes
GET /v1/nyc/matters/{id}/histories              → action timeline
GET /v1/nyc/matters/{id}/sponsors               → sponsor list
GET /v1/nyc/events?$top=1000&$skip=0            → hearings and meetings
GET /v1/nyc/events/{id}/eventitems?AgendaNote=1&MinutesNote=1
```

Base URL: `https://webapi.legistar.com/v1/nyc`
Token: request at [council.nyc.gov/legislation/api](https://council.nyc.gov/legislation/api/)

---

## Database Schema

```sql
-- one row per normalized document
CREATE TABLE documents (
  id           TEXT PRIMARY KEY,   -- e.g. "legistar-matter-17075"
  source       TEXT,               -- "legistar" | "socrata" | "checkbook"
  type         TEXT,               -- "legislation" | "contract" | "permit" | ...
  title        TEXT,
  date         DATE,
  url          TEXT,
  metadata     JSONB,              -- source-specific fields
  ingested_at  TIMESTAMPTZ
);

-- one row per chunk, with embedding
CREATE TABLE chunks (
  id           SERIAL PRIMARY KEY,
  document_id  TEXT REFERENCES documents(id),
  chunk_index  INT,
  body         TEXT,
  embedding    VECTOR(1536),       -- text-embedding-3-small dimensions
  token_count  INT
);

CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops);
```

---

## Normalized Document Schema

Every source — regardless of API or scrape — converges to this shape before storage:

```json
{
  "id":       "legistar-matter-17075",
  "source":   "legistar",
  "type":     "legislation",
  "title":    "A Local Law to amend the administrative code...",
  "body":     "Full bill text + committee + history narrative...",
  "date":     "1997-04-30",
  "url":      "https://legistar.council.nyc.gov/...",
  "metadata": {
    "committee":         "Committee on Health",
    "sponsors":          ["Council Member X", "Council Member Y"],
    "status":            "Enacted",
    "enactment_number":  "1998/003",
    "file_number":       "Int 0951-1997-A"
  }
}
```

The `body` field is synthesized from: full legislative text + title + committee + status + action history narrative. This is what gets chunked (512 tokens, 50-token overlap) and embedded.

---

## Project Phases

### Phase 01 — Data ingestion (Weeks 1–2)

**API sources**
- [X] Fetch `/bodies` → build committee lookup table
- [X] Fetch `/persons` → build council member lookup table
- [X] Paginate `/matters` → save one JSON file per matter to raw store
- [ ] Per matter: fetch `/matters/{id}/texts` → append bill text to body
- [ ] Per matter: fetch `/matters/{id}/attachments` → download PDFs via `/file` endpoint
- [ ] Per matter: fetch `/matters/{id}/histories` → action timeline
- [ ] Per matter: fetch `/matters/{id}/sponsors` → sponsor list
- [X] Paginate `/events` → save raw event records
- [ ] Per event: fetch `/events/{id}/eventitems?AgendaNote=1&MinutesNote=1`
- [ ] NYC Open Data (Socrata) — contracts, permits, payroll via `sodapy`
- [ ] Checkbook NYC API — spending and budget via XML POST

**Document scraping**
- [ ] Scrape NYC Government Publications Portal (`a860-gpp.nyc.gov`)
- [ ] Scrape community board meeting minutes (59 boards, `nyc.gov` subpages)
- [ ] Extract text layer from PDFs with `pdfplumber` or `pymupdf`
- [ ] Flag scanned/image PDFs — queue for OCR (Tesseract or AWS Textract)

**Normalize & validate**
- [ ] Define unified schema: `id`, `source`, `type`, `title`, `body`, `date`, `url`, `metadata`
- [ ] Write adapter per source: API JSON → schema, PDF text → schema
- [ ] Synthesize `body` field: title + full text + committee + history narrative
- [ ] Chunk body into 512-token segments with 50-token overlap
- [ ] Deduplication on `(source + document_id)` fingerprint
- [ ] Smoke test: ingest 100 docs end-to-end, spot-check quality

> **Note:** Start with Legistar alone — bodies → persons → matters → sub-endpoints. You can have structured data flowing within days. Scraping is additive and can come after the core pipeline is working.

---

### Phase 02 — Storage & pipeline (Weeks 3–4)

- [ ] Stand up PostgreSQL with pgvector extension
- [ ] Create `documents` table
- [ ] Create `chunks` table with vector column
- [ ] Build ingestion pipeline: raw store → parse → normalize → chunk → embed → store
- [ ] Choose embedding model (`text-embedding-3-small` or local alternative)
- [ ] Embed each chunk and write vector to chunks table
- [ ] Add deduplication on document fingerprint before insert
- [ ] Write pipeline integration tests end-to-end

> Keep raw store and embedding store separate — it lets you re-embed without re-fetching when you change models.

---

### Phase 03 — Go search microservice (Weeks 5–7)

- [ ] Initialize Go module + Gin or Echo HTTP framework
- [ ] Expose `/search`, `/document/:id`, `/health` endpoints
- [ ] Implement BM25 keyword search as fallback
- [ ] Proxy semantic search to Python embedding service
- [ ] Add result re-ranking (RRF or score fusion)
- [ ] Rate limiting + structured logging (`zap` or `slog`)
- [ ] Write Go unit tests + benchmarks
- [ ] Containerize with Dockerfile

> The Go microservice is the differentiator. It shows service-boundary thinking — a Go API in front of a Python RAG layer demonstrates you can work across languages, which is exactly what backend roles care about. Reference: [`jehiah/legislator`](https://github.com/jehiah/legislator) for an existing Go Legistar client worth studying.

---

### Phase 04 — RAG + LLM answer layer (Weeks 8–10)

- [ ] Build retrieval chain: query → Go search → top-k chunks
- [ ] Write system prompt with citation-required instructions
- [ ] Implement answer generation with source references
- [ ] Add query classification (factual vs. exploratory vs. summary)
- [ ] Build eval set: 20+ ground-truth Q&A pairs from real NYC legislation
- [ ] Tune chunk size and overlap for best retrieval accuracy
- [ ] Add streaming responses for perceived speed

> Citations are mandatory in the system prompt — hallucinations on government data destroy credibility instantly.

---

### Phase 05 — Frontend interface (Weeks 11–13)

- [ ] Search bar + results list with document previews
- [ ] Conversational Q&A panel with cited source cards
- [ ] Document viewer (PDF iframe or text extract)
- [ ] Filter by source, date range, document type, committee
- [ ] Mobile-responsive layout
- [ ] Loading states, error boundaries, empty states

> Keep it functional over clever. The tool should feel like a public records search, not a chatbot. Trust comes from visible sources.

---

### Phase 06 — Deployment & polish (Weeks 14–16)

- [ ] Deploy Go service + Python worker to Fly.io or Railway
- [ ] Deploy frontend to Vercel or Cloudflare Pages
- [ ] Add CI/CD pipeline (GitHub Actions)
- [ ] Write README with problem statement, architecture diagram, local setup
- [ ] Record Loom walkthrough demo (~90 seconds)
- [ ] Add live URL to GitHub profile and resume
- [ ] Write short blog post or LinkedIn post about the project

> A live URL + a 90-second Loom is the difference between a project that gets skimmed and one that gets remembered. This phase matters as much as the code.

---

## References

- [NYC Council Legistar API](https://council.nyc.gov/legislation/api/)
- [Legistar Web API docs](https://webapi.legistar.com/Help)
- [NYC Open Data](https://opendata.cityofnewyork.us/)
- [Checkbook NYC API](https://www.checkbooknyc.com/api-page)
- [jehiah/nyc_legislation](https://github.com/jehiah/nyc_legislation) — flat file mirror of NYC legislation
- [jehiah/legislator](https://github.com/jehiah/legislator) — Go client for Legistar API
- [opencivicdata/python-legistar-scraper](https://github.com/opencivicdata/python-legistar-scraper)

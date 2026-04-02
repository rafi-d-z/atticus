# Roadmap

Full phase breakdown and task checklist for the [NYC Government Transparency Tool](./README.md).

---

### Phase 01 — Data ingestion (Weeks 1–2)

**API sources**
- [x] Fetch `/bodies` → build committee lookup table
- [x] Fetch `/persons` → build council member lookup table
- [x] Paginate `/matters` → save one JSON file per matter to raw store
- [ ] Per matter: fetch `/matters/{id}/texts` → append bill text to body
- [ ] Per matter: fetch `/matters/{id}/attachments` → download PDFs via `/file` endpoint
- [ ] Per matter: fetch `/matters/{id}/histories` → action timeline
- [ ] Per matter: fetch `/matters/{id}/sponsors` → sponsor list
- [x] Paginate `/events` → save raw event records
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

> Start with Legistar alone — bodies → persons → matters → sub-endpoints. Structured data can be flowing within days. Scraping is additive and can come after the core pipeline is working.

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

> The Go microservice is the differentiator. It shows service-boundary thinking — a Go API in front of a Python RAG layer demonstrates you can work across languages, which is exactly what backend roles care about.

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

> A live URL + a 90-second Loom is the difference between a project that gets skimmed and one that gets remembered.
# Demo: RAG Pipeline Walkthrough

**Course lesson:** Lesson 16 — "[DEMO] Build a RAG Pipeline Walkthrough"
**Folder:** `demo-rag-pipeline/`

A working retrieval-augmented generation pipeline over sample enterprise
documents. It demonstrates every concept from the lesson: ingestion, chunking,
embeddings/indexing, hybrid retrieval with reranking, permission filtering,
freshness checks, and a groundedness evaluation.

## What it does

1. **Ingests** 4 Markdown documents from `data/` (VPN runbook, expense policy,
   password FAQ, incident runbook), each with department, classification, and
   last-updated metadata.
2. **Chunks** them on paragraph boundaries with a sliding window + overlap.
3. **Indexes** with TF-IDF + cosine similarity (pure NumPy — runs fully
   offline, no API keys, no model downloads).
4. **Retrieves** with a hybrid score (TF-IDF + exact-term boost) and
   recency-aware ranking.
5. **Filters by permission** — three caller personas show the same queries
   returning different documents:
   - `it_engineer` (internal clearance) — cannot see the confidential expense policy
   - `finance_analyst` (confidential, Finance) — the only one who sees it
   - `contractor` (public) — sees only the public password FAQ
6. **Flags stale documents** — the password FAQ (last updated 2024) is
   reported STALE on every retrieval.
7. **Checks groundedness** — every answer is verified against the retrieved
   chunks; ungrounded terms raise a warning.

## Prerequisites

- Python 3.9+

## Install

```bash
cd demo-rag-pipeline
pip install -r requirements.txt
```

## Run

```bash
python rag_pipeline.py
```

## Configure

| Env var          | Default | Meaning                              |
|------------------|---------|--------------------------------------|
| `RAG_TOP_K`      | `3`     | Chunks retrieved per query           |
| `RAG_STALE_DAYS` | `365`   | Freshness threshold in days          |

## Expected output

- `Ingested 4 documents` / `Chunked into 7 chunks` / TF-IDF vocabulary size
- Three caller sections; the finance analyst's per-diem query hits
  `Travel and Expense Policy` while the IT engineer's does not (permission
  filtering in action)
- `STALE (962 days old...)` warnings on the password FAQ
- `Groundedness check: PASS` after every answer

## Adapt it to your own corpus

Drop your own `.md` files into `data/` with a front-matter block:

```markdown
---
title: My Runbook
department: IT
classification: internal     # public | internal | confidential
updated: 2026-09-01
---
```

Then rerun. Swap the `TfidfIndex` class for a vector-DB-backed index
(Pinecone, pgvector, …) when you outgrow in-memory search — the
`search(query, top_k)` interface stays the same.

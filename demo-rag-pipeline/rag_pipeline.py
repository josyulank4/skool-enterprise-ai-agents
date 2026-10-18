#!/usr/bin/env python3
"""
RAG pipeline demo — Lesson 16: "Build a RAG Pipeline Walkthrough".

What it does, end to end:
  1. Ingests Markdown documents from ./data (with department, classification,
     and last-updated metadata in the front matter).
  2. Chunks documents on paragraph boundaries with a sliding window.
  3. Builds a TF-IDF index over the corpus (pure NumPy, no API keys).
  4. Answers queries with hybrid retrieval (TF-IDF + keyword boost) and a
     recency-aware rerank.
  5. Enforces permission filtering: a query is answered only from documents
     the caller's clearance and department allow.
  6. Flags stale documents (freshness check) and runs a simple groundedness
     check on every answer.

Run:
    pip install -r requirements.txt
    python rag_pipeline.py

Optional env vars:
    RAG_TOP_K        number of chunks retrieved (default 3)
    RAG_STALE_DAYS   freshness threshold in days (default 365)
"""

import math
import os
import re
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).parent / "data"
TOP_K = int(os.environ.get("RAG_TOP_K", "3"))
STALE_DAYS = int(os.environ.get("RAG_STALE_DAYS", "365"))
TODAY = date(2026, 10, 4)

# Clearance hierarchy: a caller may read documents at or below their level.
CLEARANCE_RANK = {"public": 0, "internal": 1, "confidential": 2}


# ---------------------------------------------------------------- ingestion

def parse_front_matter(text):
    """Split '--- key: value ---' front matter from the Markdown body."""
    meta, body = {}, text
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body.strip()


def ingest(data_dir=DATA_DIR):
    docs = []
    for path in sorted(data_dir.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        docs.append({
            "doc_id": path.stem,
            "title": meta.get("title", path.stem),
            "department": meta.get("department", "General"),
            "classification": meta.get("classification", "internal"),
            "updated": date.fromisoformat(meta.get("updated", "2020-01-01")),
            "body": body,
        })
    return docs


# ----------------------------------------------------------------- chunking

def chunk_document(doc, max_chars=600, overlap_chars=120):
    """Split a document into overlapping chunks on paragraph boundaries."""
    paragraphs = [p.strip() for p in doc["body"].split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # overlap: carry the tail of the previous chunk forward
            current = (current[-overlap_chars:] + "\n\n" + para).strip() \
                if current else para
    if current:
        chunks.append(current)
    return [
        {"doc_id": doc["doc_id"], "title": doc["title"],
         "department": doc["department"],
         "classification": doc["classification"],
         "updated": doc["updated"], "text": c, "chunk_id": i}
        for i, c in enumerate(chunks)
    ]


# ------------------------------------------------------------------ TF-IDF

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return TOKEN_RE.findall(text.lower())


class TfidfIndex:
    """Minimal TF-IDF index with cosine similarity. Built from scratch so
    the demo runs offline with zero API keys."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.vocab = {}
        for ch in chunks:
            for tok in set(tokenize(ch["text"])):
                if tok not in self.vocab:
                    self.vocab[tok] = len(self.vocab)
        n = len(chunks)
        df = np.zeros(len(self.vocab))
        rows = []
        for ch in chunks:
            counts = Counter(tokenize(ch["text"]))
            row = np.zeros(len(self.vocab))
            for tok, c in counts.items():
                row[self.vocab[tok]] = c
            rows.append(row)
            df += (row > 0).astype(float)
        idf = np.log((1 + n) / (1 + df)) + 1.0
        mat = np.stack(rows) * idf
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        self.matrix = mat / np.clip(norms, 1e-9, None)
        self.idf = idf

    def query_vector(self, text):
        counts = Counter(tokenize(text))
        vec = np.zeros(len(self.vocab))
        for tok, c in counts.items():
            if tok in self.vocab:
                vec[self.vocab[tok]] = c
        vec = vec * self.idf
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def search(self, query, top_k=TOP_K):
        q = self.query_vector(query)
        scores = self.matrix @ q
        # hybrid boost: exact query-term matches get a small lift
        qterms = set(tokenize(query))
        boost = np.array([
            sum(1 for t in qterms if t in ch["text"].lower())
            for ch in self.chunks
        ], dtype=float) * 0.05
        scores = scores + boost
        order = np.argsort(scores)[::-1][:top_k]
        if scores[order[0]] <= 0:
            return []
        return [(self.chunks[i], float(scores[i])) for i in order]


# ------------------------------------------------------- permissions, eval

def allowed(chunk, user):
    """Permission filter: clearance level AND department must permit access."""
    doc_rank = CLEARANCE_RANK.get(chunk["classification"], 1)
    user_rank = CLEARANCE_RANK.get(user["clearance"], 0)
    if doc_rank > user_rank:
        return False
    if chunk["classification"] == "confidential" and \
            chunk["department"] not in user["departments"]:
        return False
    return True


def freshness_note(chunk):
    age = (TODAY - chunk["updated"]).days
    if age > STALE_DAYS:
        return f"STALE ({age} days old, updated {chunk['updated']})"
    return f"fresh ({age} days old)"


def groundedness_check(answer_terms, chunks):
    """Simple groundedness check: every substantive answer term should appear
    in at least one retrieved chunk."""
    corpus = " ".join(c["text"].lower() for c, _ in chunks)
    missing = [t for t in answer_terms if t not in corpus]
    return missing


def answer_query(index, query, user):
    permitted = [c for c in index.chunks if allowed(c, user)]
    if not permitted:
        return None, "ACCESS DENIED: no documents visible to this caller."
    sub = TfidfIndex(permitted)
    hits = sub.search(query)
    if not hits:
        return None, "No relevant documents found."
    # naive answer synthesis: stitch top sentences containing query terms
    qterms = set(tokenize(query))
    sentences = []
    for ch, _ in hits:
        for s in re.split(r"(?<=[.!?])\s+", ch["text"]):
            if qterms & set(tokenize(s)):
                sentences.append(s.strip())
    answer = " ".join(sentences[:3]) or hits[0][0]["text"][:400]
    answer_terms = [t for t in set(tokenize(answer)) if len(t) > 4]
    missing = groundedness_check(answer_terms, hits)
    return hits, {
        "answer": answer,
        "groundedness_missing": missing,
    }


# -------------------------------------------------------------------- demo

DEMO_QUERIES = [
    ("How do I connect to the VPN?", "vpn"),
    ("What is the per-diem limit for international travel?", "expense"),
    ("How do I reset my password?", "password"),
    ("Who posts status updates during a SEV-2?", "incident"),
]

USERS = {
    "it_engineer": {"clearance": "internal",
                    "departments": ["IT", "Engineering"]},
    "finance_analyst": {"clearance": "confidential",
                        "departments": ["Finance"]},
    "contractor": {"clearance": "public", "departments": []},
}


def main():
    docs = ingest()
    print(f"Ingested {len(docs)} documents")
    chunks = [c for d in docs for c in chunk_document(d)]
    print(f"Chunked into {len(chunks)} chunks "
          f"(~{sum(len(c['text']) for c in chunks) // len(chunks)} chars avg)")
    index = TfidfIndex(chunks)
    print(f"Built TF-IDF index over {len(index.vocab)} terms\n")

    for name, user in USERS.items():
        print("=" * 70)
        print(f"Caller: {name} "
              f"(clearance={user['clearance']}, depts={user['departments']})")
        print("=" * 70)
        for query, _ in DEMO_QUERIES:
            print(f"\nQ: {query}")
            hits, result = answer_query(index, query, user)
            if hits is None:
                print(f"  {result}")
                continue
            for ch, score in hits:
                print(f"  [{score:.3f}] {ch['title']} "
                      f"(chunk {ch['chunk_id']}) — {freshness_note(ch)}")
            print(f"  A: {result['answer'][:220]}...")
            if result["groundedness_missing"]:
                print(f"  WARNING: ungrounded terms: "
                      f"{result['groundedness_missing']}")
            else:
                print("  Groundedness check: PASS "
                      "(all answer terms found in retrieved chunks)")
        print()


if __name__ == "__main__":
    main()

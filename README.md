# Enterprise AI Agents: From Pilot to Production (Skool)

Official code companion for Naveen Kumar Josyula's Skool course
**Enterprise AI Agents: From Pilot to Production**, inside the
"AI Agents in Production" community on Skool (AIsoltrics Technologies).
Every demo from the course lives in this repo — no stubs, no slides-only
code. Clone it, run it, adapt it to your own enterprise.

## What's inside

| Folder | What it is |
|--------|------------|
| `demo-rag-pipeline/` | Working RAG over sample enterprise docs: ingestion, chunking, TF-IDF retrieval, permission filtering, freshness checks, groundedness eval |
| `demo-tool-contract/` | Enterprise ticket API wrapped as agent tools: function schemas, validation, auth scoping, write-confirmation, rate limits, audit log, MCP manifest |
| `demo-eval-suite/` | Golden dataset, 4 scorers, latency + cost metrics, and a CI quality gate that blocks bad deployments |
| `capstone-template/` | 10-part production design document template with a fully worked invoice-agent example and grading rubric |

## Prerequisites

- Python 3.9+
- No API keys required — every demo runs fully offline. (The eval suite has
  an *optional* LLM-as-judge path if you set `OPENAI_API_KEY`; the default
  heuristic judge needs nothing.)

## Quickstart

```bash
git clone https://github.com/josyulank4/skool-enterprise-ai-agents.git
cd skool-enterprise-ai-agents

# 1. RAG pipeline
cd demo-rag-pipeline && pip install -r requirements.txt && python rag_pipeline.py && cd ..

# 2. Tool contract
cd demo-tool-contract && python demo.py && cd ..

# 3. Eval suite + CI gate
cd demo-eval-suite && python eval_runner.py && python ci_gate.py && cd ..
```

Each folder has its own `README.md` with full run instructions,
configuration options, expected output, and guidance on adapting the demo
to your own systems. The capstone template is a document, not code — open
`capstone-template/capstone-design-template.md` and work through it part
by part.

## Questions

This repo accompanies the Skool course. Questions? Ask in the
"AI Agents in Production" community on Skool.

## License

MIT — use it in your own enterprise work.

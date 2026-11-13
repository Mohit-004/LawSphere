# LawSphere

LawSphere is planned as an offline-first Indian legal research and document assistant. The first release will use retrieval-augmented generation (RAG); an ontology and knowledge-graph extension is reserved for a later version.

## Current milestone: Phase 1 foundation

The current implementation establishes the local Python API boundary, a status endpoint, and SQLite initialization for future application metadata. It does not yet ingest legal sources, connect to Ollama, or generate answers.

### Run the API

From `ai-engine/`, create and activate a virtual environment, then install the pinned dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The service binds to loopback by default. Visit `http://127.0.0.1:8000/docs` for the local API schema. Startup creates `local-data/database/lawsphere.db`; set `LAWSPHERE_DATABASE_PATH` to use another local path. `GET /api/v1/system/status` reports API and SQLite availability; its `ollama` value is explicitly `not_checked` until runtime detection is implemented.

## Roadmap

- [x] Phase 1, slice 1: local API skeleton, environment settings, status response contract
- [x] Phase 1, slice 2: local SQLite initialization
- [ ] Phase 1: Ollama connectivity/model status, service integration
- [ ] Phase 2: document ingestion, chunking, embeddings, retrieval, grounded answers
- [ ] Phase 3 onward: authoritative Indian legal sources, document intelligence, desktop UI, packaging
- [ ] Version 2: ontology and knowledge-graph extension after Version 1 is functional

## Privacy direction

The API binds to `127.0.0.1` by default. Legal documents, prompts, and embeddings are intended to remain local. Do not add external AI services or transmit user content outside the device.

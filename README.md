# LawSphere

LawSphere is planned as an offline-first Indian legal research and document assistant. The first release will use retrieval-augmented generation (RAG); an ontology and knowledge-graph extension is reserved for a later version.

## Current milestone: Phase 1 foundation

The current implementation establishes the local Python API boundary, SQLite initialization for future application metadata, local Ollama detection/model listing, and a Java client for reading backend status. It does not yet ingest legal sources or generate answers.

### Run the API

From `ai-engine/`, create and activate a virtual environment, then install the pinned dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The service binds to loopback by default. Visit `http://127.0.0.1:8000/docs` for the local API schema. Startup creates `local-data/database/lawsphere.db`; set `LAWSPHERE_DATABASE_PATH` to use another local path. `GET /api/v1/system/status` reports API, SQLite, and Ollama availability. `GET /api/v1/models` lists models already installed in Ollama. Configure the local Ollama endpoint with `LAWSPHERE_OLLAMA_BASE_URL`; checks time out quickly and report unavailable when the service cannot be reached.

### Java client

With the Python service running, use Java 21 and Maven from `desktop-app/` to query its local status:

```powershell
mvn compile exec:java
```

An alternate local API base URL can be passed as the first argument, for example `mvn compile exec:java "-Dexec.args=http://127.0.0.1:8001"`.

## Roadmap

- [x] Phase 1, slice 1: local API skeleton, environment settings, status response contract
- [x] Phase 1, slice 2: local SQLite initialization
- [x] Phase 1, slice 3: local Ollama connectivity and installed-model listing
- [x] Phase 1, slice 4: Java HTTP client for Python API status and model endpoints
- [ ] Phase 1: managed backend startup and desktop shell
- [ ] Phase 2: document ingestion, chunking, embeddings, retrieval, grounded answers
- [ ] Phase 3 onward: authoritative Indian legal sources, document intelligence, desktop UI, packaging
- [ ] Version 2: ontology and knowledge-graph extension after Version 1 is functional

## Privacy direction

The API binds to `127.0.0.1` by default. Legal documents, prompts, and embeddings are intended to remain local. Do not add external AI services or transmit user content outside the device.

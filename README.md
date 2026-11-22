# LawSphere

LawSphere is planned as an offline-first Indian legal research and document assistant. The first release will use retrieval-augmented generation (RAG); an ontology and knowledge-graph extension is reserved for a later version.

## Current milestone: Phase 2 RAG foundation

The current implementation establishes the local Python API boundary, SQLite metadata storage, local Ollama detection/model listing, a JavaFX status dashboard, Windows packaging scripts, and ingestion for plain text, PDF, and DOCX with offset-tracked chunks. Stored chunks can be embedded locally with Ollama, indexed in persistent local Qdrant storage, and searched semantically. Grounded answer generation is still pending.

### Run the API

From `ai-engine/`, create and activate a virtual environment, then install the pinned dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The service binds to loopback by default. Visit `http://127.0.0.1:8000/docs` for the local API schema. Startup creates `local-data/database/lawsphere.db`; set `LAWSPHERE_DATABASE_PATH` to use another local path. `GET /api/v1/system/status` reports API, SQLite, and Ollama availability. `GET /api/v1/models` lists models already installed in Ollama. Configure the local Ollama endpoint with `LAWSPHERE_OLLAMA_BASE_URL`; checks time out quickly and report unavailable when the service cannot be reached.

### Ingest plain text

`POST /api/v1/documents/text` stores a title, optional source reference, normalized text, and overlapping chunks in the local SQLite database. Each chunk records its offsets in the stored text for later source references. Requests accept up to 2 MB of text. For example:

```powershell
$body = @{
    title = "Sample legal source"
    source = "Manual import"
    content = "Paste source text here. Paragraphs and line breaks are retained."
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/documents/text" `
    -Method Post -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/documents"
```

PDF and DOCX files can be submitted as multipart uploads to `POST /api/v1/documents/upload` (20 MB maximum). The original file is saved under the local `documents/` data folder; extracted text and chunks go into SQLite. PDF chunk metadata includes its page number. Password-protected PDFs and image-only PDFs are rejected; OCR is not included yet. For a manual upload, use the interactive form at `http://127.0.0.1:8000/docs`, or run:

```powershell
curl.exe -F "file=@C:\path\to\document.pdf" `
    -F "title=Imported legal document" `
    -F "source=Manual import" `
    http://127.0.0.1:8000/api/v1/documents/upload
```

PyMuPDF is dual-licensed under AGPL-3.0 or a commercial license; review its [license terms](https://pypi.org/project/pymupdf/) before distributing a packaged build.

### Embed and index stored chunks

Install Ollama separately and pull the default embedding model once while online: `ollama pull embeddinggemma`. Embedding requests then run against the configured local Ollama endpoint. The API uses Ollama's local batch embedding interface and stores vectors and citation metadata with Qdrant's persistent local client ([Ollama embedding API](https://docs.ollama.com/capabilities/embeddings), [Qdrant Python client](https://pypi.org/project/qdrant-client/)). No model is downloaded automatically. To index a previously ingested document, send `POST /api/v1/documents/{document_id}/index`; the ID is returned by the text/upload endpoints. By default vector files are in `ai-engine/local-data/vectors`, or `%LOCALAPPDATA%\LawSphere\vectors` when launched by the desktop app. Override with `LAWSPHERE_VECTOR_STORE_PATH`.

```powershell
$documentId = "<id returned by the ingest request>"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/documents/$documentId/index" -Method Post
```

### Search indexed chunks

Send a question or search phrase to `POST /api/v1/search`. Results include ranked text excerpts, similarity scores, document titles, source references, and page/offset metadata for citations. Only indexed chunks are searched; an empty result list means no chunks are indexed yet for the configured embedding model. For example:

```powershell
$body = @{ query = "What does the source say about bail?"; limit = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/search" `
    -Method Post -ContentType "application/json" -Body $body
```

### JavaFX desktop shell

Install Python 3.11 or later, Java 21, and Maven. From the project folder, prepare the Python environment with the setup script. The script installs it in `%LOCALAPPDATA%\LawSphere\python-env` on Windows. Then launch the dashboard from `desktop-app/`. It starts the local API if needed, checks service and Ollama readiness on a background thread, and lists installed models. Closing the window stops only the backend process started by this application. Managed runs keep the database and logs under `%LOCALAPPDATA%\LawSphere`.

```powershell
.\scripts\setup-python.ps1
Set-Location .\desktop-app
mvn javafx:run
```

Set `LAWSPHERE_PYTHON_EXECUTABLE` if you need to select a different Python executable. Set `LAWSPHERE_PROJECT_ROOT` when launching from outside the project folders.

### Build a Windows package

Run packaging on 64-bit Windows with Java 21, Maven, and WiX Toolset 3.x on `PATH` for `.exe` or `.msi` installers. An app image can be built without WiX. The bundle contains the Java runtime, desktop app, and Python source. Install Python and prepare its environment separately with the included setup script; Ollama and AI models are also installed separately. Generated packages go under `packaging/build/`.

```powershell
.\packaging\package-windows.ps1
# or create an MSI / app image:
.\packaging\package-windows.ps1 -PackageType msi
.\packaging\package-windows.ps1 -PackageType app-image
```

Application data is stored under `%LOCALAPPDATA%\LawSphere` and remains outside the installed files when the app is uninstalled.

## Roadmap

- [x] Phase 1, slice 1: local API skeleton, environment settings, status response contract
- [x] Phase 1, slice 2: local SQLite initialization
- [x] Phase 1, slice 3: local Ollama connectivity and installed-model listing
- [x] Phase 1, slice 4: Java HTTP client for Python API status and model endpoints
- [x] Phase 1, slice 5: Java-managed local Python service startup and shutdown
- [x] Phase 1, slice 6: JavaFX dashboard for local service and model status
- [x] Phase 1, slice 7: Python environment setup script and startup recovery guidance
- [x] Packaging preparation: Windows EXE/MSI and app-image build script added
- [ ] Build and verify the Windows installer on a Windows packaging machine
- [x] Phase 2, slice 1: normalized plain-text storage and offset-tracked chunks
- [x] Phase 2, slice 2: PDF/DOCX upload and local text extraction
- [x] Phase 2, slice 3: local Ollama chunk embeddings and persistent Qdrant indexing
- [x] Phase 2, slice 4: semantic search with ranked chunk and citation metadata
- [ ] Phase 2: OCR and grounded answer generation
- [ ] Phase 3 onward: authoritative Indian legal sources, document intelligence, desktop UI, packaging
- [ ] Version 2: ontology and knowledge-graph extension after Version 1 is functional

## Privacy direction

The API binds to `127.0.0.1` by default. Legal documents, prompts, and embeddings are intended to remain local. Do not add external AI services or transmit user content outside the device.

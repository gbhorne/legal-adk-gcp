# adk-legal-assistant

Privacy-first AI legal assistant for small law firms. Contract review, document drafting, and legal research grounded in 9M+ real court opinions from CourtListener.

Built with Google ADK, Vertex AI Search, Gemini 2.5, Cloud DLP, and Cloud Run.

**Companion repo:** [langgraph-legal-assistant](https://github.com/gbhorne/langgraph-legal-assistant)

---

## The problem

Only 4% of small law firms have adopted AI widely (Clio 2025 Legal Trends Report). Legal teams spend 3.2 hours reviewing a single contract. Harvey, LegalOn, and Spellbook serve BigLaw. The 2-10 attorney SMB market is almost entirely unserved.

This project builds the tool for the other 96%.

---

## What it does

### Contract review (POST /review)
Paste a contract, get back a structured risk report:
- Clause-by-clause risk ratings (high / medium / low)
- Plain-English explanation of each risk
- Relevant case citations from real court opinions
- Suggested fallback language for high-risk clauses

### Legal research (POST /research)
Ask a natural language question, get back:
- Direct answer grounded in retrieved case law
- Supporting analysis with citations (case name, court, year, CourtListener URL)
- Jurisdiction-specific warnings
- Related questions to consider

### Document drafting (POST /draft)
Provide contract type, jurisdiction, and party names, get back:
- Complete first-pass contract in markdown
- Inline [ATTORNEY NOTE:] comments flagging customization required
- List of items requiring attorney review before use

**Supported contract types:** NDA, Employment Agreement, Commercial Lease, Asset Purchase Agreement

---

## Architecture
`
Attorney request
      |
      v
FastAPI (Cloud Run)
      |
      v
ADK Orchestrator (legal_orchestrator)
  |-- ReviewAgent  --> analyze_contract() --> RAG --> Gemini --> ContractRiskReport
  |-- ResearchAgent --> legal_research()  --> RAG --> Gemini --> LegalResearchMemo
  +-- DraftAgent   --> draft_document()  --> RAG --> Gemini --> DraftedDocument
                                               |
                                         Vertex AI Search
                                         (1,010+ GA opinions
                                          + clause library)
                                               |
                                         CourtListener API
                                         (nightly Cloud Run job)
`

**Compliance by design:**
- Cloud DLP tokenizes PII before every LLM call
- Per-firm GCS bucket isolation (client documents never enter shared corpus)
- VPC-SC perimeter in production
- Every output includes hardcoded attorney review requirement (ABA Rule 1.6)

---

## Data sources

| Source | Coverage | Access |
|--------|----------|--------|
| CourtListener REST API | 9M+ opinions, 471 jurisdictions | Free token |
| Harvard Caselaw Access Project | All official US case law through 2020 | Bulk CC license |
| ABA Model Rules | Professional conduct by state | Public web |
| Clause library (this repo) | Templates by contract type + jurisdiction | JSON files |

---

## Quickstart

### Prerequisites
- Python 3.12
- GCP project with billing enabled
- CourtListener API token (free at courtlistener.com/profile/api-token/)
- Google AI Studio API key (free at aistudio.google.com/apikey)

### 1. Clone and configure
`powershell
git clone https://github.com/gbhorne/legal-adk-gcp
cd legal-adk-gcp
copy .env.example .env
# Edit .env: set COURTLISTENER_TOKEN and GOOGLE_API_KEY
`

### 2. Install dependencies
`powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
`

### 3. Seed the corpus (Georgia only for first run)
`powershell
python corpus/ingest_courtlistener.py --court ga --max 500
python corpus/index_corpus.py --prefix courtlistener/
`

### 4. Run the API
`powershell
set GOOGLE_GENAI_USE_VERTEXAI=false
python api/main.py
`

### 5. Run the ADK web UI
`powershell
set GOOGLE_GENAI_USE_VERTEXAI=false
adk web
`

Open http://localhost:8000 and select the agents app.

### 6. Test the endpoints
`powershell
# Health check
curl http://localhost:8080/health

# Contract review
curl -X POST http://localhost:8080/review \
  -H "Content-Type: application/json" \
  -d "{\"contract_text\": \"Employee agrees not to compete for 5 years in the US.\", \"jurisdiction\": \"Georgia\"}"

# Legal research
curl -X POST http://localhost:8080/research \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is the maximum enforceable non-compete duration in Georgia?\", \"jurisdiction\": \"Georgia\"}"
`

---

## GCP services used

| Service | Purpose |
|---------|---------|
| Cloud Run | FastAPI API + nightly ingestion job |
| Vertex AI Search | RAG corpus - case law + clause library |
| Gemini 2.5 Flash | Clause classification, risk rating, drafting |
| Cloud DLP | PII tokenization before LLM calls |
| GCS | Raw opinions + processed corpus |
| Secret Manager | CourtListener API token |
| Cloud Scheduler | Nightly corpus update |

---

## Project structure
`
legal-adk-gcp/
+-- agents/
|   +-- agent.py          # ADK root orchestrator
|   +-- review_agent.py   # Contract risk analysis agent
|   +-- research_agent.py # Legal Q&A agent
|   +-- draft_agent.py    # Document drafting agent
|   +-- tools.py          # Shared tool functions (analyze_contract, legal_research, draft_document)
|   +-- schemas.py        # Pydantic output types
|   +-- rag.py            # Vertex AI Search query helper
+-- corpus/
|   +-- ingest_courtlistener.py  # CourtListener scraper
|   +-- index_corpus.py          # GCS to Vertex AI Search pipeline
+-- dlp/
|   +-- tokenizer.py      # Cloud DLP PII tokenization
+-- api/
|   +-- main.py           # FastAPI: /review, /draft, /research
+-- config.py
+-- requirements.txt
+-- Dockerfile
`

---

## ADK vs LangGraph

See the companion repo [langgraph-legal-assistant](https://github.com/gbhorne/langgraph-legal-assistant) for the same ReviewAgent implemented as a LangGraph StateGraph.

| Dimension | Google ADK | LangGraph |
|-----------|-----------|-----------|
| Agent definition | Declarative (Agent + FunctionTool) | Explicit StateGraph nodes |
| Multi-agent routing | Built-in sub_agents | Manual conditional edges |
| Debugging | ADK web UI with trace panel | LangGraph Studio |
| Gemini integration | Native | Via langchain-google-vertexai |
| Best for | GCP-native production deployments | Complex branching, research |

---

## Related projects

- [agent-finops-gcp](https://github.com/gbhorne/agent-finops-gcp) - GCP cost intelligence agent
- [adk-supply-chain-intel](https://github.com/gbhorne/adk-supply-chain-intel) - Multi-signal disruption detection (coming Week 5)
- [adk-benefits-intake](https://github.com/gbhorne/adk-benefits-intake) - Government benefits document AI (coming Week 9)

---

*Built by Gregory Horne - Cloud Architect and GCP AI/ML Platform Engineer*

*All outputs from this system require review by a licensed attorney before use. This system does not provide legal advice.*

---

## Experimental disclaimer

This project is experimental software intended for portfolio demonstration and research purposes only. It has not been validated for production legal use. All outputs require review by a licensed attorney before use in any legal matter. Outputs from this system do not constitute legal advice and do not create an attorney-client relationship. The authors assume no liability for any use of or reliance on system outputs. This project is not affiliated with or endorsed by any bar association, law firm, or legal technology certification body.

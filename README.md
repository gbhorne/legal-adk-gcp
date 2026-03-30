# adk-legal-assistant

Privacy-first AI legal assistant for small law firms. Contract review, document drafting, and legal research built on a pipeline sourcing from CourtListener's multi-million-opinion corpus. Current demo index uses a Georgia-focused subset of 1,010+ opinions.

Built with Google ADK, Vertex AI Search, Gemini 2.5 Flash, and Cloud Run.

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
## Architecture
![adk-legal-assistant architecture](https://raw.githubusercontent.com/gbhorne/legal-adk-gcp/main/architecture_legal.svg)

**Compliance by design:**
- Cloud DLP inspect API tokenizes seven PII infoTypes (PERSON_NAME, EMAIL_ADDRESS, PHONE_NUMBER, SSN, ITIN, CREDIT_CARD_NUMBER, STREET_ADDRESS) before every LLM call; local regex fallback if API is unavailable
- Per-firm GCS bucket isolation with CMEK planned for production; current build uses a shared corpus of public court opinions only
- VPC-SC perimeter targeted for production deployment; not provisioned in this experimental build
- Every output includes hardcoded attorney review requirement under ABA Model Rules 1.1 (Competence) and 5.3 (Supervision); confidentiality controls align with Rule 1.6

---

## Data sources

| Source | Coverage | Access |
|--------|----------|--------|
| CourtListener REST API | 9M+ opinions, 471 jurisdictions (pipeline); 1,010+ Georgia opinions in current demo index | Free token |
| Contract templates (in-code) | NDA, Employment Agreement, Commercial Lease, Asset Purchase Agreement | tools.py CONTRACT_TEMPLATES |

---

## GCP services used

| Service | Purpose |
|---------|---------|
| Cloud Run | FastAPI API host; ingestion job deployment target |
| Vertex AI Search | RAG corpus: case law retrieval |
| Gemini 2.5 Flash | Clause classification, risk rating, drafting |
| Cloud DLP | PII tokenization before every LLM call; seven infoTypes; local regex fallback |
| GCS | Raw opinions + processed corpus |
| Secret Manager | CourtListener API token |
| Cloud Scheduler | Planned for nightly corpus update; not configured in current build |

---

## Project structure

```
legal-adk-gcp/
├── agents/
│   ├── agent.py                   # ADK root orchestrator
│   ├── review_agent.py            # Contract risk analysis agent
│   ├── research_agent.py          # Legal Q&A agent
│   ├── draft_agent.py             # Document drafting agent
│   ├── tools.py                   # analyze_contract, legal_research, draft_document
│   ├── schemas.py                 # Pydantic output types
│   └── rag.py                     # Vertex AI Search query helper
├── dlp/
│   └── tokenizer.py               # Cloud DLP PII tokenization with local regex fallback
├── api/
│   └── main.py                    # FastAPI: /health /review /research /draft
├── docs/
│   └── technical-qa.md            # In-depth technical Q&A
├── requirements.txt
├── Dockerfile
└── architecture_legal.svg         # System architecture diagram
```

> Infrastructure config, corpus ingestion scripts, and environment files are not included in this public repo. The architecture and agent design are fully documented above and in `docs/technical-qa.md`.

---

## ADK vs LangGraph

See the companion repo [langgraph-legal-assistant](https://github.com/gbhorne/langgraph-legal-assistant) for the same ReviewAgent implemented as a LangGraph StateGraph.

| Dimension | Google ADK | LangGraph |
|-----------|-----------|-----------|
| Agent definition | Declarative (Agent + FunctionTool) | Explicit StateGraph nodes |
| Multi-agent routing | Built-in sub_agents | Manual conditional edges |
| Debugging | ADK web UI with trace panel | LangGraph Studio |
| Gemini integration | Native google-genai | Via langchain-google-genai |
| Best for | GCP-native production deployments | Complex branching, research |

---


*Built by Gregory Horne - Cloud Architect and GCP AI/ML Platform Engineer*

*All outputs from this system require review by a licensed attorney before use. This system does not provide legal advice.*

---

## Experimental disclaimer

This project is experimental software intended for portfolio demonstration and research purposes only. It has not been validated for production legal use. All outputs require review by a licensed attorney before use in any legal matter. Outputs from this system do not constitute legal advice and do not create an attorney-client relationship. The authors assume no liability for any use of or reliance on system outputs. This project is not affiliated with or endorsed by any bar association, law firm, or legal technology certification body.






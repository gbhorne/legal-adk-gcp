# adk-legal-assistant: Technical Q&A

**EXPERIMENTAL NOTICE:** This project is experimental software intended for portfolio demonstration and research purposes only. It has not been validated for production legal use. All outputs require review by a licensed attorney. Do not use this system for actual legal matters without qualified professional oversight. See the full disclaimer at the bottom of this document.

---

## Architecture and Design

**Q: What is the overall architecture of this system?**

The system is a multi-agent pipeline built on Google ADK 1.28. A root orchestrator agent (legal_orchestrator) receives all requests and routes them to one of three specialist agents: ReviewAgent for contract analysis, ResearchAgent for legal Q&A, and DraftAgent for document generation. Each specialist agent has one registered FunctionTool that performs the actual work. Before any contract text reaches the LLM, a local regex tokenization layer replaces PII patterns (email, phone, SSN) with reversible surrogate tokens. Vertex AI Search provides the RAG layer, and Gemini 2.5 Flash handles all generation tasks. FastAPI exposes the agents as REST endpoints deployable to Cloud Run.

**Q: Why use Google ADK instead of LangChain or a direct API integration?**

ADK provides native multi-agent orchestration with automatic tool-calling loops, session management, and sub-agent routing. The declarative Agent definition with FunctionTool wrapping is significantly less boilerplate than building an equivalent LangChain pipeline. ADK also ships a web UI with a full trace panel showing every tool call, LLM invocation, and agent transfer, which is useful for debugging and for demonstrating the system's decision path during reviews. That said, ADK is newer and less battle-tested than LangChain. The companion LangGraph repo exists specifically to compare the two approaches for this same use case.

**Q: How does the orchestrator decide which agent to route a request to?**

The root orchestrator is an ADK Agent with a system instruction that describes the routing logic in plain English. When a user sends a message, Gemini processes the instruction and the message, then calls the transfer_to_agent tool with the appropriate sub-agent name. ADK handles the actual agent transfer. The routing heuristics are: requests containing contract text or asking about clause risk go to review_agent; natural language legal questions go to research_agent; requests to create a new document go to draft_agent. In practice, routing accuracy has been high for clearly phrased requests and occasionally requires clarification for ambiguous ones.

**Q: What is the role of agents/tools.py vs the individual agent files?**

tools.py contains all the actual business logic: the three core functions (analyze_contract, legal_research, draft_document) that do the real work. The individual agent files (review_agent.py, research_agent.py, draft_agent.py) contain only the ADK Agent definition: the model name, description, instruction, and the FunctionTool wrapping that function. This separation means the core logic can be tested independently of the ADK framework, and the same tool function could theoretically be wrapped by a different agent framework without modification.

---

## Data and Corpus

**Q: Where does the case law come from?**

The corpus uses the CourtListener REST API maintained by the Free Law Project, a nonprofit. CourtListener indexes 9 million+ court opinions from 471 jurisdictions, updated daily, and provides free API access with token authentication. The initial corpus for this project is 1,010+ Georgia Supreme Court and Court of Appeals opinions filed between 2024 and 2025, chosen because they postdate most LLM training cutoffs, making them a genuine retrieval contribution rather than something Gemini already knows. The ingestion pipeline supports additional jurisdictions and larger pulls; the Georgia subset reflects the scope of this portfolio build.

**Q: How are opinions ingested and indexed?**

corpus/ingest_courtlistener.py queries the CourtListener API for opinions by court ID and date range, stores each opinion as a JSON blob in GCS under courtlistener/{court_id}/{date}/{cluster_id}.json. corpus/index_corpus.py reads those blobs, generates a JSONL file with the schema {id, structData: {case_name, court_id, date_filed, citation, source_url, text}}, uploads the JSONL to GCS, and calls the Vertex AI Search import API. In production, this pipeline would run as a Cloud Run Job triggered by Cloud Scheduler on a nightly schedule.

**Q: How does Vertex AI Search handle the retrieval?**

Vertex AI Search uses a structured data datastore. Each document in the index is a court opinion chunk with a text field and metadata fields. When an agent calls query_corpus(), the RAG helper sends the query to the search serving config endpoint and retrieves the top-k results ranked by relevance. The retrieved documents (case name, citation, court, date, and text snippet) are assembled into a context block and passed to Gemini as grounded source material. Gemini is explicitly instructed to only cite cases that appear in the retrieved context.

**Q: Why are the text snippets short in the current corpus?**

The initial ingestion uses the snippet field from the CourtListener API response, which is typically under 500 characters. This is a known limitation. Full opinion text requires fetching each opinion individually via the opinions endpoint, which is slower and generates more API calls. The production approach would fetch full text for opinions above a relevance threshold and store larger chunks. For the portfolio demonstration, snippet-level text is sufficient to show the retrieval and citation pipeline working correctly.

**Q: Can the corpus be expanded to other jurisdictions?**

Yes. The COURT_IDS map in ingest_courtlistener.py already has entries for tex (Texas), fla (Florida), ny (New York), and cal (California). Running the ingestion script with --court tex pulls Texas Supreme Court and Court of Appeals opinions. Vertex AI Search supports multiple datastores, so each jurisdiction could have its own datastore, or opinions from all jurisdictions could be mixed in a single datastore with court_id as a filter field.

---

## Privacy and Compliance

**Q: How does PII tokenization work?**

When contract text enters the system, dlp/tokenizer.py applies local regex patterns to detect and replace three PII types: EMAIL_ADDRESS, PHONE_NUMBER, and US_SSN. Each detected value is replaced with a reversible surrogate token like [EMAIL_ADDRESS_1] or [US_SSN_2]. The token-to-original mapping is stored in a TokenizationContext object. After the LLM returns its analysis, detokenize() replaces all tokens in the output with the original values. The LLM sees only tokenized text at every point in the pipeline.

This is a local implementation, not a Cloud DLP API call. The google-cloud-dlp package is included in requirements.txt as a dependency for future production hardening. A full Cloud DLP integration would expand coverage to additional infoTypes (PERSON_NAME, STREET_ADDRESS, CREDIT_CARD_NUMBER, and others), use Google-managed detection models, and provide an audit trail of inspections. That upgrade path is documented but not implemented in the current experimental build.

**Q: What is the attorney review requirement and why is it hardcoded?**

Every output schema (ContractRiskReport, LegalResearchMemo, DraftedDocument) in agents/schemas.py has a field attorney_review_required: bool = True and a fixed attorney_review_note that cannot be overridden. This is intentional. Most legal AI tools put a disclaimer in the UI footer or in the system prompt, both of which can be ignored or overridden. By making it a structural property of the output type, the requirement appears in every API response, every ADK web UI response, and every test.

The review and supervision obligation is grounded in ABA Model Rule 1.1 (Competence), which requires attorneys to maintain competence when using technology, and Rule 5.3 (Supervision of Nonlawyers), which addresses attorney responsibility for work product produced with non-lawyer assistance including AI tools. Rule 1.6 (Confidentiality) is the anchor for the DLP and data isolation controls, not the review requirement. The attorney_review_note in ContractRiskReport reflects this distinction.

**Q: Does this system comply with ABA Model Rule 1.6?**

This is an experimental system and has not been reviewed by legal ethics counsel. The PII tokenization layer and per-firm data isolation design address confidentiality concerns relevant to Rule 1.6. The attorney review requirement and supervision framing address competence and supervision obligations under Rules 1.1 and 5.3. Whether these measures are sufficient for a specific firm's obligations under Rule 1.6 and applicable state ethics rules is a question for the attorney's state bar and ethics counsel, not for this system.

**Q: What is per-firm data isolation and is it implemented here?**

The architecture design calls for each law firm to receive a dedicated GCS bucket with CMEK encryption using a firm-specific KMS key, plus a dedicated Vertex AI Search datastore for their client documents. This means two firms' data never coexist in the same storage resource. In the current implementation there is one shared corpus (public court opinions only, no client documents) and one datastore. The per-firm isolation architecture is documented and designed but not provisioned in this experimental build, because the corpus contains only public court opinions that carry no confidentiality obligation.

---

## Agents and Tools

**Q: What does analyze_contract() actually do step by step?**

First, it tokenizes the contract text through Cloud DLP. Second, it sends a prompt to Gemini asking it to extract all significant clauses as a JSON array, where each clause has a clause_type (from the ClauseType enum) and clause_text. Third, for each extracted clause, it queries Vertex AI Search for relevant case law using the clause type and jurisdiction as the search query. Fourth, it sends a second prompt to Gemini with the clause text and retrieved case law, asking it to rate the risk (high/medium/low/info), explain the risk in plain English, identify the legal basis, and suggest fallback language. Fifth, it assembles all clause analyses into a ContractRiskReport Pydantic object and returns it as JSON.

**Q: How does the system avoid hallucinated citations?**

The risk rating prompt explicitly instructs Gemini to only cite cases that appear in the retrieved context block. The retrieved cases are passed with their case name, citation, court, and date. The tool then assembles the citations list directly from the RAG results, not from the LLM output. Even if Gemini references a case in its analysis text, the structured citations in the output come from what Vertex AI Search actually returned. This two-track approach (LLM for prose analysis, RAG results for structured citations) is the core anti-hallucination mechanism.

**Q: What contract types does the DraftAgent support?**

The CONTRACT_TEMPLATES dictionary in tools.py currently defines four types: nda (Non-Disclosure Agreement), employment_agreement, commercial_lease, and asset_purchase. Each template specifies a display name and the standard party roles for that contract type. Adding a new contract type requires adding an entry to this dictionary and optionally adding jurisdiction-specific clause guidance to the prompt.

**Q: What happens when Gemini returns a list instead of a string for a field?**

This was a real issue encountered during development. Gemini 2.5 Flash occasionally returns risk_basis as a JSON array of bullet points rather than a single string. The tools.py code handles this with an isinstance check: if the value is a list, it joins the elements with spaces; if it is a string, it uses it directly. The same pattern handles risk_summary and fallback_language. This is a defensive coding pattern for working with LLMs that may not strictly follow output format instructions on every call.

**Q: Why does the API layer call the tool functions directly rather than going through the ADK agents?**

The FastAPI endpoints in api/main.py call analyze_contract(), legal_research(), and draft_document() directly from tools.py. This is intentional for the REST API path. The ADK agent layer adds conversation management, session state, and multi-turn routing on top of the tool functions: capabilities that are valuable in the interactive ADK web UI but unnecessary for a stateless REST API call. Using the tool functions directly gives the API a simpler, faster execution path without the overhead of ADK session management.

---

## Operational Concerns

**Q: What GCP services does this project use and what are the cost implications?**

The services used are: Cloud Storage (pennies per GB per month for corpus storage), Vertex AI Search (query cost plus index storage, roughly $2.50 per 1,000 queries for the custom search tier), Gemini 2.5 Flash via Google AI Studio API key (token-based pricing, approximately $0.15 per million input tokens and $0.60 per million output tokens as of March 2026), Cloud DLP (planned for production; not incurring costs in current build), Cloud Run (per-invocation pricing, negligible at low volume), and Secret Manager (minimal). For a portfolio project running occasional demos, total GCP spend is under $5/month. For a production small firm deployment handling 50 contracts per month, estimated cost is $20-50/month depending on contract length and query volume.

**Q: How is the Google API key managed?**

For local development, the API key is stored in the .env file which is excluded from the repository via .gitignore. The key is loaded into the process environment at startup. For production Cloud Run deployment, the key would be stored in Secret Manager and injected as an environment variable at container startup via Cloud Run secret references. The .env file was accidentally committed to the public repository during initial development, which triggered Google's automatic key revocation. A new key was generated and the .gitignore was corrected before further development.

**Q: What is the startup command for the ADK web UI?**

From the project root with the venv activated, set GOOGLE_GENAI_USE_VERTEXAI=false and GOOGLE_API_KEY to your key, then run adk web. ADK looks for root_agent in agents/agent.py, which it finds as the legal_orchestrator Agent. The web UI starts on http://127.0.0.1:8000. Select agents from the left panel to start a session.

**Q: Why does GOOGLE_GENAI_USE_VERTEXAI need to be set to false?**

ADK 1.28 defaults to using Vertex AI as the LLM backend, which requires OAuth2 credentials with the cloud-platform scope and a GCP project with Vertex AI Gemini API access enabled. The legal-adk GCP project does not have Vertex AI Gemini model access (a project-level allowlist issue that is separate from billing and API enablement). Setting GOOGLE_GENAI_USE_VERTEXAI=false tells ADK to use the Google AI Studio backend instead, which authenticates with a standard API key and does not require project-level Vertex AI model access.

---

## Limitations and Known Issues

**Q: What are the main limitations of the current implementation?**

The text snippets in the corpus are short (under 500 characters per opinion), which limits retrieval precision for complex legal questions. The system has been tested only with Georgia law; other jurisdictions are supported by the ingestion pipeline but the search index only contains Georgia opinions. The risk rating quality depends heavily on what Vertex AI Search retrieves, and some queries return zero results, falling back to Gemini's general knowledge. There is no user authentication, rate limiting, or access control in the current FastAPI implementation. The DLP tokenization covers common PII types but does not cover all possible confidential information in legal documents. The system has not been validated on a diverse set of real contracts.

**Q: What is the error parsing request label in the ADK trace panel?**

The ADK web UI labels any invocation that threw a Python exception at any point during execution as [error parsing request], even if the agent recovered and returned a result. During development, a Pydantic validation error occurred when Gemini returned risk_basis as a list rather than a string. The error was fixed in tools.py, but the trace panel label reflects the historical state of that invocation. In subsequent runs after the fix, the full risk report is returned successfully.

---

## EXPERIMENTAL DISCLAIMER

This software is experimental and is provided for portfolio demonstration, research, and educational purposes only.

This system has not been validated for accuracy, completeness, or fitness for any legal purpose. Outputs generated by this system do not constitute legal advice, do not create an attorney-client relationship, and must not be relied upon without independent review by a licensed attorney. The system may produce incorrect, incomplete, or misleading analysis.

The case citations returned by this system come from a corpus of publicly available court opinions. The system cannot guarantee that citations are accurate, that cases have not been overruled, or that the analysis correctly applies the cited authority to a specific legal situation.

Use of this system for actual legal matters without qualified professional oversight is not recommended and may expose users to risk. The authors assume no liability for any use of this system or reliance on its outputs.

This project is not affiliated with, endorsed by, or validated by any bar association, law firm, or legal technology certification body.

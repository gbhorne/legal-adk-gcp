import re

new_block = '## Project structure\n\n`\nlegal-adk-gcp/\n+-- agents/\n|   +-- agent.py                   # ADK root orchestrator\n|   +-- review_agent.py            # Contract risk analysis agent\n|   +-- research_agent.py          # Legal Q&A agent\n|   +-- draft_agent.py             # Document drafting agent\n|   +-- tools.py                   # analyze_contract, legal_research, draft_document\n|   +-- schemas.py                 # Pydantic output types\n|   +-- rag.py                     # Vertex AI Search query helper\n+-- corpus/\n|   +-- ingest_courtlistener.py    # CourtListener ingestion pipeline\n|   +-- index_corpus.py            # GCS to Vertex AI Search indexer\n+-- dlp/\n|   +-- tokenizer.py               # Cloud DLP PII tokenization\n+-- api/\n|   +-- main.py                    # FastAPI: /health /review /research /draft\n+-- docs/\n|   +-- technical-qa.md            # In-depth technical Q&A\n+-- config.py\n+-- requirements.txt\n+-- Dockerfile\n+-- architecture_legal.svg         # System architecture diagram\n`'

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'## Project structure.*?`', new_block, content, flags=re.DOTALL)

with open('README.md', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print('Done')

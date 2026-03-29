import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.tools import analyze_contract, legal_research, draft_document
from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("api")

app = FastAPI(
    title="adk-legal-assistant",
    description="Privacy-first AI legal assistant for small law firms",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    contract_text: str
    jurisdiction:  str = "Georgia"
    contract_name: str = "Contract"

class ResearchRequest(BaseModel):
    question:     str
    jurisdiction: str = "Georgia"

class DraftRequest(BaseModel):
    contract_type: str
    jurisdiction:  str = "Georgia"
    parties:       dict[str, str]
    parameters:    dict[str, Any] | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "project": config.PROJECT_ID,
        "version": "1.0.0",
        "corpus": "legal-adk-corpus-raw",
    }


@app.post("/review")
def review(body: ReviewRequest):
    log.info("POST /review - %s [%s]", body.contract_name, body.jurisdiction)
    try:
        import json
        result = analyze_contract(body.contract_text, body.jurisdiction)
        return json.loads(result)
    except Exception as e:
        log.error("Review failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research")
def research(body: ResearchRequest):
    log.info("POST /research - %s [%s]", body.question[:60], body.jurisdiction)
    try:
        import json
        result = legal_research(body.question, body.jurisdiction)
        return json.loads(result)
    except Exception as e:
        log.error("Research failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/draft")
def draft(body: DraftRequest):
    log.info("POST /draft - %s [%s]", body.contract_type, body.jurisdiction)
    try:
        import json
        parties_json = json.dumps(body.parties)
        result = draft_document(body.contract_type, body.jurisdiction, parties_json)
        return json.loads(result)
    except Exception as e:
        log.error("Draft failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=config.LOCAL_DEV,
    )

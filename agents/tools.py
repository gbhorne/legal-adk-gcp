import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import re

import google.generativeai as genai

from agents.schemas import (
    ClauseAnalysis, ClauseType, ContractRiskReport,
    LegalAuthority, LegalResearchMemo, DraftedDocument, RiskLevel,
)
from agents.rag import query_corpus
from dlp.tokenizer import new_context, tokenize, detokenize
from config import config

log = logging.getLogger("agents.tools")

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
_model = genai.GenerativeModel(config.GEMINI_MODEL)

CONTRACT_TEMPLATES = {
    "nda": {
        "display_name": "Non-Disclosure Agreement",
        "party_roles": ["Disclosing Party", "Receiving Party"],
    },
    "employment_agreement": {
        "display_name": "Employment Agreement",
        "party_roles": ["Employer", "Employee"],
    },
    "commercial_lease": {
        "display_name": "Commercial Lease Agreement",
        "party_roles": ["Landlord", "Tenant"],
    },
    "asset_purchase": {
        "display_name": "Asset Purchase Agreement",
        "party_roles": ["Seller", "Buyer"],
    },
}


def _gemini(prompt: str) -> str | None:
    try:
        resp = _model.generate_content(prompt)
        return resp.text
    except Exception as e:
        log.error("Gemini call failed: %s", e)
        return None


def _extract_json(text: str):
    if not text:
        return None
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        idx = text.find(start_char)
        if idx != -1:
            last = text.rfind(end_char)
            if last > idx:
                try:
                    return json.loads(text[idx:last + 1])
                except json.JSONDecodeError:
                    continue
    return None


# -- ReviewAgent tool ----------------------------------------------------------

def analyze_contract(contract_text: str, jurisdiction: str) -> str:
    """
    Analyze a contract for legal risk.

    Extracts all clauses, rates each clause as high/medium/low risk,
    retrieves relevant case law from the Georgia court opinions corpus,
    and returns a structured JSON risk report.

    Args:
        contract_text: The full text of the contract to analyze
        jurisdiction: The governing law jurisdiction, e.g. 'Georgia' or 'Texas'

    Returns:
        JSON string containing the ContractRiskReport
    """
    ctx = new_context()
    clean = tokenize(contract_text, ctx)

    # Step 1: extract clauses
    clause_types = ", ".join(ct.value for ct in ClauseType)
    extract_prompt = (
        "Extract all significant clauses from this contract as a JSON array.\n"
        "Each element must have clause_type (one of: " + clause_types + ") and clause_text.\n"
        "Return ONLY valid JSON.\n\nContract:\n" + clean[:12000]
    )
    raw = _gemini(extract_prompt)
    clauses = _extract_json(raw) or []
    if not isinstance(clauses, list):
        clauses = []

    # Step 2: rate each clause
    analyzed = []
    risk_order = {"high": 3, "medium": 2, "low": 1, "info": 0}

    for raw_clause in clauses:
        ct_str = raw_clause.get("clause_type", "miscellaneous")
        ct_text = raw_clause.get("clause_text", "").strip()
        if not ct_text:
            continue

        try:
            clause_type = ClauseType(ct_str)
        except ValueError:
            clause_type = ClauseType.MISCELLANEOUS

        # RAG lookup
        rag = query_corpus(ct_str + " " + jurisdiction + " enforceability", max_results=3)
        case_law = "\n\n".join(
            "[" + r["case_name"] + " | " + r["court_id"] + " | " + r["date_filed"] + "]\n" + r["text"]
            for r in rag
        ) or "No relevant case law retrieved."

        risk_prompt = (
            "Rate the legal risk of this clause for the signing party.\n\n"
            "Clause type: " + ct_str + "\n"
            "Jurisdiction: " + jurisdiction + "\n"
            "Clause text: " + ct_text[:2000] + "\n\n"
            "Case law:\n" + case_law[:3000] + "\n\n"
            "Return JSON: {risk_level, risk_summary, risk_basis, fallback_language}\n"
            "risk_level must be: high, medium, low, or info\n"
            "Return ONLY valid JSON."
        )
        rating = _extract_json(_gemini(risk_prompt)) or {}

        try:
            risk_level = RiskLevel(rating.get("risk_level", "medium"))
        except ValueError:
            risk_level = RiskLevel.MEDIUM

        citations = [
            LegalAuthority(
                case_name=r["case_name"],
                citation=r["citation"],
                court=r["court_id"],
                year=r["date_filed"][:4] if r.get("date_filed") else None,
                source_url=r["source_url"],
                relevance_note="Relevant to " + ct_str + " in " + jurisdiction,
            )
            for r in rag if r.get("case_name") and r["case_name"] != "Unknown"
        ]

        analyzed.append(ClauseAnalysis(
            clause_type=clause_type,
            clause_text=detokenize(ct_text, ctx),
            risk_level=risk_level,
            risk_summary=str(rating.get("risk_summary", "")) if not isinstance(rating.get("risk_summary"), list) else " ".join(rating.get("risk_summary", [])) ,
            risk_basis=str(rating.get("risk_basis", "")) if not isinstance(rating.get("risk_basis"), list) else " ".join(rating.get("risk_basis", [])) ,
            fallback_language=str(rating.get("fallback_language")) if rating.get("fallback_language") and not isinstance(rating.get("fallback_language"), list) else (" ".join(rating.get("fallback_language", [])) if isinstance(rating.get("fallback_language"), list) else None) ,
            citations=citations,
        ))

    overall = max(analyzed, key=lambda c: risk_order.get(c.risk_level.value, 0)).risk_level if analyzed else RiskLevel.INFO
    high = sum(1 for c in analyzed if c.risk_level == RiskLevel.HIGH)
    med  = sum(1 for c in analyzed if c.risk_level == RiskLevel.MEDIUM)

    report = ContractRiskReport(
        contract_name="Contract",
        jurisdiction=jurisdiction,
        overall_risk_level=overall,
        overall_summary=str(len(analyzed)) + " clauses analyzed. " + str(high) + " high-risk, " + str(med) + " medium-risk.",
        clauses=analyzed,
    )
    return report.model_dump_json()


# -- ResearchAgent tool --------------------------------------------------------

def legal_research(question: str, jurisdiction: str) -> str:
    """
    Answer a legal research question using the case law corpus.

    Retrieves relevant court opinions and returns a grounded research
    memo with direct answer, analysis, citations, and related questions.

    Args:
        question: The legal research question
        jurisdiction: The jurisdiction to focus on, e.g. 'Georgia'

    Returns:
        JSON string containing the LegalResearchMemo
    """
    ctx = new_context()
    clean_q = tokenize(question, ctx)

    rag = query_corpus(jurisdiction + " " + clean_q, max_results=5)
    if len(rag) < 2:
        rag = query_corpus(clean_q, max_results=5)

    case_law = "\n\n---\n\n".join(
        "[" + r["case_name"] + " | " + (r["citation"] or "no citation") + " | " + r["court_id"] + " | " + r["date_filed"] + "]\n" + r["text"]
        for r in rag
    ) or "No case law retrieved."

    prompt = (
        "You are a legal research assistant. Answer this question for a licensed attorney.\n\n"
        "Question: " + clean_q + "\n"
        "Jurisdiction: " + jurisdiction + "\n\n"
        "Retrieved case law:\n" + case_law[:6000] + "\n\n"
        "Return JSON with: answer, supporting_analysis, jurisdiction_warnings (array), related_questions (array)\n"
        "Only cite cases from the retrieved context. Return ONLY valid JSON."
    )

    result = _extract_json(_gemini(prompt)) or {}

    authorities = [
        LegalAuthority(
            case_name=r["case_name"],
            citation=r["citation"] or "",
            court=r["court_id"],
            year=r["date_filed"][:4] if r.get("date_filed") else None,
            source_url=r["source_url"],
            relevance_note="Relevant to: " + question[:60],
        )
        for r in rag if r.get("case_name") and r["case_name"] != "Unknown"
    ]

    memo = LegalResearchMemo(
        question=question,
        jurisdiction=jurisdiction,
        answer=detokenize(result.get("answer", "Analysis unavailable."), ctx),
        supporting_analysis=detokenize(result.get("supporting_analysis", ""), ctx),
        authorities=authorities,
        jurisdiction_warnings=result.get("jurisdiction_warnings", []),
        related_questions=result.get("related_questions", []),
    )
    return memo.model_dump_json()


# -- DraftAgent tool -----------------------------------------------------------

def draft_document(contract_type: str, jurisdiction: str, parties_json: str) -> str:
    """
    Generate a first-pass contract draft.

    Supported contract types: nda, employment_agreement, commercial_lease, asset_purchase

    Args:
        contract_type: Type of contract to draft
        jurisdiction: Governing law jurisdiction, e.g. 'Georgia'
        parties_json: JSON string mapping party roles to names,
                      e.g. '{"Disclosing Party": "Acme Corp", "Receiving Party": "Beta LLC"}'

    Returns:
        JSON string containing the DraftedDocument
    """
    ct = contract_type.lower().replace(" ", "_")
    template = CONTRACT_TEMPLATES.get(ct)
    if not template:
        available = ", ".join(CONTRACT_TEMPLATES.keys())
        return json.dumps({"error": "Unknown contract type. Available: " + available})

    try:
        parties = json.loads(parties_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "parties_json must be valid JSON"})

    parties_str = "\n".join("- " + role + ": " + name for role, name in parties.items())

    rag = query_corpus(ct.replace("_", " ") + " " + jurisdiction + " standard clauses", max_results=4)
    rag_context = "\n\n".join("[" + r["case_name"] + "]\n" + r["text"] for r in rag) or "Use standard " + jurisdiction + " terms."

    prompt = (
        "Draft a complete " + template["display_name"] + " under " + jurisdiction + " law.\n\n"
        "Parties:\n" + parties_str + "\n\n"
        "Relevant legal context:\n" + rag_context[:4000] + "\n\n"
        "Instructions:\n"
        "- Use professional legal language\n"
        "- Add [ATTORNEY NOTE: ...] where attorney must customize\n"
        "- Use [BRACKETS] for values attorney must fill in\n"
        "- Include title, recitals, numbered sections, signature block\n\n"
        "Return JSON with: markdown_text (complete draft), drafting_notes (array of 5-8 items)\n"
        "Return ONLY valid JSON."
    )

    result = _extract_json(_gemini(prompt)) or {}

    doc = DraftedDocument(
        contract_type=template["display_name"],
        jurisdiction=jurisdiction,
        parties=parties,
        markdown_text=result.get("markdown_text", "Draft generation failed."),
        drafting_notes=result.get("drafting_notes", ["Manual review required."]),
    )
    return doc.model_dump_json()



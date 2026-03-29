import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import re

import google.generativeai as genai

from agents.schemas import (
    ClauseAnalysis, ClauseType, ContractRiskReport,
    LegalAuthority, RiskLevel,
)
from agents.rag import query_corpus
from dlp.tokenizer import new_context, tokenize, detokenize
from config import config

log = logging.getLogger("agents.review")

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
model = genai.GenerativeModel(config.GEMINI_MODEL)

CLAUSE_TYPES = [ct.value for ct in ClauseType]

EXTRACT_PROMPT = """You are a legal document analyst. Extract all significant clauses from this contract.

Return a JSON array. Each element must have:
- "clause_type": one of [{types}]
- "clause_text": the exact clause text verbatim from the contract

Contract:
{contract}

Return ONLY a valid JSON array. No explanation, no markdown."""

RISK_PROMPT = """You are a legal risk analyst for a small law firm attorney.

Rate the risk of this clause for the party signing the contract.

Clause type: {clause_type}
Jurisdiction: {jurisdiction}
Clause text: {clause_text}

Relevant case law from the legal database:
{case_law}

Return a JSON object with exactly these fields:
{{
  "risk_level": "high" or "medium" or "low" or "info",
  "risk_summary": "2-3 plain English sentences explaining the risk",
  "risk_basis": "specific statute, case law, or legal principle",
  "fallback_language": "suggested replacement text, or null if clause is acceptable"
}}

Return ONLY valid JSON. No markdown."""


def _extract_json(text):
    """
    Extract JSON from a response that may contain thinking text before it.
    Finds the first [ or { and extracts from there.
    """
    text = text.strip()
    # Find first JSON array or object
    for start_char in ['[', '{']:
        idx = text.find(start_char)
        if idx != -1:
            # Find matching closing bracket
            end_char = ']' if start_char == '[' else '}'
            # Try from this position to end
            candidate = text[idx:]
            # Find last occurrence of closing bracket
            last_idx = candidate.rfind(end_char)
            if last_idx != -1:
                candidate = candidate[:last_idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
    return None


def _call_gemini(prompt):
    try:
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        log.error("Gemini call failed: %s", e)
        return None


def extract_clauses(contract_text):
    prompt = EXTRACT_PROMPT.format(
        types=", ".join(CLAUSE_TYPES),
        contract=contract_text[:12000],
    )
    raw = _call_gemini(prompt)
    if not raw:
        return []
    result = _extract_json(raw)
    if result is None:
        log.error("Failed to extract JSON from clause response")
        return []
    return result if isinstance(result, list) else []


def rate_clause(clause_type, clause_text, jurisdiction):
    rag_query = clause_type + " clause " + jurisdiction + " enforceability"
    rag_results = query_corpus(rag_query, max_results=3)

    if rag_results:
        parts = []
        for r in rag_results:
            parts.append("[" + r["case_name"] + " | " + r["court_id"] + " | " + r["date_filed"] + "]\n" + r["text"])
        case_law_text = "\n\n".join(parts)
    else:
        case_law_text = "No directly relevant case law retrieved."

    prompt = RISK_PROMPT.format(
        clause_type=clause_type,
        jurisdiction=jurisdiction,
        clause_text=clause_text[:3000],
        case_law=case_law_text[:4000],
    )
    raw = _call_gemini(prompt)
    if not raw:
        return {"risk_level": "medium", "risk_summary": "Analysis failed.", "risk_basis": "Error.", "fallback_language": None}, rag_results

    result = _extract_json(raw)
    if result is None:
        return {"risk_level": "medium", "risk_summary": "Analysis failed.", "risk_basis": "Error.", "fallback_language": None}, rag_results
    return result, rag_results


def analyze_contract(contract_text, jurisdiction, contract_name="Contract"):
    log.info("Analyzing: %s [%s]", contract_name, jurisdiction)

    ctx = new_context()
    clean_text = tokenize(contract_text, ctx)

    raw_clauses = extract_clauses(clean_text)
    log.info("Extracted %d clauses", len(raw_clauses))

    analyzed = []
    risk_order = {"high": 3, "medium": 2, "low": 1, "info": 0}

    for raw in raw_clauses:
        clause_type_str = raw.get("clause_type", "miscellaneous")
        clause_text = raw.get("clause_text", "").strip()
        if not clause_text:
            continue

        try:
            clause_type = ClauseType(clause_type_str)
        except ValueError:
            clause_type = ClauseType.MISCELLANEOUS

        rating, rag_results = rate_clause(clause_type.value, clause_text, jurisdiction)
        risk_level_str = rating.get("risk_level", "medium")
        try:
            risk_level = RiskLevel(risk_level_str)
        except ValueError:
            risk_level = RiskLevel.MEDIUM

        citations = [
            LegalAuthority(
                case_name=r["case_name"],
                citation=r["citation"],
                court=r["court_id"],
                year=r["date_filed"][:4] if r.get("date_filed") else None,
                source_url=r["source_url"],
                relevance_note="Retrieved as relevant to " + clause_type.value + " in " + jurisdiction,
            )
            for r in rag_results
            if r.get("case_name") and r["case_name"] != "Unknown"
        ]

        analyzed.append(ClauseAnalysis(
            clause_type=clause_type,
            clause_text=detokenize(clause_text, ctx),
            risk_level=risk_level,
            risk_summary=rating.get("risk_summary", ""),
            risk_basis=rating.get("risk_basis", ""),
            fallback_language=rating.get("fallback_language"),
            citations=citations,
        ))

    if not analyzed:
        overall_risk = RiskLevel.INFO
    else:
        overall_risk = max(analyzed, key=lambda c: risk_order.get(c.risk_level.value, 0)).risk_level

    high = [c for c in analyzed if c.risk_level == RiskLevel.HIGH]
    med  = [c for c in analyzed if c.risk_level == RiskLevel.MEDIUM]
    summary = (
        str(len(analyzed)) + " clauses analyzed. "
        + str(len(high)) + " high-risk, "
        + str(len(med)) + " medium-risk. "
        + ("Attorney review required before executing." if analyzed else "No clauses extracted.")
    )

    return ContractRiskReport(
        contract_name=contract_name,
        jurisdiction=jurisdiction,
        overall_risk_level=overall_risk,
        overall_summary=summary,
        clauses=analyzed,
    )

import sys, os
sys.path.insert(0, '.')
import logging
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')

from agents.review_agent import analyze_contract, extract_clauses, tokenize, new_context

contract = """
NON-DISCLOSURE AGREEMENT

1. CONFIDENTIALITY
The Receiving Party agrees to keep all Confidential Information strictly
confidential and not disclose it to any third party without prior written
consent.

2. NON-COMPETE
Employee agrees not to engage in any competing business for five years
following termination, anywhere in the United States.

3. LIMITATION OF LIABILITY
Total liability shall not exceed five hundred dollars.

4. GOVERNING LAW
This Agreement is governed by the laws of Georgia.
"""

print("Step 1: tokenize")
ctx = new_context()
from dlp.tokenizer import tokenize as tok
clean = tok(contract, ctx)
print("Clean text length:", len(clean))
print()

print("Step 2: extract_clauses")
clauses = extract_clauses(clean)
print("Clauses extracted:", len(clauses))
for c in clauses:
    print(" -", c.get("clause_type"), ":", c.get("clause_text", "")[:50])
print()

print("Step 3: full analyze_contract")
report = analyze_contract(contract, "Georgia", "Test NDA")
print("Overall risk:", report.overall_risk_level)
print("Clauses analyzed:", len(report.clauses))
for clause in report.clauses:
    print(" -", clause.clause_type.value, "|", clause.risk_level.value, "|", clause.risk_summary[:60])
print()
print("Attorney review required:", report.attorney_review_required)

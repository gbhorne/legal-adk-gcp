import sys, os
sys.path.insert(0, '.')
import json
from agents.tools import analyze_contract

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

result_json = analyze_contract(contract, "Georgia")
report = json.loads(result_json)

print("=" * 60)
print("CONTRACT:", report["contract_name"])
print("JURISDICTION:", report["jurisdiction"])
print("OVERALL RISK:", report["overall_risk_level"].upper())
print("SUMMARY:", report["overall_summary"])
print()
for clause in report["clauses"]:
    print("-" * 40)
    print("CLAUSE TYPE:", clause["clause_type"])
    print("RISK LEVEL: ", clause["risk_level"].upper())
    print("RISK SUMMARY:", clause["risk_summary"])
    print("RISK BASIS:", clause["risk_basis"])
    if clause.get("fallback_language"):
        print("FALLBACK:", clause["fallback_language"][:100])
    print("CITATIONS:", len(clause["citations"]))
    for cite in clause["citations"]:
        print("  *", cite["case_name"], "|", cite["court"], "|", cite["year"])
print()
print("=" * 60)
print("ATTORNEY REVIEW REQUIRED:", report["attorney_review_required"])
print(report["attorney_review_note"])

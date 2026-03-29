import sys
sys.path.insert(0, '.')
from agents.review_agent import analyze_contract

contract = """
NON-DISCLOSURE AGREEMENT

1. CONFIDENTIALITY
The Receiving Party agrees to keep all Confidential Information strictly
confidential and not disclose it to any third party without prior written
consent. This obligation shall survive termination indefinitely.

2. NON-COMPETE
Employee agrees not to engage in any competing business for a period of
five (5) years following termination, anywhere in the United States.

3. LIMITATION OF LIABILITY
In no event shall either party be liable for any damages exceeding five
hundred dollars ().

4. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Georgia.
"""

report = analyze_contract(contract, "Georgia", "Test NDA")
print("Contract:", report.contract_name)
print("Overall risk:", report.overall_risk_level)
print("Summary:", report.overall_summary)
print()
for clause in report.clauses:
    print("Clause:", clause.clause_type.value)
    print("Risk:  ", clause.risk_level.value)
    print("Why:   ", clause.risk_summary[:100])
    print("Cites: ", len(clause.citations), "cases")
    print()
print("Attorney review required:", report.attorney_review_required)

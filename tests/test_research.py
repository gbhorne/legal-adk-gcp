import sys, os
sys.path.insert(0, '.')
import json
from agents.tools import legal_research

result_json = legal_research(
    "What is the maximum enforceable duration for a non-compete agreement in Georgia?",
    jurisdiction="Georgia"
)
memo = json.loads(result_json)

print("QUESTION:", memo["question"])
print("JURISDICTION:", memo["jurisdiction"])
print()
print("ANSWER:")
print(memo["answer"])
print()
print("ANALYSIS:")
print(memo["supporting_analysis"][:500])
print()
print("AUTHORITIES:", len(memo["authorities"]), "cases cited")
for auth in memo["authorities"]:
    print(" *", auth["case_name"], "|", auth["court"], "|", auth["year"])
print()
if memo["jurisdiction_warnings"]:
    print("WARNINGS:")
    for w in memo["jurisdiction_warnings"]:
        print(" !", w)
print()
print("RELATED QUESTIONS:")
for q in memo["related_questions"]:
    print(" ?", q)
print()
print("ATTORNEY REVIEW REQUIRED:", memo["attorney_review_required"])

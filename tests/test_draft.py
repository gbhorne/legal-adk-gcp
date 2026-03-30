import sys, os
sys.path.insert(0, '.')
import json
from agents.tools import draft_document

result_json = draft_document(
    contract_type="nda",
    jurisdiction="Georgia",
    parties_json='{"Disclosing Party": "Acme Corp", "Receiving Party": "Beta LLC"}'
)
doc = json.loads(result_json)

print("CONTRACT TYPE:", doc["contract_type"])
print("JURISDICTION:", doc["jurisdiction"])
print("PARTIES:", doc["parties"])
print()
print("DRAFT (first 800 chars):")
print(doc["markdown_text"][:800])
print()
print("DRAFTING NOTES:")
for i, note in enumerate(doc["drafting_notes"], 1):
    print(str(i) + ".", note)
print()
print("ATTORNEY REVIEW REQUIRED:", doc["attorney_authored_required"])
print(doc["attorney_authored_note"])

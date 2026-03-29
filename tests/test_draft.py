import sys, os
sys.path.insert(0, '.')
from agents.draft_agent import draft

doc = draft(
    contract_type="nda",
    jurisdiction="Georgia",
    parties={
        "Disclosing Party": "Acme Corp",
        "Receiving Party": "Beta LLC"
    },
    parameters={
        "purpose": "Evaluation of potential acquisition",
        "term": "2 years"
    }
)

print("CONTRACT TYPE:", doc.contract_type)
print("JURISDICTION:", doc.jurisdiction)
print("PARTIES:", doc.parties)
print()
print("DRAFT (first 800 chars):")
print(doc.markdown_text[:800])
print()
print("DRAFTING NOTES:")
for i, note in enumerate(doc.drafting_notes, 1):
    print(str(i) + ".", note)
print()
print("ATTORNEY AUTHORED REQUIRED:", doc.attorney_authored_required)
print(doc.attorney_authored_note)

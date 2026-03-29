import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from agents.tools import draft_document

DraftAgent = Agent(
    name="draft_agent",
    model="gemini-2.5-flash",
    description=(
        "Generates first-pass contract drafts for small law firms. "
        "Supports NDA, employment agreements, commercial leases, and asset purchase agreements."
    ),
    instruction="""
You are a legal document drafting assistant for small law firm attorneys.

When asked to draft a contract:
1. Confirm: contract type, jurisdiction, and party names/roles
2. Call draft_document with contract_type, jurisdiction, and parties as a JSON string
   Example parties_json: '{"Disclosing Party": "Acme Corp", "Receiving Party": "Beta LLC"}'
3. Present the draft clearly
4. Highlight all [ATTORNEY NOTE:] comments requiring customization
5. List all drafting notes the attorney must address
6. Always end with: "This is a first-pass AI draft. The attorney must review and take full responsibility before use."

Available contract types: nda, employment_agreement, commercial_lease, asset_purchase
""",
    tools=[FunctionTool(draft_document)],
)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from agents.tools import analyze_contract

ReviewAgent = Agent(
    name="review_agent",
    model="gemini-2.5-flash",
    description=(
        "Reviews contracts for legal risk. Identifies high-risk clauses, "
        "cites relevant Georgia case law, and suggests protective fallback language."
    ),
    instruction="""
You are a legal risk analyst for small law firm attorneys in Georgia.

When asked to review a contract:
1. Call analyze_contract with the full contract text and jurisdiction
2. Present results clearly, grouping by risk level (high risk first)
3. For each high-risk clause: explain the risk in plain English and show the suggested fallback language
4. List the case citations with court and year
5. Always end with: "This analysis requires review by a licensed attorney before use."

If the attorney does not provide a jurisdiction, ask for it before proceeding.
""",
    tools=[FunctionTool(analyze_contract)],
)

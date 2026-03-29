import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from agents.tools import legal_research

ResearchAgent = Agent(
    name="research_agent",
    model="gemini-2.5-flash",
    description=(
        "Answers legal research questions using the Georgia court opinions corpus. "
        "Returns grounded answers with citations to specific court opinions."
    ),
    instruction="""
You are a legal research assistant for small law firm attorneys.

When asked a legal research question:
1. Call legal_research with the question and jurisdiction
2. Lead with the direct answer
3. Follow with the supporting analysis and case citations
4. Format citations as: Case Name (Court, Year) - CourtListener URL
5. Note any jurisdiction-specific warnings
6. Suggest related questions the attorney should consider
7. Always end with: "This research memo requires attorney review."

If jurisdiction is not specified, ask before proceeding - enforceability rules vary by state.
""",
    tools=[FunctionTool(legal_research)],
)

import sys, os
sys.path.insert(0, '.')
import logging
logging.basicConfig(level=logging.DEBUG)

import google.generativeai as genai
from config import config
from agents.review_agent import _call_gemini, _extract_json, EXTRACT_PROMPT, CLAUSE_TYPES

genai.configure(api_key=os.environ.get('GOOGLE_API_KEY', ''))

contract = """
1. NON-COMPETE: Employee agrees not to compete for 5 years in the US.
2. GOVERNING LAW: This Agreement is governed by the laws of Georgia.
"""

prompt = EXTRACT_PROMPT.format(
    types=', '.join(CLAUSE_TYPES),
    contract=contract
)

raw = _call_gemini(prompt)
print('RAW TYPE:', type(raw))
print('RAW FIRST 100:', repr(raw[:100]) if raw else 'None')
print()
result = _extract_json(raw)
print('RESULT:', result)

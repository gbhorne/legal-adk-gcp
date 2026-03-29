import sys, os
sys.path.insert(0, '.')
import google.generativeai as genai
import re, json
from config import config

genai.configure(api_key=os.environ.get('GOOGLE_API_KEY', ''))
model = genai.GenerativeModel(config.GEMINI_MODEL)

prompt = '''You are a legal document analyst. Extract all significant clauses from this contract.

Return a JSON array. Each element must have:
- "clause_type": one of [non_compete, confidentiality, governing_law, miscellaneous]
- "clause_text": the exact clause text verbatim from the contract

Contract:
1. NON-COMPETE: Employee agrees not to compete for 5 years in the United States.
2. GOVERNING LAW: This Agreement is governed by the laws of Georgia.

Return ONLY a valid JSON array. No explanation, no markdown.'''

resp = model.generate_content(prompt)
print('Type of resp.text:', type(resp.text))
print('First 200 chars:', repr(resp.text[:200]))
print()
raw = resp.text.strip()
raw = re.sub(r'^`(?:json)?\s*', '', raw)
raw = re.sub(r'\s*`$', '', raw)
print('After strip first 200:', repr(raw[:200]))
try:
    parsed = json.loads(raw)
    print('Parsed OK:', len(parsed), 'clauses')
except Exception as e:
    print('Parse error:', e)

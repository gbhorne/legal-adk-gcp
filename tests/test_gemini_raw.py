import sys, os
sys.path.insert(0, '.')
import google.generativeai as genai
from config import config

genai.configure(api_key=os.environ.get('GOOGLE_API_KEY', ''))
model = genai.GenerativeModel(config.GEMINI_MODEL)

prompt = '''Extract clauses from this contract as a JSON array. Each element must have "clause_type" and "clause_text".

Contract:
1. NON-COMPETE: Employee agrees not to compete for 5 years in the United States.
2. GOVERNING LAW: This Agreement is governed by the laws of Georgia.

Return ONLY a valid JSON array.'''

resp = model.generate_content(prompt)
print('RAW RESPONSE:')
print(repr(resp.text))

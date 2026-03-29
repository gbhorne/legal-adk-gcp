import sys, os
sys.path.insert(0, '.')
import google.generativeai as genai
from config import config

genai.configure(api_key=os.environ.get('GOOGLE_API_KEY', ''))
model = genai.GenerativeModel(config.GEMINI_MODEL)

contract = """
NON-DISCLOSURE AGREEMENT

1. CONFIDENTIALITY
The Receiving Party agrees to keep all Confidential Information strictly
confidential and not disclose it to any third party without prior written
consent. This obligation shall survive termination indefinitely.

2. NON-COMPETE
Employee agrees not to engage in any competing business for a period of
five (5) years following termination, anywhere in the United States.

3. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Georgia.
"""

prompt = "Extract all significant clauses from this contract as a JSON array. Each element must have clause_type (one of: non_compete, confidentiality, governing_law, miscellaneous) and clause_text. Return ONLY valid JSON.\n\nContract:\n" + contract

resp = model.generate_content(prompt)
print('FULL RESPONSE:')
print(resp.text)
print()
print('LENGTH:', len(resp.text))

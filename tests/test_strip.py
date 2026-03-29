import re, json

raw = '`json\n[\n  {"clause_type": "NON-COMPETE", "clause_text": "test"}\n]\n`'
print('Before:', repr(raw[:30]))
raw = re.sub(r'^`(?:json)?\s*', '', raw)
raw = re.sub(r'\s*`$', '', raw)
print('After:', repr(raw[:30]))
parsed = json.loads(raw)
print('Parsed OK:', parsed)

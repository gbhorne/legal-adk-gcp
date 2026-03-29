import json, re

text = '''`json
[
  {
    "clause_type": "confidentiality",
    "clause_text": "The Receiving Party agrees to keep all info confidential."
  }
]
`'''

print('Input:', repr(text[:50]))

# Try _extract_json logic
for start_char in ['[', '{']:
    idx = text.find(start_char)
    if idx != -1:
        end_char = ']' if start_char == '[' else '}'
        candidate = text[idx:]
        last_idx = candidate.rfind(end_char)
        if last_idx != -1:
            candidate = candidate[:last_idx + 1]
            print('Candidate:', repr(candidate[:50]))
            try:
                parsed = json.loads(candidate)
                print('Parsed OK:', len(parsed), 'items')
                break
            except json.JSONDecodeError as e:
                print('Parse error:', e)

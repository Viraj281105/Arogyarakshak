import re

text = "Paracetamol 500mg 10 tablets"
QUANTITY_PATTERN = re.compile(
    r"(\d+)\s*(?:x\s*)?(?:tablets?|tabs?|capsules?|caps?|strips?|sheets?|vials?|ampoules?|injections?|infusions?|suspensions?|syrups?|creams?|ointments?)",
    re.IGNORECASE
)

match = QUANTITY_PATTERN.search(text)
if match:
    print(f"Match found: '{match.group(0)}'")
    print(f"Match span: {match.span()}")
    print(f"Before match: '{text[:match.start()]}'")
    print(f"After match: '{text[match.end():]}'")
    result = text[:match.start()] + text[match.end():]
    print(f"Result: '{result}'")
    print(f"Result stripped: '{result.strip()}'")

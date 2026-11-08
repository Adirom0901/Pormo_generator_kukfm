
# Simple checks on what the model returned. If something is wrong we return a list of problems in plain English;
# the pipeline sends them back to the model for a second try.
from config import MIN_PROMO_SECONDS, MAX_PROMO_SECONDS, MAX_HOOK_SECONDS
 
 
def ends_mid_sentence(lines, number):
    """True if line `number` ends with '...' and the next line starts with '...'
    (the script split one sentence over two lines, e.g. 'You are far too plain...' / '...far too silent...')."""
    this_text = lines[number - 1]["text"].rstrip('"”')
    next_text = lines[number]["text"].lstrip('"“')
    return this_text.endswith("...") and next_text.startswith("...")
 
 
def fix_promo(promo, lines):
    """Small automatic repairs: whole numbers, and never cut a sentence in half."""
    for key in ("hook_from", "hook_to", "cliffhanger_to"):
        try:
            promo[key] = int(promo.get(key))
        except (TypeError, ValueError):
            return promo   # validate_promo will report it
 
    total = len(lines)
    while 2 <= promo["hook_from"] <= total and ends_mid_sentence(lines, promo["hook_from"] - 1):
        promo["hook_from"] -= 1
    while 1 <= promo["hook_to"] < total and ends_mid_sentence(lines, promo["hook_to"]):
        promo["hook_to"] += 1
    while 1 <= promo["cliffhanger_to"] < total and ends_mid_sentence(lines, promo["cliffhanger_to"]):
        promo["cliffhanger_to"] += 1
    return promo
 
 
def seconds_between(lines, first_number, last_number):
    chosen = lines[first_number - 1:last_number]
    start = chosen[0]["start"]
    end = max(line["end"] for line in chosen)
    return end - start
 
 
def validate_promo(promo, lines):
    """Returns a list of problems. Empty list = the promo is fine."""
    for key in ("hook_from", "hook_to", "cliffhanger_to"):
        if not isinstance(promo.get(key), int):
            return [key + " must be a whole line number"]
 
    first = promo["hook_from"]
    hook_end = promo["hook_to"]
    last = promo["cliffhanger_to"]
    if not (1 <= first <= hook_end < last <= len(lines)):
        return [f"line numbers must satisfy 1 <= hook_from <= hook_to < cliffhanger_to <= {len(lines)}, "
                f"but you gave {first}, {hook_end}, {last}"]
 
    problems = []
    hook_seconds = seconds_between(lines, first, hook_end)
    total_seconds = seconds_between(lines, first, last)
    if hook_seconds > MAX_HOOK_SECONDS:
        problems.append(f"the hook is {hook_seconds:.1f}s but must be at most {MAX_HOOK_SECONDS}s: choose a smaller hook_to")
    if total_seconds < MIN_PROMO_SECONDS:
        problems.append(f"the promo is {total_seconds:.1f}s but must be at least {MIN_PROMO_SECONDS}s: choose a larger cliffhanger_to")
    if total_seconds > MAX_PROMO_SECONDS:
        problems.append(f"the promo is {total_seconds:.1f}s but must be at most {MAX_PROMO_SECONDS}s: choose a smaller cliffhanger_to")
    return problems
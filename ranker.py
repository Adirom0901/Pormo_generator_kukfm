
# Chooses the better of the two promos with a few simple rules (no extra model call).
# Each rule gives a score between 0 and 1, and we add them up with weights.
from script_parser import time_to_seconds
 
# words in the tone tags like "(Outraged, Accusing)" that mean the moment is intense
STRONG_WORDS = ["outraged", "furious", "desperate", "cruel", "mocking", "shattered", "devastated", "accusing",
                "venomous", "gloating", "betrayed", "shouting", "livid", "threatening", "piercing", "scornful",
                "harsh", "screaming", "heartbroken", "begging"]
 
# words that suggest the scene is calming down (bad for a cliffhanger)
RESOLVED_WORDS = ["fades", "peaceful", "serenity", "relieved", "happy", "content", "safe"]
 
 
def get_span(promo):
    """Start and end of the promo in seconds."""
    blocks = promo["hook"]["blocks"] + promo["cliffhanger"]["blocks"]
    start = time_to_seconds(blocks[0]["start"])
    end = max(time_to_seconds(b["end"]) for b in blocks)
    return start, end
 
 
def has_any(text, words):
    text = text.lower()
    for word in words:
        if word in text:
            return True
    return False
 
 
def score_promo(promo):
    hook_blocks = promo["hook"]["blocks"]
    all_blocks = hook_blocks + promo["cliffhanger"]["blocks"]
    first_text = hook_blocks[0]["dialogue"]
    last_text = all_blocks[-1]["dialogue"]
 
    # 1. Hook: intense tone, a question or shout, and it starts with a spoken line (not a silent action)
    hook = 0.0
    if has_any(first_text, STRONG_WORDS):
        hook += 0.5
    if "?" in first_text or "!" in first_text:
        hook += 0.25
    if not first_text.startswith("ACTION"):
        hook += 0.25
 
    # 2. Cliffhanger: the last line hangs (question, "...", shout) and is intense, and does not sound resolved
    cliff = 0.0
    ending = last_text.rstrip('"”').strip()
    if ending.endswith("?") or ending.endswith("...") or ending.endswith("-"):
        cliff += 0.5
    elif ending.endswith("!"):
        cliff += 0.25
    if has_any(last_text, STRONG_WORDS):
        cliff += 0.5
    if has_any(last_text, RESOLVED_WORDS):
        cliff -= 0.4
    cliff = max(0.0, min(1.0, cliff))
 
    # 3. Length: 30-45 seconds is the sweet spot
    start, end = get_span(promo)
    length = 1.0 if 30 <= (end - start) <= 45 else 0.5
 
    # 4. Conflict: how often the speaker changes (back and forth = drama)
    speakers = [b["dialogue"].split(":")[0] for b in all_blocks]
    changes = 0
    for i in range(1, len(speakers)):
        if speakers[i] != speakers[i - 1]:
            changes += 1
    conflict = min(1.0, changes / 4)
 
    total = 0.35 * hook + 0.35 * cliff + 0.15 * length + 0.15 * conflict
    return {"hook": hook, "cliffhanger": cliff, "length": length, "conflict": conflict, "total": round(total, 3)}
 
 
def pick_best(promos):
    """Returns (index of the best promo, list of scores for every promo)."""
    scores = [score_promo(p) for p in promos]
    best = 0
    for i in range(len(scores)):
        if scores[i]["total"] > scores[best]["total"]:
            best = i
    return best, scores
 
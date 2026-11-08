
# The nodes of the graph. A node is a function that gets the state (a dict)
# and returns a dict with only the keys it wants to change.
from config import MAX_TRIES
from prompts import PROMO_SYSTEM, SUMMARY_SYSTEM, make_promo_prompt, make_summary_prompt
from ranker import pick_best
from schema import PROMO_SCHEMA, SUMMARY_SCHEMA
from script_parser import parse_script, make_lines, line_text, seconds_to_time
from validator import fix_promo, validate_promo
 
 
def get_previous_summary(memory, episode_number):
    """memory looks like {"1": "summary...", "2": "summary..."}.
    Returns the summary of the latest episode BEFORE this one ('' if there is none)."""
    earlier = [int(key) for key in memory if int(key) < episode_number]
    if len(earlier) == 0:
        return ""
    return memory[str(max(earlier))]
 
 
def to_block(line):
    return {"start": seconds_to_time(line["start"]), "end": seconds_to_time(line["end"]), "dialogue": line_text(line)}
 
 
def build_promo(raw, lines):
    """Turns the model's line numbers into the final promo dict, using the real script text."""
    hook_lines = lines[raw["hook_from"] - 1:raw["hook_to"]]
    cliffhanger_lines = lines[raw["hook_to"]:raw["cliffhanger_to"]]
    return {
        "hook": {"blocks": [to_block(l) for l in hook_lines], "why": raw.get("hook_why", "")},
        "cliffhanger": {"blocks": [to_block(l) for l in cliffhanger_lines], "why": raw.get("cliffhanger_why", "")},
    }
 
 
class PromoNodes:
    def __init__(self, model):
        self.model = model   # any model with .ask(system, user, schema)
 
    # NODE 1: read the script, and take the earlier summary out of memory
    def parse(self, state):
        episode = parse_script(state["script_text"])
        lines = make_lines(episode["blocks"])
        previous = get_previous_summary(state.get("memory", {}), episode["number"])
        return {
            "episode": {"number": episode["number"], "logline": episode["logline"], "continuity": episode["continuity"]},
            "lines": lines,
            "previous_summary": previous,
            # start this run from a clean slate (memory is NOT touched here)
            "promos": [], "problems": [], "feedback": "", "tries": 0, "scores": [], "best_index": None,
        }
 
    # NODE 2: ask the model for 2 promos and check them
    def generate(self, state):
        lines = state["lines"]
        prompt = make_promo_prompt(state["episode"], lines, state["previous_summary"], state["feedback"])
 
        new_promos = []
        problems = []
        try:
            answer = self.model.ask(PROMO_SYSTEM, prompt, PROMO_SCHEMA)
            for raw in answer.get("promos", []):
                raw = fix_promo(raw, lines)
                errors = validate_promo(raw, lines)
                if len(errors) == 0:
                    new_promos.append(build_promo(raw, lines))
                else:
                    problems += errors
        except Exception as error:   # e.g. the model returned broken JSON: treat it as a problem and try again
            problems.append("the answer could not be read: " + str(error))
 
        # keep the best result of all tries
        best_promos = state["promos"]
        if len(new_promos) > len(best_promos):
            best_promos = new_promos
 
        return {
            "promos": best_promos,
            "problems": problems,
            "feedback": "\n".join("- " + p for p in problems),
            "tries": state["tries"] + 1,
        }
 
    # CONDITIONAL EDGE: go back to `generate` or move on?
    def check_result(self, state):
        if len(state["promos"]) == 2 or state["tries"] >= MAX_TRIES:
            return "done"
        return "retry"
 
    # NODE 3: pick the better promo
    def rank(self, state):
        if len(state["promos"]) == 0:
            return {"best_index": None, "scores": []}
        best_index, scores = pick_best(state["promos"])
        return {"best_index": best_index, "scores": scores}
 
    # NODE 4: write the summary through this episode
    def summarize(self, state):
        prompt = make_summary_prompt(state["episode"], state["lines"], state["previous_summary"])
        try:
            answer = self.model.ask(SUMMARY_SYSTEM, prompt, SUMMARY_SCHEMA)
            summary = "Story so far: " + answer["story_so_far"] + "\nUnresolved: " + answer["unresolved"]
        except Exception:
            # if the summary fails, keep the old summary plus this episode's logline
            summary = (state["previous_summary"] + "\n" + state["episode"]["logline"]).strip()
        return {"summary": summary}
 
    # NODE 5: save the summary in memory (the checkpointer keeps it for the next run)
    def save_memory(self, state):
        memory = dict(state.get("memory", {}))
        memory[str(state["episode"]["number"])] = state["summary"]
        return {"memory": memory}
 
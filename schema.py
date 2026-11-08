#the schema for structured output from model
#the model will only answer 

PROMO_SCHEMA = {
    "type": "object",
    "properties": {
        "promos": {
            "type":"array",
            "minItems":2,
            "maxItems":2,
            "items":{
                "type":"object",
                "properties":{
                    "hook_from":{"type":"integer"},
                    "hook_to":{"type":"integer"},
                    "hook_why":{"type":"string"},
                    "cliffhanger_to":{"type":"integer"},
                    "cliffhanger_why":{"type":"string"}
                },
                "required":["hook_from", "hook_to", "hook_why", "cliffhanger_to", "cliffhanger_why"],
            },
        }
    },
    "reqired":["promos"],
}

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "story_so_far": {"type": "string"},
        "unresolved": {"type": "string"},
    },
    "required": ["story_so_far", "unresolved"],
}



# ---------------------------------------------------------------------------
# The state of the graph. Every node reads from it and returns the keys it changes.
# Because the graph has a checkpointer, LangGraph saves this state after every run,
# so "memory" is still there the next time we run the graph on the same thread.
# ---------------------------------------------------------------------------
from typing import TypedDict


 
class PipelineState(TypedDict, total=False):
    script_text: str        # INPUT: the uploaded script
    memory: dict            # SAVED BETWEEN RUNS: {"1": summary after ep 1, "2": summary after ep 2, ...}
 
    episode: dict           # number, logline, continuity
    lines: list             # numbered dialogue/action lines of this episode
    previous_summary: str   # summary of the earlier episodes (taken from memory)
 
    promos: list            # valid promos found so far
    problems: list          # what was wrong with the last answer of the model
    feedback: str           # the problems written as text, sent back to the model on a retry
    tries: int              # how many times we asked the model
 
    scores: list            # score of every promo
    best_index: int         # which promo the ranker chose (None if there is none)
    summary: str            # summary through this episode
 


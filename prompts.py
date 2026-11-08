
# All the text we send to the model.
from script_parser import line_text
 
PROMO_SYSTEM = """You are a promo editor for short vertical drama series (like ReelShort or DramaBox).
You get ONE episode as numbered lines. Each line is a spoken line or an action, with its start-end time in seconds.
 
Pick TWO different promo clips from this episode. A promo is 20 to 60 seconds long and has two parts:
1. HOOK: the first few lines of the promo (at most 10 seconds). In its first 3 seconds it must stop a scrolling viewer: a shocking line, a reveal, a betrayal, a threat.
2. CLIFFHANGER: the lines right after the hook. They build the conflict and must STOP at an unresolved moment (a hanging question, a threat, a shock) so the viewer needs the next episode. Stop BEFORE the conflict is resolved.
 
Rules:
- Answer with line NUMBERS only. Never write timestamps or dialogue.
- hook_from = first line of the hook, hook_to = last line of the hook.
- cliffhanger_to = last line of the cliffhanger. The cliffhanger starts at the line after hook_to.
- hook_from <= hook_to < cliffhanger_to.
- The whole promo (start of hook_from to end of cliffhanger_to) must be between 20 and 60 seconds. Aim for 30 to 45.
- Someone who has never seen the show should understand who is wronged, who wronged them and what is at stake. Use the story so far to judge this.
- The two promos must use different hooks.
- hook_why and cliffhanger_why: one short sentence each, explaining why it works.
Return only JSON."""
 
 
def make_promo_prompt(episode, lines, previous_summary, feedback=""):
    if previous_summary == "":
        previous_summary = "(this is the first episode)"
 
    text = "STORY SO FAR (earlier episodes):\n" + previous_summary + "\n\n"
    text += "EPISODE " + str(episode["number"]) + "\n"
    text += "Logline: " + episode["logline"] + "\n"
    text += "Continuity: " + episode["continuity"] + "\n\n"
    text += "LINES ([number] start-end in seconds | line):\n"
    for line in lines:
        text += f"[{line['id']}] {line['start']:.1f}-{line['end']:.1f} | {line_text(line)}\n"
    text += '\nReturn JSON like {"promos": [{"hook_from": N, "hook_to": N, "hook_why": "...", '
    text += '"cliffhanger_to": N, "cliffhanger_why": "..."}, { ...second promo... }]}\n'
    if feedback != "":
        text += "\nYour previous answer had problems. Fix them:\n" + feedback + "\n"
    return text
 
 
SUMMARY_SYSTEM = """You keep a running summary of a drama series.
You get the summary of the earlier episodes and the newest episode. Write the updated summary.
- story_so_far: at most 120 words. Who wronged whom, what happened, what is at stake. Keep the important earlier events.
- unresolved: 1 to 3 short sentences about conflicts or questions still open at the end of the newest episode.
Use only facts from the script. Return only JSON."""
 
 
def make_summary_prompt(episode, lines, previous_summary):
    if previous_summary == "":
        previous_summary = "(none, this is the first episode)"
 
    text = "SUMMARY OF EARLIER EPISODES:\n" + previous_summary + "\n\n"
    text += "NEWEST EPISODE " + str(episode["number"]) + "\n"
    text += "Logline: " + episode["logline"] + "\n"
    text += "Script:\n"
    for line in lines:
        text += line_text(line) + "\n"
    text += '\nReturn JSON with "story_so_far" and "unresolved".'
    return text
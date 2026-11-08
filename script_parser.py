#reads script of one episode and devides into blocks.
#BLOCK is one LABEL entry of script: CAMERA,ACTION,SOUND FX or dialogue

import re

TIME_PATTERN = re.compile(r"Start:\s*\(([\d:.]+)\)\s*\|\s*End:\s*\(([\d:.]+)\)")

def time_to_seconds(text):
    minutes,seconds= text.split(":")
    return int(minutes)*60+float(seconds)

def seconds_to_time(seconds):
    """114.0 -> '01:54.00'"""
    total = int(round(seconds * 100))
    minutes = total // 6000
    secs = (total % 6000) // 100
    hundredths = total % 100
    return f"{minutes:02d}:{secs:02d}.{hundredths:02d}"


def find_value(name,text):
    """Finds a header line like 'EPISODE LOGLINE: ....' and returns what comes after colon."""
    match= re.search(name+r":\s*(.+)",text,re.IGNORECASE)
    if match is None:
        return ""
    return match.group(1).strip()

def block_kind(label):
    label = label.upper()
    if label == "CAMERA":
        return "CAMERA"
    if label.startswith("ACTION"):
        return "ACTION"
    if label.startswith("SOUND"):
        return "SOUND FX"
    return "DIALOGUE"


def parse_script(text):
    """Returns a dict: number, logline, continuity, blocks (sorted by start time)."""
    number_match = re.search(r"EPISODE NUMBER:\s*Episode\s*(\d+)", text, re.IGNORECASE)
    if number_match is None:
        raise ValueError("Could not find 'EPISODE NUMBER: Episode N' at the top of the script.")
 
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        label_match = re.match(r"^\*\*(.+):\*\*\s*$", lines[i].strip())
        if label_match is None or i + 1 >= len(lines):
            i += 1
            continue
 
        time_match = TIME_PATTERN.search(lines[i + 1])
        if time_match is None:
            i += 1
            continue
 
        # the text of the block is every line until the next label / scene / end marker
        text_lines = []
        j = i + 2
        while j < len(lines):
            line = lines[j].strip()
            if line.startswith("**") or line.startswith("---") or re.match(r"^SCENE\s+\d+", line, re.IGNORECASE):
                break
            if line != "":
                text_lines.append(line)
            j += 1
 
        label = label_match.group(1).strip()
        blocks.append({
            "label": label,
            "kind": block_kind(label),
            "start": time_to_seconds(time_match.group(1)),
            "end": time_to_seconds(time_match.group(2)),
            "text": " ".join(text_lines),
        })
        i = j
 
    if len(blocks) == 0:
        raise ValueError("No blocks found. Is this a script in the expected format?")
 
    blocks.sort(key=lambda b: (b["start"], b["end"]))
    return {
        "number": int(number_match.group(1)),
        "logline": find_value("EPISODE LOGLINE", text),
        "continuity": find_value("CONTINUITY NOTES", text),
        "blocks": blocks,
    }
 
 
def make_lines(blocks):
    """Keeps only dialogue and action blocks (camera and sound are not useful for picking promos)
    and numbers them 1, 2, 3... The model will pick promos using these numbers."""
    lines = []
    for block in blocks:
        if block["kind"] == "DIALOGUE" or block["kind"] == "ACTION":
            line = dict(block)
            line["id"] = len(lines) + 1
            lines.append(line)
    return lines
 
 
def line_text(line):
    """One line as shown to the reader: LABEL: text"""
    return line["label"] + ": " + line["text"]
 
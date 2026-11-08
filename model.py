
# The models. Each one has the same method:  model.ask(system, user, schema) -> dict
# So you can swap the model without changing anything else.
import json
import re
import urllib.request
 
from config import MODEL_REPO, MODEL_FILE, N_CTX
 
 
def text_to_json(text):
    """Takes the model's text and returns a dict. Handles ```json fences and extra words around the JSON."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON: " + text[:200])
    return json.loads(text[start:end + 1])
 
 
class LocalModel:
    """Open-source model running on your own computer with llama-cpp-python.
    The answer is forced to follow the JSON schema."""
 
    def __init__(self, model_path=None):
        from llama_cpp import Llama   # imported here so the app still opens if it is not installed
        if model_path:
            self.llm = Llama(model_path=model_path, n_ctx=N_CTX, verbose=False)
        else:
            self.llm = Llama.from_pretrained(repo_id=MODEL_REPO, filename=MODEL_FILE, n_ctx=N_CTX, verbose=False)
 
    def ask(self, system, user, schema):
        result = self.llm.create_chat_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object", "schema": schema},
            temperature=0.3,
            max_tokens=800,
        )
        return text_to_json(result["choices"][0]["message"]["content"])
 
 
class ApiModel:
    """Any OpenAI-compatible API (OpenAI, Groq, OpenRouter, a local server...). Use this to try a stronger model."""
 
    def __init__(self, base_url, model_name, api_key):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
 
    def ask(self, system, user, schema):
        system = system + "\nThe JSON must follow this schema: " + json.dumps(schema)
        body = {
            "model": self.model_name,
            "temperature": 0.3,
            "max_tokens": 800,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.loads(response.read())
        return text_to_json(data["choices"][0]["message"]["content"])
 
 
class MockModel:
    """NOT a real model. It picks lines by simple rules so you can test the app without downloading anything.
    Its promos are not meaningful."""
 
    def ask(self, system, user, schema):
        if "story_so_far" in schema["properties"]:
            logline = re.search(r"Logline: (.*)", user)
            return {"story_so_far": logline.group(1) if logline else "(mock summary)",
                    "unresolved": "(mock) the conflict from the last scene is still open."}
 
        # read "[12] 33.7-35.4 | ..." rows from the prompt
        rows = re.findall(r"^\[(\d+)\] ([\d.]+)-([\d.]+) \|", user, re.MULTILINE)
        lines = [(int(r[0]), float(r[1]), float(r[2])) for r in rows]
 
        promos = []
        for fraction in (0.15, 0.5):
            first = int(len(lines) * fraction)
            hook_last = first
            while hook_last < len(lines) - 1 and lines[hook_last][2] - lines[first][1] < 3:
                hook_last += 1
            end = hook_last + 1
            while end < len(lines) - 1 and lines[end][2] - lines[first][1] < 40:
                end += 1
            promos.append({
                "hook_from": lines[first][0], "hook_to": lines[hook_last][0], "hook_why": "(mock) opening lines",
                "cliffhanger_to": lines[end][0], "cliffhanger_why": "(mock) where the clip stops",
            })
        return {"promos": promos}
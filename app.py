
# Streamlit frontend.  Run with:  streamlit run app.py
import os
import uuid
 
import streamlit as st
 
from graph import build_graph, run_episode, get_memory, InMemorySaver
from model import LocalModel, ApiModel, MockModel
from ranker import get_span
from script_parser import seconds_to_time
 
st.set_page_config(page_title="Promo Finder", page_icon="🎬")
st.title("🎬 Microdrama Promo Finder")
st.write("Upload ONE episode script. The graph finds the best promo for it and saves a summary of the episode "
         "in its memory, so the next episode you upload can use it.")
 
# Each browser tab gets its own thread_id. The graph's memory is saved under this id.
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())
 
 
@st.cache_resource
def get_checkpointer():
    """The place where the graph saves its memory. Created once, so it survives Streamlit reruns."""
    return InMemorySaver()
 
 
@st.cache_resource
def load_graph(choice, model_path, api_url, api_model, api_key):
    """Builds the model and the graph once and reuses them (loading a local model is slow)."""
    if choice == "Local GGUF model":
        model = LocalModel(model_path if model_path else None)
    elif choice == "API (OpenAI-compatible)":
        model = ApiModel(api_url, api_model, api_key)
    else:
        model = MockModel()
    return build_graph(model, get_checkpointer())
 
 
# ---- sidebar: choose the model ----
st.sidebar.header("Model")
choice = st.sidebar.selectbox("Which model?", ["Mock (test only)", "Local GGUF model", "API (OpenAI-compatible)"])
model_path = ""
api_url = "https://api.openai.com/v1"
api_model = "gpt-4o-mini"
api_key = ""
if choice == "Local GGUF model":
    model_path = st.sidebar.text_input("Path to .gguf file (empty = download Qwen2.5-7B from Hugging Face)")
if choice == "API (OpenAI-compatible)":
    api_url = st.sidebar.text_input("Base URL", api_url)
    api_model = st.sidebar.text_input("Model name", api_model)
    api_key = st.sidebar.text_input("API key", type="password")
 
try:
    graph = load_graph(choice, model_path, api_url, api_model, api_key)
except Exception as error:
    st.error("Could not load the model: " + str(error))
    st.stop()
 
# ---- sidebar: memory (it lives in the graph, we only read it) ----
st.sidebar.header("Memory")
if st.sidebar.button("Clear memory"):
    st.session_state["thread_id"] = str(uuid.uuid4())   # a new thread = a graph with empty memory
    st.session_state["result"] = None
memory = get_memory(graph, st.session_state["thread_id"])
st.sidebar.write("Episodes remembered: " + str(sorted(int(key) for key in memory)))
 
 
st.sidebar.header("Output files")
output_folder = st.sidebar.text_input("Folder to save the output file in", "promo_outputs")
 
 
def show_part(title, part):
    st.subheader(title)
    st.caption("Why: " + part["why"])
    for block in part["blocks"]:
        st.markdown(f"`{block['start']} – {block['end']}`  {block['dialogue']}")
 
 
def format_block(block):
    """One block in the same format as the script:  **LABEL:** / Start: (..) | End: (..) / text"""
    label, text = block["dialogue"].split(": ", 1)
    return f"**{label}:**\nStart: ({block['start']}) | End: ({block['end']})\n{text}\n"
 
 
def format_part(title, part):
    text = f"--- {title} ---\nWhy: {part['why']}\n\n"
    for block in part["blocks"]:
        text += format_block(block) + "\n"
    return text
 
 
def make_output_text(result):
    """The hook and cliffhanger of the best promo, with the summary right below them."""
    text = ""
    if len(result["promos"]) == 0:
        text += f"EPISODE {result['episode']['number']}: no valid promo was found.\n\n"
    else:
        best = result["promos"][result["best_index"]]
        start, end = get_span(best)
        text += (f"EPISODE {result['episode']['number']} - BEST PROMO "
                 f"({seconds_to_time(start)} to {seconds_to_time(end)}, {end - start:.0f} seconds)\n\n")
        text += format_part("HOOK", best["hook"])
        text += format_part("CLIFFHANGER", best["cliffhanger"])
    text += "--- SUMMARY (through this episode) ---\n" + result["summary"] + "\n"
    return text
 
 
def save_output_file(result, input_file_name, folder):
    """Writes  <folder>/output_of_<input file name>  and returns its path."""
    folder = os.path.expanduser(folder)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "output_of_" + os.path.basename(input_file_name))
    with open(path, "w", encoding="utf-8") as file:
        file.write(make_output_text(result))
    return os.path.abspath(path)
 
 
# ---- main: upload + run the graph ----
uploaded = st.file_uploader("Episode script (.txt)", type=["txt"])
 
if st.button("Find promo"):
    if uploaded is None:
        st.warning("Please upload a script first.")
    else:
        try:
            script_text = uploaded.getvalue().decode("utf-8")
            with st.spinner("Running the graph..."):
                st.session_state["result"] = run_episode(graph, script_text, st.session_state["thread_id"])
            memory = get_memory(graph, st.session_state["thread_id"])   # refresh after the run
            st.sidebar.write("Episodes remembered (updated): " + str(sorted(int(key) for key in memory)))
        except Exception as error:
            st.session_state["result"] = None
            st.error("Something went wrong: " + str(error))
 
        st.session_state["saved_path"] = None
        if st.session_state.get("result") is not None:
            if output_folder.strip() == "":
                st.info("No output folder given, so no file was saved.")
            else:
                try:
                    st.session_state["saved_path"] = save_output_file(st.session_state["result"], uploaded.name, output_folder)
                except Exception as error:
                    st.error("The result could not be saved to a file: " + str(error))
 
# ---- show the result ----
result = st.session_state.get("result")
if result is not None:
    number = result["episode"]["number"]
    if st.session_state.get("saved_path"):
        st.caption("Saved to: " + st.session_state["saved_path"])
    if len(result["promos"]) == 0:
        st.error("The model did not give a valid promo. Problems found:")
        for problem in result["problems"]:
            st.write("- " + problem)
    else:
        best = result["promos"][result["best_index"]]
        start, end = get_span(best)
        st.header(f"Best promo for Episode {number}")
        st.write(f"**{start:.1f}s → {end:.1f}s  ({end - start:.0f} seconds)**")
        show_part("🪝 HOOK", best["hook"])
        show_part("😱 CLIFFHANGER", best["cliffhanger"])
 
        with st.expander("Both promos and their scores"):
            st.write("Scores (the ranker picked the one with the higher total):")
            st.write(result["scores"])
            st.write(result["promos"])
 
    with st.expander("Memory: summary saved for the next episode"):
        st.text(result["summary"])
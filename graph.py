
# Connects the nodes into a LangGraph graph.
#
#   START -> parse -> generate -+-(2 valid promos, or out of tries)-> rank -> summarize -> save_memory -> END
#                       ^       |
#                       +-retry-+
#
# MEMORY: the graph is compiled with a checkpointer. LangGraph saves the state after each run under a
# "thread_id". Running the graph again with the same thread_id starts with the saved state, so the
# `memory` dict (summaries of earlier episodes) is still there. A new thread_id = empty memory.
from langgraph.graph import StateGraph, START, END
 
try:
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError:   # older LangGraph versions call it MemorySaver
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver
 
from nodes import PromoNodes
from schema import PipelineState
 
 
def build_graph(model, checkpointer=None):
    if checkpointer is None:
        checkpointer = InMemorySaver()
    nodes = PromoNodes(model)
 
    builder = StateGraph(PipelineState)
    builder.add_node("parse", nodes.parse)
    builder.add_node("generate", nodes.generate)
    builder.add_node("rank", nodes.rank)
    builder.add_node("summarize", nodes.summarize)
    builder.add_node("save_memory", nodes.save_memory)
 
    builder.add_edge(START, "parse")
    builder.add_edge("parse", "generate")
    builder.add_conditional_edges("generate", nodes.check_result, {"retry": "generate", "done": "rank"})
    builder.add_edge("rank", "summarize")
    builder.add_edge("summarize", "save_memory")
    builder.add_edge("save_memory", END)
 
    return builder.compile(checkpointer=checkpointer)
 
 
def run_episode(graph, script_text, thread_id):
    """Runs the graph for ONE script. Returns the final state (promos, scores, best_index, summary, memory...)."""
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke({"script_text": script_text}, config)
 
 
def get_memory(graph, thread_id):
    """Reads the memory that is saved in the graph for this thread: {"1": summary, "2": summary...}"""
    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    return snapshot.values.get("memory", {})
 
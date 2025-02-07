"""Define a simple chatbot agent.

This agent processes deck information.
"""

from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from agent.configuration import Configuration
from agent.nodes import InitNode, ProcessImagesNode
from agent.state import State

# Create node instances
init_node = InitNode()
process_images_node = ProcessImagesNode()

# Define a new graph
workflow = StateGraph(State, config_schema=Configuration)

# Add nodes to the graph
workflow.add_node("init", init_node)
workflow.add_node("process_images", process_images_node)

# Set up the graph edges
workflow.add_edge("__start__", "init")  # Start with init
workflow.add_edge("init", "process_images")  # Process images after init
workflow.add_edge("process_images", END)  # End after processing images

# Compile the workflow into an executable graph
graph = workflow.compile()
graph.name = "Deck Processing Graph"

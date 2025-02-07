"""Define a simple chatbot agent.

This agent processes deck information.
"""

from typing import Any, Dict, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from agent.configuration import Configuration
from agent.nodes import (
    InitNode,
    ProcessImagesNode,
    ExtractTablesNode,
    GeneratePresentationNode,
    SetupSlideNode,
    SetupScriptNode,
    PageParserNode
)
from agent.nodes.validate import ValidatorNode
from agent.state import State
from agent.workflow import Workflow
from agent.nodes.validate.update_slide import UpdateSlideNode
from agent.nodes.validate.update_script import UpdateScriptNode

# Create node instances
init_node = InitNode()
process_images_node = ProcessImagesNode()
extract_tables_node = ExtractTablesNode()
generate_presentation_node = GeneratePresentationNode()
setup_slide_node = SetupSlideNode()
setup_script_node = SetupScriptNode()
validator_node = ValidatorNode()
page_parser_node = PageParserNode()
update_slide_node = UpdateSlideNode()
update_script_node = UpdateScriptNode()

# Define a new graph
workflow = Workflow()

# Add nodes to the graph
workflow.add_node("init", init_node)
workflow.add_node("process_images", process_images_node)
workflow.add_node("extract_tables", extract_tables_node)
workflow.add_node("generate_presentation", generate_presentation_node)
workflow.add_node("setup_slide", setup_slide_node)
workflow.add_node("setup_script", setup_script_node)
workflow.add_node("validator", validator_node)
workflow.add_node("page_parser", page_parser_node)
workflow.add_node("update_slide", update_slide_node)
workflow.add_node("update_script", update_script_node)

# Set page_parser as the entry point for testing
# TODO: Change back to "init" for production
workflow.set_entry_point("validator")

# Set up the graph edges
# Normal flow edges
workflow.add_edge("init", "process_images")  # Process images after init
workflow.add_edge("process_images", "extract_tables")  # Extract tables after processing images
workflow.add_edge("extract_tables", "generate_presentation")  # Generate presentation after extracting tables
workflow.add_edge("generate_presentation", "setup_slide")  # Setup slides after generating presentation
workflow.add_edge("setup_slide", "setup_script")  # Setup script after setting up slides
workflow.add_edge("setup_script", "page_parser")  # Parse content into pages
workflow.add_edge("page_parser", "validator")  # Validate parsed pages
workflow.add_edge("validator", "update_slide")
workflow.add_edge("validator", "update_script")
workflow.add_edge("update_slide", "page_parser")
workflow.add_edge("update_script", "page_parser")
workflow.add_edge("validator", END)  # End after validation

# Compile the workflow into an executable graph
graph = workflow.compile()
graph.name = "Deck Processing Graph"

class AgentState(TypedDict):
    """Type definition for agent state."""
    image_paths: list[str]
    table_data: list[dict]
    presentation_data: dict
    slide_content: str
    script_content: str
    pages: list[dict]
    validation_results: dict
    validation_history: list[dict]
    update_history: list[dict]

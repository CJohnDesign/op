"""Define a simple chatbot agent.

This agent processes deck information.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal, Union, Type

from langgraph.graph import END, START, StateGraph
from langsmith import traceable

from agent.nodes.validate import (
    ValidatorNode,
    UpdateSlideNode,
    UpdateScriptNode
)
from agent.nodes import (
    InitNode,
    ProcessImagesNode,
    ExtractTablesNode,
    GeneratePresentationNode,
    SetupSlideNode,
    SetupScriptNode,
    PageParserNode
)
from agent.workflow import Workflow
from agent.types import AgentState

# Set up logging
logger = logging.getLogger(__name__)

# Define valid node types for type checking
NodeType = Literal[
    "init",
    "process_images",
    "extract_tables",
    "generate_presentation",
    "setup_slide",
    "setup_script",
    "page_parser",
    "validator",
    "update_slide",
    "update_script"
]

def route_on_validation(state: AgentState) -> Union[NodeType, Type[END]]:
    """Route to appropriate node based on validation results.
    
    Args:
        state: Current agent state containing validation results
        
    Returns:
        Next node to route to or END if validation complete
    """
    validation_results = state.get("validation_results", {})
    logger.info(f"Routing based on validation results: {validation_results}")
    
    # Get validation status for each component
    slide_valid = validation_results.get("slide", {}).get("is_valid", False)
    script_valid = validation_results.get("script", {}).get("is_valid", False)
    
    logger.info(f"Validation status - Slide: {slide_valid}, Script: {script_valid}")
    
    if slide_valid and script_valid:
        # If validation passes, save validated state and end
        deck_id = state.get("deck_id")
        if deck_id:
            state_file = Path(f"src/decks/{deck_id}/validated_state.json")
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
            logger.info(f"Saved validated state to {state_file}")
        return END
    
    # Route to appropriate update node based on what needs updating
    if not slide_valid:
        logger.info("Routing to slide update")
        return "update_slide"
    elif not script_valid:
        logger.info("Routing to script update")
        return "update_script"
    else:
        logger.info("No updates needed")
        return END

def initialize_graph() -> StateGraph:
    """Initialize and configure the graph.
    
    Returns:
        Configured and compiled graph
    """
    # Create node instances
    init_node = InitNode()
    process_images_node = ProcessImagesNode()
    extract_tables_node = ExtractTablesNode()
    generate_presentation_node = GeneratePresentationNode()
    setup_slide_node = SetupSlideNode()
    setup_script_node = SetupScriptNode()
    page_parser_node = PageParserNode()
    validator_node = ValidatorNode()
    update_slide_node = UpdateSlideNode()
    update_script_node = UpdateScriptNode()

    # Initialize workflow
    workflow = Workflow()

    # Add nodes to the graph
    workflow.add_node("init", init_node)
    workflow.add_node("process_images", process_images_node)
    workflow.add_node("extract_tables", extract_tables_node)
    workflow.add_node("generate_presentation", generate_presentation_node)
    workflow.add_node("setup_slide", setup_slide_node)
    workflow.add_node("setup_script", setup_script_node)
    workflow.add_node("page_parser", page_parser_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("update_slide", update_slide_node)
    workflow.add_node("update_script", update_script_node)

    # Add a dynamic entry router
    def entry_router(state: AgentState) -> str:
        """Route to the specified start node from state."""
        return state.get("_start_node", "init")
        
    # Set entry point using the router
    workflow.add_conditional_edges(START, entry_router)

    # Add edges for complete workflow
    workflow.add_edge("init", "process_images")  # Start with image processing
    workflow.add_edge("process_images", "extract_tables")  # Extract tables from processed images
    workflow.add_edge("extract_tables", "generate_presentation")  # Generate presentation from extracted data
    workflow.add_edge("generate_presentation", "setup_slide")  # Set up slides from presentation
    workflow.add_edge("setup_slide", "setup_script")  # Set up script from slides
    workflow.add_edge("setup_script", "page_parser")  # Parse content into pages
    workflow.add_edge("page_parser", "validator")  # Initial parsing to validation

    # Add conditional edges for validation loop
    workflow.add_conditional_edges(
        "validator",
        route_on_validation
    )

    # Add edges from update nodes back to validator
    workflow.add_edge("update_slide", "validator")
    workflow.add_edge("update_script", "validator")

    # Compile the workflow into an executable graph
    graph = workflow.compile()
    graph.name = "Complete Deck Processing Graph"
    
    return graph

# Create the graph instance
graph = initialize_graph()

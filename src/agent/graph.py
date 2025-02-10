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
    # Get current page index and total pages
    current_page_index = state.get("current_page_index", 0)
    pages = state.get("pages", {}).get("content", [])
    total_pages = len(pages) if pages else 0
    
    logger.info(f"Processing page {current_page_index + 1} of {total_pages}")
    
    # Check if we've reached the end of pages
    if current_page_index >= total_pages:
        logger.info("Reached end of pages, finishing validation")
        return END
        
    # Get validation attempts for current page
    validation_attempts = state.get("validation_attempts", {})
    current_page_key = str(current_page_index)
    current_attempts = validation_attempts.get(current_page_key, 0)
    
    # Get current validation state
    current_validation = state.get("current_validation", {})
    validation_results = current_validation.get("validation", {})
    
    # Get update history for current attempt
    update_history = state.get("update_history", {})
    current_page_updates = update_history.get(current_page_key, {})
    current_attempt_updates = current_page_updates.get(str(current_attempts), set())
    
    # Log validation state
    logger.info(f"Current page {current_page_index + 1} attempt {current_attempts}")
    logger.info(f"Validation state: {validation_results.get('is_valid', False)}")
    logger.info(f"Updates performed this attempt: {current_attempt_updates}")
    
    # Check if we've exceeded max attempts for this page
    MAX_ATTEMPTS = 3
    if current_attempts >= MAX_ATTEMPTS:
        logger.warning(f"Exceeded max validation attempts ({MAX_ATTEMPTS}) for page {current_page_index + 1}")
        # Move to next page
        next_page_index = current_page_index + 1
        if next_page_index >= total_pages:
            logger.info("No more pages to validate")
            return END
            
        # Update state for next page
        state["current_page_index"] = next_page_index
        # Clear validation state for next page
        state.pop("current_validation", None)
        state.pop("validation_results", None)
        # Reset attempts for next page
        validation_attempts[str(next_page_index)] = 0
        state["validation_attempts"] = validation_attempts
        # Clear update history for next page
        if str(next_page_index) in update_history:
            del update_history[str(next_page_index)]
        state["update_history"] = update_history
        logger.info(f"Moving to next page {next_page_index + 1}")
        return "validator"
    
    # Check if validation passed
    if validation_results.get("is_valid", False):
        # Move to next page
        next_page_index = current_page_index + 1
        logger.info(f"Validation passed for page {current_page_index + 1}")
        if next_page_index >= total_pages:
            logger.info("All pages validated successfully")
            return END
            
        # Update state for next page
        logger.info(f"Moving to page {next_page_index + 1}")
        state["current_page_index"] = next_page_index
        # Clear validation state for next page
        state.pop("current_validation", None)
        state.pop("validation_results", None)
        # Reset attempts for next page
        validation_attempts[str(next_page_index)] = 0
        state["validation_attempts"] = validation_attempts
        # Clear update history for next page
        if str(next_page_index) in update_history:
            del update_history[str(next_page_index)]
        state["update_history"] = update_history
        return "validator"
    
    # Get validation details for failed validation
    slide_valid = validation_results.get("slide", {}).get("is_valid", False)
    script_valid = validation_results.get("script", {}).get("is_valid", False)
    
    logger.info(f"Validation status - Slide: {slide_valid}, Script: {script_valid}")
    logger.info(f"Attempt {current_attempts} of {MAX_ATTEMPTS}")
    
    # Initialize update history for current page and attempt if needed
    if current_page_key not in update_history:
        update_history[current_page_key] = {}
    if str(current_attempts) not in update_history[current_page_key]:
        update_history[current_page_key][str(current_attempts)] = set()
    
    # Route based on which validation failed and hasn't been updated yet
    if not slide_valid and "slide" not in current_attempt_updates:
        logger.info("Routing to slide update")
        update_history[current_page_key][str(current_attempts)].add("slide")
        state["update_history"] = update_history
        return "update_slide"
    elif not script_valid and "script" not in current_attempt_updates:
        logger.info("Routing to script update")
        update_history[current_page_key][str(current_attempts)].add("script")
        state["update_history"] = update_history
        return "update_script"
    else:
        # If we've updated both components but validation still fails
        # Move to next attempt
        logger.warning("All updates performed for this attempt, moving to next attempt")
        # Clear validation state to force new validation
        state.pop("current_validation", None)
        state.pop("validation_results", None)
        return "validator"

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
        start_node = state.get("_start_node", "init")
        logger.info(f"Starting workflow at node: {start_node}")
        return start_node
        
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
    workflow.add_edge("update_slide", "validator")  # Return to validation after slide update
    workflow.add_edge("update_script", "validator")  # Return to validation after script update

    # Log the graph structure
    logger.info("Graph structure initialized:")
    logger.info("- Nodes: %s", workflow.nodes.keys())
    logger.info("- Edges:")
    for edge in workflow._edges:
        logger.info(f"  {edge['source']} -> {edge['target']}")

    # Compile the workflow into an executable graph
    graph = workflow.compile()
    graph.name = "Complete Deck Processing Graph"
    
    return graph

# Create the graph instance
graph = initialize_graph()

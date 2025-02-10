"""Define a simple chatbot agent.

This agent processes deck information.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal, Union, Type

from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from langchain_openai import ChatOpenAI
from openai import OpenAI
from langsmith.wrappers import wrap_openai

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

# Create traced OpenAI client
openai_client = wrap_openai(OpenAI())

# Create traced LLM instance
llm = ChatOpenAI(
    model="gpt-4o",
    max_tokens=4096,
    temperature=0,
    client=openai_client
)

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
    
    if validation_results.get("is_valid", False):
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
    if validation_results.get("needs_slide_update"):
        logger.info("Routing to slide update")
        return "update_slide"
    elif validation_results.get("needs_script_update"):
        logger.info("Routing to script update")
        return "update_script"
    else:
        # If no specific updates needed but still invalid, end to avoid infinite loop
        logger.warning("No specific updates needed but validation failed. Ending to avoid loop.")
        return END

@traceable(name="deck_processing_workflow")
def create_workflow() -> StateGraph:
    """Create and configure the workflow graph.
    
    Returns:
        Configured workflow graph
    """
    # Create node instances with traced LLM
    init_node = InitNode()
    process_images_node = ProcessImagesNode()
    process_images_node.model = llm
    extract_tables_node = ExtractTablesNode()
    extract_tables_node.model = llm
    generate_presentation_node = GeneratePresentationNode()
    generate_presentation_node.model = llm
    setup_slide_node = SetupSlideNode()
    setup_slide_node.model = llm
    setup_script_node = SetupScriptNode()
    setup_script_node.model = llm
    page_parser_node = PageParserNode()
    validator_node = ValidatorNode()
    validator_node.model = llm
    update_slide_node = UpdateSlideNode()
    update_slide_node.model = llm
    update_script_node = UpdateScriptNode()
    update_script_node.model = llm

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

    # Set entry point - start with initialization
    workflow.set_entry_point("init")

    # Add edges for complete workflow
    workflow.add_edge("init", "process_images")
    workflow.add_edge("process_images", "extract_tables")
    workflow.add_edge("extract_tables", "generate_presentation")
    workflow.add_edge("generate_presentation", "setup_slide")
    workflow.add_edge("setup_slide", "setup_script")
    workflow.add_edge("setup_script", "page_parser")
    workflow.add_edge("page_parser", "validator")
    workflow.add_conditional_edges("validator", route_on_validation)
    workflow.add_edge("update_slide", "validator")
    workflow.add_edge("update_script", "validator")

    # Compile the workflow into an executable graph
    graph = workflow.compile()
    graph.name = "Complete Deck Processing Graph"
    
    return graph

# Create the graph instance with tracing
graph = create_workflow()

@traceable(name="agent_execution")
def execute_graph(state: AgentState, config: RunnableConfig | None = None) -> AgentState:
    """Execute the graph with tracing.
    
    Args:
        state: Initial state for the graph
        config: Optional runtime configuration
        
    Returns:
        Final state after graph execution
    """
    return graph.invoke(state, config)

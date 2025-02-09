"""Workflow implementation for the agent.

This module contains the custom workflow class that extends StateGraph.
Following Single Responsibility Principle, this module only handles workflow configuration.
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Callable, Dict, Optional, Type, Union, List, TypedDict, Annotated
import operator
from functools import partial

from langgraph.graph import END, START, StateGraph
from langsmith import traceable

from agent.configuration import Configuration
from agent.types import AgentState

def merge_dicts(old_dict: Dict, new_dict: Dict) -> Dict:
    """Merge two dictionaries, with new_dict taking precedence."""
    result = old_dict.copy()
    result.update(new_dict)
    return result

# Define state with proper reducers
class WorkflowState(TypedDict):
    # Use operator.add as reducer to append values
    validation_history: Annotated[List[Dict], operator.add]
    # Use merge_dicts for dictionary updates
    validation_results: Annotated[Dict, merge_dicts]
    validation_metadata: Annotated[Dict, merge_dicts]
    current_validation: Annotated[Dict, merge_dicts]
    # Use direct assignment for primitive values
    current_page_index: int
    is_valid: bool
    # Base state items that need to be preserved
    deck_id: str
    deck_title: str
    processed_images: Dict
    extracted_tables: Dict
    presentation: Dict
    slides: Dict
    script: Dict
    pages: Dict

@traceable(with_child_runs=True, name="Process Deck")
class Workflow(StateGraph):
    """Custom workflow class for the agent.
    
    Extends StateGraph to provide additional functionality and type safety.
    """
    
    # Special nodes that are internal to LangGraph
    INTERNAL_NODES = {START, END, "__start__", "__end__"}
    
    def __init__(self) -> None:
        """Initialize the workflow with our state and config types."""
        super().__init__(WorkflowState, config_schema=Configuration)
        self.name = "Deck Processing Graph"
        self.logger = logging.getLogger(self.__class__.__name__)
        self._nodes: Dict[str, Any] = {}
        self._edges: List[Dict[str, Any]] = []
        
    def _is_internal_node(self, node: Union[str, Type[END], Type[START]]) -> bool:
        """Check if a node is internal to LangGraph.
        
        Args:
            node: Node to check
            
        Returns:
            True if node is internal, False otherwise
        """
        if isinstance(node, type):
            return node in {END, START}
        return node in self.INTERNAL_NODES
    
    def add_edge(self, source: str, target: Union[str, Type[END]], **kwargs: Any) -> None:
        """Add an edge to the graph with logging.
        
        Args:
            source: Source node name
            target: Target node name or END
            **kwargs: Additional edge parameters
        """
        # Skip validation for internal nodes
        if not self._is_internal_node(source) and source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found in graph")
        if not self._is_internal_node(target) and target != END and target not in self._nodes:
            raise ValueError(f"Target node '{target}' not found in graph")
            
        self.logger.info(f"Adding edge: {source} -> {target}")
        self._edges.append({
            "source": source,
            "target": target,
            **kwargs
        })
        super().add_edge(source, target, **kwargs)
    
    def add_node(self, name: str, node: Any) -> None:
        """Add a node to the graph with logging.
        
        Args:
            name: Name of the node
            node: The node instance to add
        """
        if self._is_internal_node(name):
            raise ValueError(f"Cannot add internal node '{name}'")
            
        self.logger.info(f"Adding node: {name}")
        self._nodes[name] = node
        
        # Wrap the node's process method to preserve state
        original_process = node.process
        
        def wrapped_process(state: AgentState, config: Any) -> AgentState:
            # Log state before processing
            self.logger.debug(f"[{name}] Pre-process state keys: {list(state.keys())}")
            
            # Process with original method
            result = original_process(state, config)
            
            # Log state after processing
            self.logger.debug(f"[{name}] Post-process state keys: {list(result.keys())}")
            
            # Return result directly - let LangGraph handle state updates
            return result
            
        node.process = wrapped_process
        super().add_node(name, node)
    
    def set_entry_point(self, node: str) -> None:
        """Set the entry point for the graph.
        
        Args:
            node: Name of the entry point node
        """
        if not self._is_internal_node(node) and node not in self._nodes:
            raise ValueError(f"Entry point node '{node}' not found in graph")
            
        self.logger.info(f"Setting entry point to: {node}")
        super().set_entry_point(node)
    
    def add_conditional_edges(
        self,
        source: str,
        condition_fn: Callable[[AgentState], Union[str, Type[END]]],
        **kwargs: Any
    ) -> None:
        """Add conditional edges to the graph with error handling.
        
        Args:
            source: Source node name
            condition_fn: Function that takes state and returns next node
            **kwargs: Additional edge parameters
            
        Raises:
            ValueError: If source node not found or condition_fn is invalid
        """
        if not self._is_internal_node(source) and source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found in graph")
            
        if not callable(condition_fn):
            raise ValueError("condition_fn must be a callable")
            
        self.logger.info(f"Adding conditional edges from: {source}")
        
        try:
            # Wrap condition function to add logging
            def wrapped_condition(state: AgentState) -> Union[str, Type[END]]:
                try:
                    next_node = condition_fn(state)
                    self.logger.info(f"Conditional routing from {source} -> {next_node}")
                    
                    # Validate next node exists if not END or internal
                    if (not self._is_internal_node(next_node) and 
                        next_node != END and 
                        next_node not in self._nodes):
                        self.logger.error(f"Invalid next node '{next_node}' returned by condition")
                        raise ValueError(f"Node '{next_node}' not found in graph")
                    
                    return next_node
                    
                except Exception as e:
                    self.logger.error(f"Error in conditional routing from {source}: {str(e)}")
                    raise
                    
            # Add conditional edges with wrapped function
            super().add_conditional_edges(source, wrapped_condition)
            
        except Exception as e:
            self.logger.error(f"Failed to add conditional edges from {source}: {str(e)}")
            raise
            
    def compile(self) -> StateGraph:
        """Compile the workflow into an executable graph.
        
        Returns:
            Compiled StateGraph ready for execution
        """
        self.logger.info("Compiling workflow graph")
        return super().compile()
        
    def invoke(self, state: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the graph with tracing.
        
        This override ensures all node executions are nested under a single trace.
        
        Args:
            state: Initial state
            config: Optional configuration
            
        Returns:
            Final state after execution
        """
        if config is None:
            config = {}
            
        # Add metadata about the execution
        config["metadata"] = {
            "deck_id": state.get("deck_id", "unknown"),
            "deck_title": state.get("deck_title", "unknown"),
            "graph_name": self.name
        }
        
        return super().invoke(state, config) 
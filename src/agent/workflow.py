"""Workflow implementation for the agent.

This module contains the custom workflow class that extends StateGraph.
Following Single Responsibility Principle, this module only handles workflow configuration.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Type, Union, List, Set

from langgraph.graph import END, START, StateGraph

from agent.configuration import Configuration
from agent.types import AgentState


class Workflow(StateGraph):
    """Custom workflow class for the agent.
    
    Extends StateGraph to provide additional functionality and type safety.
    """
    
    # Special nodes that are internal to LangGraph
    INTERNAL_NODES = {START, END, "__start__", "__end__"}
    
    def __init__(self) -> None:
        """Initialize the workflow with our state and config types."""
        super().__init__(AgentState, config_schema=Configuration)
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
            super().add_conditional_edges(
                source,
                wrapped_condition,
                **kwargs
            )
            
        except Exception as e:
            self.logger.error(f"Failed to add conditional edges from {source}: {str(e)}")
            raise 
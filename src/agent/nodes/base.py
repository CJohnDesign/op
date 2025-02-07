"""Base node interface for the agent graph.

This module defines the base interface that all nodes must implement.
Following Interface Segregation Principle, we keep the interface minimal.
"""

from __future__ import annotations

import abc
import logging
from typing import Any, Dict, TypeVar, Generic

from langchain_core.runnables import RunnableConfig
from typing_extensions import TypedDict

from agent.tracer import trace_node

# Set up logging
logger = logging.getLogger(__name__)

# Generic type for state
StateType = TypeVar("StateType", bound=TypedDict)

class BaseNode(Generic[StateType], abc.ABC):
    """Base class for all nodes in the graph.
    
    Following Single Responsibility Principle, each node should do one thing well.
    Following Open/Closed Principle, this base class is open for extension but closed for modification.
    """
    
    def __init__(self) -> None:
        """Initialize the node."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abc.abstractmethod
    @trace_node(run_type="chain")
    def process(self, state: StateType, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state and return the next state.
        
        Args:
            state: The current state
            config: The configuration for this run
            
        Returns:
            The next state
        """
        raise NotImplementedError()
    
    def __call__(self, state: StateType, config: RunnableConfig) -> Dict[str, Any]:
        """Make the node callable.
        
        This allows nodes to be used directly in the graph.
        """
        return self.process(state, config) 
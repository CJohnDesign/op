"""Base node implementation.

This module contains the base node class that all other nodes inherit from.
Following Single Responsibility Principle, this module only handles base node functionality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Generic, TypeVar

from langchain_core.runnables import RunnableConfig

T = TypeVar("T", bound=Dict[str, Any])

class BaseNode(Generic[T]):
    """Base node class that all other nodes inherit from.
    
    Following Single Responsibility Principle, this class only handles
    common node functionality.
    """
    
    def __init__(self) -> None:
        """Initialize the node with a logger."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def __call__(self, state: T, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state.
        
        Args:
            state: Current state to process
            config: Runtime configuration
            
        Returns:
            Updated state after processing
        """
        return self.process(state, config)
    
    def process(self, state: T, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state. Must be implemented by child classes.
        
        Args:
            state: Current state to process
            config: Runtime configuration
            
        Returns:
            Updated state after processing
            
        Raises:
            NotImplementedError: If child class doesn't implement this method
        """
        raise NotImplementedError("Child classes must implement process method") 
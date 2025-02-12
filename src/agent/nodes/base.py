"""Base node implementation.

This module contains the base node class that all other nodes inherit from.
Following Single Responsibility Principle, this module only handles base node functionality.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
from pathlib import Path
from typing import Any, Dict, Generic, TypeVar

from langchain_core.runnables import RunnableConfig

T = TypeVar("T", bound=Dict[str, Any])

class BaseNode(Generic[T]):
    """Base class for all nodes in the graph."""
    
    def __init__(self) -> None:
        """Initialize the base node."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _deep_merge(self, d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.
        
        Args:
            d1: First dictionary
            d2: Second dictionary
            
        Returns:
            Merged dictionary
        """
        result = dict(d1)
        for key, value in d2.items():
            # Special handling for processed_images and extracted_tables
            if key in ["processed_images", "extracted_tables"] and isinstance(result.get(key), dict) and isinstance(value, dict):
                result[key] = value  # Use new values instead of updating to prevent duplicates
            # For all other dictionary values, perform a deep merge
            elif isinstance(result.get(key), dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            # For new keys or non-dict values, use the new value
            else:
                result[key] = value
        return result

    def _load_state(self, deck_id: str) -> Dict[str, Any]:
        """Load state from file if it exists.
        
        Args:
            deck_id: ID of the current deck
            
        Returns:
            Loaded state or empty dict if file doesn't exist
        """
        state_file = Path("src/decks") / deck_id / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading state: {str(e)}")
        return {}
    
    def _save_state(self, state: Dict[str, Any]) -> None:
        """Save state to file.
        
        Args:
            state: Current state to save
        """
        try:
            deck_id = state.get("deck_id")
            if deck_id:
                state_file = Path("src/decks") / deck_id / "state.json"
                state_file.parent.mkdir(parents=True, exist_ok=True)
                with open(state_file, "w") as f:
                    json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
    
    def __call__(self, state: T, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state.
        
        Args:
            state: Current state to process
            config: Runtime configuration
            
        Returns:
            Updated state after processing
        """
        # Load existing state from file to ensure we have the complete state
        deck_id = state.get("deck_id")
        if deck_id:
            existing_state = self._load_state(deck_id)
            # Merge incoming state with existing state
            complete_state = self._deep_merge(existing_state, state)
        else:
            complete_state = state

        # Process state
        updated_state = self.process(complete_state, config)
        
        # Deep merge process result with complete state
        final_state = self._deep_merge(complete_state, updated_state)
        
        # Save updated state
        self._save_state(final_state)
        
        return final_state
    
    def process(self, state: T, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state.
        
        Args:
            state: Current state to process
            config: Runtime configuration
            
        Returns:
            Updated state after processing
            
        Raises:
            NotImplementedError: If not implemented by child class
        """
        raise NotImplementedError("Child class must implement process method")


class ParallelProcessingNode(BaseNode[T]):
    """Base class for nodes that need parallel processing capabilities."""
    
    # Default values that can be overridden by child classes
    BATCH_SIZE = 4  # Default batch size
    MAX_WORKERS = 4  # Default maximum number of parallel workers
    
    def __init__(self) -> None:
        """Initialize the parallel processing node with a thread pool executor."""
        super().__init__()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS)
    
    def __del__(self) -> None:
        """Clean up resources by shutting down the executor."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True) 
"""Base node implementation.

This module contains the base node class that all other nodes inherit from.
Following Single Responsibility Principle, this module only handles base node functionality.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Generic, TypeVar, Optional

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage
from agent.types import AgentState

T = TypeVar("T", bound=Dict[str, Any])

class BaseNode(Generic[T]):
    """Base class for all workflow nodes.
    
    This class provides common functionality for all nodes in the workflow.
    Following Single Responsibility Principle, each node should handle one specific task.
    """
    
    def __init__(self) -> None:
        """Initialize the node with a logger."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state: Optional[T] = None
    
    def __call__(self, state: T, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state.
        
        Args:
            state: Current state to process
            config: Runtime configuration
            
        Returns:
            Updated state after processing
        """
        return self.process(state, config)
    
    def process(self, state: T, config: RunnableConfig) -> T:
        """Process the current state.
        
        Args:
            state: Current state to process
            config: Runtime configuration
            
        Returns:
            Updated state
            
        Raises:
            NotImplementedError: If not implemented by child class
        """
        # Store state for use by other methods
        self.state = state
        
        raise NotImplementedError("Child class must implement process method")

class ValidatorNode(BaseNode[AgentState]):
    """Node for validating slide and script content.
    
    Following Single Responsibility Principle, this node only handles
    validation of content.
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
        self.system_message = SystemMessage(content="""You are a content validator that ONLY responds with valid JSON.
Your responses must follow this exact schema:
{
    "is_valid": boolean,
    "slide": {
        "is_valid": boolean,
        "severity": "low" | "medium" | "high",
        "suggested_fixes": string (only if is_valid is false)
    },
    "script": {
        "is_valid": boolean,
        "severity": "low" | "medium" | "high",
        "suggested_fixes": string (only if is_valid is false)
    }
}

IMPORTANT:
1. Return ONLY the JSON object - no markdown code blocks, no explanations
2. The JSON must be valid and parseable
3. Do not include any text before or after the JSON
4. Do not wrap the JSON in backticks or code blocks
5. The response should start with { and end with }
6. Slides and scripts are separate - do not expect script sections in slide content
7. Focus on formatting, completeness, and clarity of each component

Example of CORRECT response:
{
    "is_valid": false,
    "slide": {
        "is_valid": false,
        "severity": "high",
        "suggested_fixes": "Add bullet points for key features"
    },
    "script": {
        "is_valid": true,
        "severity": "low",
        "suggested_fixes": ""
    }
}""") 
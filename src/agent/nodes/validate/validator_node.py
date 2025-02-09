"""Validator node implementation.

This module contains a node that sends content to GPT-4 for validation.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.validator import VALIDATION_PROMPT
from agent.types import AgentState

class ValidatorNode(BaseNode[AgentState]):
    """Node for sending content to GPT-4 for validation."""
    
    def __init__(self) -> None:
        """Initialize the validator with GPT-4 model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
        self.logger.setLevel(logging.INFO)

    def _format_page(self, page: Dict[str, Any]) -> str:
        """Format page content for GPT validation."""
        slide = page["slide"]
        script = page["script"]
        
        return f"""SLIDE CONTENT:
{slide['content']}

SCRIPT CONTENT:
{script['content']}"""

    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Send content to GPT for validation and return simple validation result."""
        self.logger.info("Starting validation")
        
        pages = state["pages"]["content"]
        all_valid = True  # Track if all pages are valid
        
        for i, page in enumerate(pages, 1):
            self.logger.info(f"Validating page {i}")
            try:
                # Format content
                formatted = self._format_page(page)
                
                # Create prompt with proper escaping of curly braces
                prompt = VALIDATION_PROMPT.replace("{content}", formatted)
                
                # Get GPT response
                response = self.model.invoke([HumanMessage(content=prompt)])
                
                # Parse response
                validation = json.loads(response.content)
                
                # Check if both slide and script are valid
                page_valid = validation["slide"]["is_valid"] and validation["script"]["is_valid"]
                if not page_valid:
                    all_valid = False
                    break  # No need to check more pages if we found an invalid one
                
            except Exception as e:
                self.logger.error(f"Failed to validate page {i}: {str(e)}")
                raise
        
        # Return simple validation result
        return {"is_valid": all_valid} 
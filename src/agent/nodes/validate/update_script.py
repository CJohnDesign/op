"""Update script node implementation.

This module contains a node that updates script content based on validation results.
Following Single Responsibility Principle, this node only handles script updates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langsmith import traceable

from agent.nodes.base import BaseNode
from agent.prompts.update_script import UPDATE_SCRIPT_PROMPT
from agent.types import AgentState


class UpdateScriptNode(BaseNode[AgentState]):
    """Node for updating script content based on validation results.
    
    Following Single Responsibility Principle, this node only handles
    the updating of script content to match validation requirements.
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
    
    def _update_content(self, current_content: str, instructions: str) -> str:
        """Update script content based on validation instructions.
        
        Args:
            current_content: Current script content to update
            instructions: Instructions for updating the content
            
        Returns:
            Updated script content
        """
        try:
            # Create message with update prompt
            message = HumanMessage(
                content=UPDATE_SCRIPT_PROMPT.format(
                    current_content=current_content,
                    instructions=instructions
                )
            )
            
            # Get updated content from GPT-4o
            self.logger.info("Updating script content")
            response = self.model.invoke([message])
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error updating script content: {str(e)}")
            return current_content
    
    @traceable(name="update_script")
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state to update script.
        
        Args:
            state: The current state containing validation results
            config: Runtime configuration
            
        Returns:
            Updated state with modified script content
        """
        self.logger.info("Starting script content update")
        
        try:
            # Get validation results and current content
            validation_results = state.get("validation_results", {})
            current_script = state.get("script", {}).get("content", "")
            
            if not validation_results or not current_script:
                self.logger.warning("Missing validation results or script content")
                return state
            
            # Check if script needs updating
            if not validation_results.get("needs_script_update"):
                self.logger.info("No script updates needed")
                return state
            
            # Get update instructions
            instructions = validation_results.get("script_update_instructions")
            if not instructions:
                self.logger.warning("No update instructions provided")
                return state
            
            # Update script content
            updated_script = self._update_content(current_script, instructions)
            
            # Create updated state
            updated_state = dict(state)
            updated_state["script"]["content"] = updated_script
            updated_state["update_history"] = state.get("update_history", []) + [{
                "type": "script",
                "instructions": instructions
            }]
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error in script update process: {str(e)}")
            raise 
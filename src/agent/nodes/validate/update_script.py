"""Update script node implementation.

This module contains a node that updates script content based on validation results.
Following Single Responsibility Principle, this node only handles script updates.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.update_script_prompt import UPDATE_SCRIPT_PROMPT
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
        self.system_message = SystemMessage(content="""You are a script content updater that ONLY responds with valid JSON.
Your responses must follow this exact schema:
{
    "updated_content": string,
    "changes_made": string[]
}
Do not include any additional text, explanations, or formatting.""")
    
    def _update_content(self, current_content: str, instructions: str) -> str:
        """Update script content based on validation instructions.
        
        Args:
            current_content: Current script content to update
            instructions: Instructions for updating the content
            
        Returns:
            Updated script content
        """
        try:
            # Filter instructions to only include script-related updates
            script_instructions = instructions
            if "slide" in instructions.lower():
                script_instructions = "Update script sections only, ignoring slide-related changes."
            
            # Create message with update prompt
            message = HumanMessage(
                content=UPDATE_SCRIPT_PROMPT.format(
                    current_content=current_content,
                    instructions=script_instructions
                )
            )
            
            # Get updated content from GPT-4o with system message
            self.logger.info("Updating script content")
            response = self.model.invoke([self.system_message, message])
            
            # Parse JSON response
            try:
                self.logger.debug(f"Raw response: {response.content}")
                result = json.loads(response.content)
                
                if not isinstance(result, dict):
                    self.logger.error(f"Response is not a dictionary: {result}")
                    raise ValueError("Invalid response format - not a dictionary")
                    
                if "updated_content" not in result:
                    self.logger.error(f"Response missing updated_content: {result}")
                    raise ValueError("Response missing updated_content field")
                    
                # Verify script sections are properly formatted
                updated_content = result["updated_content"]
                if "----" not in updated_content:
                    self.logger.error("Missing script section headers")
                    raise ValueError("Script sections must use ---- Section Title ---- format")
                
                # Verify the content actually changed
                if updated_content.strip() == current_content.strip():
                    self.logger.error("Content unchanged after update")
                    raise ValueError("Content unchanged after update")
                
                # Log the changes that were made
                if "changes_made" in result:
                    self.logger.info("Changes made:")
                    for change in result["changes_made"]:
                        self.logger.info(f"- {change}")
                
                return updated_content
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {str(e)}")
                self.logger.error(f"Raw response: {response.content}")
                raise ValueError(f"Invalid JSON response: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error updating script content: {str(e)}")
            raise ValueError(f"Failed to update content: {str(e)}")
    
    def process(self, state: AgentState, config: RunnableConfig) -> AgentState:
        """Process the current state and update script content.
        
        Args:
            state: Current state with validation results
            config: Runtime configuration
            
        Returns:
            Updated state
            
        Raises:
            ValueError: If validation state is missing or update fails
        """
        self.logger.info("=" * 80)
        self.logger.info("UPDATE SCRIPT NODE START")
        self.logger.info("=" * 80)
        
        # Log initial state
        self.logger.info("Initial State:")
        self.logger.info(f"- State Keys: {list(state.keys())}")
        self.logger.info(f"- Current Page Index: {state.get('current_page_index')}")
        self.logger.info(f"- Has Current Validation: {bool(state.get('current_validation'))}")
        
        # Get validation details
        current_validation = state.get("current_validation")
        if not current_validation:
            error_msg = "No current validation in state - workflow cannot continue"
            self.logger.error(error_msg)
            self.logger.error(f"Available state keys: {list(state.keys())}")
            raise ValueError(error_msg)
            
        # Log validation details
        self.logger.info("\nValidation Details:")
        self.logger.info(f"- Page Index: {current_validation.get('page_index')}")
        self.logger.info("- Script Validation:")
        validation = current_validation.get("validation", {})
        script_validation = validation.get("script", {})
        self.logger.info(f"  - Is Valid: {script_validation.get('is_valid')}")
        self.logger.info(f"  - Severity: {script_validation.get('severity')}")
        self.logger.info(f"  - Suggested Fixes: {script_validation.get('suggested_fixes')}")
        
        # Get pages
        pages = state.get("pages", {}).get("content", [])
        if not pages:
            error_msg = "No pages found in state - workflow cannot continue"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        page_index = current_validation.get("page_index")
        if page_index is None or page_index >= len(pages):
            error_msg = f"Invalid page index {page_index} (total pages: {len(pages)}) - workflow cannot continue"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Get current page
        current_page = pages[page_index]
        
        # Log current content
        self.logger.info("\nCurrent Content:")
        self.logger.info("-" * 40)
        self.logger.info(current_page["script"].get("content", "No content"))
        self.logger.info("-" * 40)
        
        try:
            # Get update instructions
            instructions = script_validation.get("suggested_fixes", "")
            if not instructions:
                error_msg = "No update instructions provided - workflow cannot continue"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            self.logger.info("\nUpdate Instructions:")
            self.logger.info(instructions)
            
            # Update the content
            current_content = current_page["script"]["content"]
            updated_content = self._update_content(current_content, instructions)
            
            # Verify update was successful
            if updated_content == current_content:
                error_msg = "Update failed - content unchanged"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Log content comparison
            self.logger.info("\nContent Comparison:")
            self.logger.info("- Original Content:")
            self.logger.info("-" * 40)
            self.logger.info(current_content)
            self.logger.info("-" * 40)
            self.logger.info("- Updated Content:")
            self.logger.info("-" * 40)
            self.logger.info(updated_content)
            self.logger.info("-" * 40)
            
            # Update the page in state
            pages[page_index]["script"]["content"] = updated_content
            state["pages"]["content"] = pages
            
            # Clear validation results to force revalidation
            state.pop("validation_results", None)
            state.pop("current_validation", None)
            
            self.logger.info("\nState Update Summary:")
            self.logger.info(f"- Updated page {page_index + 1}")
            self.logger.info("- Cleared validation results")
            self.logger.info(f"- Final state keys: {list(state.keys())}")
            
        except Exception as e:
            error_msg = f"Critical error in update process: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error("Stack trace:", exc_info=True)
            raise ValueError(error_msg)
            
        self.logger.info("=" * 80)
        self.logger.info("UPDATE SCRIPT NODE END")
        self.logger.info("=" * 80)
            
        return state 
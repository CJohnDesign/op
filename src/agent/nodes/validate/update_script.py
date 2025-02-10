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
    "header": string,  // The section header (e.g., "---- Introduction ----")
    "content": string, // The script content without the header
    "changes_made": string[]
}

IMPORTANT:
1. Return ONLY the JSON object - no markdown code blocks, no explanations
2. The JSON must be valid and parseable
3. Do not include any text before or after the JSON
4. Do not wrap the JSON in backticks or code blocks
5. The response should start with { and end with }
6. The header should be in the format "---- Section Title ----"
7. The content should contain detailed speaking points

Example response:
{
    "header": "---- Introduction ----",
    "content": "- Welcome everyone warmly\\n- Today we'll discuss...",
    "changes_made": ["Updated welcome message", "Added speaking points"]
}""")
    
    def _update_content(self, current_content: str, instructions: str, slide_content: str) -> str:
        """Update script content based on validation instructions.
        
        Args:
            current_content: Current script content to update
            instructions: Instructions for updating the content
            slide_content: Content of the corresponding slide
            
        Returns:
            Updated script content with header and content
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
                    instructions=script_instructions,
                    slide_content=slide_content
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
                    
                if "header" not in result or "content" not in result:
                    self.logger.error(f"Response missing required fields: {result}")
                    raise ValueError("Response missing required fields")
                    
                # Get updated content
                updated_content = result["content"]
                header = result["header"]
                
                # Verify the content actually changed
                if updated_content.strip() == current_content.strip():
                    self.logger.error("Content unchanged after update")
                    raise ValueError("Content unchanged after update")
                
                # Log the changes that were made
                if "changes_made" in result:
                    self.logger.info("Changes made:")
                    for change in result["changes_made"]:
                        self.logger.info(f"- {change}")
                
                # Return both header and content
                return {"header": header, "content": updated_content}
                
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
        
        try:
            # Get validation details
            current_validation = state.get("current_validation")
            if not current_validation:
                error_msg = "No current validation in state - workflow cannot continue"
                self.logger.error(error_msg)
                self.logger.error(f"Available state keys: {list(state.keys())}")
                raise ValueError(error_msg)
                
            # Get current page index
            page_index = current_validation.get("page_index")
            if page_index is None:
                error_msg = "No page index in current validation"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            # Get pages
            pages = state.get("pages", {}).get("content", [])
            if not pages:
                error_msg = "No pages found in state - workflow cannot continue"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if page_index >= len(pages):
                error_msg = f"Invalid page index {page_index} (total pages: {len(pages)})"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            # Get current page
            current_page = pages[page_index]
            
            # Get validation details
            validation = current_validation.get("validation", {})
            script_validation = validation.get("script", {})
            
            # Log validation details
            self.logger.info(f"\nValidating Page {page_index + 1}:")
            self.logger.info(f"- Is Valid: {script_validation.get('is_valid')}")
            self.logger.info(f"- Severity: {script_validation.get('severity')}")
            self.logger.info(f"- Suggested Fixes: {script_validation.get('suggested_fixes')}")
            
            # Log current content
            self.logger.info("\nCurrent Content:")
            self.logger.info("-" * 40)
            self.logger.info(current_page["script"].get("content", "No content"))
            self.logger.info("-" * 40)
            
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
            slide_content = current_page["slide"]["content"]
            result = self._update_content(current_content, instructions, slide_content)
            
            # Log content comparison
            self.logger.info("\nContent Comparison:")
            self.logger.info("- Original Content:")
            self.logger.info("-" * 40)
            self.logger.info(f"Header: {current_page['script'].get('header', 'No header')}")
            self.logger.info(f"Content: {current_content}")
            self.logger.info("-" * 40)
            self.logger.info("- Updated Content:")
            self.logger.info("-" * 40)
            self.logger.info(f"Header: {result['header']}")
            self.logger.info(f"Content: {result['content']}")
            self.logger.info("-" * 40)
            
            # Update the page in state
            pages[page_index]["script"]["header"] = result["header"]
            pages[page_index]["script"]["content"] = result["content"]
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
            
        finally:
            self.logger.info("=" * 80)
            self.logger.info("UPDATE SCRIPT NODE END")
            self.logger.info("=" * 80)
            
        return state 
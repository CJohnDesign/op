"""Validator node implementation.

This module contains a reactive validator node that checks slide and script consistency.
Following Single Responsibility Principle, this node only handles validation and orchestration.
"""

from __future__ import annotations

import json
import logging
from typing import cast, Dict, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from agent.nodes.base import BaseNode
from agent.prompts.validator import VALIDATION_PROMPT
from agent.types import (
    AgentState,
    Page,
    ValidationResult,
    ValidationState,
    PageValidationState,
    SlideContent,
    ScriptContent
)
from agent.llm_config import llm


class ValidatorNode(BaseNode[AgentState]):
    """Node for validating and orchestrating updates to slides and scripts.
    
    Following ReAct pattern:
    1. Observe current state
    2. Think about what needs to be done
    3. Act by choosing appropriate tool
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        # Use shared LLM instance
        self.model = llm
        self.logger.setLevel(logging.INFO)
    
    def _validate_page(self, page: Page) -> ValidationResult:
        """Observe step: Validate current page content."""
        try:
            # Format content as JSON string with both headers and content
            content_str = json.dumps({
                "slide": page["slide"],
                "script": page["script"]
            }, indent=2)
            
            # Create validation message with explicit JSON response format
            message = HumanMessage(content=VALIDATION_PROMPT.format(content=content_str))
            
            # Get validation results
            self.logger.info("Validating page content")
            response = self.model.invoke(
                input={"messages": [message]},
                config={"response_format": { "type": "json_object" }}
            )
            
            try:
                result = json.loads(response.content)
                
                # Extract validation results
                validation_result = {
                    "is_valid": result.get("is_valid", False),
                    "update_instructions": None,
                    "validation_messages": []
                }
                
                if not result["is_valid"]:
                    # Collect all validation messages
                    messages = []
                    for issue_type in ["script_issues", "slide_issues"]:
                        if issue_type in result.get("validation_issues", {}):
                            for issue in result["validation_issues"][issue_type]:
                                messages.append(f"{issue_type}: {issue['issue']}")
                    
                    validation_result["validation_messages"] = messages
                    
                    # Store update instructions if available
                    if "suggested_fixes" in result:
                        validation_result["update_instructions"] = json.dumps(result["suggested_fixes"])
                
                self.logger.info(f"Validation complete - Valid: {validation_result['is_valid']}")
                if validation_result["validation_messages"]:
                    self.logger.info(f"Validation messages: {validation_result['validation_messages']}")
                
                return validation_result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing validation response: {str(e)}")
                self.logger.error(f"Raw response: {response.content}")
                return {
                    "is_valid": False,
                    "update_instructions": None,
                    "validation_messages": ["Error parsing validation response"]
                }
            
        except Exception as e:
            self.logger.error(f"Error validating page: {str(e)}")
            return {
                "is_valid": False,
                "update_instructions": None,
                "validation_messages": [f"Error during validation: {str(e)}"]
            }
    
    def _initialize_validation_state(self, state: AgentState) -> None:
        """Initialize validation state if not present."""
        if "validation_state" not in state:
            state["validation_state"] = {
                "current_page": 1,
                "total_pages": state["pages"]["count"],
                "pages": {},
                "update_type": "none"
            }
    
    def _validate_current_page(self, state: AgentState) -> PageValidationState:
        """Think step: Analyze validation results and determine next action."""
        current_page = state["validation_state"]["current_page"]
        page = state["pages"]["content"][current_page - 1]  # Convert to 0-based index
        
        # Observe: Validate page
        validation_result = self._validate_page(page)
        
        # Think: Determine what needs updating
        return {
            "page_number": current_page,
            "slide_valid": validation_result["is_valid"],
            "script_valid": validation_result["is_valid"],
            "slide_update_instructions": validation_result["update_instructions"],
            "script_update_instructions": validation_result["update_instructions"],
            "updated_slide": None,
            "updated_script": None
        }
    
    @traceable(name="validate_content")
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Act step: Choose next action based on validation results.
        
        Args:
            state: Current agent state
            config: Runtime configuration
            
        Returns:
            Updated agent state with validation results and next action
        """
        self._initialize_validation_state(state)
        validation_state = cast(ValidationState, state["validation_state"])
        
        # Observe and Think: Validate current page
        current_page_state = self._validate_current_page(state)
        validation_state["pages"][current_page_state["page_number"]] = current_page_state
        
        # Act: Determine next action
        if current_page_state["slide_valid"] and current_page_state["script_valid"]:
            validation_state["update_type"] = "none"
            # If both valid, prepare to move to next page
            if validation_state["current_page"] < validation_state["total_pages"]:
                validation_state["current_page"] += 1
            # Otherwise, we're done with all pages
        elif not current_page_state["slide_valid"] and not current_page_state["script_valid"]:
            validation_state["update_type"] = "both"
        elif not current_page_state["slide_valid"]:
            validation_state["update_type"] = "slide_only"
        else:
            validation_state["update_type"] = "script_only"
        
        self.logger.info(f"Page {validation_state['current_page']} validation complete")
        self.logger.info(f"Next action: {validation_state['update_type']}")
        
        return state 
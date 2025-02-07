"""Validator node implementation.

This module contains a reactive validator node that checks slide and script consistency.
Following Single Responsibility Principle, this node only handles validation and orchestration.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.validator import VALIDATION_PROMPT
from agent.types import AgentState, Page


class ValidationResult(TypedDict):
    """Type definition for validation results."""
    page_number: int
    is_valid: bool
    needs_slide_update: bool
    needs_script_update: bool
    slide_update_instructions: str | None
    script_update_instructions: str | None


class ValidatorNode(BaseNode[AgentState]):
    """Node for validating and orchestrating updates to slides and scripts.
    
    Following Single Responsibility Principle, this node only handles:
    1. Validating content consistency for each page
    2. Determining what needs updates
    3. Providing update instructions
    """
    
    def __init__(self) -> None:
        """Initialize the validator with GPT-4 model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
        self.logger.setLevel(logging.INFO)
    
    def _validate_page(self, page_number: int, page: Page) -> ValidationResult:
        """Validate a single page's slide and script content for consistency.
        
        Args:
            page_number: The index of the page being validated
            page: The page containing slide and script content
            
        Returns:
            ValidationResult for this page
        """
        try:
            self.logger.info(f"\n=== Validating Page {page_number} ===")
            self.logger.info(f"Slide header: {page['slide'].get('header', 'No header')}")
            self.logger.info(f"Script header: {page['script'].get('header', 'No header')}")
            
            # Format content as JSON string with both headers and content
            content_str = json.dumps({
                "slides": {
                    "header": page["slide"].get("header", ""),
                    "content": page["slide"]["content"],
                    "frontmatter": page["slide"].get("frontmatter", "")
                },
                "script": {
                    "header": page["script"].get("header", ""),
                    "content": page["script"]["content"]
                }
            }, indent=2)
            
            # Log the content being sent
            self.logger.info("Content being sent to GPT:")
            self.logger.info(content_str)
            
            # Create validation message with properly formatted content
            message = HumanMessage(
                content=VALIDATION_PROMPT.format(content=content_str)
            )
            
            # Get validation results
            self.logger.info(f"Sending page {page_number} content to GPT-4o for validation")
            response = self.model.invoke([message])
            self.logger.info(f"Received validation response for page {page_number}")
            
            # Log the raw response
            self.logger.info("Raw GPT response:")
            self.logger.info(response.content)
            
            # Parse response
            try:
                self.logger.info("Parsing validation response")
                result = json.loads(response.content)
                
                # Extract validation results
                is_valid = result.get("is_valid", False)
                validation_issues = result.get("validation_issues", {})
                suggested_fixes = result.get("suggested_fixes", {})
                
                # Log validation details
                self.logger.info(f"Page {page_number} valid: {is_valid}")
                if not is_valid:
                    self.logger.info(f"Found validation issues in page {page_number}:")
                    if validation_issues.get("slide_issues"):
                        self.logger.info("Slide issues:")
                        for issue in validation_issues["slide_issues"]:
                            self.logger.info(f"  - Section: {issue['section']}")
                            self.logger.info(f"    Issue: {issue['issue']}")
                            self.logger.info(f"    Severity: {issue['severity']}")
                    
                    if validation_issues.get("script_issues"):
                        self.logger.info("Script issues:")
                        for issue in validation_issues["script_issues"]:
                            self.logger.info(f"  - Section: {issue['section']}")
                            self.logger.info(f"    Issue: {issue['issue']}")
                            self.logger.info(f"    Severity: {issue['severity']}")
                
                validation_result = {
                    "page_number": page_number,
                    "is_valid": is_valid,
                    "needs_slide_update": not is_valid and bool(validation_issues.get("slide_issues")),
                    "needs_script_update": not is_valid and bool(validation_issues.get("script_issues")),
                    "slide_update_instructions": suggested_fixes.get("slides") if not is_valid else None,
                    "script_update_instructions": suggested_fixes.get("script") if not is_valid else None
                }
                
                self.logger.info(f"Page {page_number} validation result:")
                self.logger.info(f"  Is valid: {validation_result['is_valid']}")
                self.logger.info(f"  Needs slide update: {validation_result['needs_slide_update']}")
                self.logger.info(f"  Needs script update: {validation_result['needs_script_update']}")
                
                return validation_result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing validation response for page {page_number}: {str(e)}")
                self.logger.error(f"Raw response: {response.content}")
                return {
                    "page_number": page_number,
                    "is_valid": False,
                    "needs_slide_update": False,
                    "needs_script_update": False,
                    "slide_update_instructions": None,
                    "script_update_instructions": None
                }
                
        except Exception as e:
            self.logger.error(f"Error validating page {page_number}: {str(e)}")
            raise
    
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state to validate content.
        
        Args:
            state: The current state containing pages to validate
            config: Runtime configuration
            
        Returns:
            Updated state with validation results
        """
        self.logger.info("\n=== Starting Validation Process ===")
        
        try:
            # Get pages from state
            pages = state.get("pages", {}).get("content", [])
            current_page = state.get("current_page", 0)
            
            self.logger.info("Current State Info:")
            self.logger.info(f"  Total pages: {len(pages)}")
            self.logger.info(f"  Current page: {current_page}")
            
            if not pages:
                self.logger.warning("No pages found in state")
                return state
            
            if current_page >= len(pages):
                self.logger.info("All pages validated successfully")
                return state
            
            # Validate current page
            page = pages[current_page]
            validation_result = self._validate_page(current_page, page)
            
            # Update state with validation results
            self.logger.info("Updating state with validation results")
            updated_state = dict(state)
            
            # Store validation result
            updated_state["validation_results"] = validation_result
            
            # Track validation history
            validation_history = state.get("validation_history", [])
            validation_history.append({
                "page_number": current_page,
                "result": validation_result
            })
            updated_state["validation_history"] = validation_history
            
            # Update current page if validation passed
            if validation_result["is_valid"]:
                self.logger.info(f"Page {current_page} validated successfully, moving to next page")
                updated_state["current_page"] = current_page + 1
            
            self.logger.info(f"Total validation attempts: {len(validation_history)}")
            self.logger.info("=== Validation Process Complete ===")
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error in validation process: {str(e)}")
            self.logger.error("=== Validation Process Failed ===")
            raise 
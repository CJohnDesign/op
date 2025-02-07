"""Validator node implementation.

This module contains a reactive validator node that checks slide and script consistency.
Following Single Responsibility Principle, this node only handles validation and orchestration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.nodes.validate.slide_updater import SlideUpdater
from agent.nodes.validate.script_updater import ScriptUpdater
from agent.prompts.validator.prompts import VALIDATION_PROMPT
from agent.types import AgentState


class ValidationResult(TypedDict):
    """Type definition for validation results."""
    needs_slide_update: bool
    needs_script_update: bool
    slide_update_instructions: str | None
    script_update_instructions: str | None


class ValidatorNode(BaseNode[AgentState]):
    """Node for validating and orchestrating updates to slides and scripts.
    
    Following Single Responsibility Principle, this node only handles:
    1. Validating content consistency
    2. Determining what needs updates
    3. Orchestrating updates through dedicated tools
    """
    
    def __init__(self) -> None:
        """Initialize the validator with GPT-4 model and update tools."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
        self.slide_updater = SlideUpdater()
        self.script_updater = ScriptUpdater()
    
    def _validate_content(self, slides: str, script: str) -> ValidationResult:
        """Validate slides and script content for consistency.
        
        Args:
            slides: The slide content to validate
            script: The script content to validate
            
        Returns:
            ValidationResult indicating what needs updates
        """
        try:
            # Create validation message
            message = HumanMessage(
                content=VALIDATION_PROMPT.format(
                    content={
                        "slides": slides,
                        "script": script
                    }
                )
            )
            
            # Get validation results
            self.logger.info("Validating content consistency")
            response = self.model.invoke([message])
            
            # Parse response and return validation result
            # TODO: Implement response parsing
            return {
                "needs_slide_update": False,
                "needs_script_update": False,
                "slide_update_instructions": None,
                "script_update_instructions": None
            }
            
        except Exception as e:
            self.logger.error(f"Error validating content: {str(e)}")
            raise
    
    def _apply_updates(
        self,
        validation_result: ValidationResult,
        current_slides: str,
        current_script: str
    ) -> Tuple[str, str]:
        """Apply any needed updates using the appropriate tools.
        
        Args:
            validation_result: The validation results indicating what needs updates
            current_slides: Current slide content
            current_script: Current script content
            
        Returns:
            Tuple of (updated_slides, updated_script)
        """
        updated_slides = current_slides
        updated_script = current_script
        
        try:
            if validation_result["needs_slide_update"]:
                self.logger.info("Updating slides")
                updated_slides = self.slide_updater.update(
                    current_slides,
                    validation_result["slide_update_instructions"]
                )
            
            if validation_result["needs_script_update"]:
                self.logger.info("Updating script")
                updated_script = self.script_updater.update(
                    current_script,
                    validation_result["script_update_instructions"]
                )
            
            return updated_slides, updated_script
            
        except Exception as e:
            self.logger.error(f"Error applying updates: {str(e)}")
            raise
    
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state to validate and update content.
        
        Args:
            state: The current state containing slides and script content
            config: Runtime configuration
            
        Returns:
            Updated state with validated content
        """
        self.logger.info("Starting content validation")
        
        try:
            # Get current content
            slides = state.get("slides", {}).get("content", "")
            script = state.get("script", {}).get("content", "")
            
            if not slides or not script:
                self.logger.warning("Missing slides or script content")
                return state
            
            # Validate content
            validation_result = self._validate_content(slides, script)
            
            # Apply updates if needed
            if validation_result["needs_slide_update"] or validation_result["needs_script_update"]:
                updated_slides, updated_script = self._apply_updates(
                    validation_result,
                    slides,
                    script
                )
                
                # Update state with new content
                updated_state = dict(state)
                if validation_result["needs_slide_update"]:
                    updated_state["slides"]["content"] = updated_slides
                if validation_result["needs_script_update"]:
                    updated_state["script"]["content"] = updated_script
                    
                return updated_state
            
            return state
            
        except Exception as e:
            self.logger.error(f"Error in validation process: {str(e)}")
            raise 
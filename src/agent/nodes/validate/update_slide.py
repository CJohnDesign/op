"""Update slide node implementation.

This module contains a node that updates slide content based on validation results.
Following Single Responsibility Principle, this node only handles slide updates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.update_slide import UPDATE_SLIDE_PROMPT
from agent.types import AgentState, ProcessedImage


class UpdateSlideNode(BaseNode[AgentState]):
    """Node for updating slide content based on validation results.
    
    Following Single Responsibility Principle, this node only handles
    the updating of slide content to match validation requirements.
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
    
    def _format_brochure_pages(self, processed_images: Dict[int, ProcessedImage], deck_id: str) -> str:
        """Format brochure pages information for the prompt.
        
        Args:
            processed_images: Dictionary of processed images
            deck_id: Current deck ID
            
        Returns:
            Formatted string of available brochure pages
        """
        pages_info = []
        for page_num, page_data in sorted(processed_images.items()):
            page_path = f"src/decks/{deck_id}/img/pages/{page_data['new_name']}"
            pages_info.append(
                f"Page {page_num}: {page_data['page_title']}\n"
                f"Path: {page_path}\n"
                f"Summary: {page_data['summary']}\n"
            )
        return "\n".join(pages_info)
    
    def _update_content(self, current_content: str, instructions: str, processed_images: Dict[int, ProcessedImage], deck_id: str) -> str:
        """Update slide content based on validation instructions.
        
        Args:
            current_content: Current slide content to update
            instructions: Instructions for updating the content
            processed_images: Dictionary of processed images
            deck_id: Current deck ID
            
        Returns:
            Updated slide content
        """
        try:
            # Format brochure pages information
            brochure_pages = self._format_brochure_pages(processed_images, deck_id)
            
            # Create message with update prompt
            message = HumanMessage(
                content=UPDATE_SLIDE_PROMPT.format(
                    current_content=current_content,
                    brochure_pages=brochure_pages,
                    instructions=instructions
                )
            )
            
            # Get updated content from GPT-4o
            self.logger.info("Updating slide content")
            response = self.model.invoke([message])
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error updating slide content: {str(e)}")
            return current_content
    
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state to update slides.
        
        Args:
            state: The current state containing validation results
            config: Runtime configuration
            
        Returns:
            Updated state with modified slide content
        """
        self.logger.info("Starting slide content update")
        
        try:
            # Get validation results and current content
            validation_results = state.get("validation_results", {})
            current_slides = state.get("slides", {}).get("content")
            deck_id = state.get("deck_id")
            processed_images = state.get("processed_images", [])
            
            if not validation_results or not current_slides or not deck_id or not processed_images:
                self.logger.warning("Missing required state information")
                return state
            
            # Check if slide update is needed
            slide_validation = validation_results.get("slide", {})
            if slide_validation.get("is_valid", True):
                self.logger.info("No slide updates needed")
                return state
            
            # Get update instructions
            instructions = slide_validation.get("suggested_fixes")
            if not instructions:
                self.logger.warning("No slide update instructions provided")
                return state
            
            # Update slide content with brochure pages
            updated_slides = self._update_content(
                current_slides,
                instructions,
                processed_images,
                deck_id
            )
            
            # Create updated state
            updated_state = dict(state)
            updated_state["slides"]["content"] = updated_slides
            updated_state["update_history"] = state.get("update_history", []) + [{
                "type": "slide",
                "instructions": instructions
            }]
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error in slide update process: {str(e)}")
            raise 
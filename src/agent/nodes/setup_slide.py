"""Setup slide node implementation.

This module contains a node that sets up the slide content.
Following Single Responsibility Principle, this node only handles slide setup.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.setup_slides import SETUP_SLIDES_PROMPT, SETUP_SLIDES_HUMAN_TEMPLATE
from agent.types import AgentState


class SetupSlideNode(BaseNode[AgentState]):
    """Node for setting up slide content.
    
    Following Single Responsibility Principle, this node only handles
    the setup and organization of slide content.
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4 model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
    
    def _generate_slides(self, template: str, processed_summaries: str) -> str:
        """Generate slide content using GPT-4.
        
        Args:
            template: The slide template to use
            processed_summaries: The processed content summaries
            
        Returns:
            Generated slide content
        """
        try:
            # Create messages with system and human prompts
            messages = [
                HumanMessage(content=SETUP_SLIDES_PROMPT),
                HumanMessage(
                    content=SETUP_SLIDES_HUMAN_TEMPLATE.format(
                        template=template,
                        processed_summaries=processed_summaries
                    )
                )
            ]
            
            # Get slide content from GPT-4
            self.logger.info("Generating slide content")
            response = self.model.invoke(messages)
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error generating slides: {str(e)}")
            return f"Error generating slides: {str(e)}"
    
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state to set up slides.
        
        Args:
            state: The current state containing deck_id and deck_title
            config: Runtime configuration
            
        Returns:
            Updated state with slide setup
        """
        self.logger.info("Setting up slides")
        
        try:
            # Get parameters from state
            deck_id = state["deck_id"]
            deck_title = state["deck_title"]
            
            # Get template and processed content
            deck_dir = Path("src/decks") / deck_id
            template_file = deck_dir / "slides.md"
            
            if not template_file.exists():
                self.logger.error(f"Template file not found at {template_file}")
                return state
            
            # Read template
            template = template_file.read_text()
            
            # Get processed summaries from state
            processed_summaries = state.get("presentation", {}).get("content", "")
            if not processed_summaries:
                self.logger.warning("No processed content found in state")
                return state
            
            # Generate slide content
            slide_content = self._generate_slides(template, processed_summaries)
            
            # Create updated state
            updated_state = dict(state)
            updated_state["slides"] = {
                "content": slide_content,
                "template_used": template
            }
            
            # Save slide content to file
            slides_file = deck_dir / "slides.md"
            with open(slides_file, "w") as f:
                f.write(slide_content)
            
            # Save state to file
            state_file = deck_dir / "state.json"
            with open(state_file, "w") as f:
                json.dump(updated_state, f, indent=2)
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error setting up slides: {str(e)}")
            raise 
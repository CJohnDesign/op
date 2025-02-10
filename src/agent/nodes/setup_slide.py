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
from langsmith import traceable

from agent.nodes.base import BaseNode
from agent.prompts.setup_slides import SETUP_SLIDES_PROMPT, SETUP_SLIDES_HUMAN_TEMPLATE
from agent.types import AgentState


class SetupSlideNode(BaseNode[AgentState]):
    """Node for setting up slide content.
    
    Following Single Responsibility Principle, this node only handles
    the setup and organization of slide content.
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        # Initialize OpenAI client directly - no need to wrap for LangChain
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
    
    @traceable(name="generate_slides_with_gpt4")
    def _generate_slides(self, template: str, processed_summaries: str, extracted_tables: str) -> str:
        """Generate slide content using GPT-4o.
        
        Args:
            template: The slide template to use
            processed_summaries: The processed content summaries
            extracted_tables: The extracted table data
            
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
                        processed_summaries=processed_summaries,
                        extracted_tables=extracted_tables
                    )
                )
            ]
            
            # Get slide content from GPT-4o
            self.logger.info("Generating slide content")
            response = self.model.invoke(messages)
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error generating slides: {str(e)}")
            return f"Error generating slides: {str(e)}"
    
    @traceable(name="setup_slides_with_gpt4")
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
            
            # Get processed images and extracted tables from state
            processed_images = state.get("processed_images", {})
            extracted_tables = state.get("extracted_tables", {})
            
            if not processed_images:
                self.logger.warning("No processed images found in state")
                return state
                
            # Prepare content summary including both images and tables
            content_summary = []
            for page_num in sorted(processed_images.keys()):
                page_data = processed_images[page_num]
                summary = {
                    "page_number": page_data["page_number"],
                    "page_title": page_data["page_title"],
                    "summary": page_data["summary"]
                }
                content_summary.append(summary)
            
            # Convert to string format for the template
            processed_summaries = json.dumps(content_summary, indent=2)
            extracted_tables_str = json.dumps(extracted_tables, indent=2)
            
            # Generate slide content
            slide_content = self._generate_slides(template, processed_summaries, extracted_tables_str)
            
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
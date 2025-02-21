"""Setup slide node implementation.

This module contains a node that sets up the slide content.
Following Single Responsibility Principle, this node only handles slide setup.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from agent.nodes.base import BaseNode
from agent.prompts.setup_slides import SETUP_SLIDES_PROMPT, SETUP_SLIDES_HUMAN_TEMPLATE
from agent.types import AgentState, ProcessedImage
from agent.llm_config import llm


class SetupSlideNode(BaseNode[AgentState]):
    """Node for setting up slide content.
    
    Following Single Responsibility Principle, this node only handles
    the setup and organization of slide content.
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        # Use shared LLM instance
        self.model = llm
    
    def _get_image_lists(self, deck_dir: Path, processed_images: Dict[str, ProcessedImage]) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Get separate lists of page images and logo images.
        
        Args:
            deck_dir: Path to the deck directory
            processed_images: Dictionary of processed images from state
            
        Returns:
            Tuple containing (pages_list, logos_list, pages_with_tables_list, pages_with_limitations_list)
        """
        img_dir = deck_dir / "img"
        pages_list = []
        logos_list = []
        pages_with_tables = []
        pages_with_limitations = []
        
        # Get pages images
        pages_dir = img_dir / "pages"
        if pages_dir.exists():
            pages_list = [
                str(f.relative_to(img_dir))
                for f in pages_dir.glob("*")
                if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif"]
            ]
            self.logger.info(f"Found {len(pages_list)} brochure page images")
            
            # Extract pages with tables and limitations
            for page_path in pages_list:
                page_name = Path(page_path).name
                for _, page_data in processed_images.items():
                    if page_data["new_name"] == page_name:
                        if page_data.get("tableDetails", {}).get("hasBenefitsComparisonTable", False):
                            pages_with_tables.append(page_path)
                        if page_data.get("tableDetails", {}).get("hasLimitations", False):
                            pages_with_limitations.append(page_path)
            
            self.logger.info(f"Found {len(pages_with_tables)} pages with benefit tables")
            self.logger.info(f"Found {len(pages_with_limitations)} pages with limitations")
            
        # Get logos images
        logos_dir = img_dir / "logos"
        if logos_dir.exists():
            logos_list = [
                str(f.relative_to(img_dir))
                for f in logos_dir.glob("*")
                if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".svg"]
            ]
            self.logger.info(f"Found {len(logos_list)} logo images")
            
        return pages_list, logos_list, pages_with_tables, pages_with_limitations
    
    @traceable(name="generate_slides_with_gpt4")
    def _generate_slides(
        self, 
        template: str, 
        processed_summaries: str, 
        extracted_tables: str,
        presentation_content: str,
        deck_id: str,
        deck_title: str,
        instructions: str,
        pages_list: List[str],
        logos_list: List[str],
        processed_images: Dict[str, ProcessedImage]
    ) -> str:
        """Generate slide content using GPT-4o.
        
        Args:
            template: The slide template to use
            processed_summaries: The processed content summaries
            extracted_tables: The extracted table data
            presentation_content: The generated presentation content
            deck_id: ID of the current deck
            deck_title: Title of the current deck
            instructions: Instructions from instructions.md
            pages_list: List of brochure page image paths
            logos_list: List of logo image paths
            processed_images: Dictionary of processed images from state
            
        Returns:
            Generated slide content
        """
        try:
            # Sanitize instructions to escape any curly braces that might interfere with formatting
            instructions_safe = instructions.replace("{", "{{").replace("}", "}}")
            
            # Get special purpose page lists
            _, _, pages_with_tables, pages_with_limitations = self._get_image_lists(
                Path("src/decks") / deck_id,
                processed_images
            )
            
            # Create messages with system and human prompts
            messages = [
                HumanMessage(content=SETUP_SLIDES_PROMPT.format(
                    template=template,
                    deck_id=deck_id,
                    deck_title=deck_title,
                    instructions=instructions_safe,
                    pages_list=json.dumps(pages_list, indent=2),
                    logos_list=json.dumps(logos_list, indent=2),
                    pages_with_tables_list=json.dumps(pages_with_tables, indent=2),
                    pages_with_limitations_list=json.dumps(pages_with_limitations, indent=2)
                )),
                HumanMessage(
                    content=SETUP_SLIDES_HUMAN_TEMPLATE.format(
                        processed_summaries=processed_summaries,
                        extracted_tables=extracted_tables,
                        presentation_content=presentation_content,
                        deck_id=deck_id,
                        deck_title=deck_title,
                        instructions=instructions_safe,
                        pages_list=json.dumps(pages_list, indent=2),
                        logos_list=json.dumps(logos_list, indent=2),
                        pages_with_tables_list=json.dumps(pages_with_tables, indent=2),
                        pages_with_limitations_list=json.dumps(pages_with_limitations, indent=2)
                    )
                )
            ]
            
            # Get slide content from GPT-4o
            self.logger.info("Generating slide content")
            self.logger.info(f"Deck ID: {deck_id}")
            self.logger.info(f"Deck Title: {deck_title}")
            self.logger.info(f"Number of brochure pages: {len(pages_list)}")
            self.logger.info(f"Number of logos: {len(logos_list)}")
            self.logger.info(f"Number of pages with tables: {len(pages_with_tables)}")
            self.logger.info(f"Number of pages with limitations: {len(pages_with_limitations)}")
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
            processed_images = state.get("processed_images", {})
            
            # Get template and processed content
            deck_dir = Path("src/decks") / deck_id
            template_file = deck_dir / "slides.md"
            
            if not template_file.exists():
                self.logger.error(f"Template file not found at {template_file}")
                return state
            
            # Read template
            template = template_file.read_text()
            
            # Get processed images and extracted tables from state
            if not processed_images:
                self.logger.warning("No processed images found in state")
                return state
                
            # Prepare content summary including both images and tables
            content_summary = []
            page_nums = sorted([int(k) if isinstance(k, str) else k for k in processed_images.keys()])
            for page_num in page_nums:
                page_data = processed_images[str(page_num) if isinstance(page_num, int) else page_num]
                summary = {
                    "page_number": page_num,
                    "page_title": page_data["page_title"],
                    "summary": page_data["summary"]
                }
                content_summary.append(summary)
            
            # Convert to string format for the template
            processed_summaries = json.dumps(content_summary, indent=2)
            
            # Handle extracted tables
            extracted_tables = state.get("extracted_tables", {})
            extracted_tables_str = json.dumps(extracted_tables, indent=2)
            
            # Get instructions from initial deck
            instructions = state.get("initial_deck", {}).get("instructions", "")
            
            # Get generated presentation content
            presentation_content = state.get("presentation", {}).get("content", "")
            if not presentation_content:
                self.logger.warning("No generated presentation content found in state")
                presentation_content = "No presentation content available"
            
            # Get image lists
            pages_list, logos_list, _, _ = self._get_image_lists(deck_dir, processed_images)
            
            # Generate slide content with deck info
            slide_content = self._generate_slides(
                template, 
                processed_summaries, 
                extracted_tables_str,
                presentation_content,
                deck_id,
                deck_title,
                instructions,
                pages_list,
                logos_list,
                processed_images
            )
            
            # Create updated state
            updated_state = dict(state)
            updated_state["slides"] = {
                "content": slide_content,
                "template_used": template,
                "pages_list": pages_list,
                "logos_list": logos_list
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
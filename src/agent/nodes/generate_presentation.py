"""Generate presentation node implementation.

This module contains a node that generates presentation content from analyzed data.
Following Single Responsibility Principle, this node only handles presentation generation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.generate_presentation import GENERATE_PRESENTATION_PROMPT
from agent.types import AgentState


class GeneratePresentationNode(BaseNode[AgentState]):
    """Node for generating presentation content.
    
    Following Single Responsibility Principle, this node only handles
    the generation of presentation content from analyzed data.
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=4096,
            temperature=0
        )
    
    def _generate_presentation(self, summaries: List[Dict[str, Any]], tables: List[Dict[str, Any]]) -> str:
        """Generate presentation content using GPT-4o.
        
        Args:
            summaries: List of page summaries
            tables: List of extracted tables
            
        Returns:
            Generated presentation content as string
        """
        try:
            # Format the input data
            summaries_text = json.dumps(summaries, indent=2)
            tables_text = json.dumps(tables, indent=2)
            
            # Create message with formatted data
            message = HumanMessage(
                content=GENERATE_PRESENTATION_PROMPT.format(
                    individual_summaries=summaries_text,
                    extracted_tables=tables_text
                )
            )
            
            # Get presentation content from GPT-4o
            self.logger.info("Generating presentation content")
            response = self.model.invoke([message])
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error generating presentation: {str(e)}")
            return f"Error generating presentation: {str(e)}"
    
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the analyzed data to generate presentation content.
        
        Args:
            state: The current state containing deck_id and deck_title
            config: Runtime configuration
            
        Returns:
            Updated state with generated presentation
        """
        self.logger.info("Generating presentation from analyzed data")
        
        try:
            # Get parameters from state
            deck_id = state["deck_id"]
            deck_title = state["deck_title"]
            processed_images = state.get("processed_images", {})
            extracted_tables = state.get("extracted_tables", {})
            
            if not processed_images:
                self.logger.warning("No processed images found in state")
                return state
            
            # Convert processed images to list format for the template
            page_summaries = []
            for page_num in sorted(processed_images.keys()):
                page_data = processed_images[page_num]
                page_summaries.append({
                    "page_number": page_num,
                    "page_title": page_data["page_title"],
                    "summary": page_data["summary"],
                    "table_details": page_data["table_details"]
                })
            
            # Convert extracted tables to list format for the template
            tables_list = []
            for page_num in sorted(extracted_tables.keys()):
                table_data = extracted_tables[page_num]
                if "tables" in table_data:
                    for table in table_data["tables"]:
                        tables_list.append({
                            "page_number": page_num,
                            "table_title": table["table_title"],
                            "headers": table["headers"],
                            "rows": table["rows"]
                        })
            
            # Generate presentation content
            presentation_content = self._generate_presentation(page_summaries, tables_list)
            
            # Create updated state
            updated_state = dict(state)
            updated_state["presentation"] = {
                "content": presentation_content,
                "generated_at": datetime.now().isoformat()
            }
            
            # Save state to file
            deck_dir = Path("src/decks") / deck_id
            state_file = deck_dir / "state.json"
            with open(state_file, "w") as f:
                json.dump(updated_state, f, indent=2)
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error generating presentation: {str(e)}")
            raise 
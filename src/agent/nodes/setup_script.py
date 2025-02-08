"""Setup script node implementation.

This module contains a node that sets up the script content.
Following Single Responsibility Principle, this node only handles script setup.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.setup_script import SCRIPT_WRITER_SYSTEM_PROMPT, SCRIPT_WRITER_HUMAN_PROMPT
from agent.types import AgentState


class SetupScriptNode(BaseNode[AgentState]):
    """Node for setting up script content.
    
    Following Single Responsibility Principle, this node only handles
    the setup and organization of script content.
    """
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=8192,
            temperature=0
        )
    
    def _generate_script(self, template: str, processed_summaries: str, slides_content: str, extracted_tables: str) -> str:
        """Generate script content using GPT-4o.
        
        Args:
            template: The script template to use
            processed_summaries: The processed content summaries
            slides_content: The generated slide content
            extracted_tables: The extracted tables content
            
        Returns:
            Generated script content
        """
        try:
            # Create messages with system and human prompts
            messages = [
                SystemMessage(
                    content=SCRIPT_WRITER_SYSTEM_PROMPT.format(
                        template=template
                    )
                ),
                HumanMessage(
                    content=SCRIPT_WRITER_HUMAN_PROMPT.format(
                        processed_summaries=processed_summaries,
                        slides_content=slides_content,
                        extracted_tables=extracted_tables
                    )
                )
            ]
            
            # Get script content from GPT-4o
            self.logger.info("Generating script content")
            response = self.model.invoke(messages)
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error generating script: {str(e)}")
            return f"Error generating script: {str(e)}"
    
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state to set up script.
        
        Args:
            state: The current state containing deck_id and deck_title
            config: Runtime configuration
            
        Returns:
            Updated state with script setup
        """
        self.logger.info("Setting up script")
        
        try:
            # Get parameters from state
            deck_id = state["deck_id"]
            deck_title = state["deck_title"]
            
            # Get template and processed content
            deck_dir = Path("src/decks") / deck_id
            template_file = deck_dir / "audio" / "audio_script.md"
            
            if not template_file.exists():
                self.logger.error(f"Template file not found at {template_file}")
                return state
            
            # Read template
            template = template_file.read_text()
            
            # Get processed summaries, slides content and extracted tables from state
            processed_summaries = state.get("presentation", {}).get("content", "")
            slides_content = state.get("slides", {}).get("content", "")
            extracted_tables = state.get("extracted_tables", {})
            
            # Convert extracted tables to string format
            tables_str = json.dumps(extracted_tables, indent=2)
            
            if not processed_summaries or not slides_content:
                self.logger.warning("Missing required content in state")
                return state
            
            # Generate script content with tables
            script_content = self._generate_script(
                template, 
                processed_summaries, 
                slides_content,
                tables_str
            )
            
            # Create updated state
            updated_state = dict(state)
            updated_state["script"] = {
                "content": script_content,
                "template_used": template
            }
            
            # Save script content to file
            script_file = deck_dir / "audio" / "audio_script.md"
            with open(script_file, "w") as f:
                f.write(script_content)
            
            # Save state to file
            state_file = deck_dir / "state.json"
            with open(state_file, "w") as f:
                json.dump(updated_state, f, indent=2)
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error setting up script: {str(e)}")
            raise 
"""Page parser node implementation.

This module contains a node that parses slides and script content into structured pages.
Following Single Responsibility Principle, this node only handles page parsing.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig

from agent.nodes.base import BaseNode
from agent.types import AgentState

logger = logging.getLogger(__name__)

class PageParserNode(BaseNode[AgentState]):
    """Node for parsing slides and script into structured pages.
    
    Following Single Responsibility Principle, this node only handles
    the parsing of content into a structured page format.
    """
    
    # Regex pattern for slides - captures frontmatter and content between --- markers
    SLIDE_PATTERN = r"^---\n(.*?)\n---\n(.*?)(?=\n---|\Z)"
    
    # Regex pattern for script sections - captures header and content
    SCRIPT_PATTERN = r"^---- (.+?) ----\n(.*?)(?=\n---- .+? ----|\Z)"
    
    def _parse_slides(self, slides_content: str) -> List[Dict[str, str]]:
        """Parse slides content into a list of slide dictionaries."""
        slides = []
        matches = re.finditer(self.SLIDE_PATTERN, slides_content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            frontmatter = match.group(1).strip()
            content = match.group(2).strip()
            
            # Extract header from content (if exists)
            header_match = re.search(r'^#+ (.+)$', content, re.MULTILINE)
            header = header_match.group(1) if header_match else ''
            
            slides.append({
                'header': header,
                'content': content,
                'frontmatter': frontmatter
            })
        
        logger.info(f"Parsed {len(slides)} slides")
        return slides
    
    def _parse_script(self, script_content: str) -> List[Dict[str, str]]:
        """Parse script content into a list of script section dictionaries."""
        script_sections = []
        matches = re.finditer(self.SCRIPT_PATTERN, script_content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            script_sections.append({
                'header': match.group(1).strip(),
                'content': match.group(2).strip()
            })
        
        logger.info(f"Parsed {len(script_sections)} script sections")
        return script_sections
    
    def _create_pages(self, slides: List[Dict[str, str]], script_sections: List[Dict[str, str]]) -> List[Dict[str, Dict[str, str]]]:
        """Create pages by matching slides with script sections."""
        pages = []
        
        # Use the longer list to determine number of pages
        max_length = max(len(slides), len(script_sections))
        
        for i in range(max_length):
            page = {
                'slide': slides[i] if i < len(slides) else {'header': '', 'content': '', 'frontmatter': ''},
                'script': script_sections[i] if i < len(script_sections) else {'header': '', 'content': ''}
            }
            pages.append(page)
        
        logger.info(f"Created {len(pages)} pages")
        return pages
    
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the current state to parse slides and script into pages.
        
        Args:
            state: The current state containing deck_id and slides/script content
            config: Runtime configuration
            
        Returns:
            Updated state with parsed pages
        """
        logger.info("Parsing slides and script into pages")
        
        try:
            # Get content from state
            slides_content = state.get("slides", {}).get("content", "")
            script_content = state.get("script", {}).get("content", "")
            
            if not slides_content or not script_content:
                logger.warning("Missing slides or script content in state")
                return state
            
            # Parse content
            slides = self._parse_slides(slides_content)
            script_sections = self._parse_script(script_content)
            
            # Create pages
            pages = self._create_pages(slides, script_sections)
            
            # Create updated state
            updated_state = dict(state)
            updated_state["pages"] = {
                "content": pages,
                "count": len(pages)
            }
            
            # Save state to file
            deck_dir = Path("src/decks") / state["deck_id"]
            state_file = deck_dir / "state.json"
            with open(state_file, "w") as f:
                json.dump(updated_state, f, indent=2)
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Error parsing pages: {str(e)}")
            raise 
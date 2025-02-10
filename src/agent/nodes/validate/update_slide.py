"""Update slide node implementation.

This module contains a node that updates slide content based on validation results.
Following Single Responsibility Principle, this node only handles slide updates.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.update_slide_prompt import UPDATE_SLIDE_PROMPT
from agent.types import AgentState, ProcessedImage

logger = logging.getLogger(__name__)

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
        self.system_message = SystemMessage(content="""You are a slide content updater that ONLY responds with valid JSON.
Your responses must follow this exact schema:
{
    "frontmatter": string,  // The slide frontmatter (e.g., layout, image path)
    "content": string,      // The slide content without frontmatter
    "changes_made": string[]
}

IMPORTANT:
1. Return ONLY the JSON object - no markdown code blocks, no explanations
2. The JSON must be valid and parseable
3. Do not include any text before or after the JSON
4. Do not wrap the JSON in backticks or code blocks
5. The response should start with { and end with }
6. The frontmatter should be in YAML format with --- delimiters
7. The content should contain the slide content with proper markdown

Example response:
{
    "frontmatter": "---\\nlayout: one-half-img\\nimage: path/to/image.jpg\\n---",
    "content": "# Title\\n\\nContent with **bold** text",
    "changes_made": ["Updated layout", "Added image path"]
}""")
        self.state: Optional[AgentState] = None
    
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
    
    def _get_available_images(self) -> List[str]:
        """Get list of all available images in the pages directory.
        
        Returns:
            List of image paths relative to workspace
        """
        if not self.state:
            self.logger.warning("No state available")
            return []
            
        # Get deck ID from state
        deck_id = self.state.get("deck_id", "")
        if not deck_id:
            self.logger.warning("No deck ID found in state")
            return []
            
        # Get processed images from state
        processed_images = self.state.get("processed_images", {})
        
        # Build list of image paths
        image_paths = []
        pages_dir = Path(f"src/decks/{deck_id}/img/pages")
        
        if pages_dir.exists():
            # First add images from processed_images to maintain order
            for _, image_data in sorted(processed_images.items()):
                image_path = str(pages_dir / image_data["new_name"])
                if Path(image_path).exists():
                    image_paths.append(image_path)
            
            # Then add any additional jpg files not in processed_images
            for image_file in pages_dir.glob("*.jpg"):
                image_path = str(image_file)
                if image_path not in image_paths:
                    image_paths.append(image_path)
        else:
            self.logger.warning(f"Pages directory not found at {pages_dir}")
            
        return image_paths
    
    def _update_content(self, current_content: str, instructions: str, image_path: Optional[str] = None) -> str:
        """Update slide content based on validation instructions.
        
        Args:
            current_content: Current slide content to update
            instructions: Instructions for updating the content
            image_path: Optional path to image to include
            
        Returns:
            Updated slide content
        """
        try:
            # Filter instructions to only include slide-related updates
            slide_instructions = instructions
            if "script" in instructions.lower():
                slide_instructions = "Update slide content only, ignoring script-related changes."
            
            # Check if instructions mention v-clicks - if so, return current content
            if "v-click" in slide_instructions.lower():
                self.logger.info("Instructions mention v-clicks - preserving current content")
                return {
                    "frontmatter": current_page["slide"].get("frontmatter", ""),
                    "content": current_content
                }
            
            # Get available images
            available_images = self._get_available_images()
            
            # Create message with update prompt
            message = HumanMessage(
                content=UPDATE_SLIDE_PROMPT.format(
                    current_content=current_content,
                    instructions=slide_instructions,
                    available_images="\n".join(available_images)
                ) + "\n\nIMPORTANT: Return your response as a JSON object with 'frontmatter', 'content', and 'changes_made' fields."
            )
            
            # Get updated content from GPT-4o with system message
            self.logger.info("Updating slide content")
            response = self.model.invoke([self.system_message, message])
            
            # Parse JSON response
            try:
                self.logger.debug(f"Raw response: {response.content}")
                result = json.loads(response.content)
                
                if not isinstance(result, dict):
                    self.logger.error(f"Response is not a dictionary: {result}")
                    raise ValueError("Invalid response format - not a dictionary")
                    
                if "frontmatter" not in result or "content" not in result:
                    self.logger.error(f"Response missing required fields: {result}")
                    raise ValueError("Response missing required fields")
                    
                # Get updated content
                updated_content = result["content"]
                frontmatter = result["frontmatter"]
                
                # Remove any script sections if present
                if "----" in updated_content:
                    self.logger.warning("Found script section markers in slide content - removing")
                    updated_content = updated_content.split("----")[0].strip()
                
                # If content is unchanged, that's okay - return it
                if updated_content.strip() == current_content.strip():
                    self.logger.info("Content unchanged - no updates needed")
                    return {
                        "frontmatter": frontmatter,
                        "content": current_content
                    }
                
                # Log the changes that were made
                if "changes_made" in result:
                    self.logger.info("Changes made:")
                    for change in result["changes_made"]:
                        self.logger.info(f"- {change}")
                
                # Return both frontmatter and content
                return {"frontmatter": frontmatter, "content": updated_content}
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {str(e)}")
                self.logger.error(f"Raw response: {response.content}")
                raise ValueError(f"Invalid JSON response: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error updating slide content: {str(e)}")
            raise ValueError(f"Failed to update content: {str(e)}")
    
    def process(self, state: AgentState, config: RunnableConfig) -> AgentState:
        """Process the current state and update slide content.
        
        Args:
            state: Current state with validation results
            config: Runtime configuration
            
        Returns:
            Updated state
            
        Raises:
            ValueError: If validation state is missing or update fails
        """
        self.logger.info("=" * 80)
        self.logger.info("UPDATE SLIDE NODE START")
        self.logger.info("=" * 80)
        
        # Store state for use by other methods
        self.state = state
        
        try:
            # Get validation details
            current_validation = state.get("current_validation")
            if not current_validation:
                error_msg = "No current validation in state - workflow cannot continue"
                self.logger.error(error_msg)
                self.logger.error(f"Available state keys: {list(state.keys())}")
                raise ValueError(error_msg)
                
            # Get current page index
            page_index = current_validation.get("page_index")
            if page_index is None:
                error_msg = "No page index in current validation"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            # Get pages
            pages = state.get("pages", {}).get("content", [])
            if not pages:
                error_msg = "No pages found in state - workflow cannot continue"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            if page_index >= len(pages):
                error_msg = f"Invalid page index {page_index} (total pages: {len(pages)})"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            # Get current page
            current_page = pages[page_index]
            
            # Get validation details
            validation = current_validation.get("validation", {})
            slide_validation = validation.get("slide", {})
            
            # Log validation details
            self.logger.info(f"\nValidating Page {page_index + 1}:")
            self.logger.info(f"- Is Valid: {slide_validation.get('is_valid')}")
            self.logger.info(f"- Severity: {slide_validation.get('severity')}")
            self.logger.info(f"- Suggested Fixes: {slide_validation.get('suggested_fixes')}")
            
            # Log current content
            self.logger.info("\nCurrent Content:")
            self.logger.info("-" * 40)
            self.logger.info(f"Frontmatter: {current_page['slide'].get('frontmatter', 'No frontmatter')}")
            self.logger.info(f"Content: {current_page['slide'].get('content', 'No content')}")
            self.logger.info("-" * 40)
            
            # Get update instructions
            instructions = slide_validation.get("suggested_fixes", "")
            if not instructions:
                error_msg = "No update instructions provided - workflow cannot continue"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            self.logger.info("\nUpdate Instructions:")
            self.logger.info(instructions)
            
            # Update the content
            current_content = current_page["slide"]["content"]
            result = self._update_content(current_content, instructions)
            
            # Log content comparison
            self.logger.info("\nContent Comparison:")
            self.logger.info("- Original Content:")
            self.logger.info("-" * 40)
            self.logger.info(f"Frontmatter: {current_page['slide'].get('frontmatter', 'No frontmatter')}")
            self.logger.info(f"Content: {current_content}")
            self.logger.info("-" * 40)
            self.logger.info("- Updated Content:")
            self.logger.info("-" * 40)
            self.logger.info(f"Frontmatter: {result['frontmatter']}")
            self.logger.info(f"Content: {result['content']}")
            self.logger.info("-" * 40)
            
            # Update the page in state
            pages[page_index]["slide"]["frontmatter"] = result["frontmatter"]
            pages[page_index]["slide"]["content"] = result["content"]
            state["pages"]["content"] = pages
            
            # Clear validation results to force revalidation
            state.pop("validation_results", None)
            state.pop("current_validation", None)
            
            self.logger.info("\nState Update Summary:")
            self.logger.info(f"- Updated page {page_index + 1}")
            self.logger.info("- Cleared validation results")
            self.logger.info(f"- Final state keys: {list(state.keys())}")
            
        except Exception as e:
            error_msg = f"Critical error in update process: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error("Stack trace:", exc_info=True)
            raise ValueError(error_msg)
            
        finally:
            self.logger.info("=" * 80)
            self.logger.info("UPDATE SLIDE NODE END")
            self.logger.info("=" * 80)
            
        return state 
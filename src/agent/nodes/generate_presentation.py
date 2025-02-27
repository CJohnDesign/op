"""Generate presentation node implementation.

This module contains a node that generates presentation content from analyzed data.
Following Single Responsibility Principle, this node only handles presentation generation.
"""

from __future__ import annotations

import json
import logging
import csv
import base64
from io import StringIO
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langsmith import traceable

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
        # Initialize OpenAI client directly - no need to wrap for LangChain
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=4096,
            temperature=0
        )
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()

    def _get_table_page_images(self, processed_images: Dict[str, Any], deck_dir: Path) -> List[Dict[str, Any]]:
        """Get images of pages that contain limitations but not benefits comparison tables.
        
        Args:
            processed_images: Dictionary of processed images
            deck_dir: Path to the deck directory
            
        Returns:
            List of image message contents
        """
        image_messages = []
        pages_dir = deck_dir / "img" / "pages"
        
        for page_num, page_data in processed_images.items():
            table_details = page_data.get("tableDetails", {})
            # Filter for pages that have limitations but not benefit comparison tables
            if (not table_details.get("hasBenefitsComparisonTable", False) and 
                table_details.get("hasLimitations", False)):
                image_path = pages_dir / page_data["new_name"]
                if image_path.exists():
                    try:
                        image_data = self._encode_image(image_path)
                        image_messages.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high"
                            }
                        })
                        self.logger.info(f"Added limitations page image: {image_path.name}")
                    except Exception as e:
                        self.logger.error(f"Error encoding image {image_path}: {str(e)}")
                else:
                    self.logger.warning(f"Limitations page image not found: {image_path}")
        
        return image_messages

    def _convert_tables_to_csv(self, tables_list: List[Dict[str, Any]]) -> str:
        """Convert tables data to CSV format.
        
        Args:
            tables_list: List of table dictionaries
            
        Returns:
            CSV formatted string of tables data
        """
        output = StringIO()
        for table in tables_list:
            # Write table metadata
            output.write(f"Table from Page {table['page_number']}\n")
            output.write(f"Title: {table['table_title']}\n")
            
            # Create CSV writer
            writer = csv.writer(output)
            
            # Write headers
            if 'headers' in table:
                writer.writerow(table['headers'])
            
            # Write rows
            if 'rows' in table:
                writer.writerows(table['rows'])
            
            # Add spacing between tables
            output.write("\n\n")
        
        return output.getvalue()
    
    @traceable(name="generate_presentation")
    def _generate_presentation(
        self,
        page_summaries: List[Dict[str, Any]],
        tables_list: List[Dict[str, Any]],
        instructions: str,
        deck_id: str,
        deck_title: str,
        processed_images: Dict[str, Any]
    ) -> str:
        """Generate presentation content using GPT-4o.
        
        Args:
            page_summaries: List of page summaries
            tables_list: List of extracted tables
            instructions: Initial deck instructions
            deck_id: ID of the current deck
            deck_title: Title of the current deck
            processed_images: Dictionary of processed images
            
        Returns:
            Generated presentation content
        """
        try:
            self.logger.info("Starting presentation generation")
            self.logger.info(f"Page summaries count: {len(page_summaries)}")
            self.logger.info(f"Tables list count: {len(tables_list)}")
            self.logger.info(f"Instructions length: {len(instructions)}")
            
            # Format the input data
            summaries_text = json.dumps(page_summaries, indent=2)
            self.logger.info(f"Summaries text length: {len(summaries_text)}")
            
            # Convert tables to CSV format
            tables_text = self._convert_tables_to_csv(tables_list)
            self.logger.info(f"Tables text length: {len(tables_text)}")
            
            # Get table page images
            deck_dir = Path("src/decks") / deck_id
            image_messages = self._get_table_page_images(processed_images, deck_dir)
            self.logger.info(f"Image messages count: {len(image_messages)}")
            
            # Create message content list starting with the text prompt
            message_content = [
                {
                    "type": "text",
                    "text": GENERATE_PRESENTATION_PROMPT.format(
                        page_summaries=summaries_text,
                        tables_list=tables_text,
                        instructions=instructions or "No specific instructions provided",
                        deck_id=deck_id,
                        deck_title=deck_title
                    )
                }
            ]
            
            # Add image messages if any were found
            message_content.extend(image_messages)
            
            # Create message with formatted data, instructions, and images
            message = HumanMessage(content=message_content)
            
            # Log the formatted prompt for debugging
            self.logger.info(f"Deck ID: {deck_id}")
            self.logger.info(f"Deck Title: {deck_title}")
            self.logger.info(f"Number of table page images included: {len(image_messages)}")
            
            # Get presentation content from GPT-4o
            self.logger.info("Generating presentation content")
            response = self.model.invoke([message])
            
            # Log the response for debugging
            self.logger.info(f"Response type: {type(response)}")
            self.logger.info(f"Response keys: {list(response.keys()) if hasattr(response, 'keys') else 'No keys'}")
            
            # Extract the content from the response
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                self.logger.info(f"Content length: {len(content)}")
                self.logger.info(f"Content preview: {content[:100]}...")
                return content
            else:
                self.logger.error("No content found in response")
                self.logger.error(f"Full response: {response}")
                return "Error: No content found in response"
                
        except Exception as e:
            self.logger.error(f"Error in _generate_presentation: {str(e)}")
            self.logger.error(f"Exception type: {type(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error generating presentation: {str(e)}"
    
    @traceable(name="process_presentation")
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
            
            self.logger.info(f"State keys: {list(state.keys())}")
            self.logger.info(f"Processed images count: {len(processed_images)}")
            self.logger.info(f"Extracted tables count: {len(extracted_tables)}")
            
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
                    "tableDetails": page_data["tableDetails"]
                })
            
            self.logger.info(f"Page summaries count: {len(page_summaries)}")
            if page_summaries:
                self.logger.info(f"First page summary: {page_summaries[0]}")
            
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
            
            self.logger.info(f"Tables list count: {len(tables_list)}")
            if tables_list:
                self.logger.info(f"First table title: {tables_list[0]['table_title']}")
            
            # Get instructions from initial deck
            instructions = state.get("initial_deck", {}).get("instructions", "")
            self.logger.info(f"Instructions length: {len(instructions)}")
            self.logger.info(f"Instructions preview: {instructions[:100]}...")
            
            # Generate presentation content with processed_images for table page access
            presentation_content = self._generate_presentation(
                page_summaries, 
                tables_list,
                instructions,
                deck_id,
                deck_title,
                processed_images
            )
            
            # Create updated state
            updated_state = dict(state)
            updated_state["presentation"] = {
                "content": presentation_content,
                "generated_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Presentation content type: {type(presentation_content)}")
            self.logger.info(f"Presentation content length: {len(str(presentation_content))}")
            self.logger.info(f"Presentation content preview: {str(presentation_content)[:100]}...")
            
            # Save state to file
            deck_dir = Path("src/decks") / deck_id
            state_file = deck_dir / "state.json"
            with open(state_file, "w") as f:
                json.dump(updated_state, f, indent=2)
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error generating presentation: {str(e)}")
            self.logger.error(f"Exception type: {type(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise 
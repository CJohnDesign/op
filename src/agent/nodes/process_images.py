"""Process images node implementation.

This module contains a node that processes images in the graph.
Following Single Responsibility Principle, this node only handles image processing.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.analyze_insurance_page import ANALYZE_PAGE_PROMPT
from agent.types import AgentState, ProcessedImage


class ProcessImagesNode(BaseNode[AgentState]):
    """Node for processing images in the graph.
    
    Following Single Responsibility Principle, this node only handles
    the processing of images from the deck's img directory.
    """
    
    BATCH_SIZE = 8  # Process 8 images at a time
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4 model."""
        super().__init__()
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
    
    def _analyze_image(self, image_path: Path) -> ProcessedImage:
        """Analyze a single image using GPT-4.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Analysis results as a ProcessedImage
        """
        try:
            # Encode image
            image_data = self._encode_image(image_path)
            
            # Create message with image
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": ANALYZE_PAGE_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}",
                            "detail": "high"
                        }
                    }
                ]
            )
            
            # Get analysis from GPT-4
            self.logger.info(f"Analyzing {image_path.name}")
            response = self.model.invoke([message])
            
            # Parse JSON response
            try:
                # Extract JSON from the response
                response_text = response.content
                # Find the first { and last } to extract the JSON object
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    return json.loads(json_str)
                else:
                    raise ValueError("No JSON object found in response")
                    
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.error(f"Error parsing JSON response for {image_path.name}: {str(e)}")
                self.logger.error(f"Raw response: {response_text}")
                return {
                    "page_title": f"Error analyzing {image_path.name}",
                    "summary": "Failed to parse analysis results",
                    "tableDetails": {
                        "hasBenefitsTable": False,
                        "hasLimitations": False
                    }
                }
        except Exception as e:
            self.logger.error(f"Error analyzing {image_path.name}: {str(e)}")
            return {
                "page_title": f"Error analyzing {image_path.name}",
                "summary": f"Failed to analyze image: {str(e)}",
                "tableDetails": {
                    "hasBenefitsTable": False,
                    "hasLimitations": False
                }
            }

    def _rename_image(self, image_path: Path, page_title: str, page_num: int) -> Tuple[Path, str]:
        """Rename image file based on its descriptive title.
        
        Args:
            image_path: Current path of the image file
            page_title: Descriptive title for the page
            page_num: Page number for ordering
            
        Returns:
            Tuple of (new image path, new image name)
        """
        try:
            # Clean the title and create new filename
            clean_title = page_title.lower().replace(" ", "_")
            # Remove any special characters that might cause issues in filenames
            clean_title = "".join(c for c in clean_title if c.isalnum() or c in "_-")
            # Add page number prefix to maintain order
            new_name = f"{str(page_num).zfill(2)}_{clean_title}.jpg"
            new_path = image_path.parent / new_name
            
            # Rename the file
            os.rename(image_path, new_path)
            self.logger.info(f"Renamed {image_path.name} to {new_name}")
            
            return new_path, new_name
            
        except Exception as e:
            self.logger.error(f"Error renaming {image_path.name}: {str(e)}")
            return image_path, image_path.name
    
    def _process_image_batch(self, image_files: List[Path], start_index: int) -> Tuple[List[ProcessedImage], List[ImageMapping]]:
        """Process a batch of images.
        
        Args:
            image_files: List of image files to process
            start_index: Starting index for page numbering
            
        Returns:
            Tuple of (analysis results, image mappings)
        """
        analysis_results: List[ProcessedImage] = []
        image_mappings: List[ImageMapping] = []
        
        for i, image_file in enumerate(image_files, start_index + 1):
            try:
                # Analyze image
                result = self._analyze_image(image_file)
                analysis_results.append(result)
                
                # Rename image based on analysis
                new_path, new_name = self._rename_image(
                    image_file,
                    result.get("page_title", f"page_{i}"),
                    i
                )
                
                # Store mapping of old to new name
                image_mappings.append({
                    "original_name": image_file.name,
                    "new_name": new_name,
                    "page_number": i,
                    "page_title": result.get("page_title", "")
                })
                
            except Exception as e:
                self.logger.error(f"Error processing {image_file.name}: {str(e)}")
        
        return analysis_results, image_mappings
    
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process images in the current state.
        
        Args:
            state: The current state containing deck_id and deck_title
            config: Runtime configuration
            
        Returns:
            Updated state with processed images
        """
        self.logger.info("Processing images")
        
        try:
            # Get parameters from state
            deck_id = state["deck_id"]
            deck_title = state["deck_title"]
            
            # Set up paths
            deck_dir = Path("src/decks") / deck_id
            pages_dir = deck_dir / "img" / "pages"
            
            if not pages_dir.exists():
                self.logger.warning(f"Pages directory not found at {pages_dir}")
                return state
            
            # Get all jpg files in order
            image_files = sorted(pages_dir.glob("*.jpg"))
            if not image_files:
                self.logger.warning("No images found to process")
                return state
                
            total_images = len(image_files)
            self.logger.info(f"Found {total_images} images to process")
            
            # Process images in batches
            processed_images: Dict[int, ProcessedImage] = {}
            
            for batch_start in range(0, total_images, self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, total_images)
                self.logger.info(f"Processing batch {batch_start//self.BATCH_SIZE + 1} (images {batch_start + 1}-{batch_end})")
                
                # Get current batch
                batch_files = image_files[batch_start:batch_end]
                
                # Process each image in the batch
                for i, image_file in enumerate(batch_files, batch_start + 1):
                    try:
                        # Analyze image
                        analysis_result = self._analyze_image(image_file)
                        
                        # Rename image based on analysis
                        new_path, new_name = self._rename_image(
                            image_file,
                            analysis_result.get("page_title", f"page_{i}"),
                            i
                        )
                        
                        # Create processed image entry
                        processed_images[i] = {
                            "page_number": i,
                            "original_name": image_file.name,
                            "new_name": new_name,
                            "page_title": analysis_result.get("page_title", ""),
                            "summary": analysis_result.get("summary", ""),
                            "table_details": analysis_result.get("tableDetails", {
                                "hasBenefitsTable": False,
                                "hasLimitations": False
                            })
                        }
                        
                    except Exception as e:
                        self.logger.error(f"Error processing {image_file.name}: {str(e)}")
            
            # Create updated state
            updated_state = dict(state)
            updated_state["processed_images"] = processed_images
            
            # Save state to file for persistence
            state_file = deck_dir / "state.json"
            with open(state_file, "w") as f:
                json.dump(updated_state, f, indent=2)
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error processing images: {str(e)}")
            raise 
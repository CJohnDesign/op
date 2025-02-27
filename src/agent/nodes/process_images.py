"""Process images node implementation.

This module contains a node that processes images in the graph.
Following Single Responsibility Principle, this node only handles image processing.
"""

from __future__ import annotations

import base64
import concurrent.futures
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langsmith import traceable

from agent.nodes.base import ParallelProcessingNode
from agent.prompts.analyze_insurance_page import ANALYZE_PAGE_PROMPT
from agent.types import AgentState, ProcessedImage
from agent.llm_config import vision_llm

class ImageMapping(TypedDict):
    original_name: str
    new_name: str
    page_number: int
    page_title: str

class ProcessImagesNode(ParallelProcessingNode[AgentState]):
    """Node for processing images in the graph.
    
    Following Single Responsibility Principle, this node only handles
    the processing of images from the deck's img directory.
    """
    
    BATCH_SIZE = 8  # Process 8 images at a time
    MAX_WORKERS = 4  # Maximum number of parallel workers
    
    def __init__(self) -> None:
        """Initialize the node with GPT-4o model."""
        super().__init__()
        # Use shared vision LLM instance
        self.model = vision_llm
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    
    @traceable(name="analyze_insurance_page_with_gpt4", with_child_runs=True)
    def _analyze_image(self, image_path: Path, config: RunnableConfig) -> ProcessedImage:
        """Analyze a single image using GPT-4o."""
        try:
            # Extract PDF name and page number from image filename
            # Modified to handle different filename formats
            pdf_source = "unknown"
            page_num = 0
            
            # Try standard format first (e.g., AccessHealthBrochure_page_001.jpg)
            parts = image_path.stem.split('_page_')
            if len(parts) == 2:
                pdf_source = parts[0]
                try:
                    page_num = int(parts[1])
                except ValueError:
                    # If we can't convert to int, try other format
                    pass
            
            # Try renamed format (e.g., 01_cover_page_...)
            if page_num == 0:
                parts = image_path.stem.split('_')
                if parts and parts[0].isdigit():
                    try:
                        page_num = int(parts[0])
                        # Use the rest as pdf_source if standard format failed
                        if pdf_source == "unknown":
                            pdf_source = "_".join(parts[1:])
                    except ValueError:
                        pass
            
            # Encode image
            image_data = self._encode_image(image_path)
            
            # Create message with image and prompt
            messages = [
                HumanMessage(
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
            ]
            
            # Get analysis from GPT-4o
            self.logger.info(f"Analyzing {image_path.name}")
            response = self.model.invoke(messages, config=config)
            
            # Parse JSON response
            try:
                analysis = json.loads(response.content)
                
                # Create ProcessedImage structure
                processed_image = {
                    "page_number": page_num,
                    "original_name": image_path.name,
                    "original_path": f"img/pages/{image_path.name}",
                    "new_name": image_path.name,  # Will be updated by rename
                    "new_path": f"img/pages/{image_path.name}",  # Will be updated by rename
                    "page_title": analysis.get("page_title", ""),
                    "summary": analysis.get("summary", ""),
                    "tableDetails": analysis.get("tableDetails", {
                        "hasBenefitsComparisonTable": False,
                        "hasLimitations": False
                    }),
                    "pdf_source": pdf_source,
                    "global_page_num": page_num
                }
                
                # Rename the file based on analysis
                new_path, new_name = self._rename_image(
                    image_path,
                    processed_image["page_title"],
                    page_num
                )
                
                # Update paths after rename
                processed_image["new_name"] = new_name
                processed_image["new_path"] = f"img/pages/{new_name}"
                
                return processed_image
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing JSON response: {str(e)}")
                return self._create_error_analysis(image_path.name, pdf_source, page_num)
                
        except Exception as e:
            self.logger.error(f"Error analyzing image: {str(e)}")
            return self._create_error_analysis(image_path.name, "unknown", 0)

    def _create_error_analysis(self, image_name: str, pdf_source: str, page_num: int) -> ProcessedImage:
        """Create a standardized error analysis result."""
        return {
            "page_number": page_num,
            "original_name": image_name,
            "original_path": f"img/pages/{image_name}",
            "new_name": image_name,
            "new_path": f"img/pages/{image_name}",
            "page_title": f"Error analyzing {image_name}",
            "summary": "Failed to analyze image",
            "tableDetails": {
                "hasBenefitsComparisonTable": False,
                "hasLimitations": False
            },
            "pdf_source": pdf_source,
            "global_page_num": page_num
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
    
    @traceable(name="process_image_batch", with_child_runs=True)
    def _process_image_batch(self, batch_items: List[Tuple[int, ProcessedImage, Path]], config: RunnableConfig) -> List[Tuple[int, ExtractedTable, ProcessedImage]]:
        """Process a batch of images."""
        results = []
        
        # Process images in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_item = {
                executor.submit(self._analyze_image, item[2], config): item 
                for item in batch_items
            }
            
            for future in concurrent.futures.as_completed(future_to_item):
                try:
                    page_num, page_data, image_path = future_to_item[future]
                    result = future.result()
                    
                    if result:
                        results.append((page_num, result, page_data))
                        self.logger.info(f"Successfully analyzed {image_path.name}")
                    else:
                        self.logger.warning(f"No analysis results for {image_path.name}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing batch item: {str(e)}")
        
        return results
    
    @traceable(name="process_images_with_gpt4", with_child_runs=True)
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process images in the current state."""
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
            
            # Get all jpg files and sort by page number
            # Modified to handle filenames without "_page_" separator
            def get_page_num(p):
                # First try to extract from standard format (e.g., AccessHealthBrochure_page_001.jpg)
                parts = p.stem.split('_page_')
                if len(parts) == 2 and parts[1].isdigit():
                    return int(parts[1])
                
                # Then try to extract from renamed format (e.g., 01_cover_page_...)
                parts = p.stem.split('_')
                if parts and parts[0].isdigit():
                    return int(parts[0])
                
                # Default to 0 if no page number found
                return 0
                
            image_files = sorted(
                pages_dir.glob("*.jpg"),
                key=get_page_num
            )
            
            if not image_files:
                self.logger.warning("No images found to process")
                return state
                
            total_images = len(image_files)
            self.logger.info(f"Found {total_images} images to process")
            
            # Process images in batches
            processed_images: Dict[str, ProcessedImage] = {}
            
            for batch_start in range(0, total_images, self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, total_images)
                batch_files = image_files[batch_start:batch_end]
                
                self.logger.info(f"Processing batch {batch_start//self.BATCH_SIZE + 1}")
                
                # Process batch
                results = self._process_image_batch(
                    [(i, None, f) for i, f in enumerate(batch_files, batch_start + 1)],
                    config
                )
                
                # Add results to processed_images
                for page_num, result, _ in results:
                    processed_images[str(page_num)] = result
            
            # Update state
            updated_state = dict(state)
            updated_state["processed_images"] = processed_images
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error processing images: {str(e)}")
            raise 
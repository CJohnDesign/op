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
    
    @traceable(name="analyze_insurance_page_with_gpt4")
    def _analyze_image(self, image_path: Path, config: RunnableConfig) -> ProcessedImage:
        """Analyze a single image using GPT-4o.
        
        Args:
            image_path: Path to the image file
            config: Runtime configuration for tracing context
            
        Returns:
            Analysis results as a ProcessedImage
        """
        try:
            # Extract PDF name from image filename
            parts = image_path.stem.split('_page_')
            pdf_source = parts[0] if len(parts) == 2 else "unknown"
            page_num = int(parts[1]) if len(parts) == 2 else 0
            
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
            self.logger.info(f"Analyzing {image_path.name} (PDF: {pdf_source}, Page: {page_num})")
            response = self.model.invoke(messages, config=config)
            
            # Parse JSON response
            try:
                # Extract JSON from the response
                response_text = response.content
                analysis = json.loads(response_text)
                
                # Add PDF source information
                analysis["pdf_source"] = pdf_source
                analysis["global_page_num"] = page_num
                return analysis
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing JSON response for {image_path.name}: {str(e)}")
                self.logger.error(f"Raw response: {response_text}")
                return {
                    "page_title": f"Error analyzing {image_path.name}",
                    "summary": "Failed to parse analysis results",
                    "tableDetails": {
                        "hasBenefitsComparisonTable": False,
                        "hasLimitations": False
                    },
                    "pdf_source": pdf_source,
                    "global_page_num": page_num
                }
        except Exception as e:
            self.logger.error(f"Error analyzing {image_path.name}: {str(e)}")
            return {
                "page_title": f"Error analyzing {image_path.name}",
                "summary": f"Failed to analyze image: {str(e)}",
                "tableDetails": {
                    "hasBenefitsComparisonTable": False,
                    "hasLimitations": False
                },
                "pdf_source": "unknown",
                "global_page_num": 0
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
    
    def _process_image_batch(self, batch_items: List[Tuple[int, ProcessedImage, Path]], config: RunnableConfig) -> List[Tuple[int, ExtractedTable, ProcessedImage]]:
        """Process a batch of images.
        
        Args:
            batch_items: List of (index, page_data, image_path) tuples to process
            config: Runtime configuration for tracing
            
        Returns:
            List of (index, analysis_result, page_data) tuples
        """
        results = []
        
        # Submit all tasks
        future_to_item = {
            self.executor.submit(self._analyze_image, item[2], config): item 
            for item in batch_items
        }
        
        # Collect results as they complete
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
            
            # Get all jpg files and sort by PDF name and slide number
            image_files = list(pages_dir.glob("*.jpg"))
            if not image_files:
                self.logger.warning("No images found to process")
                return state
                
            # Sort files by PDF name and page number
            def get_sort_key(file_path):
                # Extract PDF name and page number from filename
                # Format is "{pdf_name}_page_{number}.jpg"
                parts = file_path.stem.split('_page_')
                if len(parts) != 2:
                    return ("", 0)  # Handle legacy filenames
                pdf_name, page_num = parts
                return (int(page_num))  # Sort by global page number only since they're now continuous
            
            image_files.sort(key=get_sort_key)
            total_images = len(image_files)
            self.logger.info(f"Found {total_images} images to process")
            
            # Process images in batches with parallel execution
            processed_images: Dict[str, ProcessedImage] = {}  # Change to string keys
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                # Submit batch processing tasks
                future_to_batch = {}
                for batch_start in range(0, total_images, self.BATCH_SIZE):
                    batch_end = min(batch_start + self.BATCH_SIZE, total_images)
                    batch_files = image_files[batch_start:batch_end]
                    
                    self.logger.info(f"Submitting batch {batch_start//self.BATCH_SIZE + 1} (images {batch_start + 1}-{batch_end})")
                    future = executor.submit(self._process_image_batch, [(i, None, f) for i, f in enumerate(batch_files, batch_start + 1)], config)
                    future_to_batch[future] = (batch_start, batch_end)
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_start, batch_end = future_to_batch[future]
                    try:
                        results = future.result()
                        
                        # Add results to processed_images
                        for page_num, result, _ in results:  # Properly unpack all three values
                            # Rename the image file
                            original_path = image_files[page_num - 1]
                            new_path, new_name = self._rename_image(
                                original_path,
                                result.get("page_title", f"page_{page_num}"),
                                page_num
                            )
                            
                            processed_images[str(page_num)] = {  # Convert to string key
                                "page_number": page_num,
                                "original_name": original_path.name,
                                "original_path": f"img/pages/{original_path.name}",
                                "new_name": new_name,
                                "new_path": f"img/pages/{new_name}",
                                "page_title": result.get("page_title", ""),
                                "summary": result.get("summary", ""),
                                "table_details": result.get("tableDetails", {
                                    "hasBenefitsComparisonTable": False,
                                    "hasLimitations": False
                                }),
                                "pdf_source": result.get("pdf_source", "unknown"),
                                "global_page_num": result.get("global_page_num", 0)
                            }
                            self.logger.info(f"Processed and renamed image {original_path.name} to {new_name}")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing batch {batch_start//self.BATCH_SIZE + 1}: {str(e)}")
            
            # Create updated state by deep merging with existing state
            updated_state = dict(state)  # Start with existing state
            if "processed_images" in updated_state and isinstance(updated_state["processed_images"], dict):
                updated_state["processed_images"].update(processed_images)  # Update existing processed images
            else:
                updated_state["processed_images"] = processed_images  # Add new processed images
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error processing images: {str(e)}")
            raise 
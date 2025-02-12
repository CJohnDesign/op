"""Extract tables node implementation.

This module contains a node that extracts tables from analyzed pages in the graph.
Following Single Responsibility Principle, this node only handles table extraction.
"""

from __future__ import annotations

import base64
import concurrent.futures
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from agent.nodes.base import ParallelProcessingNode
from agent.prompts.extract_tables import EXTRACT_TABLES_PROMPT
from agent.types import AgentState, ExtractedTable, ProcessedImage
from agent.llm_config import vision_llm


class ExtractTablesNode(ParallelProcessingNode[AgentState]):
    """Node for extracting tables from analyzed pages.
    
    Following Single Responsibility Principle, this node only handles
    the extraction and processing of tables from analyzed pages.
    """
    
    BATCH_SIZE = 4  # Process 4 tables at a time
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
    
    def _find_image_path(self, page_number: int, pages_dir: Path, processed_images: Dict[int, ProcessedImage]) -> Optional[Path]:
        """Find the correct image path using processed images.
        
        Args:
            page_number: The page number to find
            pages_dir: Directory containing the images
            processed_images: Dictionary of processed images keyed by page number
            
        Returns:
            Path to the image if found, None otherwise
        """
        if page_number in processed_images:
            return pages_dir / processed_images[page_number]["new_name"]
        return None
    
    @traceable(name="extract_tables_with_gpt4")
    def _extract_table(self, image_path: Path, config: RunnableConfig) -> Dict[str, Any]:
        """Extract table from a single image using GPT-4o."""
        try:
            # Encode image
            image_data = self._encode_image(image_path)
            
            # Create message with image and prompt
            messages = [
                HumanMessage(
                    content=[
                        {"type": "text", "text": EXTRACT_TABLES_PROMPT},
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
            
            # Get table extraction from GPT-4o
            self.logger.info(f"Extracting tables from {image_path.name}")
            response = self.model.invoke(messages, config=config)  # Pass config for tracing context
            
            # Parse JSON response
            try:
                response_text = response.content
                return json.loads(response_text)
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing JSON response for {image_path.name}: {str(e)}")
                self.logger.error(f"Raw response: {response_text}")
                return {"tables": []}
                
        except Exception as e:
            self.logger.error(f"Error extracting tables from {image_path.name}: {str(e)}")
            return {"tables": []}
    
    def _process_table_item(self, item: Tuple[int, ProcessedImage, Path]) -> Optional[Tuple[int, ExtractedTable, ProcessedImage]]:
        """Process a single table item.
        
        Args:
            item: Tuple of (index, page, image_path)
            
        Returns:
            Tuple of (index, extracted_table, page) if successful, None if failed
        """
        index, page, image_path = item
        try:
            # Extract table data
            table_data = self._extract_table(image_path, None)
            extracted_table = {
                "page_number": index + 1,
                "page_title": page.get("page_title", ""),
                "table_data": table_data
            }
            self.logger.info(f"Found and processed table from {image_path.name}")
            return (index, extracted_table, page)
        except Exception as e:
            self.logger.error(f"Error processing table from {image_path.name}: {str(e)}")
            return None
    
    def _process_table_batch(self, batch_items: List[Tuple[int, ProcessedImage, Path]], config: RunnableConfig) -> List[Tuple[int, ExtractedTable, ProcessedImage]]:
        """Process a batch of table items in parallel.
        
        Args:
            batch_items: List of (index, page_data, image_path) tuples to process
            config: Runtime configuration for tracing
            
        Returns:
            List of (index, extracted_table, page_data) tuples
        """
        results = []
        
        # Submit all tasks
        future_to_item = {
            self.executor.submit(self._extract_table, item[2], config): item 
            for item in batch_items
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_item):
            try:
                page_num, page_data, image_path = future_to_item[future]
                table_data = future.result()
                
                if table_data.get("tables"):
                    results.append((
                        page_num,
                        {"page_number": page_num, "tables": table_data["tables"]},
                        page_data
                    ))
                    self.logger.info(f"Extracted {len(table_data['tables'])} tables from {image_path.name}")
                else:
                    self.logger.info(f"No tables found in {image_path.name}")
                    
            except Exception as e:
                self.logger.error(f"Error processing batch item: {str(e)}")
        
        return results
    
    @traceable(name="extract_tables_with_gpt4", with_child_runs=True)
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the analyzed data to extract tables."""
        self.logger.info("Extracting tables from analyzed pages")
        
        try:
            # Get parameters from state
            deck_id = state["deck_id"]
            processed_images = state.get("processed_images", {})
            
            if not processed_images:
                self.logger.warning("No processed images found in state")
                return state
            
            # Set up paths
            deck_dir = Path("src/decks") / deck_id
            pages_dir = deck_dir / "img" / "pages"
            
            if not pages_dir.exists():
                self.logger.warning(f"Pages directory not found at {pages_dir}")
                return state
            
            # Find pages with tables
            table_items = []
            for page_num, page_data in processed_images.items():
                if page_data.get("table_details", {}).get("hasBenefitsComparisonTable", False):
                    # Construct image path with .jpg extension
                    image_path = pages_dir / f"{page_data['new_name']}.jpg"
                    self.logger.info(f"Found table in page {page_num}, looking for image at {image_path}")
                    if image_path.exists():
                        table_items.append((page_num, page_data, image_path))
                    else:
                        self.logger.warning(f"Image file not found at {image_path}")
            
            self.logger.info(f"Found {len(table_items)} pages with tables to process")
            
            # Process tables in batches with parallel execution
            extracted_tables: Dict[int, ExtractedTable] = {}
            
            # Process batches
            for batch_start in range(0, len(table_items), self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, len(table_items))
                batch_items = table_items[batch_start:batch_end]
                
                self.logger.info(f"Processing batch {batch_start//self.BATCH_SIZE + 1} (pages {batch_start + 1}-{batch_end})")
                
                # Process batch
                results = self._process_table_batch(batch_items, config)
                
                # Extract tables and pages
                for page_num, table, page_data in results:
                    extracted_tables[page_num] = table
                    self.logger.info(f"Extracted {len(table['tables'])} tables from page {page_num}")
            
            # Create updated state by deep merging with existing state
            updated_state = dict(state)  # Start with existing state
            if "extracted_tables" in updated_state and isinstance(updated_state["extracted_tables"], dict):
                updated_state["extracted_tables"].update(extracted_tables)  # Update existing tables
            else:
                updated_state["extracted_tables"] = extracted_tables  # Add new tables
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error extracting tables: {str(e)}")
            raise 
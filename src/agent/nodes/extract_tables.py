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
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.extract_tables import EXTRACT_TABLES_PROMPT
from agent.types import AgentState, ExtractedTable, ProcessedImage


class ExtractTablesNode(BaseNode[AgentState]):
    """Node for extracting tables from analyzed pages.
    
    Following Single Responsibility Principle, this node only handles
    the extraction and processing of tables from analyzed pages.
    """
    
    BATCH_SIZE = 4  # Process 4 tables at a time
    MAX_WORKERS = 4  # Maximum number of parallel workers
    
    def __init__(self) -> None:
        """Initialize the node with GPT-40 model."""
        super().__init__()
        self.model = ChatOpenAI(
            model="gpt-4o",
            max_tokens=4096,
            temperature=0
        )
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS)
    
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
    
    def _extract_table(self, image_path: Path) -> Dict[str, Any]:
        """Extract table from a single image using GPT-4o.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing tables array or error information
        """
        try:
            # Encode image
            image_data = self._encode_image(image_path)
            
            # Create message with image
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": EXTRACT_TABLES_PROMPT
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
            
            # Get table extraction from GPT-4o
            self.logger.info(f"Extracting tables from {image_path.name}")
            response = self.model.invoke([message])
            
            # Parse JSON response
            try:
                response_text = response.content
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    parsed_data = json.loads(json_str)
                    
                    if "tables" in parsed_data:
                        self.logger.info(f"Successfully extracted tables from {image_path.name}")
                        return parsed_data
                    else:
                        self.logger.warning(f"No tables found in {image_path.name}")
                        return {"tables": []}
                else:
                    self.logger.error(f"No JSON object found in response for {image_path.name}")
                    return {"tables": []}
                    
            except Exception as e:
                self.logger.error(f"Error parsing response for {image_path.name}: {str(e)}")
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
            table_data = self._extract_table(image_path)
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
    
    def _process_table_batch(self, items: List[Tuple[int, ProcessedImage, Path]]) -> Tuple[List[ExtractedTable], List[ProcessedImage]]:
        """Process a batch of table items in parallel."""
        extracted_tables: List[ExtractedTable] = []
        pages_with_tables: List[ProcessedImage] = []
        
        # Submit all tasks
        future_to_item = {
            self.executor.submit(self._process_table_item, item): item 
            for item in items
        }
        
        # Collect results as they complete
        results = []
        for future in concurrent.futures.as_completed(future_to_item):
            result = future.result()
            if result is not None:
                results.append(result)
        
        # Sort results by original index to maintain order
        results.sort(key=lambda x: x[0])
        
        # Extract tables and pages
        for _, table, page in results:
            extracted_tables.append(table)
            pages_with_tables.append(page)
        
        return extracted_tables, pages_with_tables
    
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
                    image_path = pages_dir / page_data["new_name"]
                    if image_path.exists():
                        table_items.append((page_num, page_data, image_path))
            
            self.logger.info(f"Found {len(table_items)} pages with tables to process")
            
            # Process tables in batches with parallel execution
            extracted_tables: Dict[int, ExtractedTable] = {}
            
            # Process batches
            for batch_start in range(0, len(table_items), self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, len(table_items))
                batch_items = table_items[batch_start:batch_end]
                
                self.logger.info(f"Processing batch {batch_start//self.BATCH_SIZE + 1} (pages {batch_start + 1}-{batch_end})")
                
                # Submit tasks
                future_to_item = {
                    self.executor.submit(self._extract_table, item[2]): item 
                    for item in batch_items
                }
                
                # Collect results
                for future in concurrent.futures.as_completed(future_to_item):
                    try:
                        page_num, _, image_path = future_to_item[future]
                        table_data = future.result()
                        
                        if table_data.get("tables"):
                            extracted_tables[page_num] = {
                                "page_number": page_num,
                                "tables": table_data["tables"]
                            }
                            self.logger.info(f"Extracted {len(table_data['tables'])} tables from page {page_num}")
                        else:
                            self.logger.info(f"No tables found in page {page_num}")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num}: {str(e)}")
            
            # Update state
            updated_state = dict(state)
            updated_state["extracted_tables"] = extracted_tables
            
            # Save state
            state_file = deck_dir / "state.json"
            with open(state_file, "w") as f:
                json.dump(updated_state, f, indent=2)
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error extracting tables: {str(e)}")
            raise 
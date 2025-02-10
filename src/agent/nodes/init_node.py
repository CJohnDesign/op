"""Initialization node implementation.

This module contains a node that initializes the deck information in the graph state.
Following Single Responsibility Principle, this node only handles initial deck setup.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from pdf2image import convert_from_path
from PIL import Image

from agent.nodes.base import BaseNode
from agent.types import AgentState, DeckInfo


class InitNode(BaseNode[AgentState]):
    """Node for initializing deck information in the graph.
    
    Following Single Responsibility Principle, this node only handles
    the initialization of deck information from input arguments.
    """
    
    def _read_file_content(self, file_path: Path) -> str:
        """Read file content and return as a single string with \n for newlines.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File content as a string with preserved newlines
        """
        if not file_path.exists():
            self.logger.warning(f"File {file_path} not found")
            return ""
            
        try:
            content = file_path.read_text()
            # Replace literal newlines with \n string
            return content.replace('\n', '\\n')
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {str(e)}")
            return ""
    
    def _convert_pdfs_to_images(self, deck_dir: Path) -> None:
        """Convert all PDFs in img/pdfs to images in img/pages.
        
        Args:
            deck_dir: Path to the deck directory
        """
        # Set up paths
        pdf_dir = deck_dir / "img" / "pdfs"
        pages_dir = deck_dir / "img" / "pages"
        
        # Create pages directory if it doesn't exist
        pages_dir.mkdir(exist_ok=True)
        
        # Find all PDFs
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            self.logger.info("No PDF files found in img/pdfs")
            return
            
        self.logger.info(f"Found {len(pdf_files)} PDF files to convert")
        
        # Process each PDF
        for pdf_file in pdf_files:
            try:
                self.logger.info(f"Converting {pdf_file.name}")
                
                # Convert PDF to images
                images = convert_from_path(pdf_file)
                
                # Save each page
                for i, image in enumerate(images):
                    # Format page number with leading zeros
                    page_num = str(i + 1).zfill(2)
                    output_file = pages_dir / f"slide_{page_num}.jpg"
                    
                    # Save as high-quality JPEG
                    image.save(output_file, "JPEG", quality=95)
                    self.logger.info(f"Saved page {i+1} as {output_file.name}")
                    
            except Exception as e:
                self.logger.error(f"Error converting {pdf_file.name}: {str(e)}")
    
    @traceable(name="init_deck")
    def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Initialize the deck information in the state.
        
        Args:
            state: The current state containing deck_id and deck_title
            config: Runtime configuration
            
        Returns:
            Validated state
        """
        self.logger.info("Initializing deck information")
        
        try:
            # Get parameters from state
            deck_id = state["deck_id"]
            deck_title = state["deck_title"]
            
            if not deck_id or not deck_title:
                raise ValueError(
                    "Missing required deck information. "
                    "Please provide both deck_id and deck_title."
                )
            
            # Log the deck information
            self.logger.info("Deck Information:")
            self.logger.info(f"  ID: {deck_id}")
            self.logger.info(f"  Title: {deck_title}")
            
            # Set up paths
            src_dir = Path("src/decks/FEN_TEMPLATE")
            dest_dir = Path("src/decks") / deck_id
            
            # Check if source exists
            if not src_dir.exists():
                raise ValueError(f"Template directory not found at {src_dir}")
                
            # Check if destination already exists
            if dest_dir.exists():
                self.logger.warning(f"Destination directory {dest_dir} already exists. Skipping copy.")
            else:
                self.logger.info(f"Copying template from {src_dir} to {dest_dir}")
                shutil.copytree(src_dir, dest_dir)
                self.logger.info("Template directory copied successfully")
            
            # Convert PDFs to images
            self.logger.info("Converting PDF files to images")
            self._convert_pdfs_to_images(dest_dir)
            
            # Read markdown files
            slides_content = self._read_file_content(dest_dir / "slides.md")
            script_content = self._read_file_content(dest_dir / "audio" / "audio_script.md")
            instructions = self._read_file_content(dest_dir / "instructions.md")
            
            # Create state.json with deck information
            state_file = dest_dir / "state.json"
            state_data = {
                "deck_info": {
                    "deck_id": deck_id,
                    "deck_title": deck_title
                },
                "initial_deck": {
                    "slides": slides_content,
                    "scripts": script_content,
                    "instructions": instructions
                }
            }
            
            # Create updated state
            updated_state = dict(state)
            updated_state.update(state_data)  # Merge the new data into state
            
            # Save to file
            with open(state_file, 'w') as f:
                json.dump(updated_state, f, indent=2)
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error initializing deck information: {str(e)}")
            raise 
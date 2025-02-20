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
import time
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
    
    def _setup_directory_structure(self, src_dir: Path, dest_dir: Path, deck_id: str) -> None:
        """Set up the directory structure for the new deck.
        
        Args:
            src_dir: Source template directory
            dest_dir: Destination directory
            deck_id: ID of the current deck
        """
        # Create base directories
        dest_dir.mkdir(parents=True, exist_ok=True)
        img_dir = dest_dir / "img"
        img_dir.mkdir(exist_ok=True)
        
        # Create empty pages directory
        pages_dir = img_dir / "pages"
        pages_dir.mkdir(exist_ok=True)
        self.logger.info("Created empty pages directory")
        
        # Copy logos directory with all contents
        src_logos = src_dir / "img" / "logos"
        dest_logos = img_dir / "logos"
        if src_logos.exists():
            if dest_logos.exists():
                shutil.rmtree(dest_logos)
            shutil.copytree(src_logos, dest_logos)
            self.logger.info("Copied logos directory with all contents")
        else:
            dest_logos.mkdir(exist_ok=True)
            self.logger.warning("Source logos directory not found, created empty directory")
            
        # Copy only the relevant PDF
        src_pdf_dir = src_dir / "img" / "pdfs" / deck_id
        if src_pdf_dir.exists():
            dest_pdf_dir = img_dir / "pdfs"
            dest_pdf_dir.mkdir(exist_ok=True)
            
            # Copy all PDFs from the deck-specific folder
            pdf_files = list(src_pdf_dir.glob("*.pdf"))
            if pdf_files:
                for pdf_file in pdf_files:
                    shutil.copy2(pdf_file, dest_pdf_dir / pdf_file.name)
                self.logger.info(f"Copied {len(pdf_files)} PDF files for deck {deck_id}")
            else:
                self.logger.warning(f"No PDF files found for deck {deck_id}")
        else:
            self.logger.warning(f"PDF directory not found for deck {deck_id}")
    
    def _get_instructions(self, deck_id: str, template_dir: Path) -> str:
        """Get instructions for the deck.
        
        Looks for deck-specific instructions first, falls back to default if not found.
        
        Args:
            deck_id: ID of the current deck
            template_dir: Path to the template directory
            
        Returns:
            Instructions content as string
        """
        # Check for deck-specific instructions
        instructions_dir = template_dir / "instructions"
        specific_instructions = instructions_dir / f"{deck_id}_instructions.md"
        
        if specific_instructions.exists():
            self.logger.info(f"Using deck-specific instructions: {specific_instructions}")
            return self._read_file_content(specific_instructions)
            
        # Fall back to default instructions if specific not found
        default_instructions = template_dir / "instructions.md"
        if default_instructions.exists():
            self.logger.warning(f"No deck-specific instructions found for {deck_id}, using default")
            return self._read_file_content(default_instructions)
            
        self.logger.error("No instructions found")
        return ""

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
            return content  # Return content as-is, preserving newlines
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
        
        # Find all PDFs in the pdfs directory
        pdf_files = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
        if not pdf_files:
            self.logger.info(f"No PDF files found in {pdf_dir}")
            return
            
        self.logger.info(f"Found {len(pdf_files)} PDF files to convert")
        
        # Track global page number across all PDFs
        global_page_num = 1
        
        # Process each PDF
        for pdf_file in pdf_files:
            try:
                self.logger.info(f"Converting {pdf_file.name}")
                
                # Get PDF name without extension for use in output filename
                pdf_name = pdf_file.stem
                
                # Add a small delay before conversion to ensure PDF is loaded
                time.sleep(1)  # 1 second delay
                
                # Convert PDF to images with dpi=300 for better quality
                images = convert_from_path(pdf_file, dpi=300)
                
                # Save each page
                for i, image in enumerate(images):
                    # Format global page number with leading zeros
                    page_num = str(global_page_num).zfill(3)  # Use 3 digits for larger numbers
                    # Include PDF name in output filename to prevent overwriting
                    output_file = pages_dir / f"{pdf_name}_page_{page_num}.jpg"
                    
                    # Add a small delay before saving to ensure proper rendering
                    time.sleep(0.5)  # 0.5 second delay
                    
                    # Save as high-quality JPEG
                    image.save(output_file, "JPEG", quality=95)
                    self.logger.info(f"Saved page {i+1} from {pdf_name} as {output_file.name}")
                    
                    # Increment global page counter
                    global_page_num += 1
                    
                # Add a delay after processing each PDF
                time.sleep(1)  # 1 second delay
                    
            except Exception as e:
                self.logger.error(f"Error converting {pdf_file.name}: {str(e)}")
    
    def _copy_instruction_file(self, deck_id: str, src_dir: Path, dest_dir: Path) -> None:
        """Copy the appropriate instruction file to the destination.
        
        Args:
            deck_id: ID of the current deck
            src_dir: Source template directory
            dest_dir: Destination directory
        """
        # Set up paths
        src_instructions_dir = src_dir / "instructions"
        dest_instructions_dir = dest_dir / "instructions"
        dest_instructions_dir.mkdir(exist_ok=True)
        
        # Determine which instruction file to use
        specific_instructions = src_instructions_dir / f"{deck_id}_instructions.md"
        default_instructions = src_dir / "instructions.md"
        
        if specific_instructions.exists():
            # Copy deck-specific instructions
            dest_file = dest_instructions_dir / f"{deck_id}_instructions.md"
            shutil.copy2(specific_instructions, dest_file)
            self.logger.info(f"Copied deck-specific instructions: {specific_instructions.name}")
        elif default_instructions.exists():
            # Copy default instructions
            dest_file = dest_instructions_dir / "instructions.md"
            shutil.copy2(default_instructions, dest_file)
            self.logger.warning(f"No deck-specific instructions found, copied default instructions")
        else:
            self.logger.error("No instructions file found to copy")

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
                
            # Set up directory structure
            self._setup_directory_structure(src_dir, dest_dir, deck_id)
            
            # Copy non-image template files
            for item in src_dir.iterdir():
                if item.name not in ["img", "instructions"]:
                    dest_item = dest_dir / item.name
                    if item.is_file():
                        shutil.copy2(item, dest_item)
                    elif item.is_dir():
                        if dest_item.exists():
                            shutil.rmtree(dest_item)
                        shutil.copytree(item, dest_item)
            
            # Copy appropriate instruction file
            self._copy_instruction_file(deck_id, src_dir, dest_dir)
            
            # Convert PDFs to images
            self.logger.info("Converting PDF files to images")
            self._convert_pdfs_to_images(dest_dir)
            
            # Read markdown files
            slides_content = self._read_file_content(dest_dir / "slides.md")
            script_content = self._read_file_content(dest_dir / "audio" / "audio_script.md")
            
            # Get instructions using new method
            instructions = self._get_instructions(deck_id, src_dir)
            
            # Create state data
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
            
            # Create updated state by deep merging with existing state
            updated_state = dict(state)  # Start with existing state
            for key, value in state_data.items():
                if key in updated_state and isinstance(updated_state[key], dict):
                    updated_state[key].update(value)  # Update nested dicts
                else:
                    updated_state[key] = value  # Add new keys
            
            # Save state to file
            state_file = dest_dir / "state.json"
            with open(state_file, "w") as f:
                json.dump(updated_state, f, indent=2)
            
            self.logger.info(f"Initialized state saved to {state_file}")
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error initializing deck information: {str(e)}")
            raise 
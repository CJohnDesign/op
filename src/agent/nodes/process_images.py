"""Process images node implementation.

This module contains a node that processes images in the graph.
Following Single Responsibility Principle, this node only handles image processing.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from agent.nodes.base import BaseNode
from agent.prompts.analyze_insurance_page import ANALYZE_PAGE_PROMPT
from agent.types import AgentState


class ProcessImagesNode(BaseNode[AgentState]):
    """Node for processing images in the graph.
    
    Following Single Responsibility Principle, this node only handles
    the processing of images from the deck's img directory.
    """
    
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
    
    def _analyze_image(self, image_path: Path) -> Dict[str, Any]:
        """Analyze a single image using GPT-4.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Analysis results as a dictionary
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
                
            self.logger.info(f"Found {len(image_files)} images to process")
            
            # Process each image
            analysis_results = []
            for image_file in image_files:
                try:
                    result = self._analyze_image(image_file)
                    analysis_results.append(result)
                except Exception as e:
                    self.logger.error(f"Error analyzing {image_file.name}: {str(e)}")
            
            # Update state with results
            state_file = deck_dir / "state.json"
            if state_file.exists():
                with open(state_file) as f:
                    state_data = json.load(f)
            else:
                state_data = {}
            
            # Add analysis results
            state_data["page_analysis"] = analysis_results
            
            # Save updated state
            self.logger.info("Saving analysis results to state.json")
            with open(state_file, "w") as f:
                json.dump(state_data, f, indent=2)
            
            # Return state
            return state
            
        except Exception as e:
            self.logger.error(f"Error processing images: {str(e)}")
            raise 
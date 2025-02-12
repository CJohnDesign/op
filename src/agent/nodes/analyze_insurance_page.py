import json
from pathlib import Path
from typing import Dict, Any
from langchain.schema import HumanMessage
from langchain.schema import RunnableConfig
from langchain.schema import traceable
from agent.prompts.analyze_insurance_page import ANALYZE_PAGE_PROMPT

class AnalyzeInsurancePage:
    @traceable(name="analyze_insurance_page_with_gpt4")
    def _analyze_page(self, image_path: Path, config: RunnableConfig) -> Dict[str, Any]:
        """Analyze a single insurance page using GPT-4o."""
        try:
            # Encode image
            image_data = self._encode_image(image_path)
            
            # Create message with image and prompt
            messages = [
                HumanMessage(
                    content=[
                        {"type": "text", "text": ANALYZE_PAGE_PROMPT},
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
            self.logger.info(f"Analyzing page {image_path.name}")
            response = self.model.invoke(messages, config=config)  # Pass config for tracing context
            
            # Parse JSON response
            try:
                response_text = response.content
                return json.loads(response_text)
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing JSON response for {image_path.name}: {str(e)}")
                self.logger.error(f"Raw response: {response_text}")
                return {"analysis": {}}
                
        except Exception as e:
            self.logger.error(f"Error analyzing page {image_path.name}: {str(e)}")
            return {"analysis": {}}

    def process(self, state_data: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
        """Process the images in the state data."""
        try:
            # Get image paths from state
            image_paths = state_data.get("image_paths", [])
            if not image_paths:
                self.logger.warning("No images found in state data")
                return state_data
            
            # Process each image
            analyses = []
            for index, image_path in enumerate(image_paths):
                try:
                    # Analyze page
                    analysis = self._analyze_page(image_path, config)
                    analysis["page_number"] = index + 1
                    analyses.append(analysis)
                    
                except Exception as e:
                    self.logger.error(f"Error processing image {image_path}: {str(e)}")
                    analyses.append({"page_number": index + 1, "analysis": {}})
            
            # Update state with analyses
            state_data["page_analyses"] = analyses
            return state_data
            
        except Exception as e:
            self.logger.error(f"Error in process: {str(e)}")
            return state_data 
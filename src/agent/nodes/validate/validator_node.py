"""Validator node for validating slide and script content."""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage
from langchain_core.runnables import RunnableConfig
import json
import logging
from datetime import datetime

from agent.nodes.base import BaseNode
from agent.types import AgentState
from agent.prompts.validator import VALIDATION_PROMPT

logger = logging.getLogger(__name__)

class ValidatorNode(BaseNode[AgentState]):
    """Node for validating slide and script content."""

    def __init__(self, model: Optional[ChatOpenAI] = None):
        """Initialize the validator node.
        
        Args:
            model: The language model to use for validation.
        """
        super().__init__()
        self.model = model or ChatOpenAI(model="gpt-4o", temperature=0)

    def get_current_time(self) -> str:
        """Get the current time in ISO format.
        
        Returns:
            Current time as string in ISO format.
        """
        return datetime.now().isoformat()

    def _validate_json_response(self, response: str) -> Dict[str, Any]:
        """Validate the JSON response from the model.
        
        Args:
            response: The JSON response string.
            
        Returns:
            The validated JSON response.
            
        Raises:
            ValueError: If the response is invalid.
        """
        try:
            # Log raw response for debugging
            logger.debug(f"Raw response: {response}")
            
            # Clean up response if needed
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Try to parse JSON
            data = json.loads(cleaned_response)
            logger.debug(f"Parsed data: {data}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            logger.error(f"Cleaned response: {cleaned_response}")
            raise ValueError(f"Invalid JSON response: {e}")

        # Check required top-level keys
        required_keys = {"is_valid", "slide", "script"}
        if not all(key in data for key in required_keys):
            logger.error(f"Missing required keys. Found keys: {list(data.keys())}")
            raise ValueError("Missing required top-level keys")

        # Validate each component
        for component in ["slide", "script"]:
            result = data[component]
            if not isinstance(result, dict):
                raise ValueError(f"{component} validation result must be a dictionary")

            required_result_keys = {"is_valid", "severity"}
            if not all(key in result for key in required_result_keys):
                raise ValueError(f"Missing required keys in {component} validation result")

            # Check suggested_fixes field is present if is_valid is false
            if not result["is_valid"] and "suggested_fixes" not in result:
                raise ValueError(f"Missing suggested_fixes field for invalid {component}")

        return data

    def _format_page(self, page: Dict[str, Any]) -> str:
        """Format the page content for validation.
        
        Args:
            page: The page content to format.
            
        Returns:
            The formatted content string.
        """
        # Extract slide content
        slide = page.get("slide", {})
        if isinstance(slide, dict):
            slide_content = slide.get("content", "")
        else:
            slide_content = str(slide)

        # Extract script content
        script = page.get("script", {})
        if isinstance(script, dict):
            script_content = script.get("content", "")
        else:
            script_content = str(script)

        # Format content
        formatted_content = [
            "SLIDE CONTENT:",
            slide_content,
            "=== CONTENT SEPARATOR ===",
            "SCRIPT CONTENT:",
            script_content
        ]
        
        return "\n".join(formatted_content)

    def _act_validate(self, page: Dict[str, Any], page_attempts: int, current_page_index: int) -> Dict[str, Any]:
        """Perform validation on a page.
        
        Args:
            page: The page to validate.
            page_attempts: Number of validation attempts for this page.
            current_page_index: Index of the current page.
            
        Returns:
            The validation results.
        """
        logger.info("ACT: Performing validation")
        
        # Format content for validation
        formatted_content = self._format_page(page)
        logger.info("Formatted content for validation:")
        logger.info("========================================")
        logger.info(formatted_content)
        logger.info("========================================")
        
        # Send to GPT for validation
        logger.info("- Sending content to GPT")
        messages = [
            SystemMessage(content=VALIDATION_PROMPT.format(content=formatted_content))
        ]
        response = self.model.invoke(messages)
        
        # Process validation results
        logger.info("- Processing validation results")
        validation = self._validate_json_response(response.content)
        
        # Add page index to validation results
        validation["page_index"] = current_page_index
        
        # Log validation results
        if not validation["is_valid"]:
            logger.info("RESULT: Page requires updates")
            if not validation["slide"]["is_valid"]:
                logger.info(f"- Slide Updates: {validation['slide']['suggested_fixes']}")
            if not validation["script"]["is_valid"]:
                logger.info(f"- Script Updates: {validation['script']['suggested_fixes']}")
        else:
            logger.info("RESULT: Page is valid")
            
        return validation

    def process(self, state: AgentState, config: RunnableConfig) -> AgentState:
        """Process the current state.
        
        Args:
            state: The current state.
            config: Runtime configuration.
            
        Returns:
            The updated state.
        """
        logger.info("=========================================================")
        logger.info("VALIDATOR NODE START - ReAct Cycle")
        logger.info("=========================================================")
        
        try:
            # OBSERVE: Get current state
            logger.info("OBSERVE: Analyzing current state")
            current_page_index = state.get("current_page_index", 0)
            current_page = current_page_index + 1
            pages = state.get("pages", {}).get("content", [])
            total_pages = len(pages)
            page_attempts = state.get("validation_attempts", {}).get(str(current_page), 0) + 1
            
            logger.info(f"- Current Page: {current_page}")
            logger.info(f"- Total Pages: {total_pages}")
            logger.info(f"- Attempt: {page_attempts}")
            
            # THINK: Reason about validation state
            logger.info("THINK: Reasoning about validation state")
            logger.info("DECISION: Proceed with attempt 1")
            
            # VALIDATE: Validate current page
            logger.info(f"VALIDATE: Page {current_page} (Attempt {page_attempts})")
            page = pages[current_page_index]
            validation = self._act_validate(page, page_attempts, current_page_index)
            
            # ACTION: Determine next action based on validation
            if not validation["is_valid"]:
                logger.info("ACTION: Route to update node")
            else:
                logger.info("ACTION: Continue to next page")
                
            # Update state with validation results
            state["validation_results"] = validation
            state["validation_metadata"] = {
                "last_validation_time": self.get_current_time(),
                "total_attempts": page_attempts,
                "current_attempt": page_attempts,
                "validation_status": "valid" if validation["is_valid"] else "updates_needed",
                "invalid_components": []
            }
            
            # Add invalid components to metadata
            if not validation["slide"]["is_valid"]:
                state["validation_metadata"]["invalid_components"].append({
                    "type": "slide",
                    "severity": validation["slide"]["severity"],
                    "fixes": validation["slide"]["suggested_fixes"]
                })
            if not validation["script"]["is_valid"]:
                state["validation_metadata"]["invalid_components"].append({
                    "type": "script",
                    "severity": validation["script"]["severity"],
                    "fixes": validation["script"]["suggested_fixes"]
                })
                
            # Add to validation history
            if "validation_history" not in state:
                state["validation_history"] = []
            state["validation_history"].append({
                "page": current_page,
                "attempt": page_attempts,
                "time": self.get_current_time(),
                "valid": validation["is_valid"],
                "slide": "✓" if validation["slide"]["is_valid"] else "⟳",
                "script": "✓" if validation["script"]["is_valid"] else "⟳"
            })
            
            # Set current validation
            state["current_validation"] = {
                "page_index": current_page_index,
                "page": current_page,
                "attempt": page_attempts,
                "validation": validation
            }
            
            # Log validation summary
            self._log_validation_summary(state)
            
        except Exception as e:
            logger.error(f"ERROR: Validation failed - {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            raise
            
        finally:
            logger.info("=========================================================")
            logger.info("VALIDATOR NODE END")
            logger.info("=========================================================")
            
        return state

    def _log_validation_summary(self, state: AgentState) -> None:
        """Log a summary of the validation results.
        
        Args:
            state: The current state.
        """
        logger.info("=========================================================")
        logger.info("VALIDATION SUMMARY:")
        
        # Log validation counts
        history = state.get("validation_history", [])
        logger.info(f"Pages Validated: {len(history)}")
        
        # Log overall status
        metadata = state.get("validation_metadata", {})
        logger.info(f"Status: {metadata.get('validation_status', 'UNKNOWN').upper()}")
        
        # Log current page results
        current_validation = state.get("current_validation", {})
        if current_validation:
            page = current_validation["page"]
            attempt = current_validation["attempt"]
            validation = current_validation["validation"]
            
            logger.info(f"Page {page} (Attempt {attempt}):")
            logger.info(f"- Slide: {'✓' if validation['slide']['is_valid'] else '⟳'}")
            logger.info(f"- Script: {'✓' if validation['script']['is_valid'] else '⟳'}")
            
            if not validation["is_valid"]:
                logger.info("- Updates Required:")
                if not validation["slide"]["is_valid"]:
                    logger.info(f"  Slide: {validation['slide']['suggested_fixes']}")
                if not validation["script"]["is_valid"]:
                    logger.info(f"  Script: {validation['script']['suggested_fixes']}")
        
        # Log validation history
        logger.info("\nVALIDATION HISTORY:")
        for entry in history:
            logger.info(f"- Page {entry['page']}, Attempt {entry['attempt']}:")
            logger.info(f"  Time: {entry['time']}")
            logger.info(f"  Valid: {entry['valid']}")
            logger.info(f"  Slide: {entry['slide']}")
            logger.info(f"  Script: {entry['script']}")
            
        # Log current state info
        logger.info("----------------------------------------")
        logger.info(f"Current State Keys: {list(state.keys())}")
        logger.info("Current Validation Info:")
        logger.info(f"- Has Current Validation: {bool(state.get('current_validation'))}")
        logger.info(f"- Current Page Index: {state.get('current_page_index')}")
        if metadata:
            logger.info("- Validation Metadata:")
            for key, value in metadata.items():
                logger.info(f"  {key}: {value}") 
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
            page: The page content to format
            
        Returns:
            The formatted content string
        """
        # Extract slide content
        slide = page.get("slide", {})
        if isinstance(slide, dict):
            frontmatter = slide.get("frontmatter", "")
            content = slide.get("content", "")
            slide_content = f"{frontmatter}\n{content}" if frontmatter else content
        else:
            slide_content = str(slide)

        # Extract script content
        script = page.get("script", {})
        if isinstance(script, dict):
            header = script.get("header", "")
            content = script.get("content", "")
            script_content = f"{header}\n{content}" if header else content
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
            pages = state.get("pages", {}).get("content", [])
            total_pages = len(pages)
            
            # Validate page index
            if current_page_index >= total_pages:
                logger.warning(f"Invalid page index {current_page_index} (total pages: {total_pages})")
                return state
            
            # Get or initialize validation attempts
            validation_attempts = state.get("validation_attempts", {})
            current_page_key = str(current_page_index)
            
            # Only increment attempt counter if this is a new validation attempt
            # (not returning from an update node)
            if not state.get("current_validation"):
                page_attempts = validation_attempts.get(current_page_key, 0)
                page_attempts += 1
                validation_attempts[current_page_key] = page_attempts
                state["validation_attempts"] = validation_attempts
            else:
                # Check if we're validating a different page than last time
                last_validation = state["current_validation"]
                last_page_index = last_validation.get("page_index")
                if last_page_index != current_page_index:
                    # We've moved to a new page, start with attempt 1
                    page_attempts = 1
                    validation_attempts[current_page_key] = page_attempts
                    state["validation_attempts"] = validation_attempts
                else:
                    page_attempts = validation_attempts.get(current_page_key, 1)
            
            logger.info(f"- Current Page: {current_page_index + 1} of {total_pages}")
            logger.info(f"- Validation Attempt: {page_attempts}")
            
            # THINK: Reason about validation state
            logger.info("THINK: Reasoning about validation state")
            
            # Get the current page
            page = pages[current_page_index]
            
            # VALIDATE: Validate current page
            logger.info(f"VALIDATE: Page {current_page_index + 1} (Attempt {page_attempts})")
            validation = self._act_validate(page, page_attempts, current_page_index)
            
            # ACTION: Determine next action based on validation
            if not validation["is_valid"]:
                logger.info("ACTION: Page requires updates")
                logger.info("Invalid components:")
                if not validation["slide"]["is_valid"]:
                    logger.info(f"- Slide: {validation['slide']['suggested_fixes']}")
                if not validation["script"]["is_valid"]:
                    logger.info(f"- Script: {validation['script']['suggested_fixes']}")
            else:
                logger.info("ACTION: Page validation successful")
                
            # Update state with validation results
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
                
            # Create new history entry
            history_entry = {
                "page": current_page_index + 1,
                "attempt": page_attempts,
                "time": self.get_current_time(),
                "valid": validation["is_valid"],
                "slide": "✓" if validation["slide"]["is_valid"] else "⟳",
                "script": "✓" if validation["script"]["is_valid"] else "⟳"
            }
            
            # Initialize or update validation history
            if "validation_history" not in state:
                state["validation_history"] = []
            
            # Remove any previous entries for this page and attempt
            state["validation_history"] = [
                entry for entry in state["validation_history"]
                if not (entry["page"] == history_entry["page"] and 
                       entry["attempt"] == history_entry["attempt"])
            ]
            state["validation_history"].append(history_entry)
            
            # Set current validation
            state["current_validation"] = {
                "page_index": current_page_index,
                "attempt": page_attempts,
                "validation": validation
            }
            
            # Log validation summary
            self._log_validation_summary(state)
            
            # If validation passed, prepare state for next page
            if validation["is_valid"]:
                next_page_index = current_page_index + 1
                if next_page_index < total_pages:
                    state["current_page_index"] = next_page_index
                    state.pop("current_validation", None)
                    state.pop("validation_results", None)
                    if str(next_page_index) not in validation_attempts:
                        validation_attempts[str(next_page_index)] = 0
                    state["validation_attempts"] = validation_attempts
            
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
        
        # Get current page index and validation
        current_page_index = state.get("current_page_index", 0)
        current_validation = state.get("current_validation", {})
        
        # Get validation history
        history = state.get("validation_history", [])
        
        # Count unique pages validated
        unique_pages = len({entry["page"] for entry in history})
        logger.info(f"Total Pages Validated: {unique_pages}")
        
        # Log current validation results if available
        if current_validation:
            validation = current_validation.get("validation", {})
            attempt = current_validation.get("attempt", 0)
            
            logger.info(f"\nCurrent Page {current_page_index + 1}:")
            logger.info(f"Attempt {attempt}:")
            logger.info(f"- Slide: {'✓' if validation.get('slide', {}).get('is_valid', False) else '⟳'}")
            logger.info(f"- Script: {'✓' if validation.get('script', {}).get('is_valid', False) else '⟳'}")
            
            if not validation.get("is_valid", False):
                logger.info("\nUpdates Required:")
                if not validation.get("slide", {}).get("is_valid", False):
                    logger.info(f"- Slide: {validation['slide'].get('suggested_fixes', 'No fixes suggested')}")
                if not validation.get("script", {}).get("is_valid", False):
                    logger.info(f"- Script: {validation['script'].get('suggested_fixes', 'No fixes suggested')}")
        
        # Filter and sort history for current page only
        current_page_history = [
            entry for entry in history 
            if entry["page"] == current_page_index + 1
        ]
        current_page_history.sort(key=lambda x: (x["attempt"], x["time"]))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_history = []
        for entry in current_page_history:
            key = (entry["page"], entry["attempt"], entry["valid"])
            if key not in seen:
                seen.add(key)
                unique_history.append(entry)
        
        if unique_history:
            logger.info("\nCURRENT PAGE HISTORY:")
            for entry in unique_history:
                logger.info(f"Attempt {entry['attempt']}:")
                logger.info(f"- Time: {entry['time']}")
                logger.info(f"- Valid: {entry['valid']}")
                logger.info(f"- Slide: {entry['slide']}")
                logger.info(f"- Script: {entry['script']}")
        
        # Log brief state info
        logger.info("\nSTATE INFO:")
        logger.info(f"- Current Page: {current_page_index + 1}")
        logger.info(f"- Has Current Validation: {bool(current_validation)}")
        
        metadata = state.get("validation_metadata", {})
        if metadata:
            status = metadata.get("validation_status", "UNKNOWN").upper()
            logger.info(f"- Status: {status}")
            logger.info(f"- Total Attempts: {metadata.get('total_attempts', 0)}") 
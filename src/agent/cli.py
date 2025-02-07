"""CLI interface for running the agent graph."""

import argparse
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from agent.graph import graph

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_state_file(state_file: str) -> Dict[str, Any]:
    """Load state from a JSON file.
    
    Args:
        state_file: Path to the state JSON file
        
    Returns:
        Dict containing the loaded state
    """
    state_path = Path(state_file)
    if not state_path.exists():
        raise FileNotFoundError(f"State file not found: {state_file}")
        
    logger.info(f"Loading state from {state_file}")
    with open(state_file) as f:
        return json.load(f)


def main(deck_id: str, deck_title: str, state_file: Optional[str] = None) -> None:
    """Run the graph with the given deck information.
    
    Args:
        deck_id: The ID of the deck to process
        deck_title: The title of the deck
        state_file: Optional path to a JSON file containing initial state
    """
    # Create initial state
    if state_file:
        state = load_state_file(state_file)
        # Ensure deck_id and title match
        if state["deck_id"] != deck_id or state["deck_title"] != deck_title:
            logger.warning("State file deck_id/title don't match provided arguments")
            state["deck_id"] = deck_id
            state["deck_title"] = deck_title
    else:
        state = {
            "deck_id": deck_id,
            "deck_title": deck_title
        }
    
    # Run the graph
    logger.info(f"Running graph with state: {state}")
    result = graph.invoke(state)
    logger.info("Graph execution completed")
    logger.info(f"Final state: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the deck processing graph")
    parser.add_argument("--deck-id", required=True, help="ID of the deck to process")
    parser.add_argument("--deck-title", required=True, help="Title of the deck")
    parser.add_argument("--state-file", help="Path to JSON file containing initial state")
    
    args = parser.parse_args()
    main(args.deck_id, args.deck_title, args.state_file) 
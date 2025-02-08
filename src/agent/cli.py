"""Command line interface for the agent.

This module provides the CLI entry point for running the agent.
Following Single Responsibility Principle, this module only handles CLI interaction.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from langsmith import Client

from agent import graph

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_state(state_file: Optional[Path]) -> dict:
    """Load state from a file if provided."""
    if state_file and state_file.exists():
        logger.info(f"Loading state from {state_file}")
        with open(state_file) as f:
            return json.load(f)
    return {}

def main(deck_id: str, deck_title: str, state_file: Optional[str] = None) -> None:
    """Main entry point for the CLI.
    
    Args:
        deck_id: ID of the deck to process
        deck_title: Title of the deck
        state_file: Optional path to state file
    """
    try:
        # Initialize LangSmith client
        client = Client()
        
        # Set up initial state
        state = load_state(Path(state_file) if state_file else None)
        state.update({
            "deck_id": deck_id,
            "deck_title": deck_title
        })
        logger.info(f"Running graph with state: {state}")
        
        # Run the graph
        result = graph.invoke(state)
        
        # Save final state
        output_file = Path(f"src/decks/{deck_id}/final_state.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
            
        logger.info(f"Final state saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error running graph: {str(e)}")
        sys.exit(1)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Run the agent on a deck")
    parser.add_argument(
        "--deck-id",
        required=True,
        help="ID of the deck to process"
    )
    parser.add_argument(
        "--deck-title",
        required=True,
        help="Title of the deck"
    )
    parser.add_argument(
        "--state-file",
        help="Path to state file"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args.deck_id, args.deck_title, args.state_file) 
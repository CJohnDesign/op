"""CLI interface for running the agent graph."""

import argparse
import logging
from typing import Optional

from agent.graph import graph

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main(deck_id: str, deck_title: str) -> None:
    """Run the graph with the given deck information.
    
    Args:
        deck_id: The ID of the deck to process
        deck_title: The title of the deck
    """
    # Create initial state
    state = {
        "deck_id": deck_id,
        "deck_title": deck_title
    }
    
    # Run the graph
    logger.info(f"Running graph with deck_id={deck_id}, deck_title={deck_title}")
    result = graph.invoke(state)
    logger.info("Graph execution completed")
    logger.info(f"Final state: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the deck processing graph")
    parser.add_argument("--deck-id", required=True, help="ID of the deck to process")
    parser.add_argument("--deck-title", required=True, help="Title of the deck")
    
    args = parser.parse_args()
    main(args.deck_id, args.deck_title) 
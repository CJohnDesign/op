#!/usr/bin/env python3
"""Convenience script for running the agent graph."""

from agent.cli import main

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the deck processing graph")
    parser.add_argument("--deck-id", required=True, help="ID of the deck to process")
    parser.add_argument("--deck-title", required=True, help="Title of the deck")
    
    args = parser.parse_args()
    main(args.deck_id, args.deck_title) 
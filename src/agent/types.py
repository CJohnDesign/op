"""Type definitions for the agent.

This module contains shared type definitions used across the agent.
Following Interface Segregation Principle, we keep types focused and minimal.
"""

from __future__ import annotations

from typing_extensions import TypedDict


class DeckInfo(TypedDict):
    """Type definition for deck information."""
    id: str
    title: str


class AgentState(TypedDict):
    """Base state interface for the agent."""
    deck_id: str
    deck_title: str 
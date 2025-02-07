"""Type definitions for the agent.

This module contains shared type definitions used across the agent.
Following Interface Segregation Principle, we keep types focused and minimal.
"""

from __future__ import annotations

from typing import List, Dict, Any
from typing_extensions import TypedDict


class DeckInfo(TypedDict):
    """Type definition for deck information."""
    id: str
    title: str


class TableDetails(TypedDict):
    """Type definition for table detection details."""
    hasBenefitsTable: bool
    hasLimitations: bool


class ProcessedImage(TypedDict):
    """Type definition for processed image information."""
    page_number: int
    original_name: str
    new_name: str
    page_title: str
    summary: str
    table_details: TableDetails


class TableData(TypedDict):
    """Type definition for extracted table data."""
    table_title: str
    headers: List[str]
    rows: List[List[str]]


class ExtractedTable(TypedDict):
    """Type definition for extracted table information."""
    page_number: int
    tables: List[TableData]


class SlideContent(TypedDict):
    """Type definition for slide content."""
    header: str
    content: str


class ScriptContent(TypedDict):
    """Type definition for script content."""
    header: str
    content: str


class Page(TypedDict):
    """Type definition for a complete page."""
    slide: SlideContent
    script: ScriptContent


class Pages(TypedDict):
    """Type definition for pages collection."""
    content: List[Page]
    count: int


class DeckInputs(TypedDict):
    """Required input fields for initializing a deck."""
    deck_id: str
    deck_title: str


class AgentState(DeckInputs, TypedDict, total=False):
    """State interface for the agent.
    
    Extends DeckInputs to include all state fields that are populated by nodes.
    total=False makes all additional fields optional by default.
    """
    processed_images: Dict[int, ProcessedImage]
    extracted_tables: Dict[int, ExtractedTable]
    presentation: Dict[str, str]
    slides: Dict[str, str]
    script: Dict[str, str]
    pages: Pages 
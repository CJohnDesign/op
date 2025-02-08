"""Type definitions for the agent.

This module contains shared type definitions used across the agent.
Following Interface Segregation Principle, we keep types focused and minimal.
"""

from __future__ import annotations

from typing import List, Dict, Any, Literal
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
    frontmatter: str | None


class ScriptContent(TypedDict):
    """Type definition for script content."""
    header: str
    content: str


class Page(TypedDict):
    """Type definition for a page containing slide and script."""
    slide: SlideContent
    script: ScriptContent


class Pages(TypedDict):
    """Type definition for pages collection."""
    content: List[Page]
    count: int


class ValidationResult(TypedDict):
    """Type definition for validation results of a single component."""
    is_valid: bool
    update_instructions: str | None
    validation_messages: List[str]


class PageValidationState(TypedDict):
    """Type definition for the validation state of a single page."""
    page_number: int
    slide_valid: bool
    script_valid: bool
    slide_update_instructions: str | None
    script_update_instructions: str | None
    updated_slide: SlideContent | None
    updated_script: ScriptContent | None


class ValidationState(TypedDict):
    """Type definition for overall validation state."""
    current_page: int
    total_pages: int
    pages: Dict[int, PageValidationState]
    update_type: Literal["none", "slide_only", "script_only", "both"] | None


class AgentState(TypedDict, total=False):
    """State interface for the agent.
    
    Following ReAct pattern for state management.
    total=False makes all fields optional by default.
    """
    # Required fields
    deck_id: str
    deck_title: str
    
    # State fields populated by nodes
    processed_images: Dict[int, ProcessedImage]
    extracted_tables: Dict[int, ExtractedTable]
    presentation: Dict[str, str]
    slides: Dict[str, str]
    script: Dict[str, str]
    pages: Pages
    validation_state: ValidationState 
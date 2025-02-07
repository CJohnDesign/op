"""Tracer implementation for tracking node execution.

This module provides tracing functionality for the agent graph nodes.
Following Single Responsibility Principle, this module only handles tracing.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from langsmith import traceable

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for the decorated function
F = TypeVar("F", bound=Callable)

def trace_node(run_type: str = "chain") -> Callable[[F], F]:
    """Decorator to trace node execution with LangSmith.
    
    Args:
        run_type: The type of run to track. Defaults to "chain".
        
    Returns:
        Decorated function that is traced by LangSmith
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the class name if it's a method
            name = f"{args[0].__class__.__name__}.{func.__name__}" if args else func.__name__
            
            # Apply LangSmith tracing
            traced_func = traceable(
                run_type=run_type,
                name=name,
            )(func)
            
            try:
                return traced_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in traced function {name}: {str(e)}")
                raise
                
        return wrapper  # type: ignore
    return decorator 
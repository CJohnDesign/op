"""LLM configuration module.

This module contains the LLM client configuration to avoid circular imports.
Following Single Responsibility Principle, this module only handles LLM setup.
"""

from langchain_openai import ChatOpenAI
from langsmith.wrappers import wrap_openai
import openai
import os

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")

# Create OpenAI client with proper configuration
openai.api_key = api_key

# Create traced LLM instance for text tasks
llm = ChatOpenAI(
    api_key=api_key,
    model="gpt-4o",
    max_tokens=4096,
    temperature=0
)

# Create traced LLM instance for vision tasks with JSON response format
vision_llm = ChatOpenAI(
    api_key=api_key,
    model="gpt-4o",
    temperature=0,
    max_tokens=4096,
    model_kwargs={
        "response_format": {"type": "json_object"}
    }
) 
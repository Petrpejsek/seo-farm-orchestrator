"""
LLM Clients package pro multi-provider podporu.
Obsahuje klienty pro OpenAI, Claude a Gemini.
"""

from .factory import LLMClientFactory
from .base import BaseLLMClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # Přidá backend/ do PATH
from openai_client import OpenAIClient
from .claude_client import ClaudeClient
from .gemini_client import GeminiClient

__all__ = [
    "LLMClientFactory",
    "BaseLLMClient", 
    "OpenAIClient",
    "ClaudeClient",
    "GeminiClient"
]
"""Message processor node implementation.

This module contains a node that processes messages in the graph.
Following Single Responsibility Principle, this node only handles message processing.
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

from agent.configuration import Configuration
from agent.nodes.base import BaseNode
from agent.types import AgentState


class MessageProcessorNode(BaseNode[AgentState]):
    """Node for processing messages in the graph.
    
    Following Dependency Inversion Principle, this class depends on abstractions (BaseNode)
    rather than concrete implementations.
    """
    
    async def process(self, state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
        """Process the messages in the current state.
        
        Args:
            state: The current state
            config: Runtime configuration
            
        Returns:
            Updated state with processed messages
        """
        self.logger.info("Processing messages")
        
        try:
            # Get configuration
            configuration = Configuration.from_runnable_config(config)
            
            # Example processing - you would customize this based on your needs
            processed_message = f"Processing deck {state['deck_title']} ({state['deck_id']})"
            
            self.logger.info(processed_message)
            
            # Return state
            return state
            
        except Exception as e:
            self.logger.error(f"Error processing messages: {str(e)}")
            raise 
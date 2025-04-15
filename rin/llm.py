import os
import asyncio
import logging
from abc import ABC, abstractmethod
from rin.config import OPENAI_API_KEY, LLM_MODEL, SYSTEM_PROMPT
from rin.logging_config import loggers

logger = loggers['llm']

class LLMInterface(ABC):
    """Abstract base class for LLM providers"""
    
    @staticmethod
    def create(provider="openai"):
        """Factory method to create appropriate LLM client"""
        if provider == "openai":
            return OpenAIClient()
        # Add more providers here as needed
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    @abstractmethod
    async def generate_response(self, query):
        """Generate a response to the given query"""
        pass

class OpenAIClient(LLMInterface):
    def __init__(self):
        # Import here to avoid loading the module if not needed
        from openai import OpenAI
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = LLM_MODEL
        logger.info(f"Initialized OpenAI client with model {self.model}")
    
    async def generate_response(self, query):
        """Asynchronously generate a response using OpenAI"""
        try:
            logger.info(f"Generating response for query using {self.model}")
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Generated response: {content[:50]}...")
            return content
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise

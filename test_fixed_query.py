#!/usr/bin/env python3
import asyncio
from rin.core import Assistant

async def test_query():
    """Test specifically the 'what are my active timers?' query"""
    print("Testing fixed reminder query...\n")
    
    # Initialize assistant
    assistant = Assistant()
    
    query = "What are my active timers?"
    print(f"Query: {query}")
    response = await assistant.process_query(query)
    print(f"Response: {response['text']}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_query()) 
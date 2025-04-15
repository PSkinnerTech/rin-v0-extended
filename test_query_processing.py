#!/usr/bin/env python3
import asyncio
from rin.core import Assistant

async def test_query_processing():
    """Test processing of queries related to lists and reminders"""
    print("Testing natural language query processing...\n")
    
    # Initialize assistant
    assistant = Assistant()
    
    # Test queries
    list_queries = [
        "Create a shopping list",
        "Add milk to my shopping list",
        "Add eggs to my shopping list",
        "Show my shopping list",
        "What's on my shopping list?"
    ]
    
    reminder_queries = [
        "Set a timer for 5 minutes for coffee",
        "Remind me to check my email at 3:30",
        "Show my reminders",
        "What are my active timers?"
    ]
    
    # Process list queries
    print("TESTING LIST QUERIES:")
    for query in list_queries:
        print(f"\nQuery: {query}")
        response = await assistant.process_query(query)
        print(f"Response: {response['text']}")
        # Small delay to avoid flooding the output
        await asyncio.sleep(0.5)
    
    # Process reminder queries
    print("\n\nTESTING REMINDER QUERIES:")
    for query in reminder_queries:
        print(f"\nQuery: {query}")
        response = await assistant.process_query(query)
        print(f"Response: {response['text']}")
        # Small delay to avoid flooding the output
        await asyncio.sleep(0.5)
    
    print("\nQuery processing test completed!")

if __name__ == "__main__":
    asyncio.run(test_query_processing()) 
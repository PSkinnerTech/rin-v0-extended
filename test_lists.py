#!/usr/bin/env python3
import asyncio
from rin.lists import ListManager

async def test_lists():
    print("Testing ListManager...")
    
    # Initialize the manager
    mgr = ListManager()
    
    # Create a list
    print("\n1. Creating shopping list...")
    success = await mgr.create_list('shopping', ['milk', 'eggs', 'bread'])
    print(f"   Result: {'Success' if success else 'Failed'}")
    
    # Get all lists
    print("\n2. Getting all lists...")
    lists = await mgr.get_lists()
    print(f"   Lists: {lists}")
    
    # Get shopping list items
    print("\n3. Getting shopping list items...")
    items = await mgr.get_list('shopping')
    print(f"   Items: {items}")
    
    # Add item to list
    print("\n4. Adding 'cheese' to shopping list...")
    success = await mgr.add_item('shopping', 'cheese')
    print(f"   Result: {'Success' if success else 'Failed'}")
    
    # Get updated list
    items = await mgr.get_list('shopping')
    print(f"   Updated items: {items}")
    
    # Remove an item
    print("\n5. Removing 'eggs' (index 1) from shopping list...")
    success = await mgr.remove_item('shopping', 1)  # Remove eggs (index 1)
    print(f"   Result: {'Success' if success else 'Failed'}")
    
    # Get updated list
    items = await mgr.get_list('shopping')
    print(f"   Updated items: {items}")
    
    # Delete list
    print("\n6. Deleting shopping list...")
    success = await mgr.delete_list('shopping')
    print(f"   Result: {'Success' if success else 'Failed'}")
    
    # Verify deletion
    lists = await mgr.get_lists()
    print(f"   Remaining lists: {lists}")
    
    print("\nList test completed!")

if __name__ == "__main__":
    asyncio.run(test_lists()) 
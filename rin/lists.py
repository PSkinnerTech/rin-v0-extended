import json
import aiosqlite
import asyncio
import logging
from pathlib import Path
from rin.config import RIN_DIR
from rin.logging_config import loggers
import datetime

logger = loggers.get('core', logging.getLogger('rin.lists'))

class ListManager:
    """SQLite-based list manager using aiosqlite"""
    
    def __init__(self):
        self.db_path = RIN_DIR / "rin.db" # Use the main database file
        logger.info(f"List Manager initialized, using DB at {self.db_path}")
    
    async def _init_db(self):
        """Ensure the lists table exists"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    items TEXT NOT NULL, -- Store items as JSON string
                    created_at TEXT NOT NULL,
                    UNIQUE(name)
                )
            ''')
            await db.commit()
    
    async def get_lists(self):
        """Get all available list names"""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT name FROM lists')
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def create_list(self, name, items=None):
        """Create a new list with optional initial items"""
        await self._init_db()
        if items is None:
            items = []
        
        items_json = json.dumps(items)
        created_at = str(datetime.datetime.now())
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO lists (name, items, created_at) VALUES (?, ?, ?)',
                    (name, items_json, created_at)
                )
                await db.commit()
            logger.info(f"Created list '{name}' with {len(items)} items")
            return True
        except aiosqlite.IntegrityError:
            logger.warning(f"List '{name}' already exists")
            return False
        except Exception as e:
            logger.error(f"Error creating list '{name}': {str(e)}")
            return False
    
    async def get_list(self, name):
        """Get a specific list by name, returning items"""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT items FROM lists WHERE name = ?', (name,))
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0]) # Return only the items list
                except json.JSONDecodeError:
                    logger.error(f"Error decoding items for list '{name}'")
                    return None
            else:
                logger.warning(f"List '{name}' not found")
                return None
    
    async def add_item(self, list_name, item):
        """Add an item to a list"""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT items FROM lists WHERE name = ?', (list_name,))
            row = await cursor.fetchone()
            if not row:
                logger.warning(f"List '{list_name}' not found for adding item")
                return False
            
            try:
                items = json.loads(row[0])
                items.append(item)
                items_json = json.dumps(items)
                await db.execute('UPDATE lists SET items = ? WHERE name = ?', (items_json, list_name))
                await db.commit()
                logger.info(f"Added item to '{list_name}': {item}")
                return True
            except Exception as e:
                logger.error(f"Error adding item to list '{list_name}': {str(e)}")
                return False
    
    async def remove_item(self, list_name, item_index):
        """Remove an item from a list by index"""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT items FROM lists WHERE name = ?', (list_name,))
            row = await cursor.fetchone()
            if not row:
                logger.warning(f"List '{list_name}' not found for removing item")
                return False
            
            try:
                items = json.loads(row[0])
                if 0 <= item_index < len(items):
                    removed = items.pop(item_index)
                    items_json = json.dumps(items)
                    await db.execute('UPDATE lists SET items = ? WHERE name = ?', (items_json, list_name))
                    await db.commit()
                    logger.info(f"Removed item from '{list_name}': {removed}")
                    return True
                else:
                    logger.warning(f"Invalid item index {item_index} for list '{list_name}'")
                    return False
            except Exception as e:
                logger.error(f"Error removing item from list '{list_name}': {str(e)}")
                return False
    
    async def delete_list(self, name):
        """Delete a list entirely"""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('DELETE FROM lists WHERE name = ?', (name,))
            await db.commit()
            if cursor.rowcount > 0:
                logger.info(f"Deleted list '{name}'")
                return True
            else:
                logger.warning(f"List '{name}' not found for deletion")
                return False 
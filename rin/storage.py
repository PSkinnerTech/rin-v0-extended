import sqlite3
import asyncio
import logging
from pathlib import Path
from rin.config import RIN_DIR
from rin.logging_config import loggers

logger = loggers['storage']

class Storage:
    """Database storage with async support"""
    
    def __init__(self):
        self.path = RIN_DIR / "rin.db"
        # Initialize synchronously
        self._init_db()
        logger.info(f"Storage initialized at {self.path}")
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.path)
        conn.execute('''CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()
    
    async def save_interaction(self, query, response):
        """Save interaction to database asynchronously"""
        try:
            logger.debug(f"Saving interaction: Q: {query[:50]}... R: {response[:50]}...")
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._save_interaction_sync,
                query,
                response
            )
            return True
        except Exception as e:
            logger.error(f"Error saving interaction: {str(e)}", exc_info=True)
            return False
    
    def _save_interaction_sync(self, query, response):
        """Synchronous database save (to be run in executor)"""
        conn = sqlite3.connect(self.path)
        conn.execute(
            "INSERT INTO interactions (query, response) VALUES (?, ?)", 
            (query, response)
        )
        conn.commit()
        conn.close()
    
    async def get_interactions(self, limit=10):
        """Get recent interactions asynchronously"""
        try:
            logger.debug(f"Retrieving {limit} recent interactions")
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._get_interactions_sync,
                limit
            )
            return result
        except Exception as e:
            logger.error(f"Error getting interactions: {str(e)}", exc_info=True)
            return []
    
    def _get_interactions_sync(self, limit):
        """Synchronous database query (to be run in executor)"""
        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT query, response FROM interactions ORDER BY timestamp DESC LIMIT ?", 
            (limit,)
        )
        result = [dict(query=row[0], response=row[1]) for row in cursor.fetchall()]
        conn.close()
        return result

import os
import json
import aiosqlite
import asyncio
import datetime
import logging
from pathlib import Path
from rin.config import RIN_DIR
from rin.logging_config import loggers
from rin.llm import LLMInterface

logger = loggers.get('core', logging.getLogger('rin.email'))

class EmailDraftCreator:
    """Create and manage email drafts using SQLite"""
    
    def __init__(self):
        self.db_path = RIN_DIR / "rin.db"
        self.llm = LLMInterface.create()
        logger.info(f"Email Draft Creator initialized, using DB at {self.db_path}")

    async def _init_db(self):
        """Ensure the email_drafts table exists"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS email_drafts (
                    id TEXT PRIMARY KEY,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tone TEXT,
                    prompt TEXT
                )
            ''')
            await db.commit()

    async def create_draft(self, recipient, subject, prompt, tone="professional"):
        """Create an email draft from a prompt and save to DB"""
        await self._init_db()
        try:
            # Generate email content using LLM
            content = await self._generate_email_content(recipient, subject, prompt, tone)
            
            # Create the draft ID and timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            draft_id = f"email_{timestamp}_{hash(prompt) % 10000}" # Simple hash for uniqueness
            created_at = str(datetime.datetime.now())
            
            draft = {
                "id": draft_id,
                "recipient": recipient,
                "subject": subject,
                "content": content,
                "created_at": created_at,
                "tone": tone,
                "prompt": prompt
            }
            
            # Save the draft to SQLite
            async with aiosqlite.connect(self.db_path) as db:
                 await db.execute(
                     'INSERT INTO email_drafts (id, recipient, subject, content, created_at, tone, prompt) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (draft["id"], draft["recipient"], draft["subject"], draft["content"], 
                      draft["created_at"], draft["tone"], draft["prompt"])
                 )
                 await db.commit()
            
            logger.info(f"Saved email draft {draft_id}")
            return draft
        except Exception as e:
            logger.error(f"Error creating email draft: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    async def get_drafts(self):
        """Get all email drafts from DB"""
        await self._init_db()
        drafts = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT * FROM email_drafts ORDER BY created_at DESC')
                rows = await cursor.fetchall()
                drafts = [dict(zip([c[0] for c in cursor.description], row)) for row in rows]
            return drafts
        except Exception as e:
            logger.error(f"Error getting email drafts: {str(e)}")
            return []
    
    async def get_draft(self, draft_id):
        """Get a specific draft by ID from DB"""
        await self._init_db()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT * FROM email_drafts WHERE id = ?', (draft_id,))
                row = await cursor.fetchone()
                if row:
                    return dict(zip([c[0] for c in cursor.description], row))
                else:
                    logger.warning(f"Draft {draft_id} not found in DB")
                    return None
        except Exception as e:
            logger.error(f"Error reading draft {draft_id}: {str(e)}")
            return None
    
    async def delete_draft(self, draft_id):
        """Delete a draft by ID from DB"""
        await self._init_db()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('DELETE FROM email_drafts WHERE id = ?', (draft_id,))
                await db.commit()
                if cursor.rowcount > 0:
                    logger.info(f"Deleted draft {draft_id}")
                    return True
                else:
                    logger.warning(f"Draft {draft_id} not found for deletion")
                    return False
        except Exception as e:
            logger.error(f"Error deleting draft {draft_id}: {str(e)}")
            return False
    
    async def _generate_email_content(self, recipient, subject, prompt, tone):
        """Generate email content using LLM"""
        # Create a prompt for the LLM
        email_prompt = f"""
        Write a {tone} email to {recipient} with the subject \"{subject}\".
        
        Details to include in the email:
        {prompt}
        
        Format the email properly with greeting, body paragraphs, and sign-off.
        Do not include the "To:", "From:", or "Subject:" lines - just write the email body.
        """
        
        # Generate the content
        content = await self.llm.generate_response(email_prompt)
        return content 
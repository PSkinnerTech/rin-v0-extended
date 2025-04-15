import json
import aiosqlite
import asyncio
import datetime
import platform
import logging
import time
from pathlib import Path
from rin.config import RIN_DIR
from rin.logging_config import loggers
from rin.tts import TTSInterface

logger = loggers.get('core', logging.getLogger('rin.reminders'))

class ReminderManager:
    """Manages timers and reminders using SQLite and notifications"""
    
    def __init__(self):
        self.db_path = RIN_DIR / "rin.db"
        self.tasks = {}  # Track running asyncio tasks
        self.tts = TTSInterface.create()
        logger.info(f"Reminder Manager initialized, using DB at {self.db_path}")
        
        # Load existing reminders asynchronously in the background
        asyncio.create_task(self._load_reminders())
    
    async def _init_db(self):
        """Ensure the reminders table exists"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY, -- Use string ID for simplicity
                    type TEXT NOT NULL, -- 'timer' or 'reminder'
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    due_time TEXT NOT NULL,
                    duration_seconds INTEGER, -- Only for timers
                    completed INTEGER DEFAULT 0
                )
            ''')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders (due_time)')
            await db.commit()

    async def _load_reminders(self):
        """Load persisted reminders and schedule them"""
        await self._init_db()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT * FROM reminders WHERE completed = 0')
                reminders = await cursor.fetchall()
            
            now = datetime.datetime.now()
            active_count = 0
            for row in reminders:
                reminder = dict(zip([c[0] for c in cursor.description], row))
                due_time = datetime.datetime.fromisoformat(reminder["due_time"])
                if due_time > now:
                    self._schedule_reminder(reminder)
                    active_count += 1
                else:
                    # Mark past-due reminders as completed
                    await self._mark_completed(reminder["id"])
            
            logger.info(f"Loaded and scheduled {active_count} active reminders")
        except Exception as e:
            logger.error(f"Error loading reminders: {str(e)}")

    async def get_reminders(self):
        """Get all active, non-completed reminders"""
        await self._init_db()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT * FROM reminders WHERE completed = 0 ORDER BY due_time ASC'
                )
                rows = await cursor.fetchall()
                return [dict(zip([c[0] for c in cursor.description], row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting reminders: {str(e)}")
            return []
    
    async def set_timer(self, duration_seconds, description="Timer"):
        """Set a simple timer"""
        await self._init_db()
        now = datetime.datetime.now()
        due_time = now + datetime.timedelta(seconds=duration_seconds)
        reminder_id = f"timer_{int(time.time())}_{duration_seconds}"
        
        reminder = {
            "id": reminder_id,
            "type": "timer",
            "description": description,
            "created_at": now.isoformat(),
            "due_time": due_time.isoformat(),
            "duration_seconds": duration_seconds,
            "completed": 0
        }
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO reminders (id, type, description, created_at, due_time, duration_seconds, completed) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (reminder["id"], reminder["type"], reminder["description"], reminder["created_at"], 
                     reminder["due_time"], reminder["duration_seconds"], reminder["completed"])
                )
                await db.commit()
            self._schedule_reminder(reminder)
            logger.info(f"Timer set: {description} (ID: {reminder_id})")
            return reminder
        except Exception as e:
             logger.error(f"Error setting timer: {str(e)}")
             return None

    async def set_reminder(self, due_time_iso, description):
        """Set a reminder for a specific time"""
        await self._init_db()
        now = datetime.datetime.now()
        reminder_id = f"reminder_{int(time.time())}"
        
        reminder = {
            "id": reminder_id,
            "type": "reminder",
            "description": description,
            "created_at": now.isoformat(),
            "due_time": due_time_iso,
            "duration_seconds": None,
            "completed": 0
        }
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO reminders (id, type, description, created_at, due_time, completed) VALUES (?, ?, ?, ?, ?, ?)',
                    (reminder["id"], reminder["type"], reminder["description"], 
                     reminder["created_at"], reminder["due_time"], reminder["completed"])
                )
                await db.commit()
            self._schedule_reminder(reminder)
            logger.info(f"Reminder set: {description} (ID: {reminder_id})")
            return reminder
        except Exception as e:
             logger.error(f"Error setting reminder: {str(e)}")
             return None

    async def cancel_reminder(self, reminder_id):
        """Cancel an active reminder by marking completed"""
        success = await self._mark_completed(reminder_id)
        if success:
            # Cancel the task if it's running
            if reminder_id in self.tasks:
                self.tasks[reminder_id].cancel()
                del self.tasks[reminder_id]
                logger.info(f"Cancelled reminder task {reminder_id}")
            return True
        else:
            logger.warning(f"Reminder {reminder_id} not found for cancellation")
            return False
            
    async def _mark_completed(self, reminder_id):
        """Mark a reminder as completed in the database"""
        await self._init_db()
        try:
             async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'UPDATE reminders SET completed = 1 WHERE id = ? AND completed = 0',
                    (reminder_id,)
                )
                await db.commit()
                if cursor.rowcount > 0:
                     logger.info(f"Marked reminder {reminder_id} as completed")
                     return True
                return False
        except Exception as e:
             logger.error(f"Error marking reminder {reminder_id} complete: {str(e)}")
             return False

    def _schedule_reminder(self, reminder):
        """Create an asyncio task for the reminder"""
        due_time = datetime.datetime.fromisoformat(reminder["due_time"])
        now = datetime.datetime.now()
        
        seconds_until_due = (due_time - now).total_seconds()
        if seconds_until_due <= 0:
            logger.warning(f"Attempted to schedule past-due reminder {reminder['id']}")
            # Mark as completed immediately if needed
            asyncio.create_task(self._mark_completed(reminder["id"]))
            return
        
        reminder_id = reminder["id"]
        if reminder_id in self.tasks and not self.tasks[reminder_id].done():
            logger.info(f"Reminder task {reminder_id} already scheduled.")
            return
            
        task = asyncio.create_task(self._notify_at_time(reminder, seconds_until_due))
        self.tasks[reminder_id] = task
        logger.info(f"Scheduled task for reminder {reminder_id} in {seconds_until_due:.1f}s")

    async def _notify_at_time(self, reminder, delay_seconds):
        """Wait for the specified time and send notification"""
        try:
            await asyncio.sleep(delay_seconds)
            
            # Double-check if it was cancelled or completed while sleeping
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('SELECT completed FROM reminders WHERE id = ?', (reminder["id"],))
                row = await cursor.fetchone()
                if not row or row[0] == 1:
                    logger.info(f"Reminder {reminder['id']} was completed/cancelled before notification.")
                    return

            # Send notification
            desc = reminder["description"]
            if reminder["type"] == "timer":
                message = f"Timer complete: {desc}"
            else:
                message = f"Reminder: {desc}"
            
            await self._show_notification("Rin Assistant", message)
            
            # Mark as completed in DB
            await self._mark_completed(reminder["id"])
            
        except asyncio.CancelledError:
            logger.info(f"Reminder task {reminder['id']} was cancelled")
        except Exception as e:
            logger.error(f"Error in reminder notification task {reminder['id']}: {str(e)}", exc_info=True)
            # Attempt to mark as completed even on error to prevent re-notification
            await self._mark_completed(reminder["id"])
        finally:
            # Clean up task reference
            if reminder["id"] in self.tasks:
                del self.tasks[reminder["id"]]

    async def _show_notification(self, title, message):
        """Show notification using console and TTS"""
        logger.info(f"Notification: {message}")
        
        # Generate speech notification
        audio_path = None
        try:
            audio_path = await self.tts.synthesize(message)
        except Exception as e:
            logger.error(f"Error generating audio notification: {str(e)}")
        
        # System notification - using console for now instead of Plyer
        # In a full implementation, we would use Plyer's notification system
        try:
            # Print a visible console notification
            print(f"\n{'='*50}")
            print(f"📢 NOTIFICATION: {title}")
            print(f"📝 {message}")
            print(f"{'='*50}\n")
        except Exception as e:
            logger.error(f"Error showing console notification: {str(e)}")
            
        # Play sound *after* showing notification
        if audio_path:
            await self._play_notification_sound(audio_path)

    async def _play_notification_sound(self, audio_path):
        """Play notification sound - simplified for this implementation"""
        # In a full implementation, we would use sounddevice or another audio library
        try:
            logger.info(f"🔊 Playing notification sound: {audio_path}")
            # For now, just log the audio path
            # In a full implementation, this would use sounddevice or similar
        except Exception as e:
            logger.error(f"Error playing notification sound: {str(e)}") 
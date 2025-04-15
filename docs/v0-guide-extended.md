# Rin V0 — Extended Features Guide

This guide builds upon the [Core Implementation Guide](./rin-v0-core-implementation-guide) to complete the remaining V0 features. By following this guide, you'll implement list storage, timers/reminders, web search capabilities, Telegram integration, and email drafting functionality.

> 🟣 These implementations complete the V0 feature set, providing a fully functional prototype assistant.

---

## 📋 Overview of Extended Features

| Feature | Purpose | Implementation Approach |
| ------- | ------- | ----------------------- |
| Simple List Storage | Store and manage basic lists (shopping, tasks, etc.) | SQLite-based storage with CRUD operations |
| Local Timer/Reminder | Create and manage basic reminders and timers | SQLite with aiosqlite for storage and Plyer for notifications |
| Web Search + Summary | Retrieve and summarize web content | Integration with search API and LLM summary |
| Telegram Echo Bot | Interact with Rin via Telegram | Python Telegram Bot API integration |
| Email Draft Creator | Generate email drafts from prompts | SQLite with aiosqlite for storage |

---

## 📝 Simple List Storage

The list storage feature enables users to create and manage simple lists such as shopping lists, todo lists, and other types of collections.

### Implementation Approach

We'll implement a SQLite-based storage system using the `aiosqlite` library for asynchronous database access. This approach provides a robust, scalable, and concurrency-safe storage solution compared to simple JSON files.

```python
# rin/lists.py
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
```

### CLI Integration

Now, let's extend the CLI to support list management:

```python
# Add to rin/cli.py
import click
import asyncio
from rin.lists import ListManager # Make sure ListManager is imported

@cli.group()
def list_cmd(): # Renamed to avoid conflict with Python's list type
    """Manage lists (shopping, todos, etc.)"""
    pass

@list_cmd.command()
def show_all():
    """Show all available lists"""
    try:
        list_manager = ListManager()
        lists = asyncio.run(list_manager.get_lists())
        if not lists:
            click.echo("No lists found.")
            return
        
        click.echo("Available lists:")
        for name in lists:
            click.echo(f"- {name}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@list_cmd.command()
@click.argument('name')
def show(name):
    """Show items in a specific list"""
    try:
        list_manager = ListManager()
        items = asyncio.run(list_manager.get_list(name))
        if items is None: # Check for None, as get_list now returns None if not found
            click.echo(f"List '{name}' not found.")
            return
        
        if not items:
            click.echo(f"List '{name}' is empty.")
            return
            
        click.echo(f"Items in {name}:")
        for i, item in enumerate(items):
            click.echo(f"{i+1}. {item}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@list_cmd.command()
@click.argument('name')
@click.argument('items', nargs=-1)
def create(name, items):
    """Create a new list with optional initial items"""
    try:
        list_manager = ListManager()
        success = asyncio.run(list_manager.create_list(name, list(items)))
        if success:
            click.echo(f"Created list '{name}'.")
        else:
            click.echo(f"Failed to create list '{name}' (it may already exist).")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@list_cmd.command()
@click.argument('name')
@click.argument('item')
def add(name, item):
    """Add an item to a list"""
    try:
        list_manager = ListManager()
        success = asyncio.run(list_manager.add_item(name, item))
        if success:
            click.echo(f"Added '{item}' to list '{name}'.")
        else:
            click.echo(f"Failed to add item to list '{name}'. List might not exist.")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@list_cmd.command()
@click.argument('name')
@click.argument('item_num', type=int)
def remove(name, item_num):
    """Remove an item from a list by its number"""
    try:
        list_manager = ListManager()
        # Adjust for 0-based indexing
        success = asyncio.run(list_manager.remove_item(name, item_num - 1))
        if success:
            click.echo(f"Removed item #{item_num} from list '{name}'.")
        else:
            click.echo(f"Failed to remove item from list '{name}'. Check list name and item number.")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@list_cmd.command()
@click.argument('name')
def delete(name):
    """Delete a list entirely"""
    try:
        list_manager = ListManager()
        success = asyncio.run(list_manager.delete_list(name))
        if success:
            click.echo(f"Deleted list '{name}'.")
        else:
            click.echo(f"Failed to delete list '{name}'. List might not exist.")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
```

### Assistant Integration

To enable natural language interactions with lists, add list handling to the core assistant:

```python
# Add to rin/core.py in the Assistant class
# (Make sure ListManager is imported)
async def handle_list_command(self, query):
    """Parse and handle list-related commands using SQLite ListManager"""
    list_manager = ListManager()
    
    # Simple pattern matching for list commands
    query = query.lower()
    
    # Helper functions (consider moving to a separate parsing module)
    def _extract_list_name(q):
        # Basic extraction, needs improvement for robustness
        match = re.search(r"(?:list|called|named) ['"]?([^'"].*?)['"]?(?: list)?(?:$| to | from )", q)
        return match.group(1).strip() if match else None

    def _extract_list_item(q):
        # Basic extraction
        match = re.search(r"(?:add|put) ['"]?([^'"].*?)['"]? to", q)
        return match.group(1).strip() if match else None
        
    # Create a new list
    if "create" in query and "list" in query:
        list_name = _extract_list_name(query)
        if not list_name:
            # Try to infer from context if name wasn't explicit
            match = re.search(r"create (?:a|an|the) (.*?) list", query)
            list_name = match.group(1).strip() if match else None
        
        if not list_name:
             return "What would you like to name your list?"
        
        success = await list_manager.create_list(list_name)
        if success:
            return f"I've created a new list called '{list_name}'."
        else:
            return f"It looks like you already have a list called '{list_name}'."
    
    # Show all lists
    if ("show" in query or "what are my" in query) and "lists" in query:
        lists = await list_manager.get_lists()
        if not lists:
            return "You don't have any lists yet. Would you like to create one?"
        
        return f"You have the following lists: {', '.join(lists)}."
    
    # Show items in a list
    if ("show" in query or "what's on" in query) and "list" in query:
        list_name = _extract_list_name(query)
        if not list_name:
            # Try to infer from context
            match = re.search(r"(?:show|what's on) my (.*?) list", query)
            list_name = match.group(1).strip() if match else None
            
        if not list_name:
            return "Which list would you like to see?"
        
        items = await list_manager.get_list(list_name)
        if items is None:
            return f"I couldn't find a list called '{list_name}'."
        
        if not items:
            return f"Your '{list_name}' list is empty."
        
        item_strings = [f"{i+1}. {item}" for i, item in enumerate(items)]
        return f"Here's your '{list_name}' list:\n" + "\n".join(item_strings)
    
    # Add to a list
    if "add" in query and "to" in query and "list" in query:
        list_name = _extract_list_name(query)
        item = _extract_list_item(query)
        
        if not list_name:
            return "Which list would you like to add to?"
        if not item:
            return f"What would you like to add to your '{list_name}' list?"
        
        success = await list_manager.add_item(list_name, item)
        if success:
            return f"Added '{item}' to your '{list_name}' list."
        else:
            return f"I couldn't add that item. Do you have a list called '{list_name}'?"
            
    # Remove from list (needs more robust parsing)
    # Example: "remove milk from my shopping list"
    remove_match = re.search(r"remove (?:item )?['"]?([^'"].*?)['"]? from (?:my|the)? (.*?) list", query)
    if remove_match:
        item_to_remove = remove_match.group(1).strip()
        list_name = remove_match.group(2).strip()
        
        items = await list_manager.get_list(list_name)
        if items is None:
            return f"I couldn't find a list called '{list_name}'."
            
        try:
            # Find the index of the item (case-insensitive match)
            item_index = next(i for i, it in enumerate(items) if it.lower() == item_to_remove.lower())
            success = await list_manager.remove_item(list_name, item_index)
            if success:
                return f"Removed '{item_to_remove}' from your '{list_name}' list."
            else:
                return f"I couldn't remove that item from '{list_name}'."
        except StopIteration:
            return f"I couldn't find '{item_to_remove}' on your '{list_name}' list."

    # Delete a list
    delete_match = re.search(r"delete (?:my|the) (.*?) list", query)
    if delete_match:
        list_name = delete_match.group(1).strip()
        success = await list_manager.delete_list(list_name)
        if success:
            return f"Okay, I've deleted the '{list_name}' list."
        else:
            return f"I couldn't find a list called '{list_name}' to delete."
            
    return None  # Return None if this handler can't process the query
```

### Usage Examples

```bash
# Create a shopping list
rin list-cmd create shopping milk eggs bread

# Show all lists
rin list-cmd show_all

# Show items in the shopping list
rin list-cmd show shopping

# Add an item to the list
rin list-cmd add shopping "chicken breast"

# Remove the second item from the list
rin list-cmd remove shopping 2

# Delete the list entirely
rin list-cmd delete shopping

# Using natural language via the assistant
rin ask "Create a new shopping list"
rin ask "Show me all my lists"
rin ask "Add milk to my shopping list"
rin ask "What's on my shopping list?"
rin ask "Remove bread from my shopping list"
rin ask "Delete my shopping list"
```

---

## ⏰ Local Timer/Reminder System

The timer/reminder system allows users to set quick timers and basic reminders that will trigger notifications.

### Implementation Approach

We'll use SQLite via `aiosqlite` for storing reminders and `Plyer` for cross-platform notifications. An `asyncio` scheduler will manage the reminder tasks.

```python
# rin/reminders.py
import json
import aiosqlite
import asyncio
import datetime
import platform
import logging
import time
from pathlib import Path
from plyer import notification # Use Plyer for notifications
from rin.config import RIN_DIR
from rin.logging_config import loggers
from rin.tts import TTSInterface

logger = loggers.get('core', logging.getLogger('rin.reminders'))

class ReminderManager:
    """Manages timers and reminders using SQLite and Plyer"""
    
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
                    # Mark past-due reminders as completed (or handle differently)
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
             if reminder_id in self.tasks:
                 del self.tasks[reminder_id]

    async def _show_notification(self, title, message):
        """Show notification using Plyer and TTS"""
        logger.info(f"Notification: {message}")
        
        # Generate speech notification
        audio_path = None
        try:
            audio_path = await self.tts.synthesize(message)
        except Exception as e:
            logger.error(f"Error generating audio notification: {str(e)}")
        
        # System notification using Plyer
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Rin Assistant",
                timeout=10  # Display for 10 seconds
            )
        except NotImplementedError:
             logger.warning("Notifications not supported on this platform via Plyer.")
             # Fallback to console print if Plyer fails
             print(f"\n[NOTIFICATION] {title}: {message}\n")
        except Exception as e:
            logger.error(f"Error showing system notification via Plyer: {str(e)}")
            print(f"\n[NOTIFICATION] {title}: {message}\n")
            
        # Play sound *after* showing notification
        if audio_path:
            await self._play_notification_sound(audio_path)

    async def _play_notification_sound(self, audio_path):
        """Play notification sound using sounddevice/soundfile"""
        try:
            import sounddevice as sd
            import soundfile as sf
            data, samplerate = sf.read(audio_path)
            sd.play(data, samplerate)
            sd.wait() # Wait for playback to finish
        except ImportError:
            logger.warning("sounddevice or soundfile not installed, skipping audio notification.")
        except Exception as e:
            logger.error(f"Error playing notification sound: {str(e)}")
```

### CLI Integration

Now, let's extend the CLI to support timer and reminder management:

```python
# Add to rin/cli.py
from rin.reminders import ReminderManager # Ensure import

@cli.group()
def reminder():
    """Manage timers and reminders"""
    pass

@reminder.command()
@click.argument('minutes', type=int)
@click.argument('description', required=False, default="Timer")
def timer(minutes, description):
    """Set a timer for X minutes"""
    try:
        reminder_manager = ReminderManager()
        seconds = minutes * 60
        reminder = asyncio.run(reminder_manager.set_timer(seconds, description))
        
        if reminder:
            due_time = datetime.datetime.fromisoformat(reminder["due_time"])
            formatted_time = due_time.strftime("%H:%M:%S")
            click.echo(f"Timer set: {description} (ID: {reminder['id']})")
            click.echo(f"Will notify at {formatted_time}")
        else:
            click.echo("Failed to set timer.")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@reminder.command("set") # Explicit name
@click.option('--time', '-t', required=True, help="Time (e.g., '15:30', '9am', 'tomorrow 10:00')")
@click.argument('description')
def set_reminder_cmd(time, description):
    """Set a reminder for a specific time"""
    # Basic time parsing (Consider using a library like `dateparser` for robustness)
    try:
        from dateutil import parser
        now = datetime.datetime.now()
        # Parse the time string relative to now
        due_time = parser.parse(time, default=now)
        
        # If parsed time is in the past, assume next occurrence (e.g., next day)
        if due_time <= now:
             if due_time.time() <= now.time(): 
                 due_time += datetime.timedelta(days=1)

        # Set reminder
        reminder_manager = ReminderManager()
        reminder = asyncio.run(reminder_manager.set_reminder(due_time.isoformat(), description))
        
        if reminder:
            formatted_time = due_time.strftime("%I:%M %p on %A") # More user-friendly format
            click.echo(f"Reminder set: {description} (ID: {reminder['id']})")
            click.echo(f"Will notify at {formatted_time}")
        else:
            click.echo("Failed to set reminder.")
            
    except ImportError:
         click.echo("Error: python-dateutil library is required for time parsing. `pip install python-dateutil`")
    except Exception as e:
        click.echo(f"Error parsing time or setting reminder: {str(e)}")

@reminder.command("list") # Explicit name
def list_reminders():
    """List all active reminders and timers"""
    try:
        reminder_manager = ReminderManager()
        reminders = asyncio.run(reminder_manager.get_reminders())
        
        if not reminders:
            click.echo("No active reminders or timers.")
            return
        
        click.echo("Active reminders and timers:")
        for r in reminders:
            due_time = datetime.datetime.fromisoformat(r["due_time"])
            formatted_time = due_time.strftime("%I:%M %p on %A")
            
            r_type = r["type"].capitalize()
            click.echo(f"{r_type} (ID: {r['id']}): {r['description']}")
            click.echo(f"  Due at: {formatted_time}")
            click.echo("")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@reminder.command()
@click.argument('reminder_id')
def cancel(reminder_id):
    """Cancel a reminder by ID"""
    try:
        reminder_manager = ReminderManager()
        success = asyncio.run(reminder_manager.cancel_reminder(reminder_id))
        
        if success:
            click.echo(f"Cancelled reminder with ID: {reminder_id}")
        else:
            click.echo(f"No active reminder found with ID: {reminder_id}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
```

### Assistant Integration

To enable natural language interactions with reminders, add timer/reminder handling to the core assistant:

```python
# Add to rin/core.py in the Assistant class
# Requires imports: from rin.reminders import ReminderManager, re, datetime, timedelta

async def handle_reminder_command(self, query):
    """Parse and handle reminder-related commands using SQLite ReminderManager"""
    reminder_manager = ReminderManager()
    query = query.lower()
    
    # Set a timer (duration based)
    timer_match = re.search(r'(set|create|start) (?:a|the)? timer (?:for|of) (\d+) (minute|minutes|min|mins|second|seconds|sec|secs|hour|hours|hr|hrs)', query)
    if timer_match:
        value = int(timer_match.group(2))
        unit = timer_match.group(3)
        seconds = 0
        if unit.startswith(('hour', 'hr')): seconds = value * 3600
        elif unit.startswith(('minute', 'min')): seconds = value * 60
        else: seconds = value
        
        description = "Timer"
        desc_match = re.search(r'(?:called|named|for) ["\']?([^"\']+)["\']?', query)
        if desc_match: description = desc_match.group(1).strip()
        
        reminder = await reminder_manager.set_timer(seconds, description)
        if reminder:
            due_time = datetime.datetime.fromisoformat(reminder["due_time"])
            formatted_time = due_time.strftime("%H:%M:%S")
            return f"Okay, I've set a {self._format_duration(seconds)} timer named '{description}'. I'll notify you at {formatted_time}."
        else:
            return "Sorry, I couldn't set that timer."

    # Set a reminder (specific time based)
    # Using a simpler regex, relying on dateutil.parser for flexibility
    reminder_match = re.search(r'(?:remind|reminder|remember) me to (.+?) (?:at|on|in) (.+)', query, re.IGNORECASE)
    if not reminder_match:
        reminder_match = re.search(r'set a reminder (?:for|to) (.+?) (?:at|on|in) (.+)', query, re.IGNORECASE)
        
    if reminder_match:
        action = reminder_match.group(1).strip()
        time_str = reminder_match.group(2).strip()
        
        try:
            from dateutil import parser
            now = datetime.datetime.now()
            due_time = parser.parse(time_str, default=now)
            if due_time <= now:
                 if due_time.time() <= now.time(): 
                     due_time += datetime.timedelta(days=1)

            reminder = await reminder_manager.set_reminder(due_time.isoformat(), action)
            if reminder:
                formatted_time = due_time.strftime("%I:%M %p on %A") # More user-friendly format
                return f"Okay, I'll remind you to {action} at {formatted_time}."
            else:
                return "Sorry, I couldn't set that reminder."
        except ImportError:
             return "I need the `python-dateutil` library to understand times like that. Please install it."
        except Exception as e:
            logger.error(f"Error parsing time for reminder: {e}")
            return "I had trouble understanding that time. Could you phrase it differently? (e.g., 'tomorrow at 3pm', 'in 2 hours')"

    # List reminders
    if re.search(r'(show|list|what|tell me about|any) (?:my)? (active )?(reminders|timers)', query):
        reminders = await reminder_manager.get_reminders()
        if not reminders:
            return "You don't have any active reminders or timers set."
        
        response = "Here are your active reminders and timers:\n"
        for i, r in enumerate(reminders):
            due_time = datetime.datetime.fromisoformat(r["due_time"])
            formatted_time = due_time.strftime("%I:%M %p on %A")
            r_type = r["type"].capitalize()
            response += f"{i+1}. {r_type}: {r['description']} at {formatted_time} (ID: {r['id']})\n"
        
        return response
        
    # Cancel reminder (basic matching by description or ID)
    cancel_match = re.search(r'(?:cancel|delete|remove) (?:the|my)? (?:reminder|timer) (?:for|called|named|with id) ["\']?([^"\']+)["\']?', query)
    if cancel_match:
        identifier = cancel_match.group(1).strip()
        reminders = await reminder_manager.get_reminders()
        found_reminder = None
        # Try matching by ID first
        for r in reminders:
            if r['id'] == identifier:
                found_reminder = r
                break
        # If not found by ID, try matching by description (case-insensitive)
        if not found_reminder:
             for r in reminders:
                 if r['description'].lower() == identifier.lower():
                      found_reminder = r
                      # TODO: Handle multiple matches? For now, cancel the first found.
                      break
                      
        if found_reminder:
            success = await reminder_manager.cancel_reminder(found_reminder['id'])
            if success:
                return f"Okay, I've cancelled the {found_reminder['type']} for '{found_reminder['description']}'."
            else:
                return f"I found the reminder, but couldn't cancel it for some reason."
        else:
            return f"I couldn't find an active reminder matching '{identifier}'."

    return None # Not a reminder command
    
# Helper methods in Assistant class (keep or refactor)
def _format_duration(self, seconds):
    # ... (implementation remains the same)
    pass
```

### Usage Examples

```bash
# Set a timer for 5 minutes
rin reminder timer 5 "Tea is ready"

# Set a reminder for a specific time using various formats
rin reminder set --time "15:30" "Team meeting"
rin reminder set --time "9am tomorrow" "Morning Standup"
rin reminder set --time "next Friday 1pm" "Project Demo"

# List all active reminders and timers
rin reminder list

# Cancel a reminder by its unique ID
rin reminder cancel timer_1678886400_300

# Using natural language via the assistant
rin ask "Set a timer for 10 minutes for my laundry"
rin ask "Remind me to call John at 3:30pm tomorrow"
rin ask "What are my reminders?"
rin ask "Cancel the reminder to call John"
```

---

## 🔍 Web Search + Summary

This feature enables Rin to search the web for information and provide concise summaries of the results.

### Implementation Approach

We'll implement a flexible web search system using a `SearchProvider` abstraction. This allows different search backends (like SerpAPI, SearxNG, DuckDuckGo) to be configured. For V0, we'll implement the `SerpAPISearch` provider. The results will be summarized using the configured LLM.

```python
# rin/search.py
import os
import json
import aiohttp
import logging
import urllib.parse
from abc import ABC, abstractmethod
from rin.config import SERPAPI_KEY, SEARCH_PROVIDER # Add SEARCH_PROVIDER to config
from rin.logging_config import loggers
from rin.llm import LLMInterface

logger = loggers.get('core', logging.getLogger('rin.search'))

# --- Search Provider Abstraction ---

class SearchProvider(ABC):
    """Abstract base class for search providers."""
    @abstractmethod
    async def search(self, query, num_results=5):
        """Perform search and return structured results or error dict."""
        pass

class SerpAPISearch(SearchProvider):
    """Search provider using SerpAPI."""
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_KEY not found in environment variables.")
        logger.info("Initialized SerpAPISearch provider.")

    async def search(self, query, num_results=5):
        encoded_query = urllib.parse.quote(query)
        url = f"https://serpapi.com/search.json?q={encoded_query}&num={num_results}&api_key={self.api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error from SerpAPI ({response.status}): {error_text}")
                        return {"error": f"Search API error: {response.status}"}
                    
                    data = await response.json()
                    
                    # Basic result parsing
                    if "organic_results" not in data or not data["organic_results"]:
                        return {"results": []} # Return empty list if no organic results
                        
                    results = []
                    for res in data["organic_results"][:num_results]:
                         results.append({
                            "title": res.get("title", "No title"),
                            "link": res.get("link", "#"),
                            "snippet": res.get("snippet", "No description available.")
                        })
                    return {"results": results}
                    
        except Exception as e:
            logger.error(f"Error during SerpAPI search: {str(e)}", exc_info=True)
            return {"error": f"Failed to execute search: {str(e)}"}

class PlaceholderSearch(SearchProvider):
    """Placeholder for other search providers like SearxNG or DuckDuckGo."""
    async def search(self, query, num_results=5):
        logger.warning(f"PlaceholderSearch used for query: {query}. No actual search performed.")
        return {"error": "Search provider not fully implemented."}
        # Example structure if implemented:
        # return {"results": [{"title": "Example", "link": "#", "snippet": "..."}]}

# --- Factory Function --- 

def create_search_provider() -> SearchProvider:
    """Creates the configured search provider instance."""
    provider_name = os.getenv("SEARCH_PROVIDER", "serpapi").lower()
    
    if provider_name == "serpapi":
        try:
            return SerpAPISearch()
        except ValueError as e:
             logger.error(f"Failed to initialize SerpAPI: {e}. Falling back to placeholder.")
             return PlaceholderSearch()
    # Add elif for "searxng", "duckduckgo", etc. here
    # elif provider_name == "searxng":
    #    return SearxNGSearch() # Assuming SearxNGSearch class exists
    else:
        logger.warning(f"Unknown SEARCH_PROVIDER '{provider_name}'. Using placeholder.")
        return PlaceholderSearch()

# --- Web Search Manager ---

class WebSearchManager:
    """Manages web search and summarization using a configured SearchProvider."""
    
    def __init__(self):
        self.search_provider = create_search_provider()
        self.llm = LLMInterface.create() # Assuming LLMInterface factory exists
        logger.info(f"Web Search Manager initialized with provider: {self.search_provider.__class__.__name__}")
    
    async def search_and_summarize(self, query, num_results=5):
        """Search the web using the configured provider and summarize results."""
        try:
            # Perform the search using the provider
            search_result = await self.search_provider.search(query, num_results)
            
            if "error" in search_result:
                return {"error": search_result["error"]}
                
            results_list = search_result.get("results", [])
            if not results_list:
                 return {"summary": "I couldn't find any relevant web results for that query.", "results": []}
            
            # Format results for LLM summarization
            search_context = f"Search query: {query}\n\nTop {len(results_list)} results:\n"
            for i, result in enumerate(results_list):
                search_context += f"{i+1}. {result['title']}\n"
                search_context += f"   URL: {result['link']}\n"
                search_context += f"   Snippet: {result['snippet']}\n\n"
            
            # Generate a summary using the LLM
            prompt = f"""Please provide a concise summary of these search results for the query \"{query}\". 
            Focus on extracting the most relevant information that answers the query.
            If the results don't seem to address the query well, mention that.
            
            {search_context}
            
            Summary:"""
            
            summary = await self.llm.generate_response(prompt)
            
            return {
                "query": query,
                "results": results_list, # Return the structured results
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error in search and summarize: {str(e)}", exc_info=True)
            return {"error": f"An unexpected error occurred during search and summarization: {str(e)}"}

    async def raw_search(self, query, num_results=5):
         """Performs a raw search without summarization."""
         return await self.search_provider.search(query, num_results)
```

### Update Configuration

Ensure the necessary API keys and provider choice are in the configuration:

```python
# Update rin/config.py to add:
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serpapi") # Default to serpapi
```

Update your `.env` file:

```env
# Add/Update in your .env file
SERPAPI_KEY=your_serpapi_key_here
# Optional: Choose a different provider if implemented
# SEARCH_PROVIDER=searxng 
```

### CLI Integration

Now, let's extend the CLI to support web search using the new manager:

```python
# Add to rin/cli.py
from rin.search import WebSearchManager # Import the manager

@cli.command()
@click.argument('query')
@click.option('--summary/--no-summary', default=True, help="Summarize results with LLM")
@click.option('--num-results', type=int, default=3, help="Number of results to fetch/summarize")
def search(query, summary, num_results):
    """Search the web for information using the configured provider"""
    try:
        search_manager = WebSearchManager()
        
        if summary:
            result = asyncio.run(search_manager.search_and_summarize(query, num_results=num_results))
            
            if "error" in result:
                click.echo(f"Error: {result['error']}")
                return
            
            click.echo(f"Search results for: {query}\n")
            click.echo("Summary:")
            click.echo(result.get("summary", "No summary generated."))
            
            if result.get("results"):
                click.echo("\nSources:")
                for i, res in enumerate(result["results"]):
                    click.echo(f"{i+1}. {res['title']}")
                    click.echo(f"   {res['link']}")
        else:
            # Raw results without summary
            result = asyncio.run(search_manager.raw_search(query, num_results=num_results))
            
            if "error" in result:
                click.echo(f"Error: {result['error']}")
                return
                
            results_list = result.get("results", [])
            if results_list:
                click.echo(f"Search results for: {query}\n")
                for i, res in enumerate(results_list):
                    click.echo(f"{i+1}. {res.get('title', 'No title')}")
                    click.echo(f"   {res.get('link', '#')}")
                    click.echo(f"   {res.get('snippet', 'No description.')}")
                    click.echo("")
            else:
                click.echo("No results found.")
                
    except Exception as e:
        click.echo(f"CLI Error: {str(e)}")
```

### Assistant Integration

To enable natural language web searches, update the search handling in the core assistant:

```python
# Add to rin/core.py in the Assistant class
# Ensure WebSearchManager is imported

async def handle_search_command(self, query):
    """Handle web search related commands using WebSearchManager"""
    import re
    
    # Check if this is a search query
    search_patterns = [
        r"search (?:for|about) (.+)",
        r"look up (.+)",
        r"find (?:information|info) (?:about|on) (.+)",
        r"what is (.+)",
        r"who is (.+)",
        r"tell me about (.+)"
    ]
    
    for pattern in search_patterns:
        match = re.search(pattern, query.lower())
        if match:
            search_query = match.group(1).strip()
            logger.info(f"Handling search query: '{search_query}'")
            
            # Perform the search and summarize
            try:
                search_manager = WebSearchManager()
                result = await search_manager.search_and_summarize(search_query)
            except Exception as e:
                 logger.error(f"Failed to instantiate or use WebSearchManager: {e}", exc_info=True)
                 return "Sorry, I'm having trouble with my search capability right now."

            if "error" in result:
                return f"I couldn't search for that: {result['error']}"
            
            # Combine summary and maybe top links (optional)
            response_text = result.get('summary', "I found some results, but couldn't summarize them.")
            # Optionally add top links
            # top_results = result.get('results', [])[:1] # Get top 1 result
            # if top_results:
            #    response_text += f"\n\nTop result: {top_results[0]['title']} ({top_results[0]['link']})"
            
            return response_text
    
    return None  # Not a search query
```

### Usage Examples

```bash
# Search with summary (default)
rin search "latest advancements in AI"

# Search without summary, get 5 raw results
rin search --no-summary --num-results 5 "python async libraries"

# Using natural language via the assistant
rin ask "Search for the weather in London"
rin ask "What is the capital of France?"
rin ask "Tell me about superconductors"
```

---

## 💬 Telegram Echo Bot

This feature allows users to interact with Rin via Telegram, extending the assistant's reach beyond the command line.

### Implementation Approach

We'll use the `python-telegram-bot` library to create a Telegram bot that forwards messages to Rin and returns responses.

```python
# rin/telegram_bot.py
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from rin.core import Assistant
from rin.config import TELEGRAM_BOT_TOKEN
from rin.logging_config import loggers

logger = loggers.get('core', logging.getLogger('rin.telegram'))

class RinTelegramBot:
    """Telegram bot integration for Rin"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not found. Telegram bot functionality disabled.")
            return
        
        self.assistant = Assistant()
        logger.info("Telegram Bot initialized")
    
    async def start(self):
        """Start the Telegram bot"""
        if not self.token:
            logger.error("Cannot start Telegram bot: No token provided")
            return False
        
        try:
            # Create the application
            application = ApplicationBuilder().token(self.token).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Start the bot
            await application.initialize()
            await application.start()
            await application.run_polling()
            
            return True
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {str(e)}")
            return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "👋 Hello! I'm Rin, your personal assistant. Ask me anything!"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
*Rin Assistant Bot*

You can ask me questions, and I'll do my best to help!

*Commands:*
/start - Start the conversation
/help - Show this help message

Just type your questions or requests normally, and I'll respond.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        logger.info(f"Telegram message from {user_id}: {user_message}")
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Process the message with Rin
            response = await self.assistant.process_query(user_message)
            
            # Send the response
            await update.message.reply_text(response.get("text", "I'm not sure how to respond to that."))
        except Exception as e:
            logger.error(f"Error processing Telegram message: {str(e)}")
            await update.message.reply_text("Sorry, I encountered an error while processing your request.")
```

### Update Configuration

Add the Telegram Bot token to the configuration:

```python
# Update rin/config.py to add:
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
```

Also update your `.env` file:

```env
# Add to your .env file
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### CLI Integration

Now, let's extend the CLI to manage the Telegram bot:

```python
# Add to rin/cli.py

@cli.command()
def telegram():
    """Start the Telegram bot"""
    try:
        from rin.telegram_bot import RinTelegramBot
        
        click.echo("Starting Telegram bot...")
        bot = RinTelegramBot()
        
        # Run the bot until terminated
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        click.echo("\nStopping Telegram bot...")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
```

### Usage Instructions

1. **Create a Telegram Bot**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` command
   - Follow instructions to set a name and username
   - Save the API token provided

2. **Configure Rin**:
   - Add the token to your `.env` file: `TELEGRAM_BOT_TOKEN=your_token_here`

3. **Run the Bot**:
   ```bash
   # Start the Telegram bot
   rin telegram
   ```

4. **Interact with Rin on Telegram**:
   - Open Telegram and find your bot by the username you created
   - Start a conversation with `/start`
   - Ask questions or give commands as you would via CLI

---

## 📧 Email Draft Creator

This feature allows Rin to generate email drafts based on user prompts, helping with email composition.

### Implementation Approach

We'll use the LLM to generate email content based on user prompts and store the resulting drafts in the SQLite database via `aiosqlite`.

```python
# rin/email_drafts.py
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
                "to": recipient,
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
                     (draft["id"], draft["to"], draft["subject"], draft["content"], 
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
```

### CLI Integration

Now, let's extend the CLI to support email draft creation and management using the SQLite backend:

```python
# Add to rin/cli.py
from rin.email_drafts import EmailDraftCreator # Ensure import

@cli.group()
def email():
    """Create and manage email drafts"""
    pass

@email.command()
@click.option('--to', prompt='Recipient', help='Email recipient')
@click.option('--subject', prompt='Subject', help='Email subject')
@click.option('--tone', default='professional', help='Email tone (professional, friendly, formal, etc.)')
@click.argument('content_prompt', required=True)
def draft(to, subject, tone, content_prompt):
    """Create an email draft from a prompt"""
    try:
        draft_creator = EmailDraftCreator()
        draft = asyncio.run(draft_creator.create_draft(to, subject, content_prompt, tone))
        
        if "error" in draft or not draft:
            click.echo(f"Error creating draft: {draft.get('error', 'Unknown error')}")
            return
        
        click.echo(f"Created email draft (ID: {draft['id']}) stored in database.")
        click.echo(f"To: {draft['to']}")
        click.echo(f"Subject: {draft['subject']}")
        click.echo(f"\n{draft['content']}")
        click.echo(f"\nUse 'rin email show {draft['id']}' to view later.")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@email.command(name="list")
def list_drafts():
    """List all email drafts from the database"""
    try:
        draft_creator = EmailDraftCreator()
        drafts = asyncio.run(draft_creator.get_drafts())
        
        if not drafts:
            click.echo("No email drafts found in the database.")
            return
        
        click.echo("Email drafts (from database):")
        for draft in drafts:
            created_at_str = draft.get("created_at", "Unknown time")
            try: # Format timestamp nicely
                 created_dt = datetime.datetime.fromisoformat(created_at_str)
                 created_at_display = created_dt.strftime("%Y-%m-%d %H:%M")
            except:
                 created_at_display = created_at_str
                 
            click.echo(f"ID: {draft['id']}")
            click.echo(f"Created: {created_at_display}")
            click.echo(f"To: {draft['to']}")
            click.echo(f"Subject: {draft['subject']}")
            click.echo(f"Tone: {draft.get('tone', 'professional')}")
            click.echo("-" * 40)
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@email.command()
@click.argument('draft_id')
def show(draft_id):
    """Show an email draft by ID from the database"""
    try:
        draft_creator = EmailDraftCreator()
        draft = asyncio.run(draft_creator.get_draft(draft_id))
        
        if not draft:
            click.echo(f"Draft {draft_id} not found in database.")
            return
        
        created_at_str = draft.get("created_at", "Unknown time")
        try: # Format timestamp nicely
             created_dt = datetime.datetime.fromisoformat(created_at_str)
             created_at_display = created_dt.strftime("%Y-%m-%d %H:%M")
        except:
             created_at_display = created_at_str
             
        click.echo(f"Email Draft (ID: {draft['id']}) - From Database")
        click.echo(f"Created: {created_at_display}")
        click.echo(f"To: {draft['to']}")
        click.echo(f"Subject: {draft['subject']}")
        click.echo(f"Tone: {draft.get('tone', 'professional')}")
        click.echo("\nContent:")
        click.echo(draft['content'])
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@email.command()
@click.argument('draft_id')
def delete(draft_id):
    """Delete an email draft by ID from the database"""
    try:
        draft_creator = EmailDraftCreator()
        success = asyncio.run(draft_creator.delete_draft(draft_id))
        
        if success:
            click.echo(f"Deleted draft {draft_id} from database.")
        else:
            click.echo(f"Failed to delete draft {draft_id}. Draft might not exist.")
    except Exception as e:
        click.echo(f"Error: {str(e)}")
```

### Assistant Integration

To enable natural language email draft creation using the SQLite backend:

```python
# Add to rin/core.py in the Assistant class
# Ensure EmailDraftCreator is imported

async def handle_email_command(self, query):
    """Parse and handle email-related commands using SQLite EmailDraftCreator"""
    import re
    
    # Check if this is an email draft request (patterns remain the same)
    email_patterns = [
        r"(?:write|draft|compose) (?:an |a )?email (?:to|for) (.+?) (?:about|regarding|re:|on) (.+)",
        r"help me (?:write|draft|compose) (?:an |a )?email (?:to|for) (.+?) (?:about|regarding|re:|on) (.+)",
        r"create (?:an |a )?email (?:to|for) (.+?) (?:about|regarding|re:|on) (.+)"
    ]
    
    for pattern in email_patterns:
        match = re.search(pattern, query.lower())
        if match:
            recipient = match.group(1).strip()
            topic = match.group(2).strip()
            
            # Extract tone if specified (remains the same)
            tone = "professional"  # default
            tone_match = re.search(r"in a (professional|formal|casual|friendly|informal) tone", query.lower())
            if tone_match: tone = tone_match.group(1)
            
            # Create email draft using the updated creator
            try:
                 draft_creator = EmailDraftCreator()
                 draft = await draft_creator.create_draft(recipient, topic, query, tone)
            except Exception as e:
                 logger.error(f"Failed to instantiate or use EmailDraftCreator: {e}", exc_info=True)
                 return "Sorry, I'm having trouble with my email drafting capability right now."

            if "error" in draft or not draft:
                return f"I couldn't create an email draft: {draft.get('error', 'Unknown error')}"
            
            return f"I've drafted an email to {recipient} about {topic}. Here it is:\n\n{draft['content']}\n\n(Saved to database with ID: {draft['id']})"
    
    # List drafts (from database)
    if re.search(r"(show|list|what) (?:are |my )?email drafts", query.lower()):
        try:
            draft_creator = EmailDraftCreator()
            drafts = await draft_creator.get_drafts()
        except Exception as e:
             logger.error(f"Failed to get drafts: {e}", exc_info=True)
             return "Sorry, I couldn't retrieve your email drafts right now."

        if not drafts:
            return "You don't have any email drafts saved in the database."
        
        response = "Here are your recent email drafts from the database:\n"
        for i, draft in enumerate(drafts[:5]):  # Show at most 5
             created_at_str = draft.get("created_at", "Unknown")
             try: created_dt = datetime.datetime.fromisoformat(created_at_str); created_at_display = created_dt.strftime("%b %d %H:%M")
             except: created_at_display = "??"
             response += f"{i+1}. To: {draft['to']} - Subject: {draft['subject']} ({created_at_display}, ID: {draft['id']})\n"
        
        return response
    
    return None  # Not an email-related command
```

### Usage Examples

```bash
# Create an email draft (saved to SQLite)
rin email draft --to "john@example.com" --subject "Meeting Tomorrow" "Discuss project timeline and deliverables"

# Create with a specific tone
rin email draft --to "team@example.com" --subject "Weekend Plans" --tone "friendly" "Invite everyone to a team barbecue on Saturday"

# List all drafts (from SQLite)
rin email list

# View a specific draft by ID (from SQLite)
rin email show email_20231027_103000_1234

# Delete a draft by ID (from SQLite)
rin email delete email_20231027_103000_1234

# Using natural language via the assistant
rin ask "Write an email to my boss about requesting vacation time next month"
rin ask "Draft a friendly email to the team about our project success"
rin ask "Show me my email drafts"
```

---

## 🎭 Next Steps

With these extended features, you now have a fully functional V0 prototype assistant. You can further enhance these features with:

1. **More List Types**: Add categorization and priority to lists
2. **Advanced Reminders**: Add recurring reminders and calendar integration
3. **Enhanced Search**: Improve search relevance with more context
4. **Rich Telegram Responses**: Add media and formatting to Telegram messages
5. **Email Integration**: Connect with SMTP to actually send drafted emails

These enhancements would begin moving your implementation toward V1 capabilities, but the current implementation satisfies all the core V0 requirements.

---

## 🔄 Recommended Refactorings

Based on deeper research, here are key improvements to consider for a more robust implementation:

### 📦 Package & Dependency Improvements

```python
# Abstract search providers with a clean interface
class SearchProvider:
    """Abstract base class for search providers"""
    @abstractmethod
    async def search(self, query, num_results=5):
        pass

class SerpAPISearch(SearchProvider):
    """SerpAPI implementation"""
    async def search(self, query, num_results=5):
        # Current implementation
        pass

class SearxNGSearch(SearchProvider):
    """Self-hosted SearxNG implementation (open source alternative)"""
    async def search(self, query, num_results=5):
        # Implementation for SearxNG
        pass
```

- **Replace JSON with SQLite** for lists, reminders, and drafts to enable:
  - ACID compliance (data integrity)
  - Better concurrency support
  - More robust error handling
  - Improved scaling for growing data

### 🚀 Async + Event Handling Architecture

```python
# Better async handling for reminders
async def schedule_reminder(self, reminder):
    """Schedule a reminder with proper async patterns"""
    # Create a persistent task that survives across runs
    delay = (reminder['due_time'] - datetime.now()).total_seconds()
    if delay > 0:
        # Use create_task for long-lived background operations
        task = asyncio.create_task(self._notify_at_time(reminder, delay))
        # Store reference to prevent garbage collection
        self.tasks[reminder['id']] = task
        
# Offload blocking operations
async def save_list(self, list_data):
    """Non-blocking file operations using executor"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,  # Default executor
        self._save_list_sync,
        list_data
    )
```

- Ensure telegram_bot, tts, and llm integrations are non-blocking
- Use asyncio.create_task() rather than direct coroutine calls for background processes

### 🧱 Modular & Abstract Core Logic

```python
# Create a skills directory structure
# rin/
#   skills/
#     __init__.py
#     lists.py
#     reminders.py
#     search.py
#     email.py

# Skill interface pattern
class Skill:
    """Base class for assistant skills"""
    async def can_handle(self, query):
        """Return True if this skill can handle the query"""
        pass
        
    async def handle(self, query):
        """Process query and return response"""
        pass

# In core.py
async def process_query(self, query, respond_with_voice=False):
    """Process with modular skills architecture"""
    # Try each skill until one can handle it
    for skill in self.skills: # Assumes self.skills is populated
        if await skill.can_handle(query):
            response = await skill.handle(query)
            if response:
                # Assuming self._format_response exists to handle TTS/output
                return await self._format_response(response, respond_with_voice)

    # Fall back to general LLM if no skill matches
    logger.info("No specific skill handled the query, falling back to LLM.")
    response = await self.llm.generate_response(query)
    await self.storage.save_interaction(query, response) # Assumes storage is available
    return await self._format_response(response, respond_with_voice)

async def _format_response(self, text_response, respond_with_voice):
     """Helper to format response and handle TTS"""
     audio_path = None
     if respond_with_voice:
         try:
             audio_path = await self.tts.synthesize(text_response)
         except Exception as e:
             logger.error(f"TTS synthesis failed: {e}")
             
     return {
         "text": text_response,
         "audio_path": audio_path
     }
```

### 🌍 Cross-Platform Consistency

```python
# Use Plyer for notifications instead of platform-specific code
from plyer import notification

async def show_notification(self, title, message):
    """Cross-platform notifications"""
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Rin Assistant"
        )
    except Exception as e:
        logger.error(f"Notification failed: {str(e)}")
        # Fallback to console notification
        print(f"\n[NOTIFICATION] {title}: {message}\n")

# Audio playback with cross-platform fallbacks
async def play_audio(self, file_path):
    """Cross-platform audio playback"""
    try:
        # Try primary audio player (sounddevice)
        import sounddevice as sd
        import soundfile as sf
        data, samplerate = sf.read(file_path)
        sd.play(data, samplerate)
        sd.wait()
        return True
    except Exception as e:
        # Fall back to OS-specific methods as needed
        # ... existing fallback code ...
```

### 🛡️ Future-Proof Against Vendor Lock-In

```python
# Abstract LLM providers with factory pattern
class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt):
        pass
        
class OpenAIProvider(LLMProvider):
    # Current implementation
    pass
    
class OllamaProvider(LLMProvider):
    # Local LLM alternative
    async def generate_response(self, prompt):
        # Implementation for Ollama
        pass

# Configuration-driven provider selection
def create_llm_provider():
    """Factory function to create the appropriate LLM provider"""
    provider_type = config.LLM_PROVIDER.lower()
    if provider_type == "openai":
        return OpenAIProvider()
    elif provider_type == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
```

### 🧰 Developer Quality-of-Life Enhancements

- **Modern Packaging**: Utilize `pyproject.toml` (using tools like `Poetry` or `Hatch`) for dependency management and packaging instead of `setup.py`.
- **Unit Testing**: Create a `tests/` directory and implement unit tests for core components like list management, reminder scheduling, and search result parsing to ensure reliability and prevent regressions.

These refactorings create a more maintainable, extensible codebase that avoids vendor lock-in and handles real-world usage requirements more effectively.

---

## 📝 Implementation Tips and Troubleshooting

For additional guidance on implementing this guide, especially regarding common issues with regular expressions, SQLite operations, and error handling, please refer to the [Rin V0 Implementation Tips](./implementation-tips.md) document. This resource provides practical solutions to challenges encountered during development.

---

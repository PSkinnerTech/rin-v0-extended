import asyncio
import logging
import datetime
import re
from rin.llm import LLMInterface
from rin.tts import TTSInterface
from rin.stt import STTInterface, WHISPER_AVAILABLE
from rin.storage import Storage
from rin.config import TTS_ENGINE, STT_ENGINE
from rin.logging_config import loggers
from rin.lists import ListManager
from rin.reminders import ReminderManager

logger = loggers['core']

class Assistant:
    """Core assistant logic, separate from UI/CLI concerns"""
    
    def __init__(self):
        self.storage = Storage()
        self.llm = LLMInterface.create()
        self.tts = TTSInterface.create(TTS_ENGINE)
        
        # Set up STT engine with fallback to dummy if configured engine not available
        stt_engine = STT_ENGINE
        try:
            self.stt = STTInterface.create(stt_engine)
        except (ImportError, NotImplementedError) as e:
            logger.warning(f"Failed to initialize {stt_engine} STT engine: {str(e)}")
            logger.warning("Falling back to dummy STT engine (no actual speech recognition)")
            self.stt = STTInterface.create("dummy")
            stt_engine = "dummy"
            
        logger.info("Assistant initialized with TTS: %s, STT: %s", TTS_ENGINE, stt_engine)
    
    async def process_query(self, query, respond_with_voice=False):
        """Process a text query and return response"""
        try:
            logger.info("Processing query: %s", query)
            
            # Check if this is a time-related query we can handle locally
            local_response = self._handle_local_queries(query)
            if local_response:
                logger.info(f"Handled query locally: {local_response}")
                response = local_response
            else:
                # Check if this is a list-related query
                list_response = await self.handle_list_command(query)
                if list_response:
                    logger.info(f"Handled list query: {list_response}")
                    response = list_response
                else:
                    # Check if this is a reminder-related query
                    reminder_response = await self.handle_reminder_command(query)
                    if reminder_response:
                        logger.info(f"Handled reminder query: {reminder_response}")
                        response = reminder_response
                    else:
                        # If not handled locally, use the LLM
                        response = await self.llm.generate_response(query)
                
            await self.storage.save_interaction(query, response)
            
            audio_path = None
            if respond_with_voice:
                audio_path = await self.tts.synthesize(response)
                
            return {
                "text": response,
                "audio_path": audio_path
            }
        except Exception as e:
            logger.error("Error processing query: %s", str(e), exc_info=True)
            return {
                "error": str(e),
                "text": "I encountered an error while processing your request."
            }
    
    def _handle_local_queries(self, query):
        """Handle common queries locally without using the LLM"""
        # Convert query to lowercase for easier matching
        query_lower = query.lower()
        
        # Time-related queries
        time_patterns = [
            r"what time is it",
            r"current time",
            r"tell me the time",
        ]
        
        # Date-related queries
        date_patterns = [
            r"what day is it",
            r"what is the date",
            r"current date",
            r"today's date",
        ]
        
        # Check for time queries
        for pattern in time_patterns:
            if re.search(pattern, query_lower):
                now = datetime.datetime.now()
                return f"The current time is {now.strftime('%I:%M %p')}."
        
        # Check for date queries
        for pattern in date_patterns:
            if re.search(pattern, query_lower):
                now = datetime.datetime.now()
                return f"Today is {now.strftime('%A, %B %d, %Y')}."
        
        # If no patterns match, return None to use the LLM
        return None
    
    async def handle_list_command(self, query):
        """Parse and handle list-related commands using SQLite ListManager"""
        list_manager = ListManager()
        
        # Simple pattern matching for list commands
        query = query.lower()
        
        # Helper functions (consider moving to a separate parsing module)
        def _extract_list_name(q):
            # Basic extraction, needs improvement for robustness
            match = re.search(r"list ([a-zA-Z0-9_\- ]+)(?: list)?", q)
            if match:
                return match.group(1).strip()
            
            match = re.search(r"called ([a-zA-Z0-9_\- ]+)", q)
            if match:
                return match.group(1).strip()
                
            match = re.search(r"named ([a-zA-Z0-9_\- ]+)", q)
            if match:
                return match.group(1).strip()
                
            return None

        def _extract_list_item(q):
            # Basic extraction
            match = re.search(r"add ([a-zA-Z0-9_\- ]+) to", q)
            if match:
                return match.group(1).strip()
                
            match = re.search(r"put ([a-zA-Z0-9_\- ]+) to", q)
            if match:
                return match.group(1).strip()
                
            return None
            
        # Create a new list
        if "create" in query and "list" in query:
            list_name = _extract_list_name(query)
            if not list_name:
                # Try to infer from context if name wasn't explicit
                match = re.search(r"create (?:a|an|the) ([a-zA-Z0-9_\- ]+) list", query)
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
        if ("show" in query or "what's on" in query or "what is in" in query) and "list" in query:
            list_name = _extract_list_name(query)
            if not list_name:
                # Try to infer from context
                match = re.search(r"(?:show|what's on|what is in) (?:my|the) ([a-zA-Z0-9_\- ]+) list", query)
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
        remove_match = re.search(r"remove (?:item )?([\w\s]+) from (?:my|the)? ([\w\s]+) list", query)
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
        delete_match = re.search(r"delete (?:my|the) ([\w\s]+) list", query)
        if delete_match:
            list_name = delete_match.group(1).strip()
            success = await list_manager.delete_list(list_name)
            if success:
                return f"Okay, I've deleted the '{list_name}' list."
            else:
                return f"I couldn't find a list called '{list_name}' to delete."
                
        return None  # Return None if this handler can't process the query
    
    async def handle_reminder_command(self, query):
        """Parse and handle reminder-related commands using ReminderManager"""
        reminder_manager = ReminderManager()
        query = query.lower()
        
        # Set a timer (duration based)
        timer_match = re.search(r'(set|create|start) (?:a|the)? timer (?:for|of) (\d+) (minute|minutes|min|mins|second|seconds|sec|secs|hour|hours|hr|hrs)', query)
        if timer_match:
            value = int(timer_match.group(2))
            unit = timer_match.group(3)
            seconds = 0
            if unit.startswith(('hour', 'hr')):
                seconds = value * 3600
            elif unit.startswith(('minute', 'min')):
                seconds = value * 60
            else:
                seconds = value
            
            description = "Timer"
            desc_match = re.search(r'(?:called|named|for) ([a-zA-Z0-9_\- ]+)', query)
            if desc_match:
                description = desc_match.group(1).strip()
            
            reminder = await reminder_manager.set_timer(seconds, description)
            if reminder:
                due_time = datetime.datetime.fromisoformat(reminder["due_time"])
                formatted_time = due_time.strftime("%H:%M:%S")
                return f"Okay, I've set a {self._format_duration(seconds)} timer named '{description}'. I'll notify you at {formatted_time}."
            else:
                return "Sorry, I couldn't set that timer."

        # Set a reminder (specific time based)
        reminder_match = re.search(r'(?:remind|reminder|remember) me (?:to|about) (.+?) (?:at|on) (.+)', query, re.IGNORECASE)
        if not reminder_match:
            reminder_match = re.search(r'set a reminder (?:for|to|about) (.+?) (?:at|on) (.+)', query, re.IGNORECASE)
            
        if reminder_match:
            action = reminder_match.group(1).strip()
            time_str = reminder_match.group(2).strip()
            
            try:
                # Simple time parsing for basic formats like "3:30"
                now = datetime.datetime.now()
                due_time = None
                
                # Handle "X:YY" format
                if ":" in time_str:
                    try:
                        hour, minute = map(int, time_str.split(":"))
                        due_time = now.replace(hour=hour, minute=minute)
                        # If the time is in the past, assume next day
                        if due_time < now:
                            due_time += datetime.timedelta(days=1)
                    except ValueError:
                        pass
                
                # Handle words like "tomorrow"
                if not due_time and "tomorrow" in time_str:
                    # Extract time part if present
                    time_parts = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)?', time_str)
                    if time_parts:
                        hour = int(time_parts.group(1))
                        minute = int(time_parts.group(2) or 0)
                        am_pm = time_parts.group(3)
                        
                        # Adjust for PM
                        if am_pm and am_pm.lower() == "pm" and hour < 12:
                            hour += 12
                        # Adjust for AM
                        if am_pm and am_pm.lower() == "am" and hour == 12:
                            hour = 0
                            
                        tomorrow = now + datetime.timedelta(days=1)
                        due_time = tomorrow.replace(hour=hour, minute=minute)
                    else:
                        # Default to 9am tomorrow if no time specified
                        tomorrow = now + datetime.timedelta(days=1)
                        due_time = tomorrow.replace(hour=9, minute=0)
                
                # If we couldn't parse the time, give a helpful message
                if not due_time:
                    return f"I'm having trouble understanding the time '{time_str}'. Please try a format like '3:30' or 'tomorrow at 2pm'."

                reminder = await reminder_manager.set_reminder(due_time.isoformat(), action)
                if reminder:
                    formatted_time = due_time.strftime("%I:%M %p on %A")
                    return f"Okay, I'll remind you about '{action}' at {formatted_time}."
                else:
                    return "Sorry, I couldn't set that reminder."
            except Exception as e:
                logger.error(f"Error parsing time for reminder: {e}")
                return "I had trouble understanding that time. Could you phrase it differently? (e.g., '3:30pm', 'tomorrow at 9am')"

        # List reminders
        list_pattern = r'(show|list|what|tell me about|any) (?:my|are my|do i have)? ?(?:active )?(reminders|timers)'
        if re.search(list_pattern, query):
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
        cancel_match = re.search(r'(?:cancel|delete|remove) (?:the|my)? (?:reminder|timer) (?:for|called|named|with id) ([a-zA-Z0-9_\- ]+)', query)
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
                          # Handle multiple matches by taking the first one
                          break
                          
            if found_reminder:
                success = await reminder_manager.cancel_reminder(found_reminder['id'])
                if success:
                    return f"Okay, I've cancelled the {found_reminder['type']} for '{found_reminder['description']}'."
                else:
                    return f"I found the reminder, but couldn't cancel it for some reason."
            else:
                return f"I couldn't find an active reminder matching '{identifier}'."

        return None  # Not a reminder command
    
    def _format_duration(self, seconds):
        """Format a duration in seconds to a human-readable string"""
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                return f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
    
    async def listen_and_respond(self):
        """Record from microphone, convert to text, and respond"""
        try:
            logger.info("Listening for speech input")
            query = await self.stt.transcribe_from_mic()
            if not query:
                return {"error": "Could not understand audio"}
                
            result = await self.process_query(query, respond_with_voice=True)
            result["query"] = query  # Include the transcribed query in the result
            return result
        except Exception as e:
            logger.error("Error in listen and respond: %s", str(e), exc_info=True)
            return {"error": str(e)}
    
    async def get_interaction_history(self, limit=10):
        """Retrieve conversation history"""
        return await self.storage.get_interactions(limit)

import click
import asyncio
import logging
import sys
import subprocess
import datetime
from rin.core import Assistant
from rin.audio import AudioHandler
from rin.logging_config import loggers
from rin.lists import ListManager
from rin.reminders import ReminderManager

logger = loggers['core']
assistant = Assistant()

@click.group()
def cli():
    """Rin CLI - Personal Assistant Prototype"""
    pass

@cli.command()
@click.argument('query')
def ask(query):
    """Ask Rin a question"""
    try:
        response = asyncio.run(assistant.process_query(query))
        click.echo(f"Rin: {response['text']}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.option('--voice/--no-voice', default=True, help="Enable/disable voice response")
def listen(voice):
    """Listen for voice command and respond"""
    try:
        result = asyncio.run(assistant.listen_and_respond())
        click.echo(f"You said: {result.get('query', '')}")
        click.echo(f"Rin: {result.get('text', '')}")
        
        if voice and result.get('audio_path'):
            playback_success = asyncio.run(AudioHandler.play_audio(result['audio_path']))
            
            # If built-in playback fails, try using system commands
            if not playback_success:
                _play_with_system_command(result['audio_path'])
                
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@cli.command()
def remember():
    """Show saved interactions"""
    try:
        interactions = asyncio.run(assistant.get_interaction_history())
        for i, item in enumerate(interactions):
            click.echo(f"[{i+1}] You: {item['query']}\nRin: {item['response']}\n")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@cli.command()
@click.argument('text')
def speak(text):
    """Convert text to speech"""
    try:
        path = asyncio.run(assistant.tts.synthesize(text))
        click.echo(f"Audio saved to {path}")
        
        # Try built-in playback first
        playback_success = asyncio.run(AudioHandler.play_audio(path))
        
        # If built-in playback fails, try using system commands
        if not playback_success:
            _play_with_system_command(path)
            
    except Exception as e:
        click.echo(f"Error: {str(e)}")

# List management commands
@cli.group()
def list_cmd():
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
        if items is None:
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

# Reminder management commands
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

@reminder.command("set")
@click.option('--time', '-t', required=True, help="Time (e.g., '15:30', '9am', 'tomorrow 10:00')")
@click.argument('description')
def set_reminder_cmd(time, description):
    """Set a reminder for a specific time"""
    try:
        # Using datetime's basic parsing for now
        now = datetime.datetime.now()
        
        # Simple time parsing for basic formats
        try:
            # Try parsing as a time
            if ":" in time:
                hour, minute = map(int, time.split(":"))
                due_time = now.replace(hour=hour, minute=minute)
                # If the time is in the past, assume next day
                if due_time < now:
                    due_time += datetime.timedelta(days=1)
            # Simple relative time (e.g., "in 30 minutes")
            elif time.startswith("in "):
                parts = time.split()
                if len(parts) >= 3 and parts[2].startswith("minute"):
                    minutes = int(parts[1])
                    due_time = now + datetime.timedelta(minutes=minutes)
                elif len(parts) >= 3 and parts[2].startswith("hour"):
                    hours = int(parts[1])
                    due_time = now + datetime.timedelta(hours=hours)
                else:
                    click.echo("Sorry, I don't understand that time format. Try using 'HH:MM' format.")
                    return
            else:
                # For demonstration - a more robust implementation would use dateutil.parser
                click.echo("Please use 'HH:MM' format for the time. For example, --time '14:30'")
                return
        except ValueError:
            click.echo("Invalid time format. Please use 'HH:MM' format, e.g., --time '14:30'")
            return
            
        # Set the reminder
        reminder_manager = ReminderManager()
        reminder = asyncio.run(reminder_manager.set_reminder(due_time.isoformat(), description))
        
        if reminder:
            formatted_time = due_time.strftime("%I:%M %p")
            click.echo(f"Reminder set: {description} (ID: {reminder['id']})")
            click.echo(f"Will notify at {formatted_time}")
        else:
            click.echo("Failed to set reminder.")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@reminder.command("list")
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

def _play_with_system_command(audio_path):
    """Play audio using system commands if PyAudio fails"""
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", audio_path])
        elif sys.platform == "win32":  # Windows
            subprocess.run(["start", audio_path], shell=True)
        elif sys.platform.startswith("linux"):  # Linux
            subprocess.run(["xdg-open", audio_path])
        logger.info(f"Played audio using system command: {audio_path}")
    except Exception as e:
        logger.error(f"Error playing audio with system command: {str(e)}")

if __name__ == '__main__':
    cli()

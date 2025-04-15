import click
import asyncio
import logging
from rin.core import Assistant
from rin.audio import AudioHandler
from rin.logging_config import loggers

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
            asyncio.run(AudioHandler.play_audio(result['audio_path']))
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
        asyncio.run(AudioHandler.play_audio(path))
    except Exception as e:
        click.echo(f"Error: {str(e)}")

if __name__ == '__main__':
    cli()

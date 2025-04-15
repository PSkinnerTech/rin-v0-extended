# Rin V0 — Step 1: Developer & Testing Tools Setup

This guide sets up the foundational development environment for Rin's prototype (V0), a voice-first AI assistant. This step includes core CLI capabilities, GPT-based interaction, TTS integration, local storage, and a modular code structure designed for scalability.

> 🟣 This step covers only V0-level features. V1 features (e.g., conversational memory, wake word, plugin system) will build upon this base.

---

## ✅ Prerequisites

Before proceeding, ensure you have:

1. **Python 3.9+** installed (use `pyenv` or official downloads).
2. **Code Editor** such as VS Code or PyCharm.
3. **Google Cloud Project** with Text-to-Speech API enabled.
4. **OpenAI API Key** from https://platform.openai.com/
5. **Virtual Environment** knowledge (`venv`, `pip`, `.env`).
6. **Cross-platform CLI** familiarity (Unix/Mac/Windows/Pi).
7. (Optional) Familiarity with modular Python structure and command-line tooling.

---

## 📁 Project Initialization

```bash
mkdir rin-cli && cd rin-cli
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -U pip
pip install click python-dotenv openai google-cloud-texttospeech sqlite-utils \
  sounddevice numpy whisper pydub asyncio python-logging aiohttp

# Project structure
mkdir rin
mkdir -p ~/.rin/drafts ~/.rin/logs

# Create modules
touch rin/__init__.py rin/cli.py rin/llm.py rin/tts.py rin/storage.py
touch rin/core.py rin/stt.py rin/audio.py rin/config.py rin/logging_config.py
```

Create a `.env` file with your credentials:

```env
OPENAI_API_KEY=your_openai_key
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-credentials.json
AUDIO_OUTPUT_DIR=~/.rin/audio
TTS_ENGINE=google  # Options: google, coqui (when implemented)
STT_ENGINE=whisper  # Options: whisper, google (when implemented)
LOG_LEVEL=INFO
```

---

## 📋 Configuration System

Centralized config management for flexibility.

```python
# rin/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base paths
HOME_DIR = Path.home()
RIN_DIR = HOME_DIR / ".rin"
LOG_DIR = RIN_DIR / "logs"
AUDIO_DIR = RIN_DIR / "audio"

# Ensure directories exist
RIN_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# API keys and credentials
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Engine options
TTS_ENGINE = os.getenv("TTS_ENGINE", "google")
STT_ENGINE = os.getenv("STT_ENGINE", "whisper")

# Application settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Default system prompt
SYSTEM_PROMPT = "You are Rin, a helpful personal assistant. Be concise but thorough."
```

---

## 📝 Logging Configuration

```python
# rin/logging_config.py
import logging
import sys
from pathlib import Path
from rin.config import LOG_DIR, LOG_LEVEL

def setup_logging():
    log_file = LOG_DIR / "rin.log"
    
    # Configure logging
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create specific loggers
    loggers = {
        'core': logging.getLogger('rin.core'),
        'llm': logging.getLogger('rin.llm'),
        'tts': logging.getLogger('rin.tts'),
        'stt': logging.getLogger('rin.stt'),
        'storage': logging.getLogger('rin.storage'),
        'audio': logging.getLogger('rin.audio'),
    }
    
    return loggers

loggers = setup_logging()
```

---

## 🔧 Core Application Layer

Abstract core functionality from UI.

```python
# rin/core.py
import asyncio
import logging
from rin.llm import LLMInterface
from rin.tts import TTSInterface
from rin.stt import STTInterface
from rin.storage import Storage
from rin.config import TTS_ENGINE, STT_ENGINE
from rin.logging_config import loggers

logger = loggers['core']

class Assistant:
    """Core assistant logic, separate from UI/CLI concerns"""
    
    def __init__(self):
        self.storage = Storage()
        self.llm = LLMInterface.create()
        self.tts = TTSInterface.create(TTS_ENGINE)
        self.stt = STTInterface.create(STT_ENGINE)
        logger.info("Assistant initialized with TTS: %s, STT: %s", TTS_ENGINE, STT_ENGINE)
    
    async def process_query(self, query, respond_with_voice=False):
        """Process a text query and return response"""
        try:
            logger.info("Processing query: %s", query)
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
    
    async def listen_and_respond(self):
        """Record from microphone, convert to text, and respond"""
        try:
            logger.info("Listening for speech input")
            query = await self.stt.transcribe_from_mic()
            if not query:
                return {"error": "Could not understand audio"}
                
            return await self.process_query(query, respond_with_voice=True)
        except Exception as e:
            logger.error("Error in listen and respond: %s", str(e), exc_info=True)
            return {"error": str(e)}
    
    async def get_interaction_history(self, limit=10):
        """Retrieve conversation history"""
        return await self.storage.get_interactions(limit)
```

---

## 🎤 Audio Module

Cross-platform audio handling.

```python
# rin/audio.py
import sounddevice as sd
import numpy as np
import wave
import logging
import time
from pathlib import Path
import tempfile
from pydub import AudioSegment
from pydub.playback import play
from rin.config import AUDIO_DIR
from rin.logging_config import loggers

logger = loggers['audio']

class AudioHandler:
    """Cross-platform audio recording and playback"""
    
    @staticmethod
    async def record_audio(duration=5, sample_rate=16000):
        """Record audio from microphone for specified duration"""
        try:
            logger.info(f"Recording {duration}s of audio at {sample_rate}Hz")
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='int16'
            )
            sd.wait()  # Wait until recording is finished
            
            # Save to temp file
            temp_file = Path(tempfile.gettempdir()) / f"rin_recording_{int(time.time())}.wav"
            with wave.open(str(temp_file), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(recording.tobytes())
            
            logger.info(f"Recording saved to {temp_file}")
            return str(temp_file)
        except Exception as e:
            logger.error(f"Error recording audio: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    async def play_audio(file_path):
        """Play audio file using pydub (cross-platform)"""
        try:
            logger.info(f"Playing audio: {file_path}")
            sound = AudioSegment.from_file(file_path)
            play(sound)
            return True
        except Exception as e:
            logger.error(f"Error playing audio: {str(e)}", exc_info=True)
            return False
```

---

## 🤖 Language Model (LLM) Handler

Factory pattern for potential model switching.

```python
# rin/llm.py
import os
import openai
import asyncio
import logging
from abc import ABC, abstractmethod
from rin.config import OPENAI_API_KEY, LLM_MODEL, SYSTEM_PROMPT
from rin.logging_config import loggers

logger = loggers['llm']

class LLMInterface(ABC):
    """Abstract base class for LLM providers"""
    
    @staticmethod
    def create(provider="openai"):
        """Factory method to create appropriate LLM client"""
        if provider == "openai":
            return OpenAIClient()
        # Add more providers here as needed
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    @abstractmethod
    async def generate_response(self, query):
        """Generate a response to the given query"""
        pass

class OpenAIClient(LLMInterface):
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
        self.model = LLM_MODEL
        logger.info(f"Initialized OpenAI client with model {self.model}")
    
    async def generate_response(self, query):
        """Asynchronously generate a response using OpenAI"""
        try:
            logger.info(f"Generating response for query using {self.model}")
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Generated response: {content[:50]}...")
            return content
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise
```

---

## 🔊 Text-to-Speech with Engine Abstraction

```python
# rin/tts.py
import os
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from google.cloud import texttospeech
from rin.config import AUDIO_DIR, GOOGLE_CREDENTIALS
from rin.logging_config import loggers

logger = loggers['tts']

class TTSInterface(ABC):
    """Abstract base class for TTS engines"""
    
    @staticmethod
    def create(engine="google"):
        """Factory method to create appropriate TTS engine"""
        if engine == "google":
            return GoogleTTS()
        elif engine == "coqui":
            # Placeholder for future implementation
            raise NotImplementedError("Coqui TTS not yet implemented")
        else:
            raise ValueError(f"Unknown TTS engine: {engine}")
    
    @abstractmethod
    async def synthesize(self, text):
        """Convert text to speech and return audio file path"""
        pass

class GoogleTTS(TTSInterface):
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS
        self.client = texttospeech.TextToSpeechClient()
        logger.info("Initialized Google TTS client")
    
    async def synthesize(self, text):
        """Asynchronously synthesize text to speech using Google Cloud"""
        try:
            logger.info(f"Synthesizing text: {text[:50]}...")
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._synthesize_sync(text)
            )
            
            # Generate unique filename
            timestamp = int(time.time())
            output_file = AUDIO_DIR / f"rin_tts_{timestamp}.mp3"
            
            # Save audio content
            with open(output_file, "wb") as out:
                out.write(response.audio_content)
                
            logger.info(f"Audio saved to {output_file}")
            return str(output_file)
        except Exception as e:
            logger.error(f"Error synthesizing speech: {str(e)}", exc_info=True)
            raise
    
    def _synthesize_sync(self, text):
        """Synchronous Google TTS call (to be run in executor)"""
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", 
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        return self.client.synthesize_speech(
            input=synthesis_input, 
            voice=voice, 
            audio_config=audio_config
        )
```

---

## 🎧 Speech-to-Text Module

```python
# rin/stt.py
import os
import whisper
import asyncio
import logging
from abc import ABC, abstractmethod
from rin.audio import AudioHandler
from rin.config import WHISPER_MODEL
from rin.logging_config import loggers

logger = loggers['stt']

class STTInterface(ABC):
    """Abstract base class for STT engines"""
    
    @staticmethod
    def create(engine="whisper"):
        """Factory method to create appropriate STT engine"""
        if engine == "whisper":
            return WhisperSTT()
        elif engine == "google":
            # Placeholder for future implementation
            raise NotImplementedError("Google STT not yet implemented")
        else:
            raise ValueError(f"Unknown STT engine: {engine}")
    
    @abstractmethod
    async def transcribe_audio(self, audio_file):
        """Transcribe audio file to text"""
        pass
        
    @abstractmethod
    async def transcribe_from_mic(self, duration=5):
        """Record from microphone and transcribe"""
        pass

class WhisperSTT(STTInterface):
    def __init__(self):
        logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
        # Load model in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        self.model = loop.run_in_executor(None, lambda: whisper.load_model(WHISPER_MODEL))
        logger.info("Whisper STT initialized")
    
    async def transcribe_audio(self, audio_file):
        """Transcribe audio file using Whisper"""
        try:
            logger.info(f"Transcribing audio file: {audio_file}")
            model = await self.model  # Ensure model is loaded
            
            # Run transcription in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: model.transcribe(audio_file)
            )
            
            text = result["text"].strip()
            logger.info(f"Transcription: {text}")
            return text
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}", exc_info=True)
            return ""
    
    async def transcribe_from_mic(self, duration=5):
        """Record from microphone and transcribe"""
        try:
            audio_file = await AudioHandler.record_audio(duration=duration)
            return await self.transcribe_audio(audio_file)
        except Exception as e:
            logger.error(f"Error in transcribe_from_mic: {str(e)}", exc_info=True)
            return ""
```

---

## 🧠 Persistent Local Memory with Async Support

```python
# rin/storage.py
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
```

---

## 🔧 Modular CLI Interface

```python
# rin/cli.py
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
        
        # Try to play with the built-in audio player first
        playback_result = asyncio.run(AudioHandler.play_audio(path))
        
        # If built-in playback fails or isn't available, use system player
        if not playback_result and sys.platform == "darwin":  # macOS
            subprocess.run(["open", path])
        elif not playback_result and sys.platform == "win32":  # Windows
            subprocess.run(["start", path], shell=True)
        elif not playback_result and sys.platform.startswith("linux"):  # Linux
            subprocess.run(["xdg-open", path])
            
    except Exception as e:
        click.echo(f"Error: {str(e)}")

if __name__ == '__main__':
    cli()
```

---

## ⚙️ Setup & Install

### 1. Install CLI
```bash
pip install -e .
```

### 2. `setup.py` (optional, if distributing)
```python
from setuptools import setup, find_packages

setup(
    name='rin-cli',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'click',
        'openai',
        'python-dotenv',
        'google-cloud-texttospeech',
        'sounddevice',
        'numpy',
        'whisper',
        'pydub',
        'asyncio',
        'aiohttp',
        'sqlite-utils'
    ],
    entry_points='''
        [console_scripts]
        rin=rin.cli:cli
    ''',
)
```

### 3. Modern Python Packaging

Using `pyproject.toml` alongside `setup.py` provides a more modern approach:

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["rin"]

[project]
name = "rin-cli"
version = "0.1.0"
description = "Rin CLI - Personal Assistant Prototype"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
dependencies = [
    "click",
    "openai",
    "python-dotenv",
    "google-cloud-texttospeech",
    "sounddevice",
    "numpy",
    "openai-whisper",  # Note: this is the correct package name on PyPI
    "pydub",
    "asyncio",
    "aiohttp",
    "sqlite-utils"
]

[project.scripts]
rin = "rin.cli:cli"
```

And create platform-specific setup scripts to simplify installation:

```bash
# setup.sh for Unix/macOS
#!/bin/bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
# Upgrade pip and install package
pip install -U pip
pip install -e .
echo "Setup complete! Run 'source venv/bin/activate' to activate environment"
```

```batch
:: setup.bat for Windows
@echo off
python -m venv venv
call venv\Scripts\activate
pip install -U pip
pip install -e .
echo Setup complete! Run 'venv\Scripts\activate' to activate environment
```

A test script can also help users verify their installation:

```python
# test_setup.py
#!/usr/bin/env python3
"""
Test script to verify Rin CLI setup
"""
import asyncio
# Import and test components
# ...

async def run_tests():
    """Run verification tests for all components"""
    # Test OpenAI, TTS, STT, storage, etc.
    # ...

if __name__ == "__main__":
    asyncio.run(run_tests())
```

---

## ✅ Sample Commands

```bash
# Ask a question via text
rin ask "What's the weather like in Bogotá?"

# Listen for a voice command
rin listen

# Replay conversation history
rin remember

# Speak text aloud
rin speak "Hello, I am Rin."
```

---

## 🚧 Next Steps (V0.x → V1)

- Enhance Whisper STT with streaming capabilities
- Add wake word detection via `openWakeWord` or `Porcupine`
- Implement Coqui TTS as a local offline alternative
- Create a simple GUI using Tauri or similar framework
- Expand memory with LLM context injection
- Implement better error recovery and retry mechanisms
- Add unit and integration tests

This enhanced step gives you a more future-proof, modular AI assistant with better scalability, error handling, and cross-platform support.

---

## 🛠 Implementation Notes & Troubleshooting

When implementing this guide, you'll likely encounter these common challenges:

### 1. FFmpeg Dependency for Whisper

Whisper requires FFmpeg to be installed on your system:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ffmpeg

# Windows (using Chocolatey)
choco install ffmpeg
```

### 2. STT Implementation

Whisper can be challenging to install. Add a fallback dummy STT implementation:

```python
# In rin/stt.py
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    logger.warning("Whisper not available")
    WHISPER_AVAILABLE = False

class DummySTT(STTInterface):
    """Fallback STT for testing"""
    async def transcribe_from_mic(self, duration=5):
        # Record audio but return dummy text
        await AudioHandler.record_audio(duration)
        return "This is dummy transcription text."
```

### 3. Audio Playback Issues

Audio playback dependencies can be tricky. Add system command fallbacks:

```python
# In rin/cli.py
if not playback_success:
    # Use system commands as fallback
    if sys.platform == "darwin":  # macOS
        subprocess.run(["open", audio_path])
    elif sys.platform == "win32":  # Windows
        subprocess.run(["start", audio_path], shell=True)
    elif sys.platform.startswith("linux"):  # Linux
        subprocess.run(["xdg-open", audio_path])
```

### 4. Handling Local Queries

For time-sensitive queries, handle them locally instead of using the LLM:

```python
# In rin/core.py
def _handle_local_queries(self, query):
    query_lower = query.lower()
    
    # Check for time pattern
    if re.search(r"what time is it|current time", query_lower):
        now = datetime.datetime.now()
        return f"The current time is {now.strftime('%I:%M %p')}."
        
    # If no pattern matches, return None to use the LLM
    return None
```

### 5. Async Loop Issues

Avoid creating futures in `__init__` methods - load models lazily on first use:

```python
async def _ensure_model_loaded(self):
    if self._model is None:
        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(None, lambda: whisper.load_model(self._model_name))
    return self._model
```

These modifications will make your implementation more robust across different environments.

---


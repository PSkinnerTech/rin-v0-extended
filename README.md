# Rin CLI - Personal Assistant Prototype

A voice-first AI assistant built with Python, featuring OpenAI GPT integration, Google Cloud Text-to-Speech, and Whisper speech recognition.

## Features

- `ask`: Ask Rin questions and get AI-powered responses
- `listen`: Listen for voice commands and respond with text and speech
- `remember`: View past conversations with Rin
- `speak`: Convert text to speech using Google's TTS API
- Local handling of time/date queries without using LLM

## Prerequisites

- Python 3.9+
- FFmpeg (required for Whisper STT)
- Google Cloud Project with Text-to-Speech API enabled
- OpenAI API Key

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/YourUsername/rin-cli.git
   cd rin-cli
   ```

2. Install FFmpeg (system dependency):
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg

   # Windows (using Chocolatey)
   choco install ffmpeg
   ```

3. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:
   ```
   pip install -e .
   ```

5. Create a `.env` file with your credentials:
   ```
   OPENAI_API_KEY=your_openai_key
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-credentials.json
   TTS_ENGINE=google
   STT_ENGINE=whisper
   LOG_LEVEL=INFO
   LLM_MODEL=gpt-4
   WHISPER_MODEL=base
   ```

6. Place your Google Cloud credentials JSON file at the path specified in your `.env` file.

## Usage

```bash
# Ask Rin a question
rin ask "What's the weather like in San Francisco?"

# Ask about the time (handled locally)
rin ask "What time is it?"

# Listen for a voice command
rin listen

# Replay conversation history
rin remember

# Speak text aloud
rin speak "Hello, I am Rin."
```

## Architecture

- **Modular Design:** Separate modules for LLM, TTS, STT, storage, and audio handling
- **Asynchronous Support:** Non-blocking operations for better responsiveness
- **Factory Pattern:** Easy engine swapping for different providers
- **Local Storage:** SQLite database for conversation history
- **Cross-platform:** Works on Linux, macOS, and Windows
- **Fallback Mechanisms:** Graceful degradation for missing dependencies
- **Local Processing:** Time/date queries handled without using LLM

## Dependencies

- **System Dependencies:**
  - FFmpeg: Required for Whisper STT
- **Python Packages:**
  - click: Command line interface
  - openai: OpenAI API integration
  - google-cloud-texttospeech: Google TTS integration
  - whisper: Speech-to-text capabilities
  - sounddevice & pydub: Audio handling
  - sqlite3: Local storage
  - asyncio: Asynchronous operations
  - python-dotenv: Environment variable management

## Robustness Features

- Graceful fallbacks for STT if Whisper is unavailable
- Fallback to system media player if direct audio playback fails
- Lazy loading of models to avoid event loop issues
- Local handling of time/date queries for faster responses

## Future Improvements

- Enhance Whisper STT with streaming capabilities
- Add wake word detection
- Implement offline TTS alternatives
- Create a GUI interface
- Expand memory with context injection
- Add unit and integration tests

## License

MIT 
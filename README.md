# Rin CLI - Personal Assistant Prototype

A command-line AI assistant built with Node.js, OpenAI GPT-4, and Google Cloud Text-to-Speech.

## Features

- `ask`: Ask Rin questions and get AI-powered responses
- `remember`: View past conversations with Rin
- `speak`: Convert text to speech using Google's TTS API

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/PSkinnerTech/rin-v0.git
   cd rin-v0
   ```

2. Install dependencies:
   ```
   pnpm install
   ```

3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_CLOUD_CREDENTIALS=keys/rin-tts.json
   GOOGLE_TTS_API_KEY=your_google_tts_api_key
   ```

4. Setup Google Cloud credentials by placing your service account JSON in `keys/rin-tts.json`

5. Link the CLI for development:
   ```
   npm link
   ```

## Usage

```
# Ask Rin a question
rin ask "What's the weather like today?"

# View conversation history
rin remember

# Convert text to speech
rin speak "Hello, my name is Rin"
```

## Dependencies

- commander: CLI interface
- openai: OpenAI API integration
- @google-cloud/text-to-speech: Google TTS integration
- sqlite3: Local storage for conversations
- dotenv: Environment variable management

## License

ISC 
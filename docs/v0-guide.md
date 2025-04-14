# Step 1: Developer & Testing Tools Setup

This guide provides a step-by-step approach to building the foundational developer tools for Rin V0.

## Prerequisites

Before you begin, ensure you have the following prerequisites installed and set up:

1. **Node.js and npm**: Ensure Node.js is installed on your system. npm (Node Package Manager) will be used to install necessary packages.

2. **Code Editor**: A code editor such as Visual Studio Code, Sublime Text, or any other editor of your choice for writing and editing your code.

3. **API Keys**:
   - **OpenAI API Key**: Required for interacting with OpenAI's models.
   - **Google Cloud Credentials**: Needed for using Google Cloud Text-to-Speech. Ensure you have downloaded the JSON credentials file after setting up a Google Cloud project.

4. **SQLite**: The local storage for interactions is handled using SQLite, a lightweight database. Ensure you have the necessary tools or libraries installed to interact with SQLite databases.

5. **Command Line Tools**: Familiarity with command line operations is necessary as the setup involves running shell commands.

6. **Internet Connection**: Required for downloading packages, interacting with APIs, and fetching updates.

7. **Environment Configuration**: Knowledge of how to set and use environment variables is crucial, especially for managing API keys and other sensitive information securely.

Once you have all the prerequisites set up, you can proceed with the following steps to configure your development and testing environment.

## CLI Interface Setup

### 1. Create Basic Project Structure
```bash
mkdir -p rin-cli/src
cd rin-cli
npm init -y
npm install commander dotenv axios openai sqlite3
touch .env src/index.js src/storage.js
```

### 2. Configure Environment
```env
# .env
OPENAI_API_KEY=your_openai_key
GOOGLE_CLOUD_CREDENTIALS=/path/to/your/google-credentials.json
```

### 3. Build CLI Entry Point
```javascript
// src/index.js
const { program } = require('commander');
const storage = require('./storage');
const { Configuration, OpenAIApi } = require('openai');
const textToSpeech = require('@google-cloud/text-to-speech');

// Initialize OpenAI
const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY,
});
const openai = new OpenAIApi(configuration);

// Initialize Google Cloud TTS
const ttsClient = new textToSpeech.TextToSpeechClient();

// Initialize storage
storage.init();

program
  .name('rin')
  .description('Rin CLI - Personal Assistant Prototype')
  .version('0.0.1');

program
  .command('ask <query>')
  .description('Ask Rin a question')
  .action(async (query) => {
    try {
      const response = await openai.createChatCompletion({
        model: 'gpt-4',
        messages: [
          { role: 'system', content: 'You are Rin, a helpful personal assistant.' },
          { role: 'user', content: query }
        ],
      });
      
      const answer = response.data.choices[0].message.content;
      console.log(`Rin: ${answer}`);
      
      // Store interaction in memory
      storage.saveInteraction(query, answer);
    } catch (error) {
      console.error('Error:', error.message);
    }
  });

program
  .command('remember')
  .description('Show past interactions')
  .action(() => {
    const interactions = storage.getInteractions();
    if (interactions.length === 0) {
      console.log('No past interactions found.');
      return;
    }
    
    console.log('Past interactions:');
    interactions.forEach((item, i) => {
      console.log(`\n--- Interaction ${i+1} ---`);
      console.log(`You: ${item.query}`);
      console.log(`Rin: ${item.response}`);
    });
  });

program
  .command('speak <text>')
  .description('Convert text to speech using Google Cloud TTS')
  .action(async (text) => {
    try {
      const request = {
        input: { text: text },
        voice: { languageCode: 'en-US', ssmlGender: 'NEUTRAL' },
        audioConfig: { audioEncoding: 'MP3' },
      };

      const [response] = await ttsClient.synthesizeSpeech(request);
      const outputFile = 'output.mp3';
      require('fs').writeFileSync(outputFile, response.audioContent, 'binary');
      console.log(`Audio content written to: ${outputFile}`);
    } catch (error) {
      console.error('Error:', error.message);
    }
  });

program.parse();
```

## Local Memory Implementation

### 1. Create SQLite-based Storage
```javascript
// src/storage.js
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

// Ensure data directory exists
const dataDir = path.join(process.env.HOME || process.env.USERPROFILE, '.rin');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir);
}

const dbPath = path.join(dataDir, 'rin.db');
let db;

function init() {
  db = new sqlite3.Database(dbPath);
  
  // Create tables if they don't exist
  db.serialize(() => {
    db.run(`
      CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  });
  
  console.log(`Local memory initialized at ${dbPath}`);
}

function saveInteraction(query, response) {
  return new Promise((resolve, reject) => {
    db.run(
      'INSERT INTO interactions (query, response) VALUES (?, ?)',
      [query, response],
      function(err) {
        if (err) return reject(err);
        resolve(this.lastID);
      }
    );
  });
}

function getInteractions(limit = 10) {
  return new Promise((resolve, reject) => {
    db.all(
      'SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?',
      [limit],
      (err, rows) => {
        if (err) return reject(err);
        resolve(rows);
      }
    );
  });
}

module.exports = { init, saveInteraction, getInteractions };
```

### 2. Package Script Setup
```json
// package.json
{
  "scripts": {
    "start": "node src/index.js"
  },
  "bin": {
    "rin": "./src/index.js"
  }
}
```

### 3. Make CLI Executable
```bash
# Add shebang to index.js
echo '#!/usr/bin/env node\n' | cat - src/index.js > temp && mv temp src/index.js
chmod +x src/index.js
npm link
```

## Usage Examples

Once set up, you can use the CLI:

```bash
# Ask Rin a question
rin ask "What's the weather today?"

# View interaction history
rin remember
```

This basic CLI and storage implementation provides the foundation for testing the core functionality before implementing more complex features.

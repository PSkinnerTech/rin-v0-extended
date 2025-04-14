#!/usr/bin/env node

// src/index.js
require('dotenv').config();
const { program } = require('commander');
const storage = require('./storage');
const OpenAI = require('openai');
const textToSpeech = require('@google-cloud/text-to-speech');
const fs = require('fs');
const path = require('path');
 
// Initialize OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});
 
// Initialize Google Cloud TTS
const ttsClient = new textToSpeech.TextToSpeechClient({
  keyFilename: process.env.GOOGLE_CLOUD_CREDENTIALS
});
 
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
      const response = await openai.chat.completions.create({
        model: 'gpt-4o',
        messages: [
          { role: 'system', content: 'You are Rin, a helpful personal assistant.' },
          { role: 'user', content: query }
        ],
        temperature: 0.7,
        max_tokens: 500
      });
      
      const answer = response.choices[0].message.content;
      console.log(`Rin: ${answer}`);
      
      // Store interaction in memory
      await storage.saveInteraction(query, answer);
    } catch (error) {
      console.error('Error:', error.message);
    }
  });
 
program
  .command('remember')
  .description('Show past interactions')
  .action(async () => {
    try {
      const interactions = await storage.getInteractions();
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
    } catch (error) {
      console.error('Error retrieving interactions:', error.message);
    }
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
      fs.writeFileSync(outputFile, response.audioContent, 'binary');
      console.log(`Audio content written to: ${outputFile}`);
    } catch (error) {
      console.error('Error:', error.message);
    }
  });
 
program.parse();
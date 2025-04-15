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

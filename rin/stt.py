import os
import asyncio
import logging
from abc import ABC, abstractmethod
from rin.audio import AudioHandler
from rin.config import WHISPER_MODEL
from rin.logging_config import loggers

logger = loggers['stt']

# Try to import whisper, but don't fail if it's not available
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    logger.warning("Whisper package not found. Speech-to-text functionality will be limited.")
    WHISPER_AVAILABLE = False

class STTInterface(ABC):
    """Abstract base class for STT engines"""
    
    @staticmethod
    def create(engine="whisper"):
        """Factory method to create appropriate STT engine"""
        if engine == "whisper":
            if not WHISPER_AVAILABLE:
                logger.error("Whisper engine requested but package is not installed. Try 'pip install openai-whisper'")
                raise ImportError("Whisper package not installed")
            return WhisperSTT()
        elif engine == "google":
            # Placeholder for future implementation
            raise NotImplementedError("Google STT not yet implemented")
        elif engine == "dummy":
            # For testing without actual STT
            return DummySTT()
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
        if not WHISPER_AVAILABLE:
            raise ImportError("Whisper package not available")
            
        logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
        # Don't load the model in the constructor - load it on first use
        # This avoids event loop issues
        self._model = None
        self._model_name = WHISPER_MODEL
        logger.info("Whisper STT initialized")
    
    async def _ensure_model_loaded(self):
        """Load the model if not already loaded"""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self._model_name}")
            # Get the current event loop and load the model in it
            loop = asyncio.get_running_loop()
            self._model = await loop.run_in_executor(
                None, 
                lambda: whisper.load_model(self._model_name)
            )
            logger.info("Whisper model loaded successfully")
        return self._model
    
    async def transcribe_audio(self, audio_file):
        """Transcribe audio file using Whisper"""
        try:
            logger.info(f"Transcribing audio file: {audio_file}")
            model = await self._ensure_model_loaded()
            
            # Run transcription in executor to avoid blocking
            loop = asyncio.get_running_loop()
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

class DummySTT(STTInterface):
    """Dummy STT implementation for testing without actual speech recognition"""
    
    def __init__(self):
        logger.info("Initializing Dummy STT (no actual speech recognition)")
    
    async def transcribe_audio(self, audio_file):
        """Return dummy text instead of actual transcription"""
        logger.info(f"Dummy transcription for file: {audio_file}")
        return "This is dummy transcription text for testing purposes."
    
    async def transcribe_from_mic(self, duration=5):
        """Simulate recording and return dummy text"""
        logger.info(f"Simulating recording for {duration} seconds")
        # We still record to test the audio recording functionality
        try:
            await AudioHandler.record_audio(duration=duration)
        except Exception as e:
            logger.error(f"Error recording audio: {str(e)}", exc_info=True)
        
        return "This is dummy transcription text for testing purposes."

import asyncio
import logging
from rin.llm import LLMInterface
from rin.tts import TTSInterface
from rin.stt import STTInterface, WHISPER_AVAILABLE
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
                
            result = await self.process_query(query, respond_with_voice=True)
            result["query"] = query  # Include the transcribed query in the result
            return result
        except Exception as e:
            logger.error("Error in listen and respond: %s", str(e), exc_info=True)
            return {"error": str(e)}
    
    async def get_interaction_history(self, limit=10):
        """Retrieve conversation history"""
        return await self.storage.get_interactions(limit)

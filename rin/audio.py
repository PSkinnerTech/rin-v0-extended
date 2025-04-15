import logging
import time
from pathlib import Path
import tempfile
import os
from rin.config import AUDIO_DIR
from rin.logging_config import loggers

logger = loggers['audio']

# Try to import audio-related modules, but handle if they're missing
AUDIO_RECORDING_AVAILABLE = False
AUDIO_PLAYBACK_AVAILABLE = False

try:
    import sounddevice as sd
    import numpy as np
    import wave
    AUDIO_RECORDING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Audio recording modules not available: {str(e)}")
    logger.warning("Audio recording will be simulated")

try:
    from pydub import AudioSegment
    from pydub.playback import play
    AUDIO_PLAYBACK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Audio playback modules not available: {str(e)}")
    logger.warning("Audio playback will be simulated")

class AudioHandler:
    """Cross-platform audio recording and playback"""
    
    @staticmethod
    async def record_audio(duration=5, sample_rate=16000):
        """Record audio from microphone for specified duration"""
        try:
            if not AUDIO_RECORDING_AVAILABLE:
                logger.warning("Audio recording not available. Creating dummy audio file.")
                # Create an empty temp file as a placeholder
                temp_file = Path(tempfile.gettempdir()) / f"rin_dummy_recording_{int(time.time())}.wav"
                with open(temp_file, 'wb') as f:
                    # Write a minimal empty wav file
                    f.write(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00>\x00\x00\x00>\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00')
                logger.info(f"Dummy recording created at {temp_file}")
                return str(temp_file)
            
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
            # Create a dummy file as fallback
            temp_file = Path(tempfile.gettempdir()) / f"rin_error_recording_{int(time.time())}.wav"
            with open(temp_file, 'wb') as f:
                # Write a minimal empty wav file
                f.write(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x00>\x00\x00\x00>\x00\x00\x01\x00\x08\x00data\x00\x00\x00\x00')
            logger.info(f"Fallback recording created at {temp_file}")
            return str(temp_file)
    
    @staticmethod
    async def play_audio(file_path):
        """Play audio file using pydub (cross-platform)"""
        try:
            if not AUDIO_PLAYBACK_AVAILABLE:
                logger.warning(f"Audio playback not available. Would have played: {file_path}")
                return True
                
            logger.info(f"Playing audio: {file_path}")
            sound = AudioSegment.from_file(file_path)
            play(sound)
            return True
        except Exception as e:
            logger.error(f"Error playing audio: {str(e)}", exc_info=True)
            return False

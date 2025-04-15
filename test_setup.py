#!/usr/bin/env python3
"""
Rin V0 - Setup Verification Script

This script checks if all components of Rin V0 are correctly configured
and the API connections are working properly.
"""

import os
import sys
import asyncio
from pathlib import Path

# Make sure the package directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    import rin
    from rin.config import OPENAI_API_KEY, GOOGLE_CREDENTIALS
    from rin.llm import LLMInterface
    from rin.tts import TTSInterface
    from rin.storage import Storage
    from rin.audio import AudioHandler, AUDIO_RECORDING_AVAILABLE, AUDIO_PLAYBACK_AVAILABLE
    from rin.stt import WHISPER_AVAILABLE
except ImportError as e:
    print(f"Error: Required modules not found: {e}")
    print("Make sure you've installed all dependencies:")
    print("pip install -e .")
    sys.exit(1)

# Load environment variables
load_dotenv()

def check_env_vars():
    """Check environment variables"""
    print("\n=== Checking Environment Variables ===")
    
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY is missing in .env file")
    else:
        masked_key = OPENAI_API_KEY[:5] + "..." + OPENAI_API_KEY[-4:]
        print(f"✅ OPENAI_API_KEY found: {masked_key}")
    
    if not GOOGLE_CREDENTIALS:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS is missing in .env file")
    else:
        print(f"✅ GOOGLE_APPLICATION_CREDENTIALS found: {GOOGLE_CREDENTIALS}")
        if not Path(GOOGLE_CREDENTIALS).exists():
            print(f"   ❌ Warning: The file {GOOGLE_CREDENTIALS} does not exist!")
        else:
            print(f"   ✅ Google credentials file exists")
            
    return OPENAI_API_KEY and GOOGLE_CREDENTIALS

async def test_openai():
    """Test OpenAI API connection"""
    print("\n=== Testing OpenAI API Connection ===")
    
    try:
        llm = LLMInterface.create()
        response = await llm.generate_response("Say hello in one word")
        print(f"✅ OpenAI API working! Response: {response}")
        return True
    except Exception as e:
        print(f"❌ Error connecting to OpenAI API: {str(e)}")
        return False

async def test_tts():
    """Test Google TTS API connection"""
    print("\n=== Testing Google TTS API Connection ===")
    
    try:
        tts = TTSInterface.create()
        output_file = await tts.synthesize("Hello, testing Rin setup.")
        print(f"✅ Google TTS API working! Audio saved to: {output_file}")
        
        print("   Testing audio playback...")
        await AudioHandler.play_audio(output_file)
        if AUDIO_PLAYBACK_AVAILABLE:
            print("   ✅ Audio playback completed")
        else:
            print("   ⚠️ Audio playback not available (simulated)")
        return True
    except Exception as e:
        print(f"❌ Error with Google TTS API: {str(e)}")
        return False

async def test_stt():
    """Test STT availability"""
    print("\n=== Testing Speech-to-Text Availability ===")
    
    if WHISPER_AVAILABLE:
        print("✅ Whisper is available for speech recognition")
        return True
    else:
        print("⚠️ Whisper is not installed. Speech recognition will use dummy mode.")
        print("   To enable actual speech recognition, install whisper:")
        print("   pip install openai-whisper")
        return False

async def test_storage():
    """Test SQLite storage"""
    print("\n=== Testing SQLite Storage ===")
    
    try:
        storage = Storage()
        await storage.save_interaction("Test query", "Test response")
        interactions = await storage.get_interactions(1)
        if interactions and len(interactions) > 0:
            print("✅ SQLite storage working!")
            return True
        else:
            print("❌ SQLite storage error: Could not retrieve stored interaction")
            return False
    except Exception as e:
        print(f"❌ Error with SQLite storage: {str(e)}")
        return False

async def test_audio():
    """Test audio recording capabilities"""
    print("\n=== Testing Audio Recording ===")
    
    try:
        print("Recording 2 seconds of audio...")
        audio_file = await AudioHandler.record_audio(duration=2)
        if AUDIO_RECORDING_AVAILABLE:
            print(f"✅ Audio recording working! Audio saved to: {audio_file}")
        else:
            print(f"⚠️ Audio recording not available (simulated). Dummy file created at: {audio_file}")
        return True
    except Exception as e:
        print(f"❌ Error with audio recording: {str(e)}")
        return False

async def run_tests():
    """Run all tests"""
    print("\n🔍 STARTING RIN V0 SETUP VERIFICATION")
    
    env_check = check_env_vars()
    if not env_check:
        print("\n❌ Environment setup incomplete. Please fix the issues above before continuing.")
        return
    
    openai_test = await test_openai()
    tts_test = await test_tts()
    stt_check = await test_stt()
    storage_test = await test_storage()
    audio_test = await test_audio()
    
    print("\n=== TEST SUMMARY ===")
    print(f"Environment Variables: {'✅' if env_check else '❌'}")
    print(f"OpenAI API: {'✅' if openai_test else '❌'}")
    print(f"Google TTS API: {'✅' if tts_test else '❌'}")
    print(f"STT Availability: {'✅' if WHISPER_AVAILABLE else '⚠️'}")
    print(f"Audio Recording: {'✅' if AUDIO_RECORDING_AVAILABLE else '⚠️'}")
    print(f"Audio Playback: {'✅' if AUDIO_PLAYBACK_AVAILABLE else '⚠️'}")
    print(f"SQLite Storage: {'✅' if storage_test else '❌'}")
    
    if all([env_check, openai_test, tts_test, storage_test]):
        print("\n🎉 SUCCESS! Core components are working correctly.")
        
        if not WHISPER_AVAILABLE:
            print("\n⚠️ NOTE: Speech recognition is in dummy mode.")
            print("   To enable actual speech recognition, install whisper:")
            print("   pip install openai-whisper")
            
        if not (AUDIO_RECORDING_AVAILABLE and AUDIO_PLAYBACK_AVAILABLE):
            print("\n⚠️ NOTE: Full audio capabilities are not available.")
            print("   Some audio dependencies could not be loaded.")
            print("   This doesn't affect text-based functionality.")
        
        print("\nYou can now use Rin CLI with the following commands:")
        print("  rin ask \"What's the weather like today?\"")
        print("  rin listen")
        print("  rin remember")
        print("  rin speak \"Hello, I am Rin\"")
    else:
        print("\n⚠️ Some tests failed. Please fix the issues above before using Rin.")

if __name__ == "__main__":
    asyncio.run(run_tests()) 
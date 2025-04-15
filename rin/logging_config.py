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

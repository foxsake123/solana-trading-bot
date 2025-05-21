import logging
import os
from datetime import datetime

class SafeFormatter(logging.Formatter):
    """
    Custom formatter that handles Unicode encoding errors
    """
    def format(self, record):
        try:
            return super().format(record)
        except UnicodeEncodeError:
            record.msg = record.msg.encode('utf-8', errors='replace').decode('utf-8')
            return super().format(record)

def setup_logging():
    """
    Configure logging for the bot
    """
    os.makedirs('logs', exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f'logs/trading_bot_{timestamp}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger('trading_bot')
    logger.setLevel(logging.INFO)
    for handler in logger.handlers + logging.getLogger().handlers:
        handler.setFormatter(SafeFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('solana').setLevel(logging.WARNING)
    return logger

logger = setup_logging()
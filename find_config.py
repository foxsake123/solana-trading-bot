"""
Script to find the location of the bot_control.json file
"""
import os
import sys
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('config_finder')

def find_bot_control_files():
    """Find all bot_control.json files in the project"""
    found_files = []
    
    # Start from the current directory
    start_dir = os.getcwd()
    logger.info(f"Searching for bot_control.json files starting from: {start_dir}")
    
    # Walk through all directories and files
    for root, dirs, files in os.walk(start_dir):
        if 'bot_control.json' in files:
            file_path = os.path.join(root, 'bot_control.json')
            found_files.append(file_path)
            
            # Try to read the file
            try:
                with open(file_path, 'r') as f:
                    content = json.load(f)
                    logger.info(f"Found file: {file_path}")
                    logger.info(f"  running: {content.get('running', 'not set')}")
                    logger.info(f"  simulation_mode: {content.get('simulation_mode', 'not set')}")
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
    
    return found_files

def update_bot_control_files(files):
    """Update all found bot_control.json files"""
    for file_path in files:
        try:
            # Read the current content
            with open(file_path, 'r') as f:
                content = json.load(f)
            
            # Update settings
            content['running'] = True
            content['simulation_mode'] = True
            
            # Write back to the file
            with open(file_path, 'w') as f:
                json.dump(content, f, indent=4)
                
            logger.info(f"Updated {file_path} with running=True and simulation_mode=True")
        except Exception as e:
            logger.error(f"Error updating {file_path}: {e}")

def create_bot_control_files():
    """Create bot_control.json files in the main locations"""
    # Default content
    content = {
        "running": True,
        "simulation_mode": True,
        "filter_fake_tokens": True,
        "use_birdeye_api": True,
        "use_machine_learning": False,
        "take_profit_target": 15.0,
        "stop_loss_percentage": 0.25,
        "max_investment_per_token": 0.1,
        "min_investment_per_token": 0.02,
        "slippage_tolerance": 0.3,
        "MIN_SAFETY_SCORE": 15.0,
        "MIN_VOLUME": 10.0,
        "MIN_LIQUIDITY": 5000.0,
        "MIN_MCAP": 10000.0,
        "MIN_HOLDERS": 10,
        "MIN_PRICE_CHANGE_1H": 1.0,
        "MIN_PRICE_CHANGE_6H": 2.0,
        "MIN_PRICE_CHANGE_24H": 5.0
    }
    
    # Create in main directory
    main_path = os.path.join(os.getcwd(), 'bot_control.json')
    try:
        with open(main_path, 'w') as f:
            json.dump(content, f, indent=4)
        logger.info(f"Created {main_path}")
    except Exception as e:
        logger.error(f"Error creating {main_path}: {e}")
    
    # Create in data directory
    data_dir = os.path.join(os.getcwd(), 'data')
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
            logger.info(f"Created data directory: {data_dir}")
        except Exception as e:
            logger.error(f"Error creating data directory: {e}")
    
    data_path = os.path.join(data_dir, 'bot_control.json')
    try:
        with open(data_path, 'w') as f:
            json.dump(content, f, indent=4)
        logger.info(f"Created {data_path}")
    except Exception as e:
        logger.error(f"Error creating {data_path}: {e}")

# Find all bot_control.json files
found_files = find_bot_control_files()

if found_files:
    # Update all found files
    update_bot_control_files(found_files)
else:
    # Create new files
    create_bot_control_files()
    
# Import config_adapter to see where it's looking
try:
    logger.info("Trying to import config_adapter to see where it looks for the file")
    from config_adapter import BOT_CONTROL_FILE
    logger.info(f"config_adapter looks for bot_control.json at: {BOT_CONTROL_FILE}")
except Exception as e:
    logger.error(f"Error importing config_adapter: {e}")
    
    # Try to find the config file path in the code
    try:
        from config import BotConfiguration
        logger.info(f"BotConfiguration.BOT_CONTROL_FILE: {BotConfiguration.BOT_CONTROL_FILE}")
    except Exception as e:
        logger.error(f"Error importing config.BotConfiguration: {e}")
        
print("\nPlease run this script to fix your bot_control.json configuration, then try running the bot again.")

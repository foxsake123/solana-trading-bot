"""
Script to check how main.py loads the configuration
"""
import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('config_check')

def check_main_imports():
    """Check how main.py imports configuration"""
    # Find main.py
    main_file = None
    for root, dirs, files in os.walk(os.getcwd()):
        if 'main.py' in files:
            main_file = os.path.join(root, 'main.py')
            break
    
    if not main_file:
        logger.error("main.py not found")
        return
    
    logger.info(f"Found main.py at: {main_file}")
    
    # Read main.py
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Look for bot_control.json references
    bot_control_refs = []
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'bot_control.json' in line:
            bot_control_refs.append((i+1, line.strip()))
    
    if bot_control_refs:
        logger.info("Found bot_control.json references in main.py:")
        for line_num, line in bot_control_refs:
            logger.info(f"  Line {line_num}: {line}")
    else:
        logger.info("No direct references to bot_control.json found in main.py")
    
    # Look for config import
    config_imports = []
    for i, line in enumerate(lines):
        if 'import' in line and ('config' in line or 'BotConfiguration' in line):
            config_imports.append((i+1, line.strip()))
    
    if config_imports:
        logger.info("Found config imports in main.py:")
        for line_num, line in config_imports:
            logger.info(f"  Line {line_num}: {line}")
    else:
        logger.info("No config imports found in main.py")

def check_bot_control_file_references():
    """Check for BOT_CONTROL_FILE references in Python files"""
    references = []
    
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                    if 'BOT_CONTROL_FILE' in content:
                        references.append(file_path)
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
    
    if references:
        logger.info("Files containing BOT_CONTROL_FILE references:")
        for file_path in references:
            logger.info(f"  {file_path}")
            
            # Read the file and find the definition
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines):
                    if 'BOT_CONTROL_FILE' in line and '=' in line:
                        logger.info(f"    Line {i+1}: {line.strip()}")
            except Exception as e:
                logger.error(f"Error checking {file_path}: {e}")
    else:
        logger.info("No files containing BOT_CONTROL_FILE references found")

def create_forced_bot_control():
    """Create forced bot_control.json files with very explicit settings"""
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
    
    # Create in multiple locations to be sure
    locations = [
        os.path.join(os.getcwd(), 'bot_control.json'),  # Root directory
        os.path.join(os.getcwd(), 'data', 'bot_control.json'),  # data directory
        os.path.join(os.getcwd(), 'core', 'bot_control.json'),  # core directory
        os.path.join(os.getcwd(), 'config', 'bot_control.json')  # config directory
    ]
    
    for location in locations:
        # Make sure the directory exists
        directory = os.path.dirname(location)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")
            except Exception as e:
                logger.error(f"Error creating directory {directory}: {e}")
                continue
        
        try:
            with open(location, 'w') as f:
                json.dump(content, f, indent=4)
            logger.info(f"Created FORCED bot_control.json at: {location}")
        except Exception as e:
            logger.error(f"Error creating {location}: {e}")

# Run the checks
check_main_imports()
check_bot_control_file_references()
create_forced_bot_control()

print("\nRun this script to create forced bot_control.json files in multiple locations, then try running the bot again.")

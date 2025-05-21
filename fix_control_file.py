import os
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fix_control')

# Locations to check
possible_locations = [
    'data/bot_control.json',
    'bot_control.json',
    'C:/Users/shorg/sol-bot_claude/data/bot_control.json',  # Full path in case current dir is different
    'C:/Users/shorg/sol-bot_claude/bot_control.json'
]

# Find the control file
control_file = None
for loc in possible_locations:
    if os.path.exists(loc):
        control_file = loc
        logger.info(f"Found control file at: {os.path.abspath(loc)}")
        
        # Read its current content
        with open(loc, 'r') as f:
            content = json.load(f)
            logger.info(f"Current simulation_mode setting: {content.get('simulation_mode')}")
            logger.info(f"Current running setting: {content.get('running')}")
        
        # Update the file
        content['simulation_mode'] = False
        content['running'] = True
        
        # Write back
        with open(loc, 'w') as f:
            json.dump(content, f, indent=4)
            logger.info(f"Updated {loc} with simulation_mode=False and running=True")

if not control_file:
    logger.error("No control file found in any expected location!")
    
    # Create a new one in the default location
    os.makedirs('data', exist_ok=True)
    control_file = 'data/bot_control.json'
    
    content = {
        "running": True,
        "simulation_mode": False,
        "filter_fake_tokens": True,
        "use_birdeye_api": True,
        "use_machine_learning": False,
        "take_profit_target": 15.0,
        "stop_loss_percentage": 0.25,
        "max_investment_per_token": 0.1,
        "min_investment_per_token": 0.02,
        "slippage_tolerance": 0.3,
        "MIN_SAFETY_SCORE": 0.0,
        "MIN_VOLUME": 0.0,
        "MIN_LIQUIDITY": 0.0,
        "MIN_MCAP": 0.0,
        "MIN_HOLDERS": 0,
        "MIN_PRICE_CHANGE_1H": 0.0,
        "MIN_PRICE_CHANGE_6H": 0.0,
        "MIN_PRICE_CHANGE_24H": 0.0
    }
    
    with open(control_file, 'w') as f:
        json.dump(content, f, indent=4)
        logger.info(f"Created new control file at {control_file}")

# Add debug to main.py to show where it's reading from
try:
    from config import BotConfiguration
    logger.info(f"Bot is configured to use control file at: {BotConfiguration.BOT_CONTROL_FILE}")
    
    # Check if that file exists
    if os.path.exists(BotConfiguration.BOT_CONTROL_FILE):
        logger.info(f"The configured control file exists")
    else:
        logger.error(f"The configured control file DOES NOT EXIST!")
except ImportError:
    logger.error("Could not import BotConfiguration")
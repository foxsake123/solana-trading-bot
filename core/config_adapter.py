"""
Configuration adapter for main.py compatibility
"""
import os
import sys
import logging
import json

# Configure logging
logger = logging.getLogger(__name__)

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Default configuration values
DEFAULT_CONFIG = {
    "MAINNET_RPC_URL": "https://api.mainnet-beta.solana.com",
    "WALLET_PRIVATE_KEY": "",
    "BOT_RUNNING": False,
    "SIMULATION_MODE": True,
    "TRADING_PARAMS": {
        "initial_investment_sol": 0.05,
        "max_investment_per_token_sol": 0.1,
        "min_liquidity_usd": 50000,
        "max_slippage_percent": 2.5,
        "buy_volume_threshold_usd": 1000,
        "min_price_change_percent": 3.0,
        "take_profit_percent": 15.0,
        "stop_loss_percent": -7.5,
        "trailing_stop_percent": 5.0,
    }
}

# Try to import from existing config
try:
    # Try importing from config module
    import config as config_module
    
    # Check if we have a BotConfiguration class
    if hasattr(config_module, 'BotConfiguration'):
        # Extract configuration from BotConfiguration
        bot_config = config_module.BotConfiguration
        
        # Extract RPC URL from configuration
        if hasattr(bot_config, 'RPC_ENDPOINT'):
            MAINNET_RPC_URL = bot_config.RPC_ENDPOINT
        elif hasattr(bot_config, 'MAINNET_RPC_URL'):
            MAINNET_RPC_URL = bot_config.MAINNET_RPC_URL
        else:
            MAINNET_RPC_URL = DEFAULT_CONFIG["MAINNET_RPC_URL"]
            logger.warning(f"Using default RPC URL: {MAINNET_RPC_URL}")
        
        # Extract wallet key from configuration
        if hasattr(bot_config, 'WALLET_PRIVATE_KEY'):
            WALLET_PRIVATE_KEY = bot_config.WALLET_PRIVATE_KEY
        elif hasattr(bot_config, 'PRIVATE_KEY'):
            WALLET_PRIVATE_KEY = bot_config.PRIVATE_KEY
        else:
            WALLET_PRIVATE_KEY = DEFAULT_CONFIG["WALLET_PRIVATE_KEY"]
            logger.warning("No wallet private key found in configuration")
        
        # Set bot running mode
        BOT_RUNNING = getattr(bot_config, 'BOT_RUNNING', DEFAULT_CONFIG["BOT_RUNNING"])
        
        # Set simulation mode
        SIMULATION_MODE = getattr(bot_config, 'SIMULATION_MODE', DEFAULT_CONFIG["SIMULATION_MODE"])
        
        # Extract trading parameters
        trading_params_dict = {}
        for param, default_value in DEFAULT_CONFIG["TRADING_PARAMS"].items():
            trading_params_dict[param] = getattr(bot_config, param.upper(), default_value)
        
        TRADING_PARAMS = trading_params_dict
        
    else:
        # No BotConfiguration class, try to extract variables directly
        MAINNET_RPC_URL = getattr(config_module, 'RPC_ENDPOINT', 
                           getattr(config_module, 'MAINNET_RPC_URL', 
                           DEFAULT_CONFIG["MAINNET_RPC_URL"]))
        
        WALLET_PRIVATE_KEY = getattr(config_module, 'WALLET_PRIVATE_KEY', 
                               getattr(config_module, 'PRIVATE_KEY', 
                               DEFAULT_CONFIG["WALLET_PRIVATE_KEY"]))
        
        BOT_RUNNING = getattr(config_module, 'BOT_RUNNING', DEFAULT_CONFIG["BOT_RUNNING"])
        SIMULATION_MODE = getattr(config_module, 'SIMULATION_MODE', DEFAULT_CONFIG["SIMULATION_MODE"])
        TRADING_PARAMS = getattr(config_module, 'TRADING_PARAMS', DEFAULT_CONFIG["TRADING_PARAMS"])
    
    logger.info("Loaded configuration from config module")
    
except ImportError:
    logger.warning("Failed to import config module, using default configuration")
    
    # Use default configuration
    MAINNET_RPC_URL = DEFAULT_CONFIG["MAINNET_RPC_URL"]
    WALLET_PRIVATE_KEY = DEFAULT_CONFIG["WALLET_PRIVATE_KEY"]
    BOT_RUNNING = DEFAULT_CONFIG["BOT_RUNNING"]
    SIMULATION_MODE = DEFAULT_CONFIG["SIMULATION_MODE"]
    TRADING_PARAMS = DEFAULT_CONFIG["TRADING_PARAMS"]

# Try to load configuration from .env file
try:
    env_file = os.path.join(project_root, '.env')
    if os.path.exists(env_file):
        logger.info("Loading configuration from .env file")
        
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                if key == 'MAINNET_RPC_URL' or key == 'RPC_ENDPOINT':
                    MAINNET_RPC_URL = value
                elif key == 'WALLET_PRIVATE_KEY' or key == 'PRIVATE_KEY':
                    WALLET_PRIVATE_KEY = value
                elif key == 'BOT_RUNNING':
                    BOT_RUNNING = value.lower() in ('true', 'yes', '1')
                elif key == 'SIMULATION_MODE':
                    SIMULATION_MODE = value.lower() in ('true', 'yes', '1')
except Exception as e:
    logger.warning(f"Error loading .env file: {e}")

# Try to load configuration from bot_control.json
try:
    control_file = os.path.join(project_root, 'bot_control.json')
    if os.path.exists(control_file):
        logger.info("Loading configuration from bot_control.json")
        
        with open(control_file, 'r') as f:
            control_data = json.load(f)
            
            if 'running' in control_data:
                BOT_RUNNING = bool(control_data['running'])
                
            if 'simulation_mode' in control_data:
                SIMULATION_MODE = bool(control_data['simulation_mode'])
                
            # Extract trading parameters if available
            for param in DEFAULT_CONFIG["TRADING_PARAMS"]:
                if param in control_data:
                    TRADING_PARAMS[param] = control_data[param]
                # Also check for uppercase versions
                elif param.upper() in control_data:
                    TRADING_PARAMS[param] = control_data[param.upper()]
except Exception as e:
    logger.warning(f"Error loading bot_control.json: {e}")

# Log the configuration
logger.info(f"MAINNET_RPC_URL: {MAINNET_RPC_URL}")
logger.info(f"WALLET_PRIVATE_KEY: {'*****' if WALLET_PRIVATE_KEY else 'Not set'}")
logger.info(f"BOT_RUNNING: {BOT_RUNNING}")
logger.info(f"SIMULATION_MODE: {SIMULATION_MODE}")
logger.info(f"TRADING_PARAMS: {json.dumps(TRADING_PARAMS, indent=2)}")
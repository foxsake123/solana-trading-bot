import os
from dotenv import load_dotenv
import logging
import json

# Load environment variables
load_dotenv()

class BotConfiguration:
    """
    Centralized configuration class for Solana Trading Bot
    """
    
    # File paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DB_PATH = os.path.join(DATA_DIR, 'trading_bot.db')
    BOT_CONTROL_FILE = os.path.join(DATA_DIR, 'bot_control.json')
    
    # API endpoints and keys
    API_KEYS = {
        'TWITTER_BEARER_TOKEN': os.getenv('TWITTER_BEARER_TOKEN'),
        'SOLANA_RPC_ENDPOINT': os.getenv('SOLANA_RPC_ENDPOINT', 'https://mainnet.helius-rpc.com/?api-key=3c05add4-9974-4e11-a003-ef52c488edee'),
        'WALLET_PRIVATE_KEY': os.getenv('WALLET_PRIVATE_KEY'),
        'DEXSCREENER_BASE_URL': os.getenv('DEXSCREENER_BASE_URL', 'https://api.dexscreener.com'),
        'JUPITER_QUOTE_API': os.getenv('JUPITER_QUOTE_API', 'https://quote-api.jup.ag/v6/quote'),
        'JUPITER_SWAP_API': os.getenv('JUPITER_SWAP_API', 'https://quote-api.jup.ag/v6/swap'),
        'BIRDEYE_API_KEY': os.getenv('BIRDEYE_API_KEY', '')
    }
    
    # Trading parameters with defaults - updated with your parameters
    TRADING_PARAMETERS = {
        # Core trading parameters
        'MAX_BUY_RETRIES': int(os.getenv('MAX_BUY_RETRIES', 3)),
        'MAX_SELL_RETRIES': int(os.getenv('MAX_SELL_RETRIES', 3)),
        'SLIPPAGE_TOLERANCE': float(os.getenv('SLIPPAGE_TOLERANCE', 0.30)),  # 30% slippage
        'TAKE_PROFIT_TARGET': float(os.getenv('TAKE_PROFIT_TARGET', 15.0)),   # 15x profit
        'STOP_LOSS_PERCENTAGE': float(os.getenv('STOP_LOSS_PERCENTAGE', 0.25)),  # 25% loss
        'MOONBAG_PERCENTAGE': float(os.getenv('MOONBAG_PERCENTAGE', 0.15)),  # 15% of position kept as moonbag
        'MAX_INVESTMENT_PER_TOKEN': float(os.getenv('MAX_INVESTMENT_PER_TOKEN', 1.0)),  # 1 SOL (increased from 0.1)
        
        # Token screening parameters
        'MIN_SAFETY_SCORE': float(os.getenv('MIN_SAFETY_SCORE', 50.0)),
        'MIN_VOLUME': float(os.getenv('MIN_VOLUME', 10.0)),          # Min volume decreased from 50K to 10 for testing
        'MIN_LIQUIDITY': float(os.getenv('MIN_LIQUIDITY', 25000)),   # Min liquidity decreased to 25K for testing
        'MIN_MCAP': float(os.getenv('MIN_MCAP', 50000)),             # Min market cap decreased for testing
        'MIN_HOLDERS': int(os.getenv('MIN_HOLDERS', 30)),            # Min holders decreased for testing
        
        # Top gainer thresholds
        'MIN_PRICE_CHANGE_1H': float(os.getenv('MIN_PRICE_CHANGE_1H', 5.0)),   # 5% min 1h gain
        'MIN_PRICE_CHANGE_6H': float(os.getenv('MIN_PRICE_CHANGE_6H', 10.0)),  # 10% min 6h gain
        'MIN_PRICE_CHANGE_24H': float(os.getenv('MIN_PRICE_CHANGE_24H', 20.0)), # 20% min 24h gain
        
        # Other settings
        'SCAN_INTERVAL': int(os.getenv('SCAN_INTERVAL', 60)),  # Reduced from 300 to 60 for more frequent scanning
        'TWITTER_RATE_LIMIT_BUFFER': int(os.getenv('TWITTER_RATE_LIMIT_BUFFER', 5)),
        'USE_BIRDEYE_API': os.getenv('USE_BIRDEYE_API', 'true').lower() == 'true',  # Default to using Birdeye API if key is provided
        'USE_MACHINE_LEARNING': os.getenv('USE_MACHINE_LEARNING', 'false').lower() == 'true',  # Default ML to disabled
    }
    
    @classmethod
    def setup_bot_controls(cls):
        """
        Set up the bot control file if it doesn't exist
        """
        # Create data directory if it doesn't exist
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        
        if not os.path.exists(cls.BOT_CONTROL_FILE):
            control_data = {
                'running': True,
                'simulation_mode': True,
                'filter_fake_tokens': True,
                'use_birdeye_api': cls.TRADING_PARAMETERS['USE_BIRDEYE_API'],
                'use_machine_learning': cls.TRADING_PARAMETERS['USE_MACHINE_LEARNING'],  # Add ML toggle
                'max_investment_per_token': cls.TRADING_PARAMETERS['MAX_INVESTMENT_PER_TOKEN'],
                'take_profit_target': cls.TRADING_PARAMETERS['TAKE_PROFIT_TARGET'],
                'stop_loss_percentage': cls.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE'],
                'slippage_tolerance': cls.TRADING_PARAMETERS['SLIPPAGE_TOLERANCE'],
                'MIN_SAFETY_SCORE': cls.TRADING_PARAMETERS['MIN_SAFETY_SCORE'],
                'MIN_VOLUME': cls.TRADING_PARAMETERS['MIN_VOLUME'],
                'MIN_LIQUIDITY': cls.TRADING_PARAMETERS['MIN_LIQUIDITY'],
                'MIN_MCAP': cls.TRADING_PARAMETERS['MIN_MCAP'],
                'MIN_HOLDERS': cls.TRADING_PARAMETERS['MIN_HOLDERS'],
                'MIN_PRICE_CHANGE_1H': cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_1H'],
                'MIN_PRICE_CHANGE_6H': cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_6H'],
                'MIN_PRICE_CHANGE_24H': cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_24H']
            }
            
            with open(cls.BOT_CONTROL_FILE, 'w') as f:
                json.dump(control_data, f, indent=4)
            
        return True
    
    @classmethod
    def load_trading_parameters(cls):
        """
        Load trading parameters from control file
        """
        try:
            # Create the control file if it doesn't exist
            cls.setup_bot_controls()
            
            with open(cls.BOT_CONTROL_FILE, 'r') as f:
                control = json.load(f)
                
            # Update core trading parameters
            cls.TRADING_PARAMETERS['MAX_INVESTMENT_PER_TOKEN'] = control.get(
                'max_investment_per_token', 
                cls.TRADING_PARAMETERS['MAX_INVESTMENT_PER_TOKEN']
            )
            
            cls.TRADING_PARAMETERS['TAKE_PROFIT_TARGET'] = control.get(
                'take_profit_target', 
                cls.TRADING_PARAMETERS['TAKE_PROFIT_TARGET']
            )
            
            cls.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE'] = control.get(
                'stop_loss_percentage', 
                cls.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE']
            )
            
            cls.TRADING_PARAMETERS['SLIPPAGE_TOLERANCE'] = control.get(
                'slippage_tolerance',
                cls.TRADING_PARAMETERS['SLIPPAGE_TOLERANCE']
            )
            
            # Update API usage settings
            cls.TRADING_PARAMETERS['USE_BIRDEYE_API'] = control.get(
                'use_birdeye_api',
                cls.TRADING_PARAMETERS['USE_BIRDEYE_API']
            )
            
            # Update ML toggle setting
            cls.TRADING_PARAMETERS['USE_MACHINE_LEARNING'] = control.get(
                'use_machine_learning',
                cls.TRADING_PARAMETERS['USE_MACHINE_LEARNING']
            )
            
            # Update screening parameters
            cls.TRADING_PARAMETERS['MIN_SAFETY_SCORE'] = control.get(
                'MIN_SAFETY_SCORE',
                cls.TRADING_PARAMETERS['MIN_SAFETY_SCORE']
            )
            
            cls.TRADING_PARAMETERS['MIN_VOLUME'] = control.get(
                'MIN_VOLUME',
                cls.TRADING_PARAMETERS['MIN_VOLUME']
            )
            
            cls.TRADING_PARAMETERS['MIN_LIQUIDITY'] = control.get(
                'MIN_LIQUIDITY',
                cls.TRADING_PARAMETERS['MIN_LIQUIDITY']
            )
            
            cls.TRADING_PARAMETERS['MIN_MCAP'] = control.get(
                'MIN_MCAP',
                cls.TRADING_PARAMETERS['MIN_MCAP']
            )
            
            cls.TRADING_PARAMETERS['MIN_HOLDERS'] = control.get(
                'MIN_HOLDERS',
                cls.TRADING_PARAMETERS['MIN_HOLDERS']
            )
            
            # Update top gainer thresholds
            cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_1H'] = control.get(
                'MIN_PRICE_CHANGE_1H',
                cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_1H']
            )
            
            cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_6H'] = control.get(
                'MIN_PRICE_CHANGE_6H',
                cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_6H']
            )
            
            cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_24H'] = control.get(
                'MIN_PRICE_CHANGE_24H',
                cls.TRADING_PARAMETERS['MIN_PRICE_CHANGE_24H']
            )
            
            # Return bot running status
            return control.get('running', True)
            
        except Exception as e:
            logging.error(f"Failed to load trading parameters: {e}")
            return True  # Default to running
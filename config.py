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
        
        # ML Configuration
        'ML_CONFIDENCE_THRESHOLD': float(os.getenv('ML_CONFIDENCE_THRESHOLD', 0.7)),
        'ML_RETRAIN_INTERVAL_HOURS': int(os.getenv('ML_RETRAIN_INTERVAL_HOURS', 24)),
        'ML_MIN_TRAINING_SAMPLES': int(os.getenv('ML_MIN_TRAINING_SAMPLES', 10)),
    }

    # Dashboard parameter configurations - defines the UI ranges and defaults
    DASHBOARD_PARAMS = {
        'take_profit': {
            'default': 15.0,  # Changed from 2.5 to match your 15x target
            'min_value': 1.1,
            'max_value': 50.0,  # Increased to accommodate 15x targets
            'step': 0.5,
            'help': "Exit position when price reaches this multiple (e.g., 15.0 = 15x profit)"
        },
        'stop_loss': {
            'default': 25.0,  # Changed from 20.0 to match your 25% loss
            'min_value': 5.0,
            'max_value': 50.0,
            'step': 1.0,
            'help': "Exit position when loss reaches this percentage"
        },
        'min_investment': {
            'default': 0.02,
            'min_value': 0.001,
            'max_value': 1.0,
            'step': 0.001,
            'help': "Minimum SOL amount to invest per token"
        },
        'max_investment': {
            'default': 1.0,  # Changed from 0.1 to match your 1 SOL max
            'min_value': 0.01,
            'max_value': 10.0,
            'step': 0.1,
            'help': "Maximum SOL amount to invest per token"
        },
        'slippage_tolerance': {
            'default': 30.0,  # Changed from 5.0 to match your 30% slippage
            'min_value': 0.1,
            'max_value': 50.0,
            'step': 0.5,
            'help': "Maximum acceptable slippage for trades (%)"
        },
        'ml_confidence_threshold': {
            'default': 0.7,
            'min_value': 0.5,
            'max_value': 0.95,
            'step': 0.05,
            'help': "Minimum confidence required for ML predictions"
        },
        'ml_retrain_interval': {
            'default': 24,
            'options': [6, 12, 24, 48, 72],
            'help': "How often to retrain the ML model (hours)"
        },
        'ml_min_samples': {
            'default': 10,
            'min_value': 5,
            'max_value': 100,
            'step': 5,
            'help': "Minimum samples required to train ML model"
        },
        'min_safety_score': {
            'default': 50.0,  # Changed from 15.0 to match your config
            'min_value': 0.0,
            'max_value': 100.0,
            'step': 5.0,
            'help': "Minimum safety score for token screening"
        },
        'min_volume': {
            'default': 10.0,
            'min_value': 0.0,
            'max_value': 1000000.0,
            'step': 10.0,
            'help': "Minimum 24h volume in USD"
        },
        'min_liquidity': {
            'default': 25000.0,  # Changed from 5000.0 to match your config
            'min_value': 0.0,
            'max_value': 1000000.0,
            'step': 1000.0,
            'help': "Minimum liquidity in USD"
        },
        'min_price_change_24h': {
            'default': 20.0,  # Changed from 5.0 to match your config
            'min_value': 0.0,
            'max_value': 100.0,
            'step': 1.0,
            'help': "Minimum 24h price change percentage"
        }
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
                'use_machine_learning': cls.TRADING_PARAMETERS['USE_MACHINE_LEARNING'],
                'max_investment_per_token': cls.TRADING_PARAMETERS['MAX_INVESTMENT_PER_TOKEN'],
                'take_profit_target': cls.TRADING_PARAMETERS['TAKE_PROFIT_TARGET'],
                'stop_loss_percentage': cls.TRADING_PARAMETERS['STOP_LOSS_PERCENTAGE'],
                'slippage_tolerance': cls.TRADING_PARAMETERS['SLIPPAGE_TOLERANCE'],
                'ml_confidence_threshold': cls.TRADING_PARAMETERS['ML_CONFIDENCE_THRESHOLD'],
                'ml_retrain_interval_hours': cls.TRADING_PARAMETERS['ML_RETRAIN_INTERVAL_HOURS'],
                'ml_min_training_samples': cls.TRADING_PARAMETERS['ML_MIN_TRAINING_SAMPLES'],
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
            
            # Update ML parameters
            cls.TRADING_PARAMETERS['ML_CONFIDENCE_THRESHOLD'] = control.get(
                'ml_confidence_threshold',
                cls.TRADING_PARAMETERS['ML_CONFIDENCE_THRESHOLD']
            )
            
            cls.TRADING_PARAMETERS['ML_RETRAIN_INTERVAL_HOURS'] = control.get(
                'ml_retrain_interval_hours',
                cls.TRADING_PARAMETERS['ML_RETRAIN_INTERVAL_HOURS']
            )
            
            cls.TRADING_PARAMETERS['ML_MIN_TRAINING_SAMPLES'] = control.get(
                'ml_min_training_samples',
                cls.TRADING_PARAMETERS['ML_MIN_TRAINING_SAMPLES']
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

    @classmethod
    def save_trading_parameters(cls, updated_params):
        """
        Save updated trading parameters to control file
        """
        try:
            # Load existing control data
            if os.path.exists(cls.BOT_CONTROL_FILE):
                with open(cls.BOT_CONTROL_FILE, 'r') as f:
                    control_data = json.load(f)
            else:
                control_data = {}
            
            # Update with new parameters
            control_data.update(updated_params)
            
            # Save back to file
            with open(cls.BOT_CONTROL_FILE, 'w') as f:
                json.dump(control_data, f, indent=4)
            
            # Reload parameters
            cls.load_trading_parameters()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to save trading parameters: {e}")
            return False

    @classmethod
    def get_dashboard_param_config(cls, param_name):
        """
        Get dashboard parameter configuration for a specific parameter
        """
        return cls.DASHBOARD_PARAMS.get(param_name, {
            'default': 0,
            'min_value': 0,
            'max_value': 100,
            'step': 1,
            'help': "No configuration available"
        })

# Initialize configuration on import
BotConfiguration.load_trading_parameters()
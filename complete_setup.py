"""
Complete setup script to ensure everything is configured correctly
"""
import os
import json
import sqlite3
import shutil
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('complete_setup')

def backup_current_state():
    """Create a backup of current configuration and database"""
    backup_dir = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup files
    files_to_backup = [
        'bot_control.json',
        'data/sol_bot.db',
        '.env'
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            if os.path.isfile(file):
                shutil.copy2(file, backup_dir)
            logger.info(f"Backed up {file}")
    
    return backup_dir

def setup_bot_control():
    """Set up correct bot_control.json"""
    config = {
        "running": True,
        "simulation_mode": True,  # Start in simulation for safety
        "filter_fake_tokens": True,
        "use_birdeye_api": True,
        "use_machine_learning": True,  # Enable ML for better trades
        
        # Realistic profit/loss parameters
        "take_profit_target": 1.15,     # 15% profit target
        "stop_loss_percentage": 0.05,   # 5% stop loss
        "trailing_stop_enabled": True,
        "trailing_stop_percentage": 0.03, # 3% trailing stop
        
        # Position sizing
        "max_investment_per_token": 0.5,  # Max 5% of portfolio (0.5 SOL of 10 SOL)
        "min_investment_per_token": 0.1,  # Min 1% of portfolio
        "max_open_positions": 5,          # Diversification
        
        # Slippage
        "slippage_tolerance": 0.10,      # 10% slippage tolerance
        
        # Enhanced filters for quality tokens
        "MIN_SAFETY_SCORE": 50.0,        # Higher safety requirement
        "MIN_VOLUME": 100000.0,          # $100k minimum volume
        "MIN_LIQUIDITY": 250000.0,       # $250k minimum liquidity
        "MIN_MCAP": 5000000.0,           # $5M minimum market cap
        "MIN_HOLDERS": 1000,             # 1000+ holders
        
        # Price movement filters (more selective)
        "MIN_PRICE_CHANGE_1H": 1.0,      # At least 1% gain in 1h
        "MIN_PRICE_CHANGE_6H": 3.0,      # At least 3% gain in 6h
        "MIN_PRICE_CHANGE_24H": 5.0,     # At least 5% gain in 24h
        "MAX_PRICE_CHANGE_24H": 100.0,   # Max 100% gain (avoid pump & dumps)
        
        # Risk management
        "max_daily_loss_percentage": 0.10,  # Stop trading if down 10% in a day
        "max_drawdown_percentage": 0.20,    # Maximum 20% drawdown allowed
        
        # Simulation settings
        "starting_simulation_balance": 10.0,  # Start with 10 SOL
        
        # For display in dashboard
        "stop_loss_percentage_display": 5.0,
        "slippage_tolerance_display": 10.0
    }
    
    with open('bot_control.json', 'w') as f:
        json.dump(config, f, indent=4)
    
    logger.info("Created optimized bot_control.json")
    return config

def setup_database():
    """Ensure database is properly set up"""
    db_path = 'data/sol_bot.db'
    os.makedirs('data', exist_ok=True)
    
    if not os.path.exists(db_path):
        logger.info(f"Creating new database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_address TEXT,
            action TEXT,
            amount REAL,
            price REAL,
            timestamp TEXT,
            tx_hash TEXT,
            gain_loss_sol REAL DEFAULT 0.0,
            percentage_change REAL DEFAULT 0.0,
            price_multiple REAL DEFAULT 1.0,
            is_simulation BOOLEAN DEFAULT 1
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            contract_address TEXT PRIMARY KEY,
            ticker TEXT,
            name TEXT,
            launch_date TEXT,
            safety_score REAL,
            volume_24h REAL,
            price_usd REAL,
            liquidity_usd REAL,
            mcap REAL,
            holders INTEGER,
            liquidity_locked BOOLEAN,
            last_updated TEXT
        )
        ''')
        
        conn.commit()
        logger.info("Database tables verified/created")
        
        # Check if we have any trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        logger.info(f"Current number of trades in database: {trade_count}")
        
    except Exception as e:
        logger.error(f"Database setup error: {e}")
    finally:
        conn.close()

def check_environment():
    """Check environment setup"""
    env_file = '.env'
    
    if not os.path.exists(env_file):
        logger.warning("No .env file found. Creating template...")
        
        template = """# Solana Trading Bot Configuration
# DO NOT COMMIT THIS FILE TO GIT

# Wallet Configuration
WALLET_PRIVATE_KEY=your_wallet_private_key_here

# RPC Endpoints (optional - will use default if not set)
SOLANA_RPC_ENDPOINT=https://api.mainnet-beta.solana.com

# API Keys (optional)
BIRDEYE_API_KEY=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_BEARER_TOKEN=
"""
        
        with open(env_file, 'w') as f:
            f.write(template)
        
        logger.info("Created .env template file")
        logger.warning("Please add your wallet private key to .env file for real trading")
    else:
        # Check if wallet key is configured
        with open(env_file, 'r') as f:
            content = f.read()
        
        has_wallet = False
        if 'WALLET_PRIVATE_KEY=' in content:
            for line in content.split('\n'):
                if line.startswith('WALLET_PRIVATE_KEY='):
                    key_value = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if key_value and len(key_value) > 20 and key_value != 'your_wallet_private_key_here':
                        has_wallet = True
                        break
        
        if has_wallet:
            logger.info("✅ Wallet private key found in .env")
            logger.warning("⚠️  Currently in SIMULATION mode. To trade with real funds, set 'simulation_mode': false in bot_control.json")
        else:
            logger.warning("❌ No valid wallet private key in .env file")
            logger.info("ℹ️  Bot will only work in simulation mode")

def display_summary():
    """Display setup summary"""
    print("\n" + "="*60)
    print("SOLANA TRADING BOT - SETUP COMPLETE")
    print("="*60)
    
    # Load config
    with open('bot_control.json', 'r') as f:
        config = json.load(f)
    
    print("\n📊 CURRENT CONFIGURATION:")
    print(f"Mode: {'SIMULATION' if config['simulation_mode'] else 'REAL TRADING'}")
    print(f"Starting Balance: {config['starting_simulation_balance']} SOL")
    print(f"ML Enabled: {'Yes' if config['use_machine_learning'] else 'No'}")
    print(f"Take Profit: {config['take_profit_target']*100-100:.0f}%")
    print(f"Stop Loss: {config['stop_loss_percentage']*100:.0f}%")
    print(f"Max Investment: {config['max_investment_per_token']} SOL per token")
    
    print("\n📈 TRADING FILTERS:")
    print(f"Min Volume: ${config['MIN_VOLUME']:,.0f}")
    print(f"Min Liquidity: ${config['MIN_LIQUIDITY']:,.0f}")
    print(f"Min Market Cap: ${config['MIN_MCAP']:,.0f}")
    print(f"Min Holders: {config['MIN_HOLDERS']:,}")
    
    print("\n🚀 NEXT STEPS:")
    print("1. View Dashboard: streamlit run enhanced_ml_dashboard_v11.py")
    print("2. Run Bot: python run_bot_updated.py")
    print("3. Monitor Trades: python enhanced_trade_monitor.py")
    
    if config['simulation_mode']:
        print("\n⚠️  SIMULATION MODE ACTIVE")
        print("Your trades will be simulated with 10 SOL starting balance")
        print("To switch to real trading: set 'simulation_mode': false in bot_control.json")
    else:
        print("\n🔴 REAL TRADING MODE")
        print("Your bot will execute real trades. Make sure your wallet is funded!")
    
    print("="*60)

def main():
    """Run complete setup"""
    print("Setting up Solana Trading Bot...")
    
    # Backup current state
    backup_dir = backup_current_state()
    print(f"Created backup in: {backup_dir}")
    
    # Setup components
    config = setup_bot_control()
    setup_database()
    check_environment()
    
    # Display summary
    display_summary()

if __name__ == "__main__":
    main()
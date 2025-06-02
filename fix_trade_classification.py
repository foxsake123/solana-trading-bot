"""
Fix trade classification to properly identify simulation vs real trades
and update bot configuration to correct values
"""
import sqlite3
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('fix_classification')

def fix_bot_control():
    """Fix bot_control.json with proper values"""
    control_file = 'bot_control.json'
    
    # Correct configuration based on your settings
    correct_config = {
        "running": True,
        "simulation_mode": True,  # Currently in simulation mode
        "filter_fake_tokens": True,
        "use_birdeye_api": True,
        "use_machine_learning": False,
        "take_profit_target": 1.15,  # 15% profit (not 25x!)
        "stop_loss_percentage": 0.05,  # 5% stop loss (not 2500%!)
        "max_investment_per_token": 0.05,  # Your current setting
        "min_investment_per_token": 0.01,
        "slippage_tolerance": 0.10,
        "MIN_SAFETY_SCORE": 15.0,
        "MIN_VOLUME": 10000,
        "MIN_LIQUIDITY": 50000.0,
        "MIN_MCAP": 100000.0,
        "MIN_HOLDERS": 100,
        "MIN_PRICE_CHANGE_1H": 10.0,
        "MIN_PRICE_CHANGE_6H": 25.0,
        "MIN_PRICE_CHANGE_24H": 5.0,
        "starting_simulation_balance": 10.0  # Start with 10 SOL for simulation
    }
    
    with open(control_file, 'w') as f:
        json.dump(correct_config, f, indent=4)
    
    logger.info(f"Fixed {control_file} with correct values")
    logger.info(f"Take profit: {correct_config['take_profit_target']} (was showing as 25x)")
    logger.info(f"Stop loss: {correct_config['stop_loss_percentage']*100}% (was showing as 2500%)")

def fix_trade_classifications():
    """Fix trades that are incorrectly classified"""
    db_file = 'data/sol_bot.db'
    
    if not os.path.exists(db_file):
        logger.error(f"Database not found at {db_file}")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        # First, check if is_simulation column exists
        cursor.execute("PRAGMA table_info(trades)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'is_simulation' not in columns:
            logger.info("Adding is_simulation column to trades table")
            cursor.execute("ALTER TABLE trades ADD COLUMN is_simulation BOOLEAN DEFAULT 1")
            conn.commit()
        
        # Get all trades
        cursor.execute("SELECT id, contract_address, tx_hash FROM trades")
        trades = cursor.fetchall()
        
        logger.info(f"Found {len(trades)} trades to check")
        
        # Fix classifications
        real_count = 0
        sim_count = 0
        
        for trade_id, contract_address, tx_hash in trades:
            # Determine if simulation based on patterns
            is_simulation = False
            
            # Check contract address patterns
            if contract_address and isinstance(contract_address, str):
                if (contract_address.startswith('Sim') or 
                    'TopGainer' in contract_address or
                    'test' in contract_address.lower() or
                    'simulation' in contract_address.lower()):
                    is_simulation = True
            
            # Check transaction hash patterns
            if tx_hash and isinstance(tx_hash, str):
                if (tx_hash.startswith('SIM_') or 
                    tx_hash.startswith('SIMULATED_') or
                    'simulation' in tx_hash.lower()):
                    is_simulation = True
            
            # Your real contract addresses from the monitor output
            real_addresses = ['DezXAZ8z', 'AFbX8oGj', '7dHbWXmc']
            if any(addr in str(contract_address) for addr in real_addresses):
                # These are your actual trades, but if we're in simulation mode, mark as simulation
                # Check bot_control.json to see current mode
                with open('bot_control.json', 'r') as f:
                    config = json.load(f)
                    if config.get('simulation_mode', True):
                        is_simulation = True
                    else:
                        is_simulation = False
            
            # Update the trade
            cursor.execute(
                "UPDATE trades SET is_simulation = ? WHERE id = ?",
                (1 if is_simulation else 0, trade_id)
            )
            
            if is_simulation:
                sim_count += 1
            else:
                real_count += 1
        
        conn.commit()
        logger.info(f"Updated {len(trades)} trades: {real_count} real, {sim_count} simulation")
        
        # Show current balance calculation
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN action = 'BUY' THEN amount ELSE 0 END) as total_bought,
                SUM(CASE WHEN action = 'SELL' THEN amount ELSE 0 END) as total_sold
            FROM trades 
            WHERE is_simulation = 1
        """)
        
        result = cursor.fetchone()
        if result:
            total_bought, total_sold = result
            if total_bought is None:
                total_bought = 0
            if total_sold is None:
                total_sold = 0
            
            # For simulation, we start with 10 SOL
            starting_balance = 10.0
            current_balance = starting_balance - total_bought + total_sold
            
            logger.info(f"Simulation balance calculation:")
            logger.info(f"  Starting balance: {starting_balance} SOL")
            logger.info(f"  Total bought: {total_bought:.6f} SOL")
            logger.info(f"  Total sold: {total_sold:.6f} SOL")
            logger.info(f"  Current balance: {current_balance:.6f} SOL")
        
    except Exception as e:
        logger.error(f"Error fixing classifications: {e}")
        conn.rollback()
    finally:
        conn.close()

def check_real_wallet():
    """Check if we have a real wallet configured"""
    env_file = '.env'
    has_wallet = False
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            content = f.read()
            if 'WALLET_PRIVATE_KEY=' in content:
                # Check if it's not empty
                for line in content.split('\n'):
                    if line.startswith('WALLET_PRIVATE_KEY='):
                        key_value = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if key_value and len(key_value) > 10:
                            has_wallet = True
                            break
    
    if has_wallet:
        logger.info("Real wallet found in .env file")
        logger.info("To switch to REAL trading mode, set 'simulation_mode': false in bot_control.json")
    else:
        logger.warning("No real wallet configured in .env file")
        logger.warning("Bot can only run in simulation mode")

def main():
    """Run all fixes"""
    logger.info("Starting fixes...")
    
    # Fix bot control first
    fix_bot_control()
    
    # Fix trade classifications
    fix_trade_classifications()
    
    # Check wallet status
    check_real_wallet()
    
    logger.info("\nNext steps:")
    logger.info("1. If you want REAL trading, set 'simulation_mode': false in bot_control.json")
    logger.info("2. Make sure your wallet private key is in .env file")
    logger.info("3. Run the enhanced monitor to see corrected data: python enhanced_trade_monitor.py")

if __name__ == "__main__":
    main()
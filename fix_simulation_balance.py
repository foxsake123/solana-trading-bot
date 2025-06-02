"""
Fix simulation wallet balance to start with 10 SOL instead of 1 SOL
"""
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('fix_simulation_balance')

def update_simulation_balance():
    """Update all relevant files to use 10 SOL as starting simulation balance"""
    
    # Files to update
    files_to_update = [
        ('core/simplified_trading_bot.py', '1.0', '10.0'),
        ('trading_bot.py', '1.0', '10.0'),
        ('core/trading_bot.py', '1.0', '10.0'),
        ('solana_trader.py', 'default_balance = 1.0', 'default_balance = 10.0'),
        ('core/solana_trader.py', 'default_balance = 1.0', 'default_balance = 10.0'),
        ('enhanced_trade_monitor.py', 'return 1.0', 'return 10.0'),
        ('new_dashboard.py', 'return 1.0', 'return 10.0'),
        ('enhanced_ml_dashboard_v11.py', 'return 1.0', 'return 10.0'),
    ]
    
    for file_path, old_text, new_text in files_to_update:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Replace all instances of starting balance
                content = content.replace('starting_balance = 1.0', 'starting_balance = 10.0')
                content = content.replace('Start with 1 SOL', 'Start with 10 SOL')
                content = content.replace('Default 1 SOL', 'Default 10 SOL')
                content = content.replace(old_text, new_text)
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                logger.info(f"Updated {file_path}")
            except Exception as e:
                logger.error(f"Error updating {file_path}: {e}")
        else:
            logger.warning(f"File not found: {file_path}")
    
    # Update bot_control.json to reflect better parameters
    update_bot_control()
    
    logger.info("Simulation balance update complete - now starts with 10 SOL")

def update_bot_control():
    """Update bot_control.json with improved parameters based on AI guide"""
    control_file = 'bot_control.json'
    
    if os.path.exists(control_file):
        with open(control_file, 'r') as f:
            control = json.load(f)
        
        # Update with improved parameters from the AI guide
        control.update({
            "starting_simulation_balance": 10.0,  # New field
            "simulation_mode": True,  # Keep in simulation for testing
            "use_machine_learning": True,  # Enable ML as per guide
            
            # Improved parameters based on successful strategies in the guide
            "take_profit_target": 1.15,  # 15% profit (more realistic than 25x)
            "stop_loss_percentage": 0.05,  # 5% stop loss (tighter risk management)
            "trailing_stop_enabled": True,  # Add trailing stop
            "trailing_stop_percentage": 0.03,  # 3% trailing stop
            
            # Position sizing
            "max_investment_per_token": 0.5,  # 5% of 10 SOL portfolio
            "min_investment_per_token": 0.1,  # 1% of portfolio
            "max_open_positions": 5,  # Diversification
            
            # Enhanced filters based on AI guide
            "MIN_LIQUIDITY": 100000.0,  # Higher liquidity requirement
            "MIN_VOLUME": 50000.0,  # Higher volume requirement
            "MIN_HOLDERS": 500,  # More holders = more stable
            "MIN_MCAP": 1000000.0,  # $1M minimum market cap
            
            # AI-driven indicators
            "use_ai_channels": True,  # From the guide
            "use_ai_momentum": True,  # From the guide
            "use_multi_layer_confirmation": True,  # From the guide
            
            # Entry conditions (more selective)
            "MIN_PRICE_CHANGE_1H": 2.0,  # Minimum 2% gain in 1 hour
            "MIN_PRICE_CHANGE_6H": 5.0,  # Minimum 5% gain in 6 hours
            "MIN_PRICE_CHANGE_24H": 10.0,  # Minimum 10% gain in 24 hours
            
            # Risk management
            "max_daily_loss": 0.2,  # Stop trading if down 20% in a day
            "max_drawdown": 0.3,  # Maximum 30% drawdown allowed
        })
        
        with open(control_file, 'w') as f:
            json.dump(control, f, indent=4)
        
        logger.info(f"Updated {control_file} with improved parameters")

if __name__ == "__main__":
    update_simulation_balance()
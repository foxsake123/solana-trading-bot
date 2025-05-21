"""
setup_real_trading.py - Script to set up real trading mode
"""
import os
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('setup_real_trading')

def setup_real_trading():
    """Set up real trading mode in the bot"""
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Define the control file path
    control_file = os.path.join(project_root, 'bot_control.json')
    
    # Check if file exists in the data directory
    data_control_file = os.path.join(project_root, 'data', 'bot_control.json')
    if os.path.exists(data_control_file) and not os.path.exists(control_file):
        control_file = data_control_file
    
    # Check if the control file exists
    if not os.path.exists(control_file):
        # Create a default control file
        control_data = {
            "running": False,  # Default to not running initially
            "simulation_mode": False,  # Set to real trading mode
            "filter_fake_tokens": True,
            "use_birdeye_api": True,
            "use_machine_learning": False,
            "take_profit_target": 15.0,
            "stop_loss_percentage": 25.0,
            "max_investment_per_token": 0.1,
            "min_investment_per_token": 0.02,
            "slippage_tolerance": 0.3,
            "MIN_SAFETY_SCORE": 15.0,
            "MIN_VOLUME": 1000.0,  # Minimum 24h volume in USD
            "MIN_LIQUIDITY": 1000.0,  # Minimum liquidity in USD
            "MIN_MCAP": 10000.0,
            "MIN_HOLDERS": 10,
            "MIN_PRICE_CHANGE_1H": 1.0,
            "MIN_PRICE_CHANGE_6H": 2.0,
            "MIN_PRICE_CHANGE_24H": 5.0
        }
    else:
        # Load existing control file
        with open(control_file, 'r') as f:
            control_data = json.load(f)
        
        # Update key settings for real trading
        control_data["simulation_mode"] = False  # Set to real trading mode
    
    # Print information
    print("=== SOLANA TRADING BOT - REAL TRADING SETUP ===")
    print("This script will configure your bot for real trading.")
    print("WARNING: Real trading involves financial risk.")
    
    # Confirm with user
    if sys.stdin.isatty():  # Only ask for confirmation in interactive mode
        if 'WALLET_PRIVATE_KEY' not in os.environ:
            print("\nWARNING: WALLET_PRIVATE_KEY environment variable not set.")
            print("You need to set this for real trading to work.")
            set_key = input("Would you like to set it now? (y/n): ")
            if set_key.lower() == 'y':
                private_key = input("Enter your wallet private key: ")
                os.environ['WALLET_PRIVATE_KEY'] = private_key
                
                # Update .env file if it exists
                env_file = os.path.join(project_root, '.env')
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        env_content = f.read()
                    
                    # Check if WALLET_PRIVATE_KEY already exists in .env
                    if 'WALLET_PRIVATE_KEY=' in env_content:
                        # Replace existing key
                        import re
                        env_content = re.sub(
                            r'WALLET_PRIVATE_KEY=.*',
                            f'WALLET_PRIVATE_KEY={private_key}',
                            env_content
                        )
                    else:
                        # Add key to end of file
                        env_content += f'\nWALLET_PRIVATE_KEY={private_key}\n'
                    
                    # Write updated .env file
                    with open(env_file, 'w') as f:
                        f.write(env_content)
                    
                    print("Updated .env file with private key.")
                else:
                    # Create new .env file
                    with open(env_file, 'w') as f:
                        f.write(f'WALLET_PRIVATE_KEY={private_key}\n')
                    
                    print("Created .env file with private key.")
    
    # Configure trading parameters
    print("\n== Trading Parameters ==")
    print("Configure how much you want to invest per trade and your profit/loss targets.")
    
    if sys.stdin.isatty():  # Only ask for input in interactive mode
        # Max investment per token
        max_investment = input(f"Maximum investment per token in SOL (current: {control_data['max_investment_per_token']}): ")
        if max_investment.strip():
            try:
                control_data['max_investment_per_token'] = float(max_investment)
            except ValueError:
                print("Invalid value. Using current setting.")
        
        # Take profit
        take_profit = input(f"Take profit percentage (current: {control_data['take_profit_target']}%): ")
        if take_profit.strip():
            try:
                control_data['take_profit_target'] = float(take_profit)
            except ValueError:
                print("Invalid value. Using current setting.")
        
        # Stop loss
        stop_loss = input(f"Stop loss percentage (current: {control_data['stop_loss_percentage']}%): ")
        if stop_loss.strip():
            try:
                control_data['stop_loss_percentage'] = float(stop_loss)
            except ValueError:
                print("Invalid value. Using current setting.")
        
        # Token filtering
        print("\n== Token Filtering ==")
        print("Higher minimum values = less risk but fewer trading opportunities")
        
        # Min liquidity
        min_liquidity = input(f"Minimum liquidity in USD (current: ${control_data['MIN_LIQUIDITY']}): ")
        if min_liquidity.strip():
            try:
                control_data['MIN_LIQUIDITY'] = float(min_liquidity)
            except ValueError:
                print("Invalid value. Using current setting.")
        
        # Min 24h volume
        min_volume = input(f"Minimum 24h volume in USD (current: ${control_data['MIN_VOLUME']}): ")
        if min_volume.strip():
            try:
                control_data['MIN_VOLUME'] = float(min_volume)
            except ValueError:
                print("Invalid value. Using current setting.")
    
    # Save the updated control file
    with open(control_file, 'w') as f:
        json.dump(control_data, f, indent=4)
    
    print("Settings saved to", control_file)
    print("\nREMINDER: The bot is set to 'not running'. To start it:")
    print("1. Verify all settings in bot_control.json")
    print("2. Set 'running': true when you're ready to begin")
    print("3. Run 'python main.py' to start the bot")

if __name__ == "__main__":
    setup_real_trading()

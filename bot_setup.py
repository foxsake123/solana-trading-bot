"""
Setup script for configuring real trading with the Solana Trading Bot
"""
import os
import sys
import json
import logging
from getpass import getpass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('real_trade_setup')

def check_env_file():
    """Check if .env file exists and has the required variables"""
    env_file = '.env'
    
    # Required variables
    required_vars = [
        'WALLET_PRIVATE_KEY',
        'SOLANA_RPC_ENDPOINT'
    ]
    
    # Check if file exists
    if not os.path.exists(env_file):
        logger.warning(f"{env_file} file not found")
        create_env = input("Would you like to create a .env file? (y/n): ")
        
        if create_env.lower() == 'y':
            with open(env_file, 'w') as f:
                f.write("# Solana Trading Bot Configuration\n\n")
                
                # Get wallet private key
                wallet_key = getpass("Enter your wallet private key (input will be hidden): ")
                f.write(f"WALLET_PRIVATE_KEY='{wallet_key}'\n")
                
                # Get RPC endpoint
                rpc_endpoint = input("Enter Solana RPC endpoint (press Enter for default): ")
                if not rpc_endpoint:
                    rpc_endpoint = "https://api.mainnet-beta.solana.com"
                f.write(f"SOLANA_RPC_ENDPOINT='{rpc_endpoint}'\n")
                
                logger.info(f"Created {env_file} file")
                return True
        else:
            logger.warning("Skipping .env file creation")
            return False
    else:
        # Check if required variables exist
        with open(env_file, 'r') as f:
            content = f.read()
            
        missing_vars = []
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"Missing variables in {env_file}: {', '.join(missing_vars)}")
            update_env = input("Would you like to update the .env file? (y/n): ")
            
            if update_env.lower() == 'y':
                with open(env_file, 'a') as f:
                    f.write("\n# Added by setup script\n")
                    
                    for var in missing_vars:
                        if var == 'WALLET_PRIVATE_KEY':
                            wallet_key = getpass("Enter your wallet private key (input will be hidden): ")
                            f.write(f"WALLET_PRIVATE_KEY='{wallet_key}'\n")
                        elif var == 'SOLANA_RPC_ENDPOINT':
                            rpc_endpoint = input("Enter Solana RPC endpoint (press Enter for default): ")
                            if not rpc_endpoint:
                                rpc_endpoint = "https://api.mainnet-beta.solana.com"
                            f.write(f"SOLANA_RPC_ENDPOINT='{rpc_endpoint}'\n")
                
                logger.info(f"Updated {env_file} file")
                return True
            else:
                logger.warning("Skipping .env file update")
                return False
        else:
            logger.info(f"{env_file} file exists and has the required variables")
            return True

def update_bot_control():
    """Update the bot control file for real trading"""
    control_files = [
        'data/bot_control.json',
        'bot_control.json'
    ]
    
    # Find the control file
    control_file = None
    for file in control_files:
        if os.path.exists(file):
            control_file = file
            break
    
    if not control_file:
        logger.warning("Bot control file not found")
        create_control = input("Would you like to create a bot_control.json file? (y/n): ")
        
        if create_control.lower() == 'y':
            control_file = 'data/bot_control.json'
            os.makedirs(os.path.dirname(control_file), exist_ok=True)
            
            # Default settings for real trading
            settings = {
                "running": True,
                "simulation_mode": False,
                "filter_fake_tokens": True,
                "use_birdeye_api": True,
                "use_machine_learning": False,
                "take_profit_target": 0.15,  # 15%
                "stop_loss_percentage": 0.25,  # 25%
                "max_investment_per_token": 0.05,  # 0.05 SOL
                "min_investment_per_token": 0.01,  # 0.01 SOL
                "slippage_tolerance": 0.3,  # 30%
                "MIN_SAFETY_SCORE": 50.0,
                "MIN_VOLUME": 10000.0,
                "MIN_LIQUIDITY": 10000.0,
                "MIN_MCAP": 50000.0,
                "MIN_HOLDERS": 50,
                "MIN_PRICE_CHANGE_1H": 1.0,
                "MIN_PRICE_CHANGE_6H": 2.0,
                "MIN_PRICE_CHANGE_24H": 5.0
            }
            
            # Write the file
            with open(control_file, 'w') as f:
                json.dump(settings, f, indent=4)
                
            logger.info(f"Created {control_file} with real trading settings")
            return settings
        else:
            logger.warning("Skipping control file creation")
            return None
    else:
        # Load the existing file
        with open(control_file, 'r') as f:
            settings = json.load(f)
        
        # Ask if user wants to update to real trading settings
        update_control = input("Would you like to update the bot control file for real trading? (y/n): ")
        
        if update_control.lower() == 'y':
            # Update key settings for real trading
            settings['simulation_mode'] = False
            
            # Get custom settings
            max_investment = input("Enter maximum investment per token in SOL (default: 0.05): ")
            if max_investment:
                settings['max_investment_per_token'] = float(max_investment)
            else:
                settings['max_investment_per_token'] = 0.05
            
            min_investment = input("Enter minimum investment per token in SOL (default: 0.01): ")
            if min_investment:
                settings['min_investment_per_token'] = float(min_investment)
            else:
                settings['min_investment_per_token'] = 0.01
            
            take_profit = input("Enter take profit percentage (default: 15): ")
            if take_profit:
                settings['take_profit_target'] = float(take_profit) / 100  # Convert to decimal
            else:
                settings['take_profit_target'] = 0.15
            
            stop_loss = input("Enter stop loss percentage (default: 25): ")
            if stop_loss:
                settings['stop_loss_percentage'] = float(stop_loss) / 100  # Convert to decimal
            else:
                settings['stop_loss_percentage'] = 0.25
            
            # Update safety settings
            settings['MIN_SAFETY_SCORE'] = 50.0
            settings['MIN_VOLUME'] = 10000.0
            settings['MIN_LIQUIDITY'] = 10000.0
            
            # Write the updated settings
            with open(control_file, 'w') as f:
                json.dump(settings, f, indent=4)
                
            logger.info(f"Updated {control_file} with real trading settings")
            return settings
        else:
            logger.info("Keeping existing bot control settings")
            return settings

def main():
    """Main setup function"""
    print("\n=======================================")
    print("   Solana Trading Bot - Real Trading Setup")
    print("=======================================\n")
    
    print("This script will configure your bot for real trading on the Solana blockchain.")
    print("IMPORTANT: Real trading involves real funds. Use at your own risk!")
    print("Start with small amounts and monitor the bot's behavior carefully.\n")
    
    # Confirm setup
    confirm = input("Do you want to proceed with setting up real trading? (y/n): ")
    if confirm.lower() != 'y':
        print("Setup cancelled.")
        return
    
    # Check requirements
    print("\nChecking requirements...\n")
    
    # Check .env file
    env_ok = check_env_file()
    
    # Update bot control
    settings = update_bot_control()
    
    if env_ok and settings is not None:
        print("\n=======================================")
        print("   Setup completed successfully!")
        print("=======================================\n")
        
        print("Real trading settings:")
        print(f"- Simulation Mode: {'Enabled' if settings['simulation_mode'] else 'Disabled'}")
        print(f"- Min Investment: {settings['min_investment_per_token']} SOL")
        print(f"- Max Investment: {settings['max_investment_per_token']} SOL")
        print(f"- Take Profit: {settings['take_profit_target'] * 100}%")
        print(f"- Stop Loss: {settings['stop_loss_percentage'] * 100}%")
        
        print("\nTo start the bot with real trading, run:")
        print("python run_bot_updated.py")
        
        print("\nTo monitor trades, run the dashboard:")
        print("python dashboard.py")
        
        print("\nTo verify real trades on the blockchain:")
        print("python real_trade_verifier.py")
    else:
        print("\nSetup incomplete. Please fix the issues and try again.")

if __name__ == "__main__":
    main()

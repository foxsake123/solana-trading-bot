#!/usr/bin/env python
"""
Solana Trading Bot - Dependency Installer
This script installs all required dependencies for the Solana Trading Bot
including the packages needed for real trading mode.
"""

import subprocess
import sys
import os
import platform

def check_python_version():
    """Check Python version is 3.8+"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required.")
        print(f"Current version: {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"✅ Python version {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected.")

def check_pip():
    """Check pip is installed"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, capture_output=True)
        print("✅ pip is installed.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pip is not installed.")
        print("Please install pip before continuing.")
        return False

def install_packages():
    """Install required packages"""
    base_packages = [
        "tweepy",
        "aiohttp",
        "asyncio",
        "pandas",
        "streamlit",
        "plotly",
        "python-dotenv",
        "vaderSentiment",
        "scikit-learn"
    ]
    
    # Packages required for real trading mode
    solana_packages = [
        "solana",
        "solders",
        "spl-token",
        "base58"
    ]
    
    # Install base packages
    print("\n📦 Installing base packages...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", *base_packages, "--upgrade"
        ], check=True)
        print("✅ Base packages installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing base packages: {e}")
        return False
    
    # Install Solana packages
    print("\n📦 Installing Solana blockchain packages...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", *solana_packages, "--upgrade"
        ], check=True)
        print("✅ Solana packages installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing Solana packages: {e}")
        print("⚠️ Real trading mode will not work without these packages.")
        print("You can still use simulation mode.")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and has required keys"""
    env_exists = os.path.exists('.env')
    if not env_exists:
        print("\n⚠️ No .env file found. Creating template .env file...")
        with open('.env', 'w') as f:
            f.write("""# API Keys
TWITTER_BEARER_TOKEN=
SOLANA_RPC_ENDPOINT=https://api.mainnet-beta.solana.com
WALLET_PRIVATE_KEY=
DEXSCREENER_BASE_URL=https://api.dexscreener.com
JUPITER_QUOTE_API=https://quote-api.jup.ag/v6/quote
JUPITER_SWAP_API=https://quote-api.jup.ag/v6/swap

# Trading Parameters
MAX_BUY_RETRIES=3
MAX_SELL_RETRIES=3
SLIPPAGE_TOLERANCE=0.30
TAKE_PROFIT_TARGET=15.0
STOP_LOSS_PERCENTAGE=0.25
MOONBAG_PERCENTAGE=0.15
MAX_INVESTMENT_PER_TOKEN=1.0
MIN_SAFETY_SCORE=50
MIN_VOLUME_24H=10
SCAN_INTERVAL=300
""")
        print("✅ Created template .env file. Please edit it with your API keys and wallet information.")
    else:
        # Check if file contains required keys for real trading
        with open('.env', 'r') as f:
            content = f.read()
            if 'WALLET_PRIVATE_KEY=' in content and 'WALLET_PRIVATE_KEY=\n' not in content:
                print("✅ Found wallet private key in .env file.")
            else:
                print("⚠️ No wallet private key found in .env file.")
                print("   Real trading mode requires a wallet private key.")
                
            if 'SOLANA_RPC_ENDPOINT=' in content and 'SOLANA_RPC_ENDPOINT=\n' not in content:
                print("✅ Found Solana RPC endpoint in .env file.")
            else:
                print("⚠️ No Solana RPC endpoint found in .env file.")
                print("   Real trading mode requires a Solana RPC endpoint.")

def create_directories():
    """Create required directories"""
    directories = ['data', 'logs']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created {directory} directory.")
        else:
            print(f"✅ {directory} directory already exists.")

def check_bot_control():
    """Check if bot_control.json exists"""
    control_path = os.path.join('data', 'bot_control.json')
    if not os.path.exists(control_path):
        print("⚠️ bot_control.json file not found. It will be created on first run.")
    else:
        print("✅ bot_control.json file found.")

def main():
    """Main installation function"""
    banner = """
    ╔══════════════════════════════════════════════════╗
    ║        SOLANA MEMECOIN TRADING BOT SETUP         ║
    ╚══════════════════════════════════════════════════╝
    """
    print(banner)
    
    print("🔍 Checking system requirements...")
    check_python_version()
    if not check_pip():
        return
    
    create_directories()
    check_env_file()
    check_bot_control()
    
    if install_packages():
        print("\n✅ All dependencies installed successfully!")
    else:
        print("\n⚠️ Some dependencies could not be installed.")
        print("   Please check the errors above and try to resolve them.")
    
    print("\n🚀 Setup complete! You can now run the bot with:")
    print("   1. Simulation mode: python main.py")
    print("   2. Dashboard: streamlit run enhanced_dashboard.py")
    print("\n⚠️ IMPORTANT: Before switching to real trading mode:")
    print("   1. Make sure your wallet has SOL for trades and gas fees")
    print("   2. Set MAX_INVESTMENT_PER_TOKEN to a small value for testing (0.01 SOL)")
    print("   3. Test thoroughly in simulation mode first")

if __name__ == "__main__":
    main()

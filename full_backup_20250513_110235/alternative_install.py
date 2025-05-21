#!/usr/bin/env python
"""
Solana Trading Bot - Alternative Installation
This script installs compatible versions of Solana packages.
"""

import subprocess
import sys
import os
import platform

def install_individual_packages():
    """Install packages individually with specific versions"""
    print("🔧 Installing Solana packages individually with specific versions...")
    
    packages = [
        "base58==2.1.1",                # For base58 encoding/decoding
        "construct==2.10.68",           # Required dependency
        "typing-extensions>=4.3.0",     # Required dependency
        "solders==0.19.0",              # Solana data structures
        "solana==0.30.2",               # Main Solana package
    ]
    
    success = True
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}")
            print(f"Error: {e.stderr}")
            success = False
    
    return success

def modify_solana_trader():
    """Update solana_trader.py to handle missing imports gracefully"""
    file_path = 'solana_trader.py'
    if not os.path.exists(file_path):
        print("⚠️ Could not find solana_trader.py to update.")
        return False
    
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Check if we already modified the file
        if "# Modified imports for compatibility" in content:
            print("✅ solana_trader.py already updated.")
            return True
        
        # Modify the imports section
        new_imports = """import os
import time
import random
import logging
import asyncio
from datetime import datetime, timedelta, timezone

# Import your configuration
from config import BotConfiguration

# Modified imports for compatibility
REAL_TRADING_AVAILABLE = False
try:
    # Try to import Solana packages
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    import base58
    REAL_TRADING_AVAILABLE = True
except ImportError:
    # If imports fail, we'll run in simulation mode only
    logging.warning("Solana packages not available. Real trading mode will not work.")
    logging.warning("The bot will run in simulation mode only.")

# Set up logging
logger = logging.getLogger(__name__)
"""
        
        # Replace the import section
        import_end = content.find("# Set up logging")
        if import_end == -1:
            import_end = content.find("class SolanaTrader:")
        
        if import_end == -1:
            print("⚠️ Could not locate where to insert imports in solana_trader.py")
            return False
            
        modified_content = new_imports + content[import_end + len("# Set up logging"):]
        
        # Also modify the __init__ method to check REAL_TRADING_AVAILABLE
        init_section = """    def __init__(self, db, simulation_mode=True):
        """
        enhanced_init = """    def __init__(self, db, simulation_mode=True):
        # Force simulation mode if real trading packages aren't available
        if not REAL_TRADING_AVAILABLE and not simulation_mode:
            logger.warning("Forcing simulation mode as Solana packages are not available")
            simulation_mode = True
            
        """
        
        modified_content = modified_content.replace(init_section, enhanced_init)
        
        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.write(modified_content)
            
        print("✅ Updated solana_trader.py to handle missing imports gracefully.")
        return True
        
    except Exception as e:
        print(f"❌ Error updating solana_trader.py: {e}")
        return False

def alternative_installation():
    """Try an alternative installation method"""
    print("🔄 Trying alternative installation method...")
    
    # Create requirements file
    req_file = "requirements_solana.txt"
    if not os.path.exists(req_file):
        print("Creating requirements file...")
        with open(req_file, "w") as f:
            f.write("""solana==0.30.2
solders==0.19.0
base58==2.1.1
construct==2.10.68
typing-extensions>=4.3.0
""")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file],
            check=True
        )
        print("✅ Installed Solana packages via requirements file")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install via requirements file: {e}")
        return False

def main():
    """Main function"""
    banner = """
    ╔═════════════════════════════════════════════════════╗
    ║        SOLANA PACKAGE ALTERNATIVE INSTALLATION      ║
    ╚═════════════════════════════════════════════════════╝
    """
    print(banner)
    
    print("🔍 Checking Python version...")
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Python version: {py_version}")
    
    # First try individual package installation
    if install_individual_packages():
        print("\n✅ Successfully installed Solana packages individually.")
    else:
        # If that fails, try the requirements file method
        print("\n⚠️ Individual installation failed, trying alternative method...")
        if alternative_installation():
            print("\n✅ Successfully installed Solana packages via requirements file.")
        else:
            print("\n❌ Failed to install Solana packages.")
            print("\n⚠️ The bot will run in simulation mode only.")
    
    # Update the solana_trader.py file to handle missing imports
    modify_solana_trader()
    
    print("\n🚀 Installation complete!")
    print("You can now run the bot in simulation mode with: python main.py")
    print("And the dashboard with: streamlit run enhanced_dashboard.py")
    print("\nIf the Solana packages were successfully installed, you can try real trading mode.")
    print("If not, the bot will automatically use simulation mode only.")

if __name__ == "__main__":
    main()

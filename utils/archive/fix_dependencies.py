#!/usr/bin/env python
"""
Solana Trading Bot - Dependency Fixer
This script installs the correct Solana packages required for real trading.
"""

import subprocess
import sys
import os

def install_solana_packages():
    """Install the correct Solana packages"""
    print("🔧 Installing Solana packages with corrected dependencies...")
    
    # The correct packages to install
    packages = [
        "solana-py",       # Contains SPL token functionality
        "solders",         # Rust-based Solana data structures
        "anchorpy",        # For Anchor program interactions (optional)
        "base58"           # For base58 encoding/decoding
    ]
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", *packages, "--upgrade"
        ], check=True)
        print("✅ Solana packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing Solana packages: {e}")
        return False

def check_installation():
    """Verify that the packages are working correctly"""
    print("\n🔍 Verifying installation...")
    
    try:
        # Try to import key modules to verify installation
        print("Importing solana...")
        import solana
        print(f"✅ solana-py installed (version: {solana.__version__})")
        
        print("Importing solders...")
        import solders
        print(f"✅ solders installed (version: {solders.__version__})")
        
        print("Importing base58...")
        import base58
        print(f"✅ base58 installed")
        
        # Test key modules specifically needed for real trading
        print("\nTesting key modules...")
        
        print("Importing Keypair from solders...")
        from solders.keypair import Keypair
        print("✅ Can import Keypair")
        
        print("Importing AsyncClient from solana.rpc...")
        from solana.rpc.async_api import AsyncClient
        print("✅ Can import AsyncClient")
        
        print("Creating a test keypair...")
        keypair = Keypair.new_keypair()
        print(f"✅ Successfully created test keypair: {keypair.pubkey()}")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing Solana packages: {e}")
        return False

def main():
    """Main function"""
    banner = """
    ╔══════════════════════════════════════════════════╗
    ║        SOLANA PACKAGE INSTALLATION FIX           ║
    ╚══════════════════════════════════════════════════╝
    """
    print(banner)
    
    if install_solana_packages():
        if check_installation():
            print("\n✅ All Solana packages installed and working correctly!")
            print("\n🚀 You can now use real trading mode!")
        else:
            print("\n⚠️ Installation issues detected. Try restarting your environment.")
    else:
        print("\n❌ Failed to install Solana packages.")
        print("   Make sure you have an internet connection and try again.")

if __name__ == "__main__":
    main()

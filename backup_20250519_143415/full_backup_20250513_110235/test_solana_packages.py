#!/usr/bin/env python
"""
Updated test script to verify if Solana packages are properly installed
with proper keypair creation method for newer versions
"""

import sys
import os

def test_solana_imports():
    """Test if required Solana modules can be imported"""
    print("Testing Solana package imports...")
    
    # Track missing packages
    missing_packages = []
    
    # Test solders package
    try:
        print("Importing solders.pubkey.Pubkey...", end="")
        from solders.pubkey import Pubkey
        print(" ✅")
        
        print("Importing solders.keypair.Keypair...", end="")
        from solders.keypair import Keypair
        print(" ✅")
    except ImportError as e:
        print(f" ❌ Error: {e}")
        missing_packages.append("solders")
    
    # Test solana package
    try:
        print("Importing solana.rpc.async_api.AsyncClient...", end="")
        from solana.rpc.async_api import AsyncClient
        print(" ✅")
    except ImportError as e:
        print(f" ❌ Error: {e}")
        missing_packages.append("solana")
    
    # Test base58 package
    try:
        print("Importing base58...", end="")
        import base58
        print(" ✅")
    except ImportError as e:
        print(f" ❌ Error: {e}")
        missing_packages.append("base58")
    
    return missing_packages

def test_keypair_creation():
    """Test if we can create a Solana keypair"""
    print("\nTesting keypair creation...")
    
    try:
        from solders.keypair import Keypair
        
        # Try different methods of creating keypair based on version
        try:
            # First try new method in newer versions
            keypair = Keypair()
            method_used = "Keypair()"
        except:
            try:
                # Try another common method
                keypair = Keypair.new()
                method_used = "Keypair.new()"
            except:
                try:
                    # Try another possible method
                    from solders.keypair import new_keypair
                    keypair = new_keypair()
                    method_used = "new_keypair()"
                except:
                    # Try yet another possible method (older versions)
                    keypair = Keypair.random()
                    method_used = "Keypair.random()"
        
        # Print details about the keypair
        pubkey = keypair.pubkey()
        print(f"Successfully created keypair with method: {method_used}")
        print(f"Public key: {pubkey}")
        return True
    except Exception as e:
        print(f"❌ Failed to create keypair: {e}")
        
        # Print more diagnostic info
        print("\nLet's see what methods are available on Keypair:")
        from solders.keypair import Keypair
        methods = [method for method in dir(Keypair) if not method.startswith('_')]
        print(f"Available methods: {methods}")
        
        return False

def test_rpc_connection():
    """Test if we can create an RPC client connection"""
    print("\nTesting RPC client creation...")
    
    try:
        from solana.rpc.async_api import AsyncClient
        client = AsyncClient("https://api.mainnet-beta.solana.com")
        print("Successfully created RPC client")
        return True
    except Exception as e:
        print(f"❌ Failed to create RPC client: {e}")
        return False

def check_dot_env():
    """Check if .env file contains necessary keys for real trading"""
    print("\nChecking .env file configuration...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False
    
    with open('.env', 'r') as f:
        content = f.read()
    
    wallet_key = 'WALLET_PRIVATE_KEY=' in content and not 'WALLET_PRIVATE_KEY=' + os.linesep in content
    rpc_endpoint = 'SOLANA_RPC_ENDPOINT=' in content and not 'SOLANA_RPC_ENDPOINT=' + os.linesep in content
    
    if wallet_key:
        print("✅ WALLET_PRIVATE_KEY found in .env")
    else:
        print("❌ WALLET_PRIVATE_KEY not found or empty in .env")
    
    if rpc_endpoint:
        print("✅ SOLANA_RPC_ENDPOINT found in .env")
    else:
        print("❌ SOLANA_RPC_ENDPOINT not found or empty in .env")
    
    return wallet_key and rpc_endpoint

def main():
    """Main test function"""
    print("\n" + "="*50)
    print("SOLANA REAL TRADING MODE TEST")
    print("="*50 + "\n")
    
    # Test package imports
    missing_packages = test_solana_imports()
    
    if missing_packages:
        print("\n❌ Some required packages are missing:", ", ".join(missing_packages))
        print("Real trading mode will NOT work.")
        return False
    
    # Test keypair creation
    keypair_ok = test_keypair_creation()
    
    # Test RPC connection
    rpc_ok = test_rpc_connection()
    
    # Check .env configuration
    env_ok = check_dot_env()
    
    # Overall result
    print("\n" + "="*50)
    if keypair_ok and rpc_ok and env_ok:
        print("✅ SUCCESS: All tests passed! Real trading mode should work.")
        return True
    else:
        print("❌ FAILED: Some tests failed. Real trading mode might not work properly.")
        if not keypair_ok:
            print("  - Could not create a keypair")
        if not rpc_ok:
            print("  - Could not create an RPC client")
        if not env_ok:
            print("  - .env file is not properly configured")
        return False

if __name__ == "__main__":
    main()

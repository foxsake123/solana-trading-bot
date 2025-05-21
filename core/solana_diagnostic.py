#!/usr/bin/env python
"""
Diagnostic script to check Solana SDK and keypair implementations
"""

import sys
import logging
import inspect
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_package_version(package_name):
    """Get the version of an installed package"""
    try:
        import importlib.metadata
        try:
            version = importlib.metadata.version(package_name)
            return version
        except importlib.metadata.PackageNotFoundError:
            return "Not installed"
    except ImportError:
        # Fallback for Python < 3.8
        try:
            import pkg_resources
            return pkg_resources.get_distribution(package_name).version
        except:
            return "Unknown"

def inspect_module(module):
    """Inspect a module and print its attributes and methods"""
    logger.info(f"Inspecting module: {module.__name__}")
    
    # Get all public attributes/methods
    items = [item for item in dir(module) if not item.startswith('_')]
    
    # Filter classes and functions
    classes = []
    functions = []
    
    for item_name in items:
        try:
            item = getattr(module, item_name)
            if inspect.isclass(item):
                classes.append(item_name)
            elif inspect.isfunction(item):
                functions.append(item_name)
        except:
            pass
    
    logger.info(f"Classes: {', '.join(classes)}")
    logger.info(f"Functions: {', '.join(functions)}")
    
    return classes, functions

def inspect_class(cls):
    """Inspect a class and print its methods"""
    logger.info(f"Inspecting class: {cls.__name__}")
    
    # Get all public methods
    methods = [m for m in dir(cls) if not m.startswith('_') and callable(getattr(cls, m))]
    
    class_methods = []
    instance_methods = []
    
    # Try to determine if they're class or instance methods
    for method_name in methods:
        try:
            method = getattr(cls, method_name)
            if isinstance(method, classmethod) or isinstance(method, staticmethod):
                class_methods.append(method_name)
            else:
                instance_methods.append(method_name)
        except:
            instance_methods.append(method_name)
    
    logger.info(f"Class methods: {', '.join(class_methods)}")
    logger.info(f"Instance methods: {', '.join(instance_methods)}")
    
    return methods

def test_keypair_creation():
    """Test different ways to create a Solana keypair"""
    logger.info("Testing Solana keypair creation methods")
    
    try:
        from solders.keypair import Keypair
        
        # Test method 1: Simple constructor
        try:
            logger.info("Testing Keypair() constructor...")
            keypair = Keypair()
            pubkey = keypair.pubkey()
            logger.info(f"✅ Success! Public key: {pubkey}")
            
            # Try to access private key
            try:
                # Get the seed or secret directly if available
                if hasattr(keypair, 'seed'):
                    logger.info("Keypair has 'seed' attribute")
                    private_bytes = keypair.seed()
                elif hasattr(keypair, 'secret'):
                    logger.info("Keypair has 'secret' attribute")
                    private_bytes = keypair.secret()
                else:
                    # Try accessing as bytes
                    logger.info("Trying bytes(keypair)")
                    all_bytes = bytes(keypair)
                    logger.info(f"Total bytes: {len(all_bytes)}")
                    
                    # First 32 bytes should be private key
                    private_bytes = all_bytes[:32]
                
                if private_bytes:
                    # Show first few bytes
                    logger.info(f"Private key starts with: {private_bytes[:8].hex()}")
                    
                    # Test creating from these bytes
                    try:
                        logger.info("Testing recreation from private bytes...")
                        methods_to_try = [
                            ('from_bytes', lambda: Keypair.from_bytes(private_bytes)),
                            ('from_seed', lambda: Keypair.from_seed(private_bytes)),
                            ('direct constructor', lambda: Keypair(private_bytes))
                        ]
                        
                        for method_name, method_func in methods_to_try:
                            try:
                                logger.info(f"Trying {method_name}...")
                                kp = method_func()
                                pk = kp.pubkey()
                                logger.info(f"✅ {method_name} worked! Pubkey: {pk}")
                            except Exception as e:
                                logger.info(f"❌ {method_name} failed: {e}")
                            
                    except Exception as e:
                        logger.error(f"Error during recreation tests: {e}")
                
            except Exception as e:
                logger.error(f"Could not access private key: {e}")
            
        except Exception as e:
            logger.error(f"Keypair() constructor failed: {e}")
        
        # Return the Keypair class for further inspection
        return Keypair
        
    except ImportError as e:
        logger.error(f"Could not import Keypair: {e}")
        return None

if __name__ == "__main__":
    logger.info("============= SOLANA SDK DIAGNOSTIC =============")
    
    # Check package versions
    packages = ['solana', 'solders', 'base58', 'nacl']
    logger.info("Checking installed packages:")
    for package in packages:
        version = check_package_version(package)
        logger.info(f"  - {package}: {version}")
    
    # Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Test Solana keypair
    keypair_class = test_keypair_creation()
    
    if keypair_class:
        # Inspect the Keypair class
        methods = inspect_class(keypair_class)
        
        # Try to import and inspect key modules
        try:
            import solders
            solders_classes, _ = inspect_module(solders)
            
            if 'pubkey' in solders_classes:
                import solders.pubkey
                inspect_module(solders.pubkey)
        except ImportError as e:
            logger.error(f"Error importing solders: {e}")
        
        try:
            import solana
            inspect_module(solana)
            
            import solana.rpc
            inspect_module(solana.rpc)
            
            import solana.rpc.async_api
            inspect_module(solana.rpc.async_api)
        except ImportError as e:
            logger.error(f"Error importing solana: {e}")
    
    logger.info("=================================================")
    logger.info("Diagnostic complete!")

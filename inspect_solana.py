import solana
import inspect
import os

# Print information about the package
print(f"Solana version: {solana.__version__ if hasattr(solana, '__version__') else 'Unknown'}")
print(f"Solana package path: {os.path.dirname(inspect.getfile(solana))}")

# List all modules and submodules
print("\nAvailable modules in solana package:")
for item in dir(solana):
    if not item.startswith('__'):
        print(f"- {item}")

# Try to find PublicKey class
print("\nLooking for PublicKey class:")
if hasattr(solana, 'publickey'):
    print("publickey module exists")
    from solana import publickey
    if hasattr(publickey, 'PublicKey'):
        print("PublicKey class exists in publickey module")
    else:
        print("publickey module exists but PublicKey class not found")
else:
    print("publickey module not found")

# Look for alternative modules that might have the functionality
print("\nExploring other modules:")
if hasattr(solana, 'keypair'):
    print("keypair module exists")
    try:
        from solana.keypair import Keypair
        print("Keypair class exists in keypair module")
    except ImportError as e:
        print(f"Error importing Keypair: {e}")

# Check if solders package is installed (it's a dependency with similar functionality)
try:
    import solders
    print("\nSolders package found:")
    print(f"Solders path: {os.path.dirname(inspect.getfile(solders))}")
    print("Available modules in solders:")
    for item in dir(solders):
        if not item.startswith('__'):
            print(f"- {item}")
except ImportError:
    print("\nSolders package not found")
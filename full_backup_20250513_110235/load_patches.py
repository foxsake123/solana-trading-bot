
# load_patches.py - Script to load patches before running main.py
import sys
import os
import importlib
import subprocess

print("Loading patches...")

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add patches directory to Python path
patches_dir = os.path.join(current_dir, 'patches')
if os.path.exists(patches_dir) and patches_dir not in sys.path:
    sys.path.insert(0, patches_dir)

# Try to load patches
try:
    import patches
    print("Patches loaded successfully")
except ImportError:
    print("Warning: patches directory not found, some features may not work correctly")
except Exception as e:
    print(f"Error loading patches: {e}")

# Now run the main script
print("Starting main.py...")
try:
    # Run in the same process
    import main
    
    # If main has a main() function, call it
    if hasattr(main, 'main'):
        main.main()
except Exception as e:
    print(f"Error running main.py: {e}")
    sys.exit(1)

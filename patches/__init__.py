
# patch_loader.py - Load all patches
import logging
import sys
import os
import importlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('patch_loader')

def load_patches():
    """Load all patches from the patches directory"""
    # Get the patches directory path
    patches_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add patches directory to Python path
    if patches_dir not in sys.path:
        sys.path.insert(0, patches_dir)
    
    # List of patches to load
    patches = [
        'database_patch',
        'token_analyzer_patch'
    ]
    
    # Load each patch
    for patch in patches:
        try:
            importlib.import_module(patch)
            logger.info(f"Loaded patch: {patch}")
        except ImportError as e:
            logger.error(f"Could not import patch {patch}: {e}")
        except Exception as e:
            logger.error(f"Error loading patch {patch}: {e}")
    
    print("Patch loading complete")
    return True

# Load patches when imported
load_patches()

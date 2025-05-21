# combined_fix.py - Combined fix for both database and token_analyzer issues

import os
import sys
import logging
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('combined_fix')

def create_patches_dir():
    """Create a directory for storing patch modules"""
    patches_dir = 'patches'
    os.makedirs(patches_dir, exist_ok=True)
    return patches_dir

def create_database_patch(patches_dir):
    """Create a runtime patch for Database class"""
    patch_code = '''
# Database patch module - Adds missing save_token method
import logging
import sys
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('patch.database')

# Define the UTC timezone constant
UTC = timezone.utc

# Define save_token function to add to Database class
def save_token(self, token_data=None, **kwargs):
    """
    Save token information to the database (patched)
    
    :param token_data: Dictionary containing token data
    :param kwargs: Individual token attributes as keyword arguments
    :return: True if operation successful, False otherwise
    """
    # Check if store_token exists and use it (might be the actual method name)
    if hasattr(self, 'store_token'):
        return self.store_token(token_data, **kwargs)
    
    # Otherwise implement save_token directly
    try:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        
        try:
            cursor = conn.cursor()
            
            # Handle both dictionary and keyword arguments
            if token_data is None:
                token_data = kwargs
            elif kwargs:
                # If both are provided, merge them with kwargs taking precedence
                merged_data = token_data.copy()
                merged_data.update(kwargs)
                token_data = merged_data
            
            # Check if contract_address is present
            if 'contract_address' not in token_data:
                logger.error("Missing required field: contract_address")
                return False
                
            # Set last_updated timestamp if not provided
            if 'last_updated' not in token_data:
                token_data['last_updated'] = datetime.now(UTC).isoformat()
            
            # Get column names from tokens table
            cursor.execute("PRAGMA table_info(tokens)")
            columns = [info[1] for info in cursor.fetchall()]
            
            # Filter token_data to include only valid columns
            filtered_data = {k: v for k, v in token_data.items() if k in columns}
            
            # Prepare SQL command
            placeholders = ', '.join(['?'] * len(filtered_data))
            columns_str = ', '.join(filtered_data.keys())
            values = list(filtered_data.values())
            
            # Use INSERT OR REPLACE to handle both insert and update
            cursor.execute(f"""
            INSERT OR REPLACE INTO tokens ({columns_str})
            VALUES ({placeholders})
            """, values)
            
            conn.commit()
            return True
                
        except Exception as e:
            logger.error(f"Error saving token data for {token_data.get('contract_address', 'unknown')}: {e}")
            return False
                
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Critical error in save_token patch: {e}")
        return False

# Apply patches to Database class
def patch_database():
    try:
        # First try to import the Database class
        from database import Database
        
        # Add save_token method if it doesn't exist
        if not hasattr(Database, 'save_token'):
            Database.save_token = save_token
            logger.info("Added save_token method to Database class")
            return True
        else:
            logger.info("Database class already has save_token method")
            return True
    except Exception as e:
        logger.error(f"Failed to patch Database class: {e}")
        return False

# Apply the patch when this module is imported
success = patch_database()
if success:
    print("Database patch applied successfully - save_token method is now available")
else:
    print("Failed to apply Database patch")
'''
    
    patch_file = os.path.join(patches_dir, 'database_patch.py')
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    logger.info(f"Created database patch at {patch_file}")
    return patch_file

def create_token_analyzer_patch(patches_dir):
    """Create a runtime patch for TokenAnalyzer"""
    patch_code = '''
# TokenAnalyzer patch module - Adds safe token saving functionality
import logging
import sys
import asyncio

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('patch.token_analyzer')

# Define safe_save_token method for TokenAnalyzer
def safe_save_token(self, token_data):
    """
    Safely save token data to the database
    
    :param token_data: Token data dictionary
    :return: True if successful, False otherwise
    """
    if self.db is None:
        return False
        
    # Try store_token first (might be the actual method name)
    if hasattr(self.db, 'store_token'):
        try:
            return self.db.store_token(token_data)
        except Exception as e:
            logger.error(f"Error using store_token for {token_data.get('contract_address', 'unknown')}: {e}")
    
    # Try save_token if available
    if hasattr(self.db, 'save_token'):
        try:
            return self.db.save_token(token_data)
        except Exception as e:
            logger.error(f"Error using save_token for {token_data.get('contract_address', 'unknown')}: {e}")
    
    # If neither method is available, log a warning
    logger.warning(f"No method available to save token {token_data.get('contract_address', 'unknown')}")
    return False

# Apply patches to TokenAnalyzer class
def patch_token_analyzer():
    try:
        # First try to import TokenAnalyzer
        from token_analyzer import TokenAnalyzer
        
        # Add safe_save_token method
        TokenAnalyzer.safe_save_token = safe_save_token
        
        # Patch fetch_token_data method if it exists
        if hasattr(TokenAnalyzer, 'fetch_token_data'):
            original_fetch_token_data = TokenAnalyzer.fetch_token_data
            
            async def patched_fetch_token_data(self, contract_address):
                """Patched version that uses safe_save_token"""
                # Call the original method
                result = await original_fetch_token_data(self, contract_address)
                
                # Replace any direct call to save_token with safe_save_token
                try:
                    if self.db and result:
                        # Manually call safe_save_token after fetch
                        self.safe_save_token(result)
                except Exception as e:
                    logger.error(f"Error in patched fetch_token_data: {e}")
                
                return result
            
            # Apply the patched method
            TokenAnalyzer.fetch_token_data = patched_fetch_token_data
            
        logger.info("Applied patches to TokenAnalyzer class")
        return True
    except Exception as e:
        logger.error(f"Failed to patch TokenAnalyzer class: {e}")
        return False

# Apply the patch when this module is imported
success = patch_token_analyzer()
if success:
    print("TokenAnalyzer patch applied successfully - safe_save_token method is now available")
else:
    print("Failed to apply TokenAnalyzer patch")
'''
    
    patch_file = os.path.join(patches_dir, 'token_analyzer_patch.py')
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    logger.info(f"Created token_analyzer patch at {patch_file}")
    return patch_file

def create_main_patch(patches_dir):
    """Create a main patch loader"""
    patch_code = '''
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
'''
    
    patch_file = os.path.join(patches_dir, '__init__.py')
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    logger.info(f"Created patch loader at {patch_file}")
    return patch_file

def create_main_patch_loader():
    """Create a patch loader for main.py"""
    patch_code = '''
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
'''
    
    patch_file = 'load_patches.py'
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    logger.info(f"Created main patch loader at {patch_file}")
    return patch_file

def backup_files():
    """Create backups of key files"""
    files_to_backup = [
        'database.py',
        'token_analyzer.py',
        'main.py'
    ]
    
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    for file in files_to_backup:
        if os.path.exists(file):
            backup_path = os.path.join(backup_dir, f"{file}.bak")
            try:
                shutil.copy2(file, backup_path)
                logger.info(f"Created backup of {file} at {backup_path}")
            except Exception as e:
                logger.error(f"Failed to backup {file}: {e}")

def main():
    print("=" * 60)
    print("COMBINED FIX - Database and TokenAnalyzer issues")
    print("=" * 60)
    print()
    
    print("1. Creating backups of key files...")
    backup_files()
    print()
    
    print("2. Creating patches directory and patch modules...")
    patches_dir = create_patches_dir()
    create_database_patch(patches_dir)
    create_token_analyzer_patch(patches_dir)
    create_main_patch(patches_dir)
    print()
    
    print("3. Creating main patch loader...")
    create_main_patch_loader()
    print()
    
    print("=" * 60)
    print("FIX COMPLETE!")
    print("=" * 60)
    print()
    print("To run your bot with the patches applied, use:")
    print("python load_patches.py")
    print()
    print("This will load all the necessary patches before running your main.py script.")
    print("The patches will fix the missing save_token method and ensure token data is saved correctly.")
    print()
    print("Alternatively, you can add this line at the top of your main.py:")
    print("import patches  # Load all patches")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()

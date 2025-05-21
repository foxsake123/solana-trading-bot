
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

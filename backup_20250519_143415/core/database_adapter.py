"""
Database initializer for core/main.py compatibility
"""
import os
import logging
import sys

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Configure logging
logger = logging.getLogger(__name__)

# Try to import your existing Database class
try:
    from database import Database
except ImportError as e:
    logger.error(f"Failed to import Database class: {e}")
    
    # Define a simple placeholder if import fails
    class Database:
        def __init__(self, db_path='data/sol_bot.db'):
            logger.warning("Using placeholder Database class")
            self.db_path = db_path
            
        def _initialize_db(self):
            logger.info("Placeholder database initialization")
            return True

# Create a global database instance
_db_instance = None

def init_database():
    """
    Initialize the database
    This function provides compatibility with main.py's expected interface
    """
    global _db_instance
    
    try:
        logger.info("Initializing database")
        
        # Create Database instance if it doesn't exist
        if _db_instance is None:
            _db_instance = Database()
            
        # Call the initialization method
        if hasattr(_db_instance, '_initialize_db'):
            _db_instance._initialize_db()
            
        logger.info("Database tables initialized")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def get_db():
    """
    Get the database instance
    
    :return: Database instance
    """
    global _db_instance
    
    if _db_instance is None:
        init_database()
        
    return _db_instance
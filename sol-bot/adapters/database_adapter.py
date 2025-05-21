# Create the database adapter file
$databaseAdapterContent = @"
"""
Database adapter module for compatibility
"""

try:
    from sol-bot.database.database import Database
except ImportError:
    try:
        from database.database import Database
    except ImportError:
        try:
            from ..database.database import Database
        except ImportError:
            from database import Database

# This adapter provides backward compatibility for scripts
__all__ = ['Database']

# Simple proxy class
class DatabaseAdapter:
    def __init__(self, db_instance=None):
        """
        Initialize the database adapter
        
        :param db_instance: Optional existing database instance
        """
        if db_instance:
            self.db = db_instance
        else:
            self.db = Database()
            
    def __getattr__(self, name):
        """Forward all method calls to the underlying database"""
        return getattr(self.db, name)
"@

$databaseAdapterContent | Set-Content -Path sol-bot\adapters\database_adapter.py
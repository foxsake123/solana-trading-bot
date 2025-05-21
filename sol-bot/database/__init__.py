"""
Database adapter to bridge between old and new database imports
"""

from database.database import Database as OriginalDatabase

class Database(OriginalDatabase):
    """
    Database adapter that inherits from the original Database class
    """
    def __init__(self, db_path='data/sol_bot.db'):
        super().__init__(db_path)

# Export the Database class
__all__ = ['Database']

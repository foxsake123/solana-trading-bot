"""
Database adapter module for compatibility
"""

from database.database import Database

# This adapter provides backward compatibility for scripts 
# that import Database from database_adapter
__all__ = ['Database']

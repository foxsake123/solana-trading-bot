"""
Fixed database adapter for compatibility with both simplified and original database implementations
"""
import os
import logging
from datetime import datetime, timezone

# Set up logging
logger = logging.getLogger('database_adapter')

class DatabaseAdapter:
    """
    Adapter class that wraps the Database class and provides compatibility methods
    """
    
    def __init__(self, db):
        """
        Initialize the adapter with the original database instance
        
        :param db: Original Database instance
        """
        self.db = db
        logger.info("Initialized database adapter")
        
    def save_token(self, token_data):
        """
        Save token to database using compatible method
        
        :param token_data: Token data dictionary
        :return: Result of save operation
        """
        try:
            # First try store_token method which is in database.py
            if hasattr(self.db, 'store_token'):
                return self.db.store_token(token_data)
            # Try save_token method as fallback
            elif hasattr(self.db, 'save_token'):
                return self.db.save_token(token_data)
            else:
                # Log available methods for debugging
                methods = [method for method in dir(self.db) 
                         if callable(getattr(self.db, method)) and not method.startswith('_')]
                
                logger.info(f"Available database methods: {methods}")
                
                # If neither method is available, try other common method names
                if hasattr(self.db, 'add_token'):
                    return self.db.add_token(token_data)
                else:
                    logger.error("No compatible method found to save token")
                    return False
        except Exception as e:
            logger.error(f"Error saving token: {e}")
            return False
    
    def record_trade(self, contract_address, action, amount, price, tx_hash=None, is_simulation=True):
        """
        Record a trade in the database using compatible method
        
        :param contract_address: Token contract address
        :param action: Trade action (BUY/SELL)
        :param amount: Trade amount in SOL
        :param price: Token price in SOL
        :param tx_hash: Transaction hash (optional)
        :param is_simulation: Whether this is a simulation trade (removed from actual call)
        :return: Result of record operation
        """
        try:
            # Call the record_trade method but omit is_simulation if not supported
            if hasattr(self.db, 'record_trade'):
                import inspect
                sig = inspect.signature(self.db.record_trade)
                params = sig.parameters
                
                # Check if 'is_simulation' is a parameter
                if 'is_simulation' in params:
                    # Method accepts is_simulation parameter
                    return self.db.record_trade(
                        contract_address=contract_address,
                        action=action,
                        amount=amount,
                        price=price,
                        tx_hash=tx_hash,
                        is_simulation=is_simulation
                    )
                else:
                    # Method doesn't accept is_simulation parameter, so omit it
                    return self.db.record_trade(
                        contract_address=contract_address,
                        action=action,
                        amount=amount,
                        price=price,
                        tx_hash=tx_hash
                    )
            else:
                logger.error("No record_trade method found in database")
                return False
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            return False
    
    def get_active_orders(self):
        """
        Get active orders from the database
        
        :return: Active orders from the database
        """
        try:
            if hasattr(self.db, 'get_active_orders'):
                return self.db.get_active_orders()
            else:
                logger.error("No get_active_orders method found in database")
                return []
        except Exception as e:
            logger.error(f"Error getting active orders: {e}")
            return []
    
    def __getattr__(self, name):
        """
        Forward any other method calls to the underlying database object
        
        :param name: Method name
        :return: Method from the database object
        """
        if hasattr(self.db, name):
            return getattr(self.db, name)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


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

"""
TokenScannerWrapper: Adapts the token scanner to work with the trading bot
"""
import logging
import time
import threading
from typing import Any, Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

class TokenScannerWrapper:
    """
    Wrapper for any token scanner that adapts it to the interface expected by the TradingBot
    """
    def __init__(self, token_scanner, processing_callback=None, interval_seconds=60):
        """
        Initialize the wrapper with the token scanner and optional callback
        
        Args:
            token_scanner: The token scanner instance to wrap
            processing_callback: Callback function to call with discovered tokens
            interval_seconds: How often to run the scanner in seconds
        """
        self.token_scanner = token_scanner
        self.processing_callback = processing_callback
        self.interval_seconds = interval_seconds
        self.running = False
        self.scan_thread = None
        self.last_tokens = []
        
        # Logging scanner capabilities
        self._log_scanner_capabilities()
    
    def _log_scanner_capabilities(self):
        """Log available methods on the token scanner"""
        methods = [method for method in dir(self.token_scanner) 
                  if callable(getattr(self.token_scanner, method)) and not method.startswith('_')]
        logger.info(f"TokenScanner has the following methods:")
        for method in methods:
            logger.info(f"- {method}")
    
    def start(self):
        """Start the token scanner in a background thread"""
        logger.info("Starting token scanner wrapper")
        if self.running:
            logger.warning("Token scanner already running")
            return
            
        self.running = True
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        logger.info("Token scanner wrapper started successfully")
    
    def stop(self):
        """Stop the token scanner"""
        logger.info("Stopping token scanner wrapper")
        self.running = False
        if self.scan_thread:
            self.scan_thread.join(timeout=5)
        logger.info("Token scanner wrapper stopped")
    
    def _scan_loop(self):
        """Background thread that periodically scans for tokens"""
        logger.info("Token scanner loop starting")
        
        while self.running:
            try:
                self._perform_scan()
            except Exception as e:
                logger.error(f"Error in token scanner loop: {str(e)}", exc_info=True)
                
            # Sleep until next scan
            time.sleep(self.interval_seconds)
    
    def _perform_scan(self):
        """Perform a single scan for tokens"""
        tokens = []
        
        # Try different methods depending on what's available
        if hasattr(self.token_scanner, 'start_scanning'):
            logger.info("Using start_scanning method")
            tokens = self.token_scanner.start_scanning()
        elif hasattr(self.token_scanner, 'get_trending_tokens'):
            logger.info("Using get_trending_tokens method")
            tokens = self.token_scanner.get_trending_tokens()
        elif hasattr(self.token_scanner, 'get_top_gainers'):
            logger.info("Using get_top_gainers method for 1h")
            tokens = self.token_scanner.get_top_gainers(timeframe='1h')
            
        if not tokens and hasattr(self.token_scanner, 'get_top_gainers'):
            # Fallback to 24h gainers if no tokens found
            logger.info("Falling back to 24h top gainers")
            tokens = self.token_scanner.get_top_gainers(timeframe='24h')
            
        # Process the tokens
        if tokens:
            logger.info(f"Found {len(tokens)} tokens to process")
            self.last_tokens = tokens
            
            if self.processing_callback:
                self.processing_callback(tokens)
            
            return tokens
        else:
            logger.warning("No tokens found by scanner")
            return []

    def get_latest_tokens(self):
        """Return the most recently discovered tokens"""
        return self.last_tokens

"""
Trading parameters module for Solana trading bot
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TradingParameters:
    """
    Trading parameters for the Solana trading bot
    """
    # Default parameters
    DEFAULT_PARAMS = {
        # Trading Amounts
        "initial_investment_sol": 0.05,       # SOL amount for initial trades
        "max_investment_per_token_sol": 0.1,  # Maximum SOL to invest in a single token
        "min_liquidity_usd": 50000,           # Minimum liquidity in USD
        "max_slippage_percent": 2.5,          # Maximum acceptable slippage
        
        # Entry/Exit Conditions
        "buy_volume_threshold_usd": 1000,     # Minimum 24h volume
        "min_price_change_percent": 3.0,      # Minimum price change to consider buying
        "take_profit_percent": 15.0,          # Take profit threshold  
        "stop_loss_percent": -7.5,            # Stop loss threshold
        "trailing_stop_percent": 5.0,         # Trailing stop percentage
        
        # Risk Management
        "max_concurrent_trades": 3,           # Maximum number of concurrent trades
        "max_daily_trades": 10,               # Maximum number of trades per day
        "max_daily_loss_percent": 5.0,        # Maximum daily loss as percentage of portfolio
        
        # Token Evaluation Parameters
        "min_security_score": 6.0,            # Minimum security score (0-10)
        "require_liquidity_locked": False,    # Require liquidity to be locked
        
        # Time-based Parameters
        "minimum_token_age_hours": 1,         # Minimum token age in hours
        "maximum_hold_time_hours": 24,        # Maximum time to hold a token
        "monitor_interval_seconds": 60,       # Time between position checks
        
        # Scanner Parameters
        "scanner_interval_seconds": 60,       # Time between token scans
        "prefer_trending_tokens": True,       # Prioritize trending tokens
        
        # Advanced Options
        "enable_trailing_stop": True,         # Enable trailing stop
        "enable_automatic_reinvestment": True, # Auto-reinvest profits
        "max_trades_per_token": 1,           # Maximum number of trades per token
    }
    
    def __init__(self, user_params: Optional[Dict[str, Any]] = None):
        """
        Initialize trading parameters with defaults, overridden by user parameters
        
        Args:
            user_params: User-specified parameters to override defaults
        """
        # Start with default parameters
        self.params = self.DEFAULT_PARAMS.copy()
        
        # Override with user parameters if provided
        if user_params:
            for key, value in user_params.items():
                if key in self.params:
                    self.params[key] = value
                else:
                    logger.warning(f"Unknown parameter: {key}")
        
        # Log the parameters
        self._log_parameters()
    
    def _log_parameters(self):
        """Log the current parameters"""
        logger.info("Trading parameters:")
        for key, value in self.params.items():
            logger.info(f"  {key}: {value}")
    
    def get(self, key: str, default=None) -> Any:
        """
        Get a parameter value
        
        Args:
            key: Parameter name
            default: Default value if parameter doesn't exist
            
        Returns:
            Parameter value or default
        """
        return self.params.get(key, default)
    
    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update parameters with new values
        
        Args:
            updates: Dictionary of parameter updates
        """
        for key, value in updates.items():
            if key in self.params:
                self.params[key] = value
                logger.info(f"Updated parameter {key} to {value}")
            else:
                logger.warning(f"Ignoring unknown parameter: {key}")
        
        # Log updated parameters
        self._log_parameters()
    
    def validate(self) -> bool:
        """
        Validate that parameters are within acceptable ranges
        
        Returns:
            True if parameters are valid, False otherwise
        """
        # Validation rules
        validations = [
            self.params["initial_investment_sol"] > 0,
            self.params["max_investment_per_token_sol"] >= self.params["initial_investment_sol"],
            self.params["min_liquidity_usd"] > 0,
            self.params["max_slippage_percent"] > 0,
            self.params["buy_volume_threshold_usd"] > 0,
            self.params["min_price_change_percent"] > 0,
            self.params["take_profit_percent"] > 0,
            self.params["stop_loss_percent"] < 0,
            self.params["max_concurrent_trades"] > 0,
            self.params["max_daily_trades"] > 0,
            self.params["max_daily_loss_percent"] > 0,
            self.params["min_security_score"] >= 0 and self.params["min_security_score"] <= 10,
            self.params["minimum_token_age_hours"] >= 0,
            self.params["maximum_hold_time_hours"] > 0,
            self.params["monitor_interval_seconds"] > 0,
            self.params["scanner_interval_seconds"] > 0,
        ]
        
        is_valid = all(validations)
        
        if not is_valid:
            logger.error("Parameter validation failed")
            # Log which validations failed
            for i, validation in enumerate(validations):
                if not validation:
                    logger.error(f"Validation {i} failed")
        
        return is_valid

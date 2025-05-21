"""
Jupiter client implementation for Solana token swaps
"""
import logging
import traceback
import time
import requests

logger = logging.getLogger(__name__)

class JupiterClient:
    """
    Client for Jupiter Aggregator API
    """
    def __init__(self, version="v6"):
        """Initialize the Jupiter client"""
        self.base_url = f"https://quote-api.jup.ag/{version}"
        self.quote_endpoint = f"{self.base_url}/quote"
        self.swap_endpoint = f"{self.base_url}/swap"
    
    async def get_quote(self, input_mint, output_mint, amount, slippage=0.5):
        """
        Get a quote for a token swap
        
        :param input_mint: Input token mint address
        :param output_mint: Output token mint address
        :param amount: Amount in input token (in smallest units)
        :param slippage: Slippage tolerance in percentage
        :return: Quote response
        """
        try:
            # Build query parameters
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),  # Convert to string to avoid formatting issues
                "slippageBps": int(slippage * 100)  # Convert to basis points
            }
            
            logger.info(f"Getting Jupiter quote: {input_mint} → {output_mint}, amount: {amount}, slippage: {slippage}%")
            
            # Send request
            response = requests.get(self.quote_endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                # Try to extract quote details for logging
                try:
                    in_amount = data.get('inAmount', '0')
                    out_amount = data.get('outAmount', '0')
                    price_impact = data.get('priceImpactPct', '0')
                    
                    # Convert price_impact to float for formatting if it's a string
                    if isinstance(price_impact, str) and price_impact:
                        price_impact = float(price_impact)
                    else:
                        price_impact = 0.0
                        
                    logger.info(f"Quote received: {in_amount} → {out_amount} (impact: {price_impact:.2f}%)")
                except Exception as e:
                    logger.error(f"Error parsing quote response: {e}")
                    logger.error(traceback.format_exc())
                
                return data
            
            logger.warning(f"Failed to get Jupiter quote: {response.text}")
            return None
        
        except Exception as e:
            logger.error(f"Error getting Jupiter quote: {e}")
            logger.error(traceback.format_exc())
            return None
    
    async def prepare_swap_transaction(self, quote, user_public_key):
        """
        Prepare a swap transaction
        
        :param quote: Quote response from get_quote
        :param user_public_key: User's public key
        :return: Swap transaction data
        """
        try:
            # Build payload
            payload = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "wrapUnwrapSOL": True
            }
            
            # Send request
            response = requests.post(self.swap_endpoint, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            
            logger.warning(f"Failed to prepare Jupiter swap: {response.text}")
            return None
        
        except Exception as e:
            logger.error(f"Error preparing Jupiter swap: {e}")
            return None
    
    async def execute_swap(self, swap_transaction, keypair, rpc_endpoint):
        """
        Execute a swap transaction
        
        :param swap_transaction: Swap transaction data from prepare_swap_transaction
        :param keypair: User's keypair
        :param rpc_endpoint: RPC endpoint
        :return: Transaction signature or None on failure
        """
        # This is where you would implement the actual transaction signing and sending
        # For now, just return a simulated signature
        return f"SIMULATED_SWAP_TX_{int(time.time())}"
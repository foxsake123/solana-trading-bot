"""
fix_jupiter.py - Fix Jupiter API integration in solders_adapter.py
"""
import os
import re
import logging
import traceback
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('fix_jupiter')

def fix_jupiter_api():
    """Fix the Jupiter API integration in solders_adapter.py"""
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Add the project root and core directory to the Python path
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    core_dir = os.path.join(project_root, 'core')
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    
    # Check all possible locations of solders_adapter.py
    locations = [
        os.path.join(core_dir, 'solders_adapter.py'),
        os.path.join(project_root, 'solders_adapter.py'),
    ]
    
    # Try to find the file
    adapter_file = None
    for location in locations:
        if os.path.exists(location):
            adapter_file = location
            break
    
    if not adapter_file:
        logger.error("Could not find solders_adapter.py")
        return False
    
    logger.info(f"Found solders_adapter.py at {adapter_file}")
    
    # Read the file
    with open(adapter_file, 'r') as f:
        content = f.read()
    
    # Check if the file contains the buggy code
    problem_pattern = r'logger\.info\(f"Quote received: \{in_amount\} → \{out_amount\} \(impact: \{price_impact:\.2f\}%\)"\)'
    
    # Create a backup of the file
    backup_file = adapter_file + '.bak'
    with open(backup_file, 'w') as f:
        f.write(content)
    logger.info(f"Created backup at {backup_file}")

    if re.search(problem_pattern, content):
        # Replace the problematic line
        fixed_content = re.sub(
            problem_pattern,
            'logger.info(f"Quote received: {in_amount} → {out_amount} (impact: {float(price_impact):.2f}%)")',
            content
        )
        
        # Write the fixed file
        with open(adapter_file, 'w') as f:
            f.write(fixed_content)
        
        logger.info(f"Fixed Jupiter API integration in {adapter_file}")
        return True
    else:
        logger.info(f"Could not find the line to fix in {adapter_file}")
        
        # Check if the JupiterClient class exists in the file
        if 'class JupiterClient' in content:
            # Prepare the Jupiter client fix
            jupiter_fix = """
class JupiterClient:
    \"\"\"
    Client for Jupiter Aggregator API
    \"\"\"
    def __init__(self, version="v6"):
        \"\"\"Initialize the Jupiter client\"\"\"
        self.base_url = f"https://quote-api.jup.ag/{version}"
        self.quote_endpoint = f"{self.base_url}/quote"
        self.swap_endpoint = f"{self.base_url}/swap"
    
    async def get_quote(self, input_mint, output_mint, amount, slippage=0.5):
        \"\"\"
        Get a quote for a token swap
        
        :param input_mint: Input token mint address
        :param output_mint: Output token mint address
        :param amount: Amount in input token (in smallest units)
        :param slippage: Slippage tolerance in percentage
        :return: Quote response
        \"\"\"
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
            import requests
            import traceback
            
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
        \"\"\"
        Prepare a swap transaction
        
        :param quote: Quote response from get_quote
        :param user_public_key: User's public key
        :return: Swap transaction data
        \"\"\"
        try:
            # Build payload
            payload = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "wrapUnwrapSOL": True
            }
            
            # Send request
            import requests
            response = requests.post(self.swap_endpoint, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            
            logger.warning(f"Failed to prepare Jupiter swap: {response.text}")
            return None
        
        except Exception as e:
            logger.error(f"Error preparing Jupiter swap: {e}")
            return None
    
    async def execute_swap(self, swap_transaction, keypair, rpc_endpoint):
        \"\"\"
        Execute a swap transaction
        
        :param swap_transaction: Swap transaction data from prepare_swap_transaction
        :param keypair: User's keypair
        :param rpc_endpoint: RPC endpoint
        :return: Transaction signature or None on failure
        \"\"\"
        # This is where you would implement the actual transaction signing and sending
        # For now, just return a simulated signature
        import time
        return f"SIMULATED_SWAP_TX_{int(time.time())}"
"""
            
            # Create the fixed file with corrected JupiterClient
            pattern = r'class JupiterClient:.*?def execute_swap\([^)]*\):.*?return f"SIMULATED_SWAP_TX_\{int\(time\.time\(\)\)}"'
            fixed_content = re.sub(pattern, jupiter_fix.strip(), content, flags=re.DOTALL)
            
            # Write the fixed file
            with open(adapter_file, 'w') as f:
                f.write(fixed_content)
            
            logger.info(f"Replaced JupiterClient class in {adapter_file}")
            return True
        else:
            logger.warning("JupiterClient class not found in the file")
            
            # Create a new JupiterClient implementation file
            fixed_jupiter_file = os.path.join(core_dir, 'jupiter_client.py')
            with open(fixed_jupiter_file, 'w') as f:
                f.write("""\"\"\"
Jupiter client implementation for Solana token swaps
\"\"\"
import logging
import traceback
import time
import requests

logger = logging.getLogger(__name__)

class JupiterClient:
    \"\"\"
    Client for Jupiter Aggregator API
    \"\"\"
    def __init__(self, version="v6"):
        \"\"\"Initialize the Jupiter client\"\"\"
        self.base_url = f"https://quote-api.jup.ag/{version}"
        self.quote_endpoint = f"{self.base_url}/quote"
        self.swap_endpoint = f"{self.base_url}/swap"
    
    async def get_quote(self, input_mint, output_mint, amount, slippage=0.5):
        \"\"\"
        Get a quote for a token swap
        
        :param input_mint: Input token mint address
        :param output_mint: Output token mint address
        :param amount: Amount in input token (in smallest units)
        :param slippage: Slippage tolerance in percentage
        :return: Quote response
        \"\"\"
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
        \"\"\"
        Prepare a swap transaction
        
        :param quote: Quote response from get_quote
        :param user_public_key: User's public key
        :return: Swap transaction data
        \"\"\"
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
        \"\"\"
        Execute a swap transaction
        
        :param swap_transaction: Swap transaction data from prepare_swap_transaction
        :param keypair: User's keypair
        :param rpc_endpoint: RPC endpoint
        :return: Transaction signature or None on failure
        \"\"\"
        # This is where you would implement the actual transaction signing and sending
        # For now, just return a simulated signature
        return f"SIMULATED_SWAP_TX_{int(time.time())}"
""")
            logger.info(f"Created jupiter_client.py at {fixed_jupiter_file}")
            
            return True

if __name__ == "__main__":
    fix_jupiter_api()

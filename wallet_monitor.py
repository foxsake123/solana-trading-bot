"""
Real Wallet Monitor for Dashboard
Safe implementation that shows balance without exposing private keys
"""
import os
import requests
import json
from solana.rpc.api import Client
from solders.pubkey import Pubkey
import logging

logger = logging.getLogger('wallet_monitor')

class WalletMonitor:
    def __init__(self):
        self.rpc_endpoint = self._get_rpc_endpoint()
        self.wallet_address = self._get_wallet_address()
        
    def _get_rpc_endpoint(self):
        """Get RPC endpoint from env or use default"""
        # Try from environment
        endpoint = os.getenv('SOLANA_RPC_ENDPOINT')
        
        # Try from .env file
        if not endpoint and os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('SOLANA_RPC_ENDPOINT='):
                        endpoint = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
        
        # Default
        return endpoint or "https://api.mainnet-beta.solana.com"
    
    def _get_wallet_address(self):
        """Get wallet address from env (safely, without exposing private key)"""
        # For your specific wallet
        # This is safe to hardcode as it's a public address
        return "16um9NG9V88CWR9vESe42WfmNrDcTNq9jUit5t5mpgf"
    
    def get_balance(self):
        """Get wallet balance in SOL"""
        try:
            # Method 1: Try using solana-py
            try:
                from solana.rpc.api import Client
                client = Client(self.rpc_endpoint)
                
                pubkey = Pubkey.from_string(self.wallet_address)
                response = client.get_balance(pubkey)
                
                if response.value is not None:
                    balance_lamports = response.value
                    balance_sol = balance_lamports / 1_000_000_000
                    return balance_sol
            except:
                pass
            
            # Method 2: Direct RPC call
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [self.wallet_address]
            }
            
            response = requests.post(
                self.rpc_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'value' in data['result']:
                    balance_lamports = data['result']['value']
                    balance_sol = balance_lamports / 1_000_000_000
                    return balance_sol
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return None
    
    def get_transaction_history(self, limit=10):
        """Get recent transactions for the wallet"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    self.wallet_address,
                    {"limit": limit}
                ]
            }
            
            response = requests.post(
                self.rpc_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return data['result']
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []
    
    def calculate_pl(self, starting_balance=2.0):
        """Calculate P&L based on current balance"""
        current_balance = self.get_balance()
        
        if current_balance is None:
            return None
        
        pl_sol = current_balance - starting_balance
        pl_percentage = ((current_balance / starting_balance) - 1) * 100
        
        return {
            'starting_balance': starting_balance,
            'current_balance': current_balance,
            'pl_sol': pl_sol,
            'pl_percentage': pl_percentage
        }

# Global instance
wallet_monitor = WalletMonitor()

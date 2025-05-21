import re

file_path = 'core/solana_trader.py'

# Read the file
with open(file_path, 'r') as file:
    content = file.read()

# Fix 1: Update _initialize_wallet method
initialize_wallet_pattern = r'def _initialize_wallet\(self\):.*?self\.wallet_address = "ERROR_INITIALIZING_WALLET"'
initialize_wallet_replacement = '''def _initialize_wallet(self):
    """Initialize the Solana wallet using the private key"""
    if not wallet_initialized:
        logger.warning("Solana libraries not available, wallet initialization skipped")
        self.wallet_address = "SIMULATED_WALLET_ADDRESS"
        return
            
    try:
        # Import the Keypair from solders_adapter
        from solders_adapter import Keypair
        
        # Determine the format of the private key
        if len(self.private_key) == 64:  # Hex string
            logger.info("Processing private key as hex string")
            private_key_bytes = bytes.fromhex(self.private_key)
            logger.info("Attempting to create keypair using seed method")
            self.keypair = create_keypair_from_secret(self.private_key)
        elif len(self.private_key) == 88:  # Base58 encoded
            logger.info("Processing private key as base58 string")
            private_key_bytes = base58.b58decode(self.private_key)
            self.keypair = create_keypair_from_secret(self.private_key)
        else:
            logger.error("Invalid private key format")
            self.keypair = None
            return
                
        # Get the wallet address
        self.wallet_address = str(self.keypair.pubkey())
        logger.info(f"Wallet address: {self.wallet_address}")
    except Exception as e:
        logger.error(f"Error initializing wallet: {e}")
        self.keypair = None
        self.wallet_address = "ERROR_INITIALIZING_WALLET"'''

# Fix 2: Update connect method
connect_pattern = r'async def connect\(self\):.*?logger\.error\(f"Error connecting to Solana network: {e}"\)'
connect_replacement = '''async def connect(self):
    """Connect to the Solana network"""
    if not wallet_initialized:
        logger.warning("Solana libraries not available, using simulated connection")
        self.client = "SIMULATED_CLIENT"
        return
            
    try:
        # Import AsyncClient from the adapter
        from solders_adapter import AsyncClient
        
        # Create the RPC client with reasonable timeout
        endpoint = self.rpc_endpoint or "https://api.mainnet-beta.solana.com"
        self.client = AsyncClient(endpoint, timeout=30)
        
        # Test the connection with a simple request
        response = await self.client.is_connected()
        if response:
            logger.info(f"Connected to Solana network via {endpoint}")
        else:
            logger.error(f"Failed to connect to Solana network via {endpoint}")
    except Exception as e:
        logger.error(f"Error connecting to Solana network: {e}")'''

# Apply the fixes using regular expressions with DOTALL flag to match across lines
content = re.sub(initialize_wallet_pattern, initialize_wallet_replacement, content, flags=re.DOTALL)
content = re.sub(connect_pattern, connect_replacement, content, flags=re.DOTALL)

# Write the changes back to the file
with open(file_path, 'w') as file:
    file.write(content)

print("Fixed Keypair and AsyncClient references in solana_trader.py successfully!")
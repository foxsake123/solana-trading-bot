from solders.keypair import Keypair
from solders.pubkey import Pubkey

# Your base58 private key
base58_key='RU4qNP5oQqHWvgyZ5rsToThPYsZZUU2uK44pS4YrjnytkXM4j9vTzN1XbpB2QjNJjjTePk9ohTRfc7sJJsm98x2'

try:
    # Create a Keypair from the base58 private key
    keypair = Keypair.from_base58_string(base58_key)
    
    # Get the private key in bytes and convert to hexadecimal
    private_key_hex = keypair.secret().hex()
    
    # Print the hexadecimal private key
    print(f"Hexadecimal private key: {private_key_hex}")
    
    # Print the public key for reference
    print(f"Public key: {keypair.pubkey()}")
except Exception as e:
    print(f"Error: {e}")

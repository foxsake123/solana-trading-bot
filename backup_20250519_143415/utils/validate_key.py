from solders.keypair import Keypair

private_key = '8e9af7d7469f4b39aa253a6cc9f8f796f69139daef337be59de5c43f070f10a86bf82753a459a3e40fe8fcbf39d17ef38176a6b52208f5f4a459e5db29c33bdf'
try:
    keypair = Keypair.from_bytes(bytes.fromhex(private_key))
    print(f"Public key: {keypair.pubkey()}")
except Exception as e:
    print(f"Error: {e}")
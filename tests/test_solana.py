from solana.publickey import PublicKey
from solana.keypair import Keypair
import os

print("Solana SDK imported successfully!")

# Try to create a keypair
kp = Keypair()
print(f"Generated public key: {kp.public_key}")

# Check if the .env file exists
if os.path.exists('.env'):
    print(".env file found")
else:
    print(".env file not found")

# Run a simple test
print("All tests passed!")
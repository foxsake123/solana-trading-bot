import json

with open('wallet.json', 'r') as f:
    keypair = json.load(f)

private_key_hex = bytes(keypair).hex()
print(f"Hexadecimal private key: {private_key_hex}")
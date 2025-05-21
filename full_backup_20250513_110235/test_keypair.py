from solders.keypair import Keypair

private_key = '15195fae2c9395eccc39baca450d8692c2fb5fadbc8a398093b6a2ebe27bb504be7869502b4aa677a4f2687244281e506ec1643fa0473365097c864a7efeb87'
try:
    keypair = Keypair.from_bytes(bytes.fromhex(private_key))
    print(f"Public key: {keypair.pubkey()}")
except Exception as e:
    print(f"Error: {e}")
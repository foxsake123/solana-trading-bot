try:
    import solders
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    
    print("Solders imported successfully!")
    
    # Create a keypair
    kp = Keypair()
    print(f"Generated public key: {kp.pubkey()}")
    
    # Test Pubkey creation
    pubkey = Pubkey.new_unique()
    print(f"Created new public key: {pubkey}")
    
    print("All tests passed!")
except Exception as e:
    print(f"Error: {e}")
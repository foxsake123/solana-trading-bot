# check_token_scanner.py
import inspect
try:
    from core.simplified_token_scanner import TokenScanner
    
    # Check the __init__ signature
    sig = inspect.signature(TokenScanner.__init__)
    print(f"TokenScanner.__init__ signature: {sig}")
    
    # Check all methods
    print("\nTokenScanner methods:")
    for name, method in inspect.getmembers(TokenScanner, predicate=inspect.ismethod):
        if not name.startswith('_'):
            print(f"  - {name}")
            
except Exception as e:
    print(f"Error: {e}")
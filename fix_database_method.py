# fix_database_method.py
import os

def fix_token_analyzer():
    """Fix the save_token to store_token issue"""
    
    files_to_fix = ["token_analyzer.py", "core/token_analyzer.py"]
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Replace save_token with store_token
            content = content.replace('self.db.save_token(', 'self.db.store_token(')
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Fixed {file_path}")

if __name__ == "__main__":
    fix_token_analyzer()